# routes/routers/translation.py
import asyncio
import logging
from typing import Optional
import io
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse
from PIL import Image

from models.requests import TranslationRequest
from models.responses import (
    TranslationResultResponse,  
    TranslationStatusResponse,
)
from models.schemas import ProcessingStatus, ProcessingStage, Language
from services.orchestrator import TranslationOrchestrator
from utils.image_utils import ImageUtils
from utils.exceptions import ProcessingError

from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = TranslationOrchestrator()

# Store for processing status (in production, use Redis or similar)
processing_status = {}

# File validation constants (from settings)
MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024
ALLOWED_MIME_TYPES = settings.allowed_mime_types
ALLOWED_EXTENSIONS = settings.allowed_extensions


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file"""
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}. Got: {file.content_type}"
        )
    
    if file.filename:
        ext = '.' + file.filename.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )


def validate_image_content(contents: bytes) -> np.ndarray:
    """Validate and load image content"""
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds {settings.max_file_size_mb}MB limit"
        )
    
    try:
        image = ImageUtils.load_image_from_bytes(contents)
        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file - could not decode image data"
            )
        
        height, width = image.shape[:2]
        if width < 50 or height < 50:
            raise HTTPException(
                status_code=400,
                detail="Image too small - minimum dimensions are 50x50 pixels"
            )
        
        return image
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Image validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid image file - could not process image"
        )


@router.post("/translate", response_class=StreamingResponse)
async def translate_manga(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description=f"Image file to translate ({', '.join(ALLOWED_EXTENSIONS)}, max {settings.max_file_size_mb}MB)"),
    source_language: str = Form("japanese", description="Source language code"),
    target_language: str = Form("english", description="Target language code"),
    session_id: Optional[str] = Form(None, description="Session ID for status tracking")
):
    """Main manga translation endpoint"""
    validate_image_file(file)
    
    try:
        contents = await file.read()
        image = validate_image_content(contents)
        
        supported_langs = list(settings.font_mappings.keys())
        if source_language not in supported_langs:
            raise HTTPException(400, f"Unsupported source language: {source_language}")
        if target_language not in supported_langs:
            raise HTTPException(400, f"Unsupported target language: {target_language}")
        
        translation_request = TranslationRequest(
            source_language=source_language,
            target_language=target_language,
        )
        
        if session_id:
            processing_status[session_id] = ProcessingStatus(
                stage=ProcessingStage.INITIALIZED,
                message="Translation request received.",
            )
        
        def status_callback(status: ProcessingStatus):
            if session_id:
                processing_status[session_id] = status
        
        # Process translation
        logger.info(f"Starting translation for file: {file.filename}")
        
        translated_image, text_boxes = await orchestrator.process_manga_translation(
            image=image,
            request=translation_request,
            status_callback=status_callback if session_id else None
        )
        # Convert result to bytes with error handling
        try:
            success, buffer = cv2.imencode('.png', translated_image)
            if not success:
                raise HTTPException(500, "Failed to encode result image")
            img_bytes = io.BytesIO(buffer.tobytes())
        except Exception as e:
            logger.error(f"Image encoding error: {str(e)}")
            raise HTTPException(500, "Failed to process translated image")
        
        # Clean up status after some time
        if session_id:
            background_tasks.add_task(cleanup_status, session_id, delay=300)
        
        logger.info("Translation completed successfully")
        
        return StreamingResponse(
            img_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=translated_{file.filename}",
                "X-Text-Boxes-Count": str(len(text_boxes)),
                "Cache-Control": "no-cache"
            }
        )
    except ProcessingError as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(422, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(500, "Internal server error during translation")


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages"""
    languages = [
        {"code": "english", "name": "English", "source_only": False},
        {"code": "sim_chinese", "name": "Simplified Chinese", "source_only": False},
        {"code": "trad_chinese", "name": "Traditional Chinese", "source_only": False},
        {"code": "korean", "name": "Korean", "source_only": False},
        {"code": "japanese", "name": "Japanese", "source_only": False},
        {"code": "vietnamese", "name": "Vietnamese", "source_only": False},
    ]
    
    return {
        "languages": languages,
        "max_file_size_mb": settings.max_file_size_mb,
        "allowed_formats": settings.allowed_mime_types
    }


@router.get("/status/{session_id}", response_model=TranslationStatusResponse)
async def get_processing_status(session_id: str):
    if session_id not in processing_status:
        raise HTTPException(404, "Session not found or expired")
    status: ProcessingStatus = processing_status[session_id]
    return TranslationStatusResponse(
        job_id=session_id,
        status=status.stage.value,
        message=status.message,
        timestamp=getattr(status, "timestamp", None)
    )


async def cleanup_status(session_id: str, delay: int = 300):
    await asyncio.sleep(delay)
    if session_id in processing_status:
        del processing_status[session_id]
        logger.info(f"Cleaned up status for session: {session_id}")
