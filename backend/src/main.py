# main.py
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from routes.routers import translation, health
from config import settings
from services.ocr.ocr_manager import OCRManager
from services.translate.translation_manager import TranslationManager
from utils.exceptions import ProcessingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("manga_translation.log") if settings.log_to_file else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global services
ocr_manager = None
translation_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Manga Translation API...")
    
    try:
        # Initialize services
        global ocr_manager, translation_manager
        
        logger.info("Initializing OCR services...")
        ocr_manager = OCRManager()
        await ocr_manager.initialize()
        
        logger.info("Initializing translation services...")
        translation_manager = TranslationManager()
        await translation_manager.initialize()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Manga Translation API...")
    
    try:
        if translation_manager:
            await translation_manager.cleanup()
        
        if ocr_manager:
            await ocr_manager.cleanup()
            
        logger.info("Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS configuration with specific frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        "https://your-frontend-domain.com",  # Production frontend
        # Add your actual frontend URLs here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Request size limit middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class FileSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: StarletteRequest, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "file_too_large",
                            "detail": f"File size exceeds {self.max_size / (1024*1024):.1f}MB limit",
                            "max_size_mb": self.max_size / (1024*1024)
                        }
                    )
        
        response = await call_next(request)
        return response

app.add_middleware(FileSizeLimitMiddleware, max_size=10 * 1024 * 1024)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Request logging middleware"""
    import time
    
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Request started: {request.method} {request.url.path} from {client_ip}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(ProcessingError)
async def processing_error_handler(request: Request, exc: ProcessingError):
    """Handle custom processing errors"""
    logger.error(f"Processing error: {exc.detail}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "processing_error",
            "detail": exc.detail,
            "type": "ProcessingError"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": "Invalid request parameters",
            "errors": exc.errors()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )


# Include API routes
app.include_router(translation.router, prefix="/api/v1", tags=["translation"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Ink Translation API",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    settings = settings
    host = settings.HOST
    port = settings.PORT
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG
    )