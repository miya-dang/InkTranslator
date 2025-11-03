import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, List
from models.schemas import TextBox, BoundingBox, Language, TextDirection, get_text_direction_for_language
from .font_manager import font_manager
from .layout_calculator import LayoutCalculator

class TextRenderer:
    
    def _is_cjk_language(self, language: str) -> bool:
        """Check if language is CJK (Chinese, Japanese, Korean)"""
        if isinstance(language, Language):
            language = language.value
        return language.lower() in ['japanese', 'sim_chinese', 'trad_chinese', 'korean']
    
    async def render_text(self, image: np.ndarray, text_box: TextBox, 
                         target_language: Language) -> np.ndarray:
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)
        
        language_str = target_language.value if isinstance(target_language, Language) else target_language
        text_direction = get_text_direction_for_language(target_language)
        
        # Calculate font size with language context
        font_size = LayoutCalculator.calculate_optimal_font_size(
            text_box.translated_text, text_box.bbox, language_str, text_direction
        )
        font = font_manager.get_font(language_str, font_size)
        
        # Handle vertical vs horizontal text rendering
        if text_direction == TextDirection.TTB and self._is_cjk_language(language_str):
            # Render vertical text for CJK languages
            self._render_vertical_text(draw, text_box, font, language_str)
        else:
            # Render horizontal text (original logic)
            self._render_horizontal_text(draw, text_box, font, language_str)
        
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _render_horizontal_text(self, draw: ImageDraw.Draw, text_box: TextBox, 
                              font: ImageFont.FreeTypeFont, language: str):
        """Render horizontal text (original multiline logic)"""
        # Use font_manager for wrapping instead of LayoutCalculator
        lines = font_manager.wrap_text_for_size(
            text_box.translated_text, text_box.bbox.width - 4, font, language
        )
        
        positions = LayoutCalculator.calculate_multiline_position(
            lines, text_box.bbox, font, TextDirection.LTR
        )
        
        # Render each line with outline
        for line, (x, y) in zip(lines, positions):
            # White outline (4-directional)
            draw.text((x-1, y-1), line, font=font, fill="white")
            draw.text((x+1, y-1), line, font=font, fill="white")
            draw.text((x-1, y+1), line, font=font, fill="white")
            draw.text((x+1, y+1), line, font=font, fill="white")
            # Black text
            draw.text((x, y), line, font=font, fill="black")
    
    def _render_vertical_text(self, draw: ImageDraw.Draw, text_box: TextBox, 
                            font: ImageFont.FreeTypeFont, language: str):
        """Render vertical text for CJK languages (top-to-bottom, right-to-left columns)"""
        text = text_box.translated_text
        bbox = text_box.bbox
        
        # Calculate character dimensions
        char_width, char_height = font_manager.measure_text("测", font, language)
        
        # Calculate how many characters can fit vertically
        available_height = bbox.height - 8  # padding
        chars_per_column = max(1, available_height // char_height)
        
        # Split text into columns
        columns = []
        for i in range(0, len(text), chars_per_column):
            columns.append(text[i:i + chars_per_column])
        
        # Calculate column spacing with improved horizontal spacing
        available_width = bbox.width - 8  # padding
        
        # Improved column spacing for CJK languages
        if language.lower() == 'japanese':
            # Japanese needs more spacing to prevent overlap
            base_spacing = char_width + 20
        elif language.lower() in ['sim_chinese', 'trad_chinese']:
            # Chinese needs good spacing between columns
            base_spacing = char_width + 14
        else:
            # Other CJK languages
            base_spacing = char_width + 10
        
        # Ensure we don't exceed available width
        if len(columns) > 1:
            max_spacing = available_width // len(columns)
            column_spacing = min(base_spacing, max_spacing)
        else:
            column_spacing = base_spacing
        
        # Start from the right side (right-to-left column order)
        text_block_width = len(columns) * column_spacing
        start_x = bbox.x1 + bbox.width - (bbox.width - text_block_width) // 2 - char_width
        
        for col_idx, column in enumerate(columns):
            # Calculate x position for this column (moving left)
            x = start_x - (col_idx * column_spacing)
            
            # Skip if column would be outside the bounding box
            if x < bbox.x1:
                break
            
            # Render each character in the column vertically with improved spacing
            y = bbox.y1 + 4  # start from top
            
            for char_idx, char in enumerate(column):
                if char.strip():  # Skip whitespace
                    # White outline (4-directional)
                    draw.text((x-1, y-1), char, font=font, fill="white")
                    draw.text((x+1, y-1), char, font=font, fill="white")
                    draw.text((x-1, y+1), char, font=font, fill="white")
                    draw.text((x+1, y+1), char, font=font, fill="white")
                    # Black text
                    draw.text((x, y), char, font=font, fill="black")
                
                # Improved vertical spacing between characters
                if language.lower() == 'japanese':
                    # Japanese needs slightly more vertical spacing
                    char_spacing = char_height + 2
                else:
                    # Chinese languages
                    char_spacing = char_height - 1
                    
                y += char_spacing
                
                # Stop if we exceed the bounding box height
                if y + char_height > bbox.y2:
                    break
    
    def _render_vertical_text_pil_native(self, draw: ImageDraw.Draw, text_box: TextBox, 
                                        font: ImageFont.FreeTypeFont, language: str):
        """Alternative implementation using PIL's native vertical text support"""
        try:
            # Try using PIL's direction parameter for vertical text
            x = text_box.bbox.x1 + text_box.bbox.width // 2
            y = text_box.bbox.y1 + 4
            
            # White outline
            draw.text((x-1, y-1), text_box.translated_text, font=font, fill="white", 
                     direction='ttb', anchor='lt')
            draw.text((x+1, y-1), text_box.translated_text, font=font, fill="white", 
                     direction='ttb', anchor='lt')
            draw.text((x-1, y+1), text_box.translated_text, font=font, fill="white", 
                     direction='ttb', anchor='lt')
            draw.text((x+1, y+1), text_box.translated_text, font=font, fill="white", 
                     direction='ttb', anchor='lt')
            # Black text
            draw.text((x, y), text_box.translated_text, font=font, fill="black", 
                     direction='ttb', anchor='lt')
        except Exception as e:
            # Fallback to character-by-character rendering if PIL doesn't support direction
            self._render_vertical_text(draw, text_box, font, language)