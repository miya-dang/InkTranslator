# services/translate/translation_manager.py
import asyncio
import logging
from typing import List, Optional, Dict, Union
from .base import (
    SUPPORTED_LANGUAGES, 
    TranslationException, RateLimitException
)
from .google_translator import GoogleTranslator
from .deepl_translator import DeepLTranslator

logger = logging.getLogger(__name__)

class TranslationManager:
    """
    Main translation manager with fallback logic
    Manages multiple translation services and handles automatic fallback
    """
    
    def __init__(self, deepl_api_key: Optional[str] = None, google_timeout: int = 30):
        self.deepl_api_key = deepl_api_key
        self.google_timeout = google_timeout
        self.translators = []
        self.service_priority = []
        self._initialized = False
    
    async def initialize(self):
        """Initialize translation services asynchronously"""
        if self._initialized:
            return
        
        try:
            # Initialize DeepL first (higher quality when available)
            if self.deepl_api_key:
                try:
                    deepl_translator = DeepLTranslator(self.deepl_api_key)
                    if deepl_translator.is_available():
                        self.translators.append(deepl_translator)
                        self.service_priority.append('DeepL')
                        logger.info("DeepL translator initialized successfully")
                    else:
                        logger.warning("DeepL translator initialized but not available")
                except Exception as e:
                    logger.error(f"Failed to initialize DeepL: {e}")
            
            # Always initialize Google as fallback
            try:
                google_translator = GoogleTranslator(timeout=self.google_timeout)
                self.translators.append(google_translator)
                self.service_priority.append('Google')
                logger.info("Google Translate initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Translate: {e}")
            
            if not self.translators:
                raise Exception("No translation services could be initialized")
            
            self._initialized = True
            logger.info(f"Translation manager ready with services: {self.service_priority}")
            
        except Exception as e:
            logger.error(f"Translation manager initialization failed: {e}")
            raise
    
    def _initialize_sync(self):
        """Synchronous initialization fallback"""
        if self._initialized:
            return
        
        # Initialize DeepL first (higher quality when available)
        if self.deepl_api_key:
            try:
                deepl_translator = DeepLTranslator(self.deepl_api_key)
                if deepl_translator.is_available():
                    self.translators.append(deepl_translator)
                    self.service_priority.append('DeepL')
                    logger.info("DeepL translator initialized successfully")
                else:
                    logger.warning("DeepL translator initialized but not available")
            except Exception as e:
                logger.error(f"Failed to initialize DeepL: {e}")
        
        # Always initialize Google as fallback
        try:
            google_translator = GoogleTranslator(timeout=self.google_timeout)
            self.translators.append(google_translator)
            self.service_priority.append('Google')
            logger.info("Google Translate initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate: {e}")
        
        if not self.translators:
            raise Exception("No translation services could be initialized")
        
        self._initialized = True
        logger.info(f"Translation manager ready with services: {self.service_priority}")
    
    def _ensure_initialized(self):
        """Ensure translation manager is initialized"""
        if not self._initialized:
            self._initialize_sync()
    
    def _validate_languages(self, from_lang: str, to_lang: str) -> tuple:
        """Validate languages"""
        # Validate source language
        if from_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Unsupported source language: "{from_lang}". Supported: {list(SUPPORTED_LANGUAGES.keys())}')
        
        # Validate target language
        if to_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Unsupported target language: "{to_lang}". Supported: {list(SUPPORTED_LANGUAGES.keys())}')
        
        # Check if translation is needed
        if from_lang == to_lang:
            return from_lang, to_lang, False  # No translation needed
        
        return from_lang, to_lang, True
    
    async def translate(self, text: str, from_lang: str = 'JPN', to_lang: str = 'ENG') -> Optional[str]:
        """
        Translate single text with automatic service fallback
        
        Args:
            text: Text to translate
            from_lang: Source language code (default: 'JPN')
            to_lang: Target language code (default: 'ENG') 
            
        Returns:
            Translated text or None if all services failed
        """
        self._ensure_initialized()
        
        if not text or not text.strip():
            return text
        
        # Validate languages
        from_lang, to_lang, needs_translation = self._validate_languages(from_lang, to_lang)
        if not needs_translation:
            return text
        
        logger.info(f"Translating '{text[:50]}...' from {from_lang} to {to_lang}")
        
        # Try each translator in priority order
        last_exception = None
        
        for translator in self.translators:
            if not translator.is_available():
                logger.debug(f"{translator.__class__.__name__} not available, skipping")
                continue
            
            # Check if translator supports this language pair
            if not translator.supports_languages(from_lang, to_lang):
                logger.debug(f"{translator.__class__.__name__} doesn't support {from_lang}->{to_lang}")
                continue
            
            try:
                # Use the translator's batch method with single item
                result = await translator.translate(from_lang, to_lang, [text])
                
                if result and result[0] and result[0].strip():
                    logger.info(f"Successfully translated with {translator.__class__.__name__}")
                    return result[0]
                else:
                    logger.warning(f"{translator.__class__.__name__} returned empty result")
                    
            except RateLimitException as e:
                logger.warning(f"{translator.__class__.__name__} rate limited: {e}")
                last_exception = e
                continue
            except Exception as e:
                logger.error(f"{translator.__class__.__name__} failed: {e}")
                last_exception = e
                continue
        
        logger.error(f"All translation services failed. Last error: {last_exception}")
        return None
    
    async def translate_batch(self, texts: List[str], from_lang: str, 
                            to_lang: str = 'JPN', max_concurrent: int = 3) -> List[Optional[str]]:
        """
        Translate multiple texts with concurrency control
        
        Args:
            texts: List of texts to translate
            from_lang: Source language code  
            to_lang: Target language code
            max_concurrent: Maximum concurrent translations
            
        Returns:
            List of translated texts (None for failures)
        """
        self._ensure_initialized()
        
        if not texts:
            return []
        
        # Validate languages
        from_lang, to_lang, needs_translation = self._validate_languages(from_lang, to_lang)
        if not needs_translation:
            return texts
        
        logger.info(f"Batch translating {len(texts)} texts from {from_lang} to {to_lang}")
        
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_with_semaphore(text):
            async with semaphore:
                return await self.translate(text, from_lang, to_lang)
        
        # Create tasks for all texts
        tasks = [translate_with_semaphore(text) for text in texts]
        
        # Execute with proper exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch translation failed for text {i}: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r is not None)
        logger.info(f"Batch translation completed: {success_count}/{len(texts)} successful")
        
        return processed_results
    
    async def translate_with_service(self, text: str, service_name: str, 
                                   from_lang: str = 'JPN', to_lang: str = 'ENG') -> Optional[str]:
        """
        Translate using a specific service (no fallback)
        
        Args:
            text: Text to translate
            service_name: Name of service ('DeepL' or 'Google')
            from_lang: Source language code
            to_lang: Target language code
            
        Returns:
            Translated text or None if failed
        """
        self._ensure_initialized()
        
        if not text or not text.strip():
            return text
        
        # Find the requested translator
        translator = None
        for t in self.translators:
            if t.__class__.__name__.replace('Translator', '') == service_name:
                translator = t
                break
        
        if not translator:
            raise ValueError(f"Service '{service_name}' not available. Available: {self.get_available_services()}")
        
        if not translator.is_available():
            raise Exception(f"Service '{service_name}' is currently not available")
        
        # Validate languages
        from_lang, to_lang, needs_translation = self._validate_languages(from_lang, to_lang)
        if not needs_translation:
            return text
        
        # Check language support
        if not translator.supports_languages(from_lang, to_lang):
            raise Exception(f"Service '{service_name}' doesn't support {from_lang}->{to_lang}")
        
        # Translate
        result = await translator.translate(from_lang, to_lang, [text])
        return result[0] if result and result[0] else None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages dictionary"""
        return SUPPORTED_LANGUAGES.copy()
    
    def get_available_services(self) -> List[str]:
        """Get list of currently available translation services"""
        self._ensure_initialized()
        available = []
        for translator in self.translators:
            if translator.is_available():
                service_name = translator.__class__.__name__.replace('Translator', '')
                available.append(service_name)
        return available
    
    def get_service_status(self) -> Dict[str, dict]:
        """Get detailed status of all translation services"""
        self._ensure_initialized()
        status = {}
        for translator in self.translators:
            service_name = translator.__class__.__name__.replace('Translator', '')
            
            # Get basic status
            service_status = {
                'available': translator.is_available(),
                'requests_made': getattr(translator, 'request_count', 0),
            }
            
            # Add service-specific information
            if hasattr(translator, 'get_usage_stats'):
                service_status.update(translator.get_usage_stats())
            
            status[service_name] = service_status
        
        return status
    
    def get_language_support_matrix(self) -> Dict[str, Dict[str, List[str]]]:
        """Get language support matrix for each service"""
        self._ensure_initialized()
        matrix = {}
        
        for translator in self.translators:
            service_name = translator.__class__.__name__.replace('Translator', '')
            supported_langs = list(getattr(translator, '_LANGUAGE_CODE_MAP', {}).keys())
            
            matrix[service_name] = {
                'source_languages': supported_langs,
                'target_languages': supported_langs
            }
        
        return matrix
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all services"""
        self._ensure_initialized()
        health = {}
        
        for translator in self.translators:
            service_name = translator.__class__.__name__.replace('Translator', '')
            
            try:
                # Try a simple translation as health check
                test_result = await translator.translate('JPN', 'ENG', ['test'])
                health[service_name] = bool(test_result and test_result[0])
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health[service_name] = False
        
        return health
    
    async def close(self):
        """Clean up all translator resources"""
        logger.info("Closing translation manager...")
        
        for translator in self.translators:
            try:
                if hasattr(translator, 'close'):
                    await translator.close()
            except Exception as e:
                logger.error(f"Error closing translator: {e}")
        
        self.translators.clear()
        self.service_priority.clear()
        self._initialized = False
        logger.info("Translation manager closed")
    
    def __enter__(self):
        return self
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()