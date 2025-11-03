# utils/exceptions.py
"""
Custom exceptions for the manga translator application
"""

class MangaTranslatorException(Exception):
    """Base exception class for all manga translator errors"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message

class ProcessingError(MangaTranslatorException):
    """Base class for all processing-related exceptions"""
    pass

class OCRError(ProcessingError):
    """Raised when OCR processing fails"""
    pass

class TranslationError(ProcessingError):
    """Raised when translation fails"""
    pass

class InpaintingError(ProcessingError):
    """Raised when inpainting fails"""
    pass

class RenderingError(ProcessingError):
    """Raised when text rendering fails"""
    pass

class ImageValidationError(ProcessingError):
    """Raised when image validation fails"""
    pass

class FontNotFoundError(RenderingError):
    """Raised when required font is not found"""
    pass

class LayoutError(RenderingError):
    """Raised when text layout calculation fails"""
    pass

class ConfigurationError(MangaTranslatorException):
    """Raised when configuration is invalid"""
    pass

class ServiceUnavailableError(MangaTranslatorException):
    """Raised when a required service is unavailable"""
    pass

class RateLimitError(MangaTranslatorException):
    """Raised when rate limit is exceeded"""
    pass

class InvalidLanguageError(MangaTranslatorException):
    """Raised when an unsupported language is specified"""
    pass

class TextBoxError(ProcessingError):
    """Raised when text box operations fail"""
    pass

class MaskGenerationError(InpaintingError):
    """Raised when mask generation fails"""
    pass

class ValidationError(MangaTranslatorException):
    """Raised when input validation fails"""
    pass

class FileValidationError(ValidationError):
    """Raised when file validation fails"""
    pass

class ParameterValidationError(ValidationError):
    """Raised when parameter validation fails"""
    pass