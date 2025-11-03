# ocr/manga_ocr.py
import numpy as np
import cv2
import logging
from typing import List
from manga_ocr import MangaOcr
from PIL import Image
import easyocr

from .base import OCRService
from models.schemas import TextBox, BoundingBox
from config import settings

logger = logging.getLogger(__name__)

class MangaOCRService(OCRService):
    def __init__(self):
        # MangaOCR (recognition model)
        self.mocr = MangaOcr()

        # EasyOCR (for bounding boxes only)
        self.reader = easyocr.Reader(['ja', 'en'], gpu=True, verbose=False)

    async def extract_text(self, image: np.ndarray, language: str) -> List[TextBox]:
        """Detect bounding boxes with EasyOCR, then recognize text with MangaOCR"""
        # Convert BGR -> RGB
        if len(image.shape) == 3:
            rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_img = image

        # Step 1: Use EasyOCR to detect text regions
        detections = self.reader.readtext(rgb_img, paragraph=False)  
        # detections = [(bbox, text, confidence), ...]

        boxes: List[TextBox] = []

        for bbox, _, _ in detections:
            points = np.array(bbox).astype(int)
            x1, y1 = points.min(axis=0)
            x2, y2 = points.max(axis=0)

            # Crop region for MangaOCR
            cropped = rgb_img[y1:y2, x1:x2]
            if cropped.size == 0:
                continue  

            pil_img = Image.fromarray(cropped)

            # Step 2: Run MangaOCR recognition
            try:
                recognized_text = self.mocr(pil_img).strip()
            except Exception as e:
                logger.error(f"MangaOCR failed on region: {e}")
                recognized_text = ""

            if recognized_text:
                boxes.append(TextBox(
                    text=recognized_text,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                ))

        # Step 3: Merge nearby text boxes if enabled
        if settings.merge_nearby_textboxes:
            boxes = self._merge_nearby_boxes(boxes)

        return boxes

    def is_available(self) -> bool:
        return self.mocr is not None and self.reader is not None

    def get_supported_languages(self) -> List[str]:
        return ["japanese", "sim_chinese", "trad_chinese"]