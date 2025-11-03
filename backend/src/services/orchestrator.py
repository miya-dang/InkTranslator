# orchestator.py
import asyncio
import logging
from typing import List, Tuple, Optional, Callable
import numpy as np
import cv2
from PIL import Image

from models.schemas import TextBox, ProcessingStatus, ProcessingStage
from models.requests import TranslationRequest
from services.ocr.ocr_manager import OCRManager
from services.translate.translation_manager import TranslationManager
from services.inpaint.opencv_inpainter import OpenCVInpainter
from services.render.text_renderer import TextRenderer
from utils.exceptions import ProcessingError
from utils.image_utils import ImageUtils


class TranslationOrchestrator:
    """Orchestrates the entire manga translation pipeline"""
    
    def __init__(self):
        self.ocr_manager = OCRManager()
        self.translation_manager = TranslationManager()
        self.inpainter = OpenCVInpainter()
        self.text_renderer = TextRenderer()
        self.logger = logging.getLogger(__name__)
    
    async def process_manga_translation(
        self,
        image: np.ndarray,
        request: TranslationRequest,
        status_callback: Optional[None],
    ) -> Tuple[np.ndarray, List[TextBox]]:
        """
        Main translation pipeline
        
        Args:
            image: Input image as numpy array
            request: Translation request parameters
            status_callback: Optional callback for status updates
            
        Returns:
            Tuple of (translated_image, text_boxes)
        """
        try:
            # Initialize status
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.INITIALIZED,
                    message="Translation process started."
                ))
            
            # Step 1: OCR
            self.logger.info("Starting OCR text extraction...")
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.OCR,
                    message="Starting OCR text extraction..."
                ))
            
            text_boxes = await self._extract_text(image, request.source_language)
            
            if not text_boxes:
                raise ProcessingError("No text found in image.")
            
            self.logger.info(f"Extracted {len(text_boxes)} text boxes.")
            
            # Step 2: Translation
            self.logger.info("Starting translation...")
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.TRANSLATION,
                    message="Translating extracted text..."
                ))
            
            await self._translate_text_boxes(text_boxes, request)
            
            # Step 3: Inpainting
            self.logger.info("Starting inpainting...")
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.INPAINTING,
                    message="Removing original text from image..."
                ))
            
            inpainted_image = await self._inpaint_text_regions(image, text_boxes)
            
            # Step 4: Text Rendering
            self.logger.info("Starting text rendering...")
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.RENDERING,
                    message="Adding translated text to image..."
                ))
            
            final_image = await self._render_translated_text(
                inpainted_image, text_boxes, request
            )
            
            # Completed
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.COMPLETED,
                    message="Translation completed successfully."
                ))
            
            self.logger.info("Translation process completed successfully.")
            return final_image, text_boxes
            
        except Exception as e:
            self.logger.error(f"Translation process failed: {str(e)}.")
            if status_callback:
                status_callback(ProcessingStatus(
                    stage=ProcessingStage.ERROR,
                    message=f"Translation failed: {str(e)}."
                ))
            raise ProcessingError(f"Translation process failed: {str(e)}.")
    
    async def _extract_text(
        self, 
        image: np.ndarray, 
        source_language: str
    ) -> List[TextBox]:
        """Extract text using appropriate OCR service"""
        try:
            ocr_service = await self.ocr_manager.get_ocr_service(source_language)
            return await ocr_service.extract_text(image, source_language)
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            raise ProcessingError(f"Text extraction failed: {str(e)}")
    
    # In orchestrator.py - fix the translation method calls
    async def _translate_text_boxes(self, text_boxes: List[TextBox], request: TranslationRequest):
        """Translate all text boxes while maintaining context"""
        try:
            # Combine all text for context
            combined_text = self._combine_text_for_context(text_boxes)
            
            # Fix: Use correct method signature from translation_manager
            translated_combined = await self.translation_manager.translate(
                text=combined_text,
                from_lang=request.source_language.value,  # Use enum value
                to_lang=request.target_language.value
            )
            
            # Split translated text back to individual boxes
            self._distribute_translated_text(text_boxes, translated_combined)
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            # Fallback: keep original text
            for text_box in text_boxes:
                if not hasattr(text_box, 'translated_text') or not text_box.translated_text:
                    text_box.translated_text = text_box.text  # Fix: use 'text' not 'original_text'
                        
    def _combine_text_for_context(self, text_boxes: List[TextBox]) -> str:
        """Combine text boxes into a single text for translation with context markers"""
        # Sort text boxes by reading order
        sorted_boxes = self._sort_text_boxes_reading_order(text_boxes)
        
        # Combine with special markers to maintain separation
        combined_parts = []
        for i, text_box in enumerate(sorted_boxes):
            if text_box.text.strip():  # Fix: use 'text' not 'original_text'
                combined_parts.append(f"[{i}]{text_box.text}[/{i}]")
        
        return " ".join(combined_parts)
    
    def _sort_text_boxes_reading_order(self, text_boxes: List[TextBox]) -> List[TextBox]:
        """Sort text boxes: top to bottom first, then left-to-right or right-to-left by language"""
        
        def get_sort_key(text_box):
            # Primary sort: top to bottom (y-coordinate)
            y_pos = text_box.bbox.y1
            
            # Secondary sort: depends on detected language
            x_pos = text_box.bbox.x1
            
            # For Japanese and Chinese: right to left (negate x for reverse order)
            if (hasattr(text_box, 'language') and text_box.language in 
                ['japanese', 'trad_chinese', 'sim_chinese']):
                return (y_pos, -x_pos)  # Right to left
            else:
                return (y_pos, x_pos)   # Left to right (Korean, English, Simplified Chinese)
        
        return sorted(text_boxes, key=get_sort_key)
    
    def _distribute_translated_text(self, text_boxes: List[TextBox], translated_combined: str) -> None:
        """Distribute translated text back to individual text boxes"""
        try:
            # Extract translated parts using markers
            import re
            pattern = r'\[(\d+)\](.*?)\[/\1\]'
            matches = re.findall(pattern, translated_combined, re.DOTALL)
            
            # Create a mapping of index to translated text
            translations = {int(idx): text.strip() for idx, text in matches}
            
            # Sort boxes in the same order as combination
            sorted_boxes = self._sort_text_boxes_reading_order(text_boxes)
            
            # Assign translations
            for i, text_box in enumerate(sorted_boxes):
                if i in translations and translations[i]:
                    text_box.translated_text = translations[i]
                else:
                    # Fallback
                    text_box.translated_text = text_box.text  # Fix: use 'text'
                    
        except Exception as e:
            self.logger.error(f"Failed to distribute translated text: {str(e)}")
            # Fallback: simple splitting
            self._simple_text_distribution(text_boxes, translated_combined)
    
    def _simple_text_distribution(self, text_boxes: List[TextBox], translated_text: str) -> None:
        """Fallback method for distributing translated text"""
        sentences = translated_text.split('.')
        sentences = [s.strip() + '.' for s in sentences if s.strip()]
        
        for i, text_box in enumerate(text_boxes):
            if i < len(sentences):
                text_box.translated_text = sentences[i].strip('.')
            else:
                text_box.translated_text = text_box.text  # Fix: use 'text'
    
    async def _inpaint_text_regions(self, image: np.ndarray, text_boxes: List[TextBox]) -> np.ndarray:
        """Inpaint all text regions"""
        try:
            result_image = image.copy()
            
            for text_box in text_boxes:
                # Fix: Remove await since inpaint_textbox is not async
                result_image = self.inpainter.inpaint_textbox(result_image, text_box)
            
            return result_image
            
        except Exception as e:
            self.logger.error(f"Inpainting failed: {str(e)}")
            return image
    
    async def _render_translated_text(self, image: np.ndarray, text_boxes: List[TextBox], request: TranslationRequest) -> np.ndarray:
        """Render translated text onto the inpainted image"""
        try:
            result_image = image.copy()
            
            for text_box in text_boxes:
                if hasattr(text_box, 'translated_text') and text_box.translated_text.strip():
                    result_image = await self.text_renderer.render_text(
                        image=result_image,
                        text_box=text_box,
                        target_language=request.target_language
                        # Remove text_direction parameter - it's determined automatically
                    )
            
            return result_image
            
        except Exception as e:
            self.logger.error(f"Text rendering failed: {str(e)}")
            return image
    
    async def get_processing_preview(
        self, 
        image: np.ndarray, 
        source_language: str
    ) -> Tuple[List[TextBox], np.ndarray]:
        """
        Get a preview of detected text boxes without translation
        Useful for frontend preview
        """
        try:
            # Extract text boxes
            text_boxes = await self._extract_text(image, source_language)
            
            # Create preview image with bounding boxes
            preview_image = ImageUtils.draw_text_boxes(image, text_boxes)
            
            return text_boxes, preview_image
            
        except Exception as e:
            self.logger.error(f"Preview generation failed: {str(e)}")
            raise ProcessingError(f"Preview generation failed: {str(e)}")