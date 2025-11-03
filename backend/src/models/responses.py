from pydantic import BaseModel, Field
from typing import List, Optional
from .schemas import Language, TextBox

class HealthResponse(BaseModel):
    status: str = Field(..., description="API health status")
    version: str = Field(..., description="API version")
    ocr_models_loaded: int = Field(..., description="Number of OCR models loaded")
    translation_services_available: List[str] = Field(..., description="Available translation services")
    uptime_seconds: float = Field(..., description="API uptime in seconds")

class SupportedLanguagesResponse(BaseModel):
    ocr_languages: List[Language] = Field(..., description="Supported OCR languages")
    translation_languages: List[Language] = Field(..., description="Supported translation languages")
    
class TranslationStatusResponse(BaseModel):
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Current processing status")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    
class TranslationResultResponse(BaseModel):
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Final status")
    text_boxes: List[TextBox] = Field(..., description="Detected and translated text boxes")
    processing_time: float = Field(..., description="Total processing time in seconds")
    original_text_count: int = Field(..., description="Number of original text boxes detected")
    translated_text_count: int = Field(..., description="Number of successfully translated text boxes")
    
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Detailed error information")
    job_id: Optional[str] = Field(None, description="Job ID if applicable")
    timestamp: Optional[str] = Field(None, description="Error timestamp")

class OCRResultResponse(BaseModel):
    text_boxes: List[TextBox] = Field(..., description="Detected text boxes")
    detection_time: float = Field(..., description="OCR processing time in seconds")
    confidence_average: float = Field(..., description="Average confidence score")