# base.py
import re
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Standardized language codes - single source of truth
class LanguageCode(Enum):
    CHINESE_SIMPLIFIED = "sim_chinese"
    CHINESE_TRADITIONAL = "trad_chinese"
    JAPANESE = "japanese"
    KOREAN = "korean"
    VIETNAMESE = "vietnamese"
    ENGLISH = "english"

# Language display names
SUPPORTED_LANGUAGES = {
    LanguageCode.CHINESE_SIMPLIFIED.value: 'Chinese (Simplified)',
    LanguageCode.CHINESE_TRADITIONAL.value: 'Chinese (Traditional)',
    LanguageCode.KOREAN.value: 'Korean',
    LanguageCode.VIETNAMESE.value: 'Vietnamese', 
    LanguageCode.JAPANESE.value: 'Japanese',
    LanguageCode.ENGLISH.value: 'English'
}

# Legacy code mapping for backward compatibility
LEGACY_LANGUAGE_MAP = {
    'JPN': LanguageCode.JAPANESE.value,
    'ENG': LanguageCode.ENGLISH.value,
    'KOR': LanguageCode.KOREAN.value,
    'VIN': LanguageCode.VIETNAMESE.value,
    'CHI': LanguageCode.CHINESE_SIMPLIFIED.value,
    'CHT': LanguageCode.CHINESE_TRADITIONAL.value,
}

class TranslationException(Exception):
    """Base exception for translation errors"""
    pass

class InvalidServerResponse(TranslationException):
    """Server returned invalid response"""
    pass

class MissingAPIKeyException(TranslationException):
    """API key is missing or invalid"""
    pass

class LanguageUnsupportedException(TranslationException):
    """Language not supported by translator"""
    
    def __init__(self, language_code: str, translator: str = None, supported_languages: List[str] = None):
        error = f'Language not supported for {translator or "chosen translator"}: "{language_code}"'
        if supported_languages:
            error += f'. Supported languages: "{", ".join(supported_languages)}"'
        super().__init__(error)

class RateLimitException(TranslationException):
    """Rate limit exceeded"""
    pass

def normalize_language_code(lang_code: str) -> str:
    """Normalize language code to standard format"""
    if lang_code in LEGACY_LANGUAGE_MAP:
        return LEGACY_LANGUAGE_MAP[lang_code]
    return lang_code

def is_valuable_text(text: str) -> bool:
    """Check if text contains valuable content worth translating"""
    if not text or not text.strip():
        return False
    
    # Remove whitespace and check if there's actual content
    cleaned = re.sub(r'\s+', '', text)
    if len(cleaned) < 2:
        return False
    
    # Check if it's mostly punctuation or symbols
    alphanumeric_count = sum(1 for c in cleaned if c.isalnum())
    if alphanumeric_count < len(cleaned) * 0.3:  # Less than 30% alphanumeric
        return False
    
    return True

