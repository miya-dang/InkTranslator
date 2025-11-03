# deepL_translate.py
import asyncio
import logging
from typing import List, Optional
from .base import BaseTranslator, MissingAPIKeyException, RateLimitException

try:
    import deepl
except ImportError:
    deepl = None

logger = logging.getLogger(__name__)

class DeepLTranslator(BaseTranslator):
    """DeepL translation service implementation"""
    
    # DeepL's language codes for your supported languages
    _LANGUAGE_CODE_MAP = {
        'sim_chinese':  'zh',         # Chinese (DeepL auto-detects simplified vs traditional)
        'trad_chinese': 'zh-hant',    # Chinese Traditional (DeepL Pro only)
        'korean':       'ko',         # Korean
        'japanese':     'ja',         # Japanese
        'english':      'en',         # English
    }
    
    # Configuration
    _MAX_REQUESTS_PER_MINUTE = 3   # Conservative for free tier
    _INVALID_REPEAT_COUNT = 0       # DeepL is usually accurate, no need to retry
    
    def __init__(self, api_key: str):
        super().__init__()
        
        if not deepl:
            raise ImportError("deepl package not installed. Install with: pip install deepl")
        
        if not api_key:
            raise MissingAPIKeyException("DeepL API key is required")
        
        self.api_key = api_key
        self.translator = None
        self.quota_exceeded = False
        self.auth_failed = False
        
        self._initialize_translator()
    
    def _initialize_translator(self):
        """Initialize DeepL translator and test API key"""
        try:
            self.translator = deepl.Translator(self.api_key)
            
            # Test API key by checking usage
            usage = self.translator.get_usage()
            self.logger.info(f"DeepL initialized - Usage: {usage.character.count}/{usage.character.limit}")
            
            # Check if we're near quota
            if usage.character.count >= usage.character.limit * 0.9:
                self.logger.warning("DeepL quota nearly exhausted")
            
        except deepl.AuthorizationException:
            self.logger.error("DeepL API key authorization failed")
            self.auth_failed = True
            self.translator = None
        except deepl.DeepLException as e:
            self.logger.error(f"DeepL initialization failed: {e}")
            self.translator = None
        except Exception as e:
            self.logger.error(f"Unexpected error initializing DeepL: {e}")
            self.translator = None
    
    def supports_languages(self, from_lang: str, to_lang: str, fatal: bool = False) -> bool:
        """Override to handle DeepL's limited language support"""
        # DeepL doesn't support Vietnamese
        if from_lang == 'VIN' or to_lang == 'VIN':
            if fatal:
                from .base import LanguageUnsupportedException
                raise LanguageUnsupportedException('VIN', 'DeepL', list(self._LANGUAGE_CODE_MAP.keys()))
            return False
        
        return super().supports_languages(from_lang, to_lang, fatal)
    
    async def _translate(self, from_lang: str, to_lang: str, queries: List[str]) -> List[str]:
        """Translate queries using DeepL API"""
        if not self.translator:
            raise Exception("DeepL translator not initialized")
        
        if not queries:
            return []
        
        translations = []
        
        for query in queries:
            if not query.strip():
                translations.append('')
                continue
            
            try:
                translation = await self._translate_single(query, from_lang, to_lang)
                translations.append(translation or '')
                
            except Exception as e:
                self.logger.error(f"DeepL translation failed for '{query}': {e}")
                translations.append('')
        
        return translations
    
    async def _translate_single(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """Translate single text using DeepL"""
        try:
            # DeepL API is synchronous, so run in executor
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                self._translate_sync,
                text,
                from_lang,
                to_lang
            )
            
            if result and result.text:
                self.request_count += 1
                return result.text
                
        except deepl.QuotaExceededException:
            self.logger.warning("DeepL quota exceeded")
            self.quota_exceeded = True
            raise RateLimitException("DeepL quota exceeded")
            
        except deepl.AuthorizationException:
            self.logger.error("DeepL authorization failed")
            self.auth_failed = True
            raise MissingAPIKeyException("DeepL authorization failed")
            
        except deepl.DeepLException as e:
            self.logger.error(f"DeepL API error: {e}")
            raise Exception(f"DeepL API error: {e}")
            
        return None
    
    def _translate_sync(self, text: str, source_lang: str, target_lang: str):
        """Synchronous DeepL translation call"""
        return self.translator.translate_text(
            text,
            source_lang=source_lang,
            target_lang=target_lang
        )
    
    def is_available(self) -> bool:
        """Check if DeepL is available for use"""
        return (self.translator is not None and 
                not self.quota_exceeded and 
                not self.auth_failed)
    
    def get_usage_info(self) -> dict:
        """Get current DeepL usage information"""
        if not self.translator:
            return {}
        
        try:
            usage = self.translator.get_usage()
            return {
                'characters_used': usage.character.count,
                'character_limit': usage.character.limit,
                'characters_remaining': usage.character.limit - usage.character.count,
                'usage_percentage': (usage.character.count / usage.character.limit) * 100
            }
        except Exception as e:
            self.logger.error(f"Failed to get DeepL usage info: {e}")
            return {}
    
    def get_supported_languages_info(self) -> dict:
        """Get detailed language support info from DeepL"""
        if not self.translator:
            return {}
        
        try:
            source_languages = self.translator.get_source_languages()
            target_languages = self.translator.get_target_languages()
            
            return {
                'source_languages': [{'code': lang.code, 'name': lang.name} for lang in source_languages],
                'target_languages': [{'code': lang.code, 'name': lang.name} for lang in target_languages]
            }
        except Exception as e:
            self.logger.error(f"Failed to get DeepL language info: {e}")
            return {}
    
    def reset_quota_status(self):
        """Reset quota exceeded status (for testing)"""
        self.quota_exceeded = False
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics"""
        usage_info = self.get_usage_info()
        
        return {
            'service': 'DeepL',
            'requests_made': self.request_count,
            'quota_exceeded': self.quota_exceeded,
            'auth_failed': self.auth_failed,
            'available': self.is_available(),
            **usage_info
        }