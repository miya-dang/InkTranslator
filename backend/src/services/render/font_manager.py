import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging
from PIL import ImageFont
from config import settings

logger = logging.getLogger(__name__)

class FontManager:
    """Manages fonts strictly from the fonts/ folder with CJK support"""

    def __init__(self):
        self.fonts_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self.font_paths = self._get_font_paths()

    def _get_font_paths(self) -> Dict[str, str]:
        """Load font paths only from fonts/ folder (as defined in config.py)"""
        font_paths = {}
        for lang, relative_path in settings.font_mappings.items():
            full_path = Path(__file__).parent.parent.parent / relative_path
            if full_path.exists():
                font_paths[lang] = str(full_path)
                logger.info(f"Loaded font for {lang}: {full_path}")
            else:
                logger.error(f"Missing required font file for {lang}: {full_path}")
                raise FileNotFoundError(f"Font file not found for {lang}: {full_path}")
        return font_paths

    def get_font(self, language: str, size: int) -> ImageFont.FreeTypeFont:
        """Get font for specific language and size. Caches results."""
        cache_key = f"{language}_{size}"
        if cache_key in self.fonts_cache:
            return self.fonts_cache[cache_key]

        font_path = self._get_font_path_for_language(language)
        if not font_path:
            raise ValueError(f"No font available for language: {language}")

        try:
            font = ImageFont.truetype(font_path, size)
            self.fonts_cache[cache_key] = font
            return font
        except Exception as e:
            logger.error(f"Failed to load font for {language}: {e}")
            raise

    def _get_font_path_for_language(self, language: str) -> Optional[str]:
        """Get font path for a language, with simple language family fallback"""
        if language in self.font_paths:
            return self.font_paths[language]

        lang_families = {
            'ja': 'japanese', 'jp': 'japanese', 'jpn': 'japanese',
            'zh': 'sim_chinese', 'zh-cn': 'sim_chinese',
            'zh-tw': 'trad_chinese', 'zh-hk': 'trad_chinese',
            'cn': 'sim_chinese', 'tw': 'trad_chinese', 'hk': 'trad_chinese',
            'chi': 'sim_chinese',
            'ko': 'korean', 'kr': 'korean', 'kor': 'korean',
            'en': 'english', 'eng': 'english',
            'vi': 'vietnamese', 'vie': 'vietnamese',
        }

        lang_family = lang_families.get(language.lower())
        if lang_family and lang_family in self.font_paths:
            return self.font_paths[lang_family]

        return None

    def get_best_font_for_text(self, text: str, size: int) -> ImageFont.FreeTypeFont:
        """Select best font for a piece of text based on script detection"""
        detected_language = self._detect_script(text)
        return self.get_font(detected_language, size)

    def _detect_script(self, text: str) -> str:
        """Detect script/language from text characters"""
        if not text:
            return 'english'

        hiragana_katakana = sum(1 for c in text if '\u3040' <= c <= '\u30FF')
        kanji = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
        hangul = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')
        latin = sum(1 for c in text if c.isascii() and c.isalpha())
        total_chars = len([c for c in text if not c.isspace()])

        if total_chars == 0:
            return 'english'

        if (hiragana_katakana + kanji) / total_chars > 0.3:
            return 'japanese'
        elif hangul / total_chars > 0.3:
            return 'korean'
        elif kanji / total_chars > 0.3:
            return 'sim_chinese'
        elif latin / total_chars > 0.7:
            return 'english'
        else:
            if hiragana_katakana > 0:
                return 'japanese'
            elif hangul > 0:
                return 'korean'
            elif kanji > 0:
                return 'sim_chinese'
            else:
                return 'english'

    def _is_cjk_language(self, language: str) -> bool:
        """Check if language is CJK (Chinese, Japanese, Korean)"""
        return language.lower() in ['japanese', 'sim_chinese', 'trad_chinese', 'korean']

    def measure_text(self, text: str, font: ImageFont.FreeTypeFont, language: str = 'english') -> tuple:
        """Measure text dimensions with given font, accounting for CJK specifics"""
        try:
            if hasattr(font, 'getbbox'):
                bbox = font.getbbox(text)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                
                # For CJK languages, use more accurate height calculation
                if self._is_cjk_language(language):
                    # Get font metrics for more accurate height
                    ascent, descent = font.getmetrics()
                    # Use full line height for CJK characters
                    height = ascent + descent
                    
                return (width, height)
            else:
                width, height = font.getsize(text)
                # Apply CJK height adjustment for older PIL versions
                if self._is_cjk_language(language):
                    height = int(height * 1.2)  # CJK characters often need more vertical space
                return (width, height)
        except Exception as e:
            logger.error(f"Text measurement failed: {e}")
            # Fallback with CJK consideration
            char_width = 16 if self._is_cjk_language(language) else 10
            char_height = 20 if self._is_cjk_language(language) else 16
            return (len(text) * char_width, char_height)

    def wrap_text_for_size(self, text: str, target_width: int, font: ImageFont.FreeTypeFont, 
                          language: str = 'english') -> List[str]:
        """Wrap text considering language-specific characteristics"""
        if not text.strip():
            return []

        # For CJK languages, handle character-based wrapping
        if self._is_cjk_language(language):
            return self._wrap_cjk_text(text, target_width, font, language)
        else:
            return self._wrap_latin_text(text, target_width, font, language)

    def _wrap_cjk_text(self, text: str, target_width: int, font: ImageFont.FreeTypeFont, 
                      language: str) -> List[str]:
        """Wrap CJK text character by character"""
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            line_width, _ = self.measure_text(test_line, font, language)
            
            if line_width <= target_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
            
        return lines

    def _wrap_latin_text(self, text: str, target_width: int, font: ImageFont.FreeTypeFont, 
                        language: str) -> List[str]:
        """Wrap Latin text word by word (original logic)"""
        words = text.split()
        lines = []
        current_line = ""

        for i, word in enumerate(words):
            test_line = f"{current_line} {word}".strip()
            line_width, _ = self.measure_text(test_line, font, language)

            if line_width <= target_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)

                word_width, _ = self.measure_text(word, font, language)
                if word_width > target_width:
                    broken = self._break_long_word_with_hyphen(word, target_width, font, language)
                    lines.extend(broken[:-1])
                    current_line = broken[-1]
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        # Enforce bottom-line rule for short last word (only for Latin text)
        if len(lines) > 1:
            last_line = lines[-1]
            last_word = last_line.split()[-1]
            if len(last_word) <= 10 and ' ' in last_line:
                lines[-1] = ' '.join(last_line.split()[:-1])
                lines.append(last_word)
                if not lines[-2].strip():
                    lines.pop(-2)

        return lines

    def _break_long_word_with_hyphen(self, word: str, max_width: int, font: ImageFont.FreeTypeFont, 
                                   language: str) -> List[str]:
        """Break a long word into multiple parts with hyphens if needed."""
        parts = []
        current_part = ""

        for char in word:
            test_part = current_part + char
            width, _ = self.measure_text(test_part + "-", font, language)  # measure with hyphen
            if width <= max_width:
                current_part = test_part
            else:
                if current_part:
                    parts.append(current_part + "-")
                current_part = char

        if current_part:
            parts.append(current_part)

        return parts if parts else [word]

    def find_optimal_font_size_multiline(self, text: str, target_width: int, target_height: int,
                                        language: str = 'english', max_lines: Optional[int] = None) -> int:
        """
        Binary search to find optimal font size for multi-line text within given box.
        Accounts for CJK language characteristics.
        """
        min_size = settings.font_size_min
        max_size = settings.font_size_max
        left, right = min_size, max_size
        best_size = min_size

        # Adjust size limits for CJK languages
        if self._is_cjk_language(language):
            # CJK characters generally need larger sizes to be readable
            min_size = max(min_size, 12)
            left = min_size

        while left <= right:
            mid_size = (left + right) // 2
            font = self.get_font(language, mid_size)

            lines = self.wrap_text_for_size(text, target_width, font, language)

            if max_lines and len(lines) > max_lines:
                right = mid_size - 1
                continue

            line_height = self.measure_text("测" if self._is_cjk_language(language) else "A", 
                                          font, language)[1]
            
            # Vertical spacing
            if self._is_cjk_language(language):
                line_spacing = max(8, int(line_height * 0.4))
            else:
                line_spacing = max(5, int(line_height * 0.4))
                
            total_height = len(lines) * line_height + (len(lines) - 1) * line_spacing

            if total_height <= target_height:
                best_size = mid_size
                left = mid_size + 1
            else:
                right = mid_size - 1

        return best_size

    def find_optimal_font_size(self, text: str, target_width: int, target_height: int,
                               language: str = 'english') -> int:
        """Find optimal font size for text (single or multi-line)."""
        return self.find_optimal_font_size_multiline(text, target_width, target_height, language)

    def get_text_layout_info(self, text: str, target_width: int, target_height: int,
                            language: str = 'english') -> Tuple[int, List[str], int]:
        """
        Get complete layout info (font_size, wrapped_lines, total_height).
        Accounts for language-specific characteristics.
        """
        font_size = self.find_optimal_font_size_multiline(text, target_width, target_height, language)
        font = self.get_font(language, font_size)
        lines = self.wrap_text_for_size(text, target_width, font, language)

        line_height = self.measure_text("测" if self._is_cjk_language(language) else "A", 
                                      font, language)[1]
        
        # Consistent spacing calculation with font size optimization
        if language.lower() == 'korean':
            line_spacing = max(4, int(line_height * 0.3))
        elif language.lower() in ['japanese', 'sim_chinese', 'trad_chinese']:
            line_spacing = max(8, int(line_height * 0.4))
        else:
            line_spacing = max(4, int(line_height * 0.3))
            
        total_height = len(lines) * line_height + (len(lines) - 1) * line_spacing

        return font_size, lines, total_height

    def get_available_fonts(self) -> Dict[str, str]:
        return self.font_paths.copy()

    def clear_cache(self):
        self.fonts_cache.clear()


# Global font manager instance
font_manager = FontManager()