
# ocr/easy_ocr.py
import easyocr
import numpy as np
import cv2
import logging
from typing import List, Dict
from .base import OCRService
from models.schemas import TextBox, BoundingBox
from config import settings

logger = logging.getLogger(__name__)

class EasyOCRService(OCRService):
    def __init__(self):
        self.readers: Dict[str, easyocr.Reader] = {}
        self._init_readers()
    
    def _init_readers(self):
        """Initialize readers for supported languages"""
        configs = {
            'english': ['en'],
            'japanese': ['ja', 'en'],
            'sim_chinese': ['ch_sim', 'en'], 
            'trad_chinese': ['ch_tra', 'en'],
            'korean': ['ko', 'en'],
            'vietnamese': ['vi', 'en'],
        }
        
        for lang, codes in configs.items():
            try:
                self.readers[lang] = easyocr.Reader(codes, gpu=True, verbose=False)
                logger.info(f"EasyOCR {lang} reader initialized")
            except Exception as e:
                try:
                    self.readers[lang] = easyocr.Reader(codes, gpu=False, verbose=False)
                    logger.info(f"EasyOCR {lang} reader initialized (CPU)")
                except Exception:
                    logger.error(f"Failed to initialize {lang} reader: {e}")

    async def extract_text(self, image: np.ndarray, language: str) -> List[TextBox]:
        """Extract text using EasyOCR"""
        reader = self.readers.get(language)
        if not reader:
            raise ValueError(f"No reader available for: {language}")
        
        # Convert BGR to RGB
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = reader.readtext(image, paragraph=True)
        boxes = []
        
        for bbox, text in results:
            if text.strip():
                points = np.array(bbox).astype(int)
                x1, y1 = points.min(axis=0)
                x2, y2 = points.max(axis=0)
                
                boxes.append(TextBox(
                    text=text.strip(),
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    # confidence=confidence,
                    # language=self._detect_language(text)
                ))
                
        
        if settings.merge_nearby_textboxes:
            boxes = self._merge_nearby_boxes(boxes)
        
        return boxes
    
    def is_available(self) -> bool:
        return len(self.readers) > 0
    
    def get_supported_languages(self) -> List[str]:
        return ["english", "korean", "vietnamese", "japanese", "sim_chinese", "trad_chinese"]
    