def repeating_sequence(text: str) -> str:
    """Find the shortest repeating sequence in text"""
    if not text:
        return ""
    
    text_len = len(text)
    for seq_len in range(1, text_len // 2 + 1):
        sequence = text[:seq_len]
        repeats = text_len // seq_len
        if sequence * repeats == text[:repeats * seq_len]:
            return sequence
    
    return text

class BaseTranslator(ABC):
    """Base class for all translators following the original pattern"""
    
    # Language code mapping - to be overridden by subclasses
    _LANGUAGE_CODE_MAP = {}
    
    # Retry configuration
    _INVALID_REPEAT_COUNT = 0
    _MAX_REQUESTS_PER_MINUTE = -1
    
    def __init__(self):
        self.logger = logger
        self._last_request_ts = 0
        self.request_count = 0
        
    def supports_languages(self, from_lang: str, to_lang: str, fatal: bool = False) -> bool:
        """Check if translator supports the language pair"""
        # Normalize language codes
        from_lang = normalize_language_code(from_lang)
        to_lang = normalize_language_code(to_lang)
        
        supported_languages = list(self._LANGUAGE_CODE_MAP.keys()) if self._LANGUAGE_CODE_MAP else []
    
        # Fixed logic: Check both languages properly
        unsupported_lang = None
        if from_lang not in supported_languages:
            unsupported_lang = from_lang
        elif to_lang not in supported_languages:
            unsupported_lang = to_lang
            
        if unsupported_lang:
            if fatal:
                raise LanguageUnsupportedException(unsupported_lang, self.__class__.__name__, supported_languages)
            return False
            
        return True
    
    def parse_language_codes(self, from_lang: str, to_lang: str, fatal: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Parse and convert language codes to translator-specific format"""
        # Normalize input codes
        from_lang = normalize_language_code(from_lang)
        to_lang = normalize_language_code(to_lang)
        
        if not self.supports_languages(from_lang, to_lang, fatal):
            return None, None
            
        if isinstance(self._LANGUAGE_CODE_MAP, list):
            return from_lang, to_lang
        
        _from_lang = self._LANGUAGE_CODE_MAP.get(from_lang)
        _to_lang = self._LANGUAGE_CODE_MAP.get(to_lang)
        
        return _from_lang, _to_lang
    
    async def translate(self, from_lang: str, to_lang: str, queries: List[str], **kwargs) -> List[str]:
        """
        Main translation method following the original pattern
        """
        # Normalize language codes
        from_lang = normalize_language_code(from_lang)
        to_lang = normalize_language_code(to_lang)
        
        # Validate languages
        if to_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Invalid target language: "{to_lang}". Choose from: {", ".join(SUPPORTED_LANGUAGES.keys())}')
            
        if from_lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Invalid source language: "{from_lang}". Choose from: {", ".join(SUPPORTED_LANGUAGES.keys())}')
        
        # Fixed log message with proper spacing
        self.logger.info(f'Translating from {SUPPORTED_LANGUAGES[from_lang]} into {SUPPORTED_LANGUAGES[to_lang]}')
        
        # Skip translation if source and target are the same
        if from_lang == to_lang:
            return queries
        
        # Filter out queries without valuable text
        query_indices = []
        final_translations = []
        
        for i, query in enumerate(queries):
            if not is_valuable_text(query):
                final_translations.append(query)  # Keep original for non-valuable text
            else:
                final_translations.append(None)  # Placeholder for translation
                query_indices.append(i)
        
        # Extract only queries that need translation
        queries_to_translate = [queries[i] for i in query_indices]
        
        if not queries_to_translate:
            return final_translations
        
        # Initialize translation arrays
        translations = [''] * len(queries_to_translate)
        untranslated_indices = list(range(len(queries_to_translate)))
        
        # Retry loop for invalid translations
        for attempt in range(1 + self._INVALID_REPEAT_COUNT):
            if attempt > 0:
                self.logger.warning(f'Repeating due to invalid translation. Attempt: {attempt + 1}')
                await asyncio.sleep(0.1)
            
            # Rate limiting
            await self._ratelimit_sleep()
            
            # Perform translation
            try:
                _translations = await self._translate(
                    *self.parse_language_codes(from_lang, to_lang, fatal=True),
                    queries_to_translate
                )
            except Exception as e:
                self.logger.error(f"Translation failed: {e}")
                break
            
            # Ensure translations list has correct length
            if len(_translations) < len(queries_to_translate):
                _translations.extend([''] * (len(queries_to_translate) - len(_translations)))
            elif len(_translations) > len(queries_to_translate):
                _translations = _translations[:len(queries_to_translate)]
            
            # Update translations for untranslated indices
            for j in untranslated_indices:
                translations[j] = _translations[j]
            
            # If no retry logic, break here
            if self._INVALID_REPEAT_COUNT == 0:
                break
            
            # Check for invalid translations and prepare for retry
            new_untranslated_indices = []
            for j in untranslated_indices:
                query, translation = queries_to_translate[j], translations[j]
                if self._is_translation_invalid(query, translation):
                    new_untranslated_indices.append(j)
                    queries_to_translate[j] = self._modify_invalid_translation_query(query, translation)
            
            untranslated_indices = new_untranslated_indices
            if not untranslated_indices:
                break
        
        # Clean up translations
        cleaned_translations = []
        for query, translation in zip(queries_to_translate, translations):
            cleaned = self._clean_translation_output(query, translation, to_lang)
            cleaned_translations.append(cleaned)
        
        # Merge translations back into final result
        for i, translation in enumerate(cleaned_translations):
            final_translations[query_indices[i]] = translation
            self.logger.info(f'{i}: {queries_to_translate[i]} => {translation}')
        
        return final_translations
    
    @abstractmethod
    async def _translate(self, from_lang: str, to_lang: str, queries: List[str]) -> List[str]:
        """Actual translation implementation - to be overridden"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if translator is available"""
        pass
    
    async def _ratelimit_sleep(self):
        """Handle rate limiting"""
        if self._MAX_REQUESTS_PER_MINUTE > 0:
            now = time.time()
            min_interval = 60.0 / self._MAX_REQUESTS_PER_MINUTE
            time_since_last = now - self._last_request_ts
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                self.logger.info(f'Rate limit sleep: {sleep_time:.2f}s')
                await asyncio.sleep(sleep_time)
            
            self._last_request_ts = time.time()
    
    def _is_translation_invalid(self, query: str, translation: str) -> bool:
        """Check if translation appears invalid"""
        if not translation and query:
            return True
            
        if not query or not translation:
            return False
        
        # Check for lack of diversity in characters (repeated characters)
        query_unique_chars = len(set(query))
        trans_unique_chars = len(set(translation))
        
        if (query_unique_chars > 6 and 
            trans_unique_chars < 6 and 
            trans_unique_chars < 0.25 * len(translation)):
            return True
        
        return False
    
    def _modify_invalid_translation_query(self, query: str, translation: str) -> str:
        """Modify query for retry - can be overridden"""
        return query
    
    def _clean_translation_output(self, query: str, translation: str, to_lang: str) -> str:
        """Clean up translation output following original pattern"""
        if not query or not translation:
            return ''
        
        # Normalize whitespace
        translation = re.sub(r'\s+', ' ', translation)
        
        # Fix punctuation spacing: 'text.text' -> 'text. text'
        translation = re.sub(r'(?<![.,;!?])([.,;!?])(?=\w)', r'\1 ', translation)
        
        # Consolidate repeated punctuation: ' ! ! . . ' -> ' !!.. '
        translation = re.sub(r'([.,;!?])\s+(?=[.,;!?]|$)', r'\1', translation)
        
        # Remove space before punctuation: 'text .' -> 'text.'
        translation = re.sub(r'(?<=[.,;!?\w])\s+([.,;!?])', r'\1', translation)
        
        # Fix ellipsis spacing: ' ... text' -> ' ...text'  
        translation = re.sub(r'((?:\s|^)\.+)\s+(?=\w)', r'\1', translation)
        
        # Handle repeating sequences
        seq = repeating_sequence(translation.lower())
        
        # Fix translations that are just repeated characters
        if len(translation) < len(query) and len(seq) < 0.5 * len(translation):
            # Rebuild translation matching original query length
            translation = seq * max(len(query) // len(seq), 1)
            
            # Transfer capitalization from query
            new_translation = ''
            for i in range(min(len(translation), len(query))):
                char = translation[i]
                new_translation += char.upper() if query[i].isupper() else char
            translation = new_translation
        
        return translation.strip()