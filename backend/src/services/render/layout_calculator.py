import math
from typing import Tuple, List, Optional
import logging
from PIL import ImageFont

from models.schemas import TextBox, BoundingBox, TextDirection
from .font_manager import font_manager
from config import settings

logger = logging.getLogger(__name__)

class LayoutCalculator:
    """Calculates optimal text layout and positioning with CJK support"""
    
    @staticmethod
    def _is_cjk_language(language: str) -> bool:
        """Check if language is CJK (Chinese, Japanese, Korean)"""
        return language.lower() in ['japanese', 'sim_chinese', 'trad_chinese', 'korean']
    
    @staticmethod
    def calculate_optimal_font_size(text: str, bbox: BoundingBox, language: str = 'english',
                                  direction: TextDirection = TextDirection.LTR) -> int:
        if direction is None:
            from models.schemas import get_text_direction_for_language, Language
            try:
                lang_enum = Language(language)
                direction = get_text_direction_for_language(lang_enum)
            except ValueError:
                direction = TextDirection.LTR
                
        if not text.strip():
            return settings.default_font_size
        
        target_width = bbox.width - 4
        target_height = bbox.height - 4
        
        # For vertical text (CJK), we need to consider different dimensions
        if direction == TextDirection.TTB and LayoutCalculator._is_cjk_language(language):
            # For vertical CJK text, the "width" constraint becomes character spacing
            # and "height" constraint becomes the column height
            # We might need multiple columns, so adjust target_width for character width
            pass  # Keep original dimensions, font_manager will handle CJK specifics
        elif direction == TextDirection.TTB:
            # For non-CJK vertical text, swap dimensions
            target_width, target_height = target_height, target_width
        
        optimal_size = font_manager.find_optimal_font_size(
            text, target_width, target_height, language
        )
        
        # Apply language-specific multipliers
        if LayoutCalculator._is_cjk_language(language):
            # CJK characters often need slight size adjustment
            optimal_size = int(optimal_size * settings.font_size_multiplier * 1.1)
        else:
            optimal_size = int(optimal_size * settings.font_size_multiplier)
            
        return max(settings.font_size_min, min(optimal_size, settings.font_size_max))

    @staticmethod
    def calculate_text_position(text: str, bbox: BoundingBox, font: ImageFont.FreeTypeFont,
                              direction: TextDirection = TextDirection.LTR, 
                              alignment: str = 'center', language: str = 'english') -> Tuple[int, int]:
        
        text_width, text_height = font_manager.measure_text(text, font, language)
        
        if direction == TextDirection.LTR:
            # Horizontal text positioning
            if alignment == 'left':
                x = bbox.x1 + 2
            elif alignment == 'right':
                x = bbox.x2 - text_width - 2
            else:
                x = bbox.x1 + (bbox.width - text_width) // 2
            y = bbox.y1 + (bbox.height - text_height) // 2
            
        elif direction == TextDirection.TTB:
            # Vertical text positioning
            if LayoutCalculator._is_cjk_language(language):
                # For CJK vertical text, start from top-right
                x = bbox.x2 - text_width - 2  # Right-aligned for first column
                if alignment == 'top':
                    y = bbox.y1 + 2
                elif alignment == 'bottom':
                    y = bbox.y2 - text_height - 2
                else:
                    y = bbox.y1 + 2  # Start from top for vertical text
            else:
                # For non-CJK vertical text, center horizontally
                x = bbox.x1 + (bbox.width - text_width) // 2
                if alignment == 'top':
                    y = bbox.y1 + 2
                elif alignment == 'bottom':
                    y = bbox.y2 - text_height - 2
                else:
                    y = bbox.y1 + (bbox.height - text_height) // 2
                    
        return (x, y)

    @staticmethod
    def wrap_text_to_fit(text: str, bbox: BoundingBox, font: ImageFont.FreeTypeFont,
                        direction: TextDirection = TextDirection.LTR, language: str = 'english') -> List[str]:
        """Delegate wrapping to font_manager (with CJK support)."""
        if not text.strip():
            return []
            
        if direction == TextDirection.TTB and LayoutCalculator._is_cjk_language(language):
            # For vertical CJK text, we don't wrap in the traditional sense
            # Instead, we'll let the renderer handle column layout
            max_height = bbox.height - 4
            # For now, return the full text; vertical renderer will handle column breaks
            return [text]
        else:
            max_width = bbox.width - 4
            return font_manager.wrap_text_for_size(text, max_width, font, language)

    @staticmethod
    def calculate_multiline_position(lines: List[str], bbox: BoundingBox, font: ImageFont.FreeTypeFont,
                                   direction: TextDirection = TextDirection.LTR, 
                                   language: str = 'english') -> List[Tuple[int, int]]:
        if not lines:
            return []
        
        positions = []
        
        if direction == TextDirection.TTB and LayoutCalculator._is_cjk_language(language):
            # Vertical CJK text positioning - this is handled by the text renderer
            # Return a single position for the text block
            x = bbox.x2 - 4  # Start from right edge
            y = bbox.y1 + 4  # Start from top
            positions.append((x, y))
        else:
            # Horizontal text positioning (improved spacing)
            line_height = font_manager.measure_text("A", font, language)[1]
            
            # Improved line spacing for all languages
            if LayoutCalculator._is_cjk_language(language):
                line_spacing = max(8, int(line_height * 0.4))
            else:
                line_spacing = max(5, int(line_height * 0.4))
                
            total_text_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
            start_y = bbox.y1 + (bbox.height - total_text_height) // 2

            for i, line in enumerate(lines):
                line_width, _ = font_manager.measure_text(line, font, language)
                x = bbox.x1 + (bbox.width - line_width) // 2
                y = start_y + i * (line_height + line_spacing)
                positions.append((x, y))
        
        return positions

    @staticmethod
    def calculate_vertical_text_layout(text: str, bbox: BoundingBox, font: ImageFont.FreeTypeFont,
                                     language: str = 'japanese') -> List[Tuple[str, int, int]]:
        """Calculate layout for vertical CJK text (columns of characters)"""
        if not LayoutCalculator._is_cjk_language(language):
            return [(text, bbox.x1, bbox.y1)]
        
        char_width, char_height = font_manager.measure_text("测", font, language)
        
        # Calculate how many characters fit in one column
        available_height = bbox.height - 8
        chars_per_column = max(1, available_height // char_height)
        
        # Split text into columns
        columns = []
        for i in range(0, len(text), chars_per_column):
            column_text = text[i:i + chars_per_column]
            columns.append(column_text)
        
        # Calculate positions for each column (right to left)
        column_positions = []
        available_width = bbox.width - 8
        
        if len(columns) > 1:
            column_spacing = min(char_width + 10, available_width // len(columns))
        else:
            column_spacing = char_width
        
        # Start from right edge
        start_x = bbox.x2 - 4 - char_width
        
        for col_idx, column_text in enumerate(columns):
            x = start_x - (col_idx * column_spacing)
            y = bbox.y1 + 4
            
            # Only include columns that fit within the bounding box
            if x >= bbox.x1:
                column_positions.append((column_text, x, y))
            
        return column_positions

    @staticmethod
    def optimize_text_layout(text_boxes: List[TextBox], image_width: int, image_height: int) -> List[TextBox]:
        if len(text_boxes) <= 1:
            return text_boxes
        
        optimized_boxes = []
        for i, text_box in enumerate(text_boxes):
            adjusted_box = text_box.copy()
            for existing_box in optimized_boxes:
                if LayoutCalculator._boxes_overlap(adjusted_box.bbox, existing_box.bbox):
                    adjusted_box.bbox = LayoutCalculator._resolve_overlap(
                        adjusted_box.bbox, existing_box.bbox, image_width, image_height
                    )
            optimized_boxes.append(adjusted_box)
        return optimized_boxes

    @staticmethod
    def _boxes_overlap(bbox1: BoundingBox, bbox2: BoundingBox) -> bool:
        return not (bbox1.x2 < bbox2.x1 or bbox2.x2 < bbox1.x1 or 
                   bbox1.y2 < bbox2.y1 or bbox2.y2 < bbox1.y1)
    
    @staticmethod
    def _resolve_overlap(bbox1: BoundingBox, bbox2: BoundingBox, 
                        image_width: int, image_height: int) -> BoundingBox:
        movements = [
            (0, bbox2.y2 - bbox1.y1 + 5),
            (0, bbox2.y1 - bbox1.y2 - 5),
            (bbox2.x2 - bbox1.x1 + 5, 0),
            (bbox2.x1 - bbox1.x2 - 5, 0),
        ]
        for dx, dy in movements:
            new_x1 = bbox1.x1 + dx
            new_y1 = bbox1.y1 + dy
            new_x2 = bbox1.x2 + dx
            new_y2 = bbox1.y2 + dy
            if (0 <= new_x1 and new_x2 <= image_width and 
                0 <= new_y1 and new_y2 <= image_height):
                return BoundingBox(x1=new_x1, y1=new_y1, x2=new_x2, y2=new_y2)
        return bbox1