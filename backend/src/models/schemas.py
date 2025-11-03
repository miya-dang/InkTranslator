# models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from config import settings

# Language 
class Language(str, Enum):
    JAPANESE = "japanese"
    SIM_CHINESE = "sim_chinese"
    TRAD_CHINESE = "trad_chinese"
    KOREAN = "korean"
    ENGLISH = "english"
    VIETNAMESE = "vietnamese"

class TextDirection(str, Enum):
    LTR = "ltr"  # Horizontal text
    TTB = "ttb"  # Vertical text

_missing_fonts = [lang.value for lang in Language if lang.value not in settings.font_mappings]
if _missing_fonts:
    raise ValueError(f"Missing font mappings in config for: {', '.join(_missing_fonts)}")

def get_font_for_language(language: Language) -> str:
    """Return font path for given language, falling back to default."""
    return settings.font_mappings.get(language.value, settings.font_mappings["default"])

def get_text_direction_for_language(language: Language) -> TextDirection:
    """Return text direction for the given language (from config)."""
    direction = settings.text_directions.get(language.value, settings.text_directions["default"])
    return TextDirection(direction)


# Status Tracking
class ProcessingStage(str, Enum):
    """Processing stages for status reporting"""
    INITIALIZED = "initialized"
    OCR = "ocr"
    TRANSLATION = "translation"
    INPAINTING = "inpainting"
    RENDERING = "rendering"
    COMPLETED = "completed"
    ERROR = "error"

class ProcessingStatus(BaseModel):
    stage: ProcessingStage
    message: str
    details: Optional[dict] = None


# Translation Job Model
class TranslationJob(BaseModel):
    session_id: str
    status: ProcessingStatus = Field(
        default=ProcessingStatus(
            stage=ProcessingStage.INITIALIZED,
            message="Job received",
        )
    )
    result: Optional[str] = None


# Data Models
class BoundingBox(BaseModel):
    x1: int = Field(..., description="Left coordinate")
    y1: int = Field(..., description="Top coordinate") 
    x2: int = Field(..., description="Right coordinate")
    y2: int = Field(..., description="Bottom coordinate")
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    @property
    def center_x(self) -> int:
        return (self.x1 + self.x2) // 2
    @property
    def center_y(self) -> int:
        return (self.y1 + self.y2) // 2

class TextBox(BaseModel):
    """
    Standardized text box representation
    Contains both original extracted text and translated text
    """
    text: str  # Original extracted text (primary attribute name)
    bbox: BoundingBox  # Bounding box coordinates
    # confidence: float = 0.0  # OCR confidence score
    translated_text: str = ""  # Translated text (empty until translated)
    # language: Optional[str] = None  # Detected language
    # font_size: Optional[int] = None  # Estimated font size
    # text_direction: Optional[str] = None  # 'horizontal' or 'vertical'
    
    @property
    def has_translation(self) -> bool:
        """Check if this text box has been translated"""
        return bool(self.translated_text.strip())
    
    @property
    def display_text(self) -> str:
        """Get text to display (translated if available, otherwise original)"""
        return self.translated_text if self.has_translation else self.text