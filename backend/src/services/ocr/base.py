# ocr/base.py
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from models.schemas import TextBox, BoundingBox

class OCRService(ABC):
    @abstractmethod
    async def extract_text(self, image: np.ndarray, language: str) -> List[TextBox]:
        """Extract text from image"""
        pass
   
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR service is available"""
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return list of supported languages"""
        pass
   
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character sets"""
        if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in text):
            return 'japanese' if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' for c in text) else 'chinese'
        if any('\uAC00' <= c <= '\uD7A3' for c in text):
            return 'korean'
        return 'english'

    def _merge_nearby_boxes(self, boxes: List[TextBox], threshold: int = 20) -> List[TextBox]:
        """Merge nearby text boxes"""
        if not boxes:
            return boxes
        
        merged = []
        used = set()
        
        for i, box1 in enumerate(boxes):
            if i in used:
                continue
                
            group = [box1]
            used.add(i)
            
            for j, box2 in enumerate(boxes[i+1:], i+1):
                if j in used:
                    continue
                if self._boxes_nearby(box1.bbox, box2.bbox, threshold):
                    group.append(box2)
                    used.add(j)
            
            if len(group) > 1:
                merged.append(self._merge_text_boxes(group))
            else:
                merged.append(box1)
        
        return merged
    
    def _boxes_nearby(self, bbox1: BoundingBox, bbox2: BoundingBox, threshold: int) -> bool:
        """Check if two boxes are nearby"""
        c1x, c1y = (bbox1.x1 + bbox1.x2) // 2, (bbox1.y1 + bbox1.y2) // 2
        c2x, c2y = (bbox2.x1 + bbox2.x2) // 2, (bbox2.y1 + bbox2.y2) // 2
        return ((c1x - c2x) ** 2 + (c1y - c2y) ** 2) ** 0.5 <= threshold
    
    def _merge_text_boxes(self, boxes: List[TextBox]) -> TextBox:
        """Merge multiple text boxes into one"""

        if len(boxes) == 1:
            return boxes[0]
        
        min_x1 = min(b.bbox.x1 for b in boxes)
        min_y1 = min(b.bbox.y1 for b in boxes)
        max_x2 = max(b.bbox.x2 for b in boxes)
        max_y2 = max(b.bbox.y2 for b in boxes)
        
        return TextBox(
            text=" ".join(b.text for b in boxes),
            bbox=BoundingBox(x1=min_x1, y1=min_y1, x2=max_x2, y2=max_y2),
            confidence=sum(b.confidence for b in boxes) / len(boxes),
            language=boxes[0].language
        )