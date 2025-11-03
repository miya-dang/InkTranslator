# models/requests.py
from pydantic import BaseModel, Field
from typing import Optional
from .schemas import Language
from config import settings

class TranslationRequest(BaseModel):
    source_language: Language = Field(
        description="Source language for OCR and translation"
    )
    target_language: Language = Field(
        description="Target language for translation"
    )
    preserve_formatting: bool = Field(
        default=True,
        description="Whether to preserve original text formatting"
    )
    font_size_multiplier: float = Field(
        default=settings.font_size_multiplier,
        ge=0.5,
        le=2.0,
        description="Font size multiplier for rendered text"
    )

class WebSocketMessage(BaseModel):
    type: str = Field(..., description="Message type")
    job_id: str = Field(..., description="Job ID")
    data: dict = Field(default_factory=dict, description="Message data")
    timestamp: Optional[str] = Field(None, description="Message timestamp")