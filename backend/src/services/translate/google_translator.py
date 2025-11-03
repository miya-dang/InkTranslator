# google_translate.py
import aiohttp
import asyncio
import logging
from typing import List, Optional
from .base import BaseTranslator, RateLimitException, InvalidServerResponse

logger = logging.getLogger(__name__)

class GoogleTranslator(BaseTranslator):
    """Google Translate free service implementation"""
    
    # Google's language code mapping for your supported languages
    _LANGUAGE_CODE_MAP = {
        'sim_chinese':  'zh-cn',      # Chinese Simplified
        'trad_chinese': 'zh-tw',      # Chinese Traditional  
        'korean':       'ko',         # Korean
        'vietnamese':   'vi',         # Vietnamese
        'japanese':     'ja',         # Japanese
        'english':      'en'          # English
    }
    
    # Configuration
    _MAX_REQUESTS_PER_MINUTE = 3    # Requests per minute
    _INVALID_REPEAT_COUNT = 1       # Retry once for invalid translations
    
    def __init__(self, timeout: int = 30):
        super().__init__()
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        self.session = None
        self.timeout = timeout
        self.rate_limited = False
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    async def _translate(self, from_lang: str, to_lang: str, queries: List[str]) -> List[str]:
        """Translate queries using Google's free API"""
        if not queries:
            return []
        
        translations = []
        session = await self._get_session()
        
        for query in queries:
            if not query.strip():
                translations.append('')
                continue
            
            try:
                translation = await self._translate_single(session, query, from_lang, to_lang)
                translations.append(translation or '')
                
            except RateLimitException:
                self.rate_limited = True
                raise
            except Exception as e:
                self.logger.error(f"Google translation failed for '{query}': {e}")
                translations.append('')
        
        return translations
    
    async def _translate_single(self, session: aiohttp.ClientSession, 
                              text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """Translate a single text using Google API"""
        params = {
            'client': 'gtx',
            'sl': from_lang, 
            'tl': to_lang,
            'dt': 't',  # Return translation
            'q': text
        }
        
        try:
            async with session.get(self.base_url, params=params) as response:
                # Handle rate limiting
                if response.status == 429:
                    self.logger.warning("Google Translate rate limit hit")
                    raise RateLimitException("Google Translate rate limited")
                
                # Handle other HTTP errors
                if response.status != 200:
                    self.logger.error(f"Google API returned status {response.status}")
                    raise InvalidServerResponse(f"HTTP {response.status}")
                
                # Parse response
                try:
                    data = await response.json()
                except Exception as e:
                    raise InvalidServerResponse(f"Invalid JSON response: {e}")
                
                # Extract translation from response structure
                if not data or not data[0]:
                    raise InvalidServerResponse("Empty response data")
                
                # Google returns translation as nested array
                translation_parts = []
                for item in data[0]:
                    if item and item[0]:
                        translation_parts.append(item[0])
                
                if not translation_parts:
                    raise InvalidServerResponse("No translation found in response")
                
                result = ''.join(translation_parts)
                self.request_count += 1
                
                return result
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise InvalidServerResponse(f"Network error: {e}")
    
    def is_available(self) -> bool:
        """Check if Google Translate is available"""
        return not self.rate_limited
    
    def _modify_invalid_translation_query(self, query: str, translation: str) -> str:
        """Modify query for retry by adding context"""
        # Add some context to help Google understand better
        if len(query.split()) == 1:
            # Single word - add "word:" prefix
            return f"Word: {query}"
        else:
            # Multi-word - add "Text:" prefix  
            return f"Text: {query}"
    
    def _is_translation_invalid(self, query: str, translation: str) -> bool:
        """Enhanced invalid translation detection for Google"""
        # Use base class logic
        if super()._is_translation_invalid(query, translation):
            return True
        
        # Google-specific checks
        if translation and query:
            # Check if translation is just the original query (no translation occurred)
            if translation.strip().lower() == query.strip().lower():
                return True
            
            # Check for Google's error patterns
            error_patterns = [
                "translation error",
                "service unavailable", 
                "quota exceeded"
            ]
            
            for pattern in error_patterns:
                if pattern in translation.lower():
                    return True
        
        return False
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def reset_rate_limit(self):
        """Reset rate limit status"""
        self.rate_limited = False
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics"""
        return {
            'service': 'Google Translate',
            'requests_made': self.request_count,
            'rate_limited': self.rate_limited,
            'available': self.is_available()
        }