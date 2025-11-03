# ocr/ocr_manager.py
import logging
import inspect
from typing import Dict, List, Union
from models.schemas import Language
from .base import OCRService
from .easy_ocr import EasyOCRService
from .manga_ocr import MangaOCRService

logger = logging.getLogger(__name__)


class OCRManager:
    def __init__(self):
        self.services: Dict[str, OCRService] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize OCR services asynchronously."""
        if self._initialized:
            return

        try:
            # Available OCR services
            ocr_services = {
                "easy": EasyOCRService,
                "manga": MangaOCRService,
            }

            for name, service in ocr_services.items():
                ocr_service = service()
                if ocr_service.is_available():
                    self.services[name] = ocr_service
                    logger.info(f"{name.capitalize()}OCR service loaded")

            if not self.services:
                logger.warning("No OCR services initialized.")
            else:
                logger.info(
                    f"OCR Manager initialized with: {', '.join(self.services.keys())}."
                )
            self._initialized = True

        except Exception as e:
            logger.error(f"OCR initialization failed: {e}")
            raise


    def _normalize_language(self, language: Union[str, Language]) -> str:
        """Ensure language is always a lowercase string."""
        if isinstance(language, Language):
            return language.value
        return str(language).lower()

    async def get_ocr_service(self, language: Union[str, Language]) -> OCRService:
        """Return the OCR service that supports the given language, 
        preferring MangaOCR for JP/CN if available."""
        if not self._initialized:
            await self.initialize()

        lang = self._normalize_language(language)

        # Prioritize MangaOCR for Japanese and Chinese
        if lang in ["japanese", "sim_chinese", "trad_chinese"]:
            if "manga" in self.services and lang in self.services["manga"].get_supported_languages():
                return self.services["manga"]

        # Fallback to any service that supports the language
        for name, service in self.services.items():
            if hasattr(service, "get_supported_languages") and lang in service.get_supported_languages():
                return service

        raise RuntimeError(f"No OCR service available for language: {lang}")

    def is_available(self) -> bool:
        """Check if any OCR services are available."""
        return len(self.services) > 0

    def get_available_languages(self) -> List[str]:
        """Get supported languages from all services."""
        langs = []
        for service in self.services.values():
            if hasattr(service, "get_supported_languages"):
                langs.extend(service.get_supported_languages())
        return sorted(set(langs))

    def get_service_status(self) -> Dict[str, Dict]:
        """Return structured status for each OCR service."""
        status = {}
        for name, service in self.services.items():
            status[name] = {
                "available": service.is_available(),
                "languages": getattr(service, "get_supported_languages", lambda: [])(),
            }
        return status

    async def close(self):
        """Clean up all OCR services."""
        for name, service in self.services.items():
            try:
                if hasattr(service, "close"):
                    if inspect.iscoroutinefunction(service.close):
                        await service.close()
                    else:
                        service.close()
            except Exception as e:
                logger.error(f"Error closing OCR service {name}: {e}")

        self.services.clear()
        self._initialized = False
        logger.info("OCR Manager closed")
