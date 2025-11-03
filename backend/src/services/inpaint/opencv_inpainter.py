# inpaint/opencv_inpainter.py
import cv2
import numpy as np
from typing import List, Optional
import logging

from models.schemas import TextBox
from .mask_generator import MaskGenerator
from config import settings

logger = logging.getLogger(__name__)

class OpenCVInpainter:
    """OpenCV-based inpainting service for removing text from images"""
    
    def __init__(self):
        self.mask_generator = MaskGenerator()
    
    def inpaint_textbox(self, image: np.ndarray, text_box: TextBox, 
                       method: str = "telea") -> np.ndarray:
        """
        Inpaint a single text box
        
        Args:
            image: Source image
            text_box: Text box to inpaint
            method: Inpainting method ("telea" or "ns")
            
        Returns:
            Inpainted image
        """
        try:
            # Create mask for the text box
            mask = self.mask_generator.create_smart_mask(image, text_box)
            
            # Choose inpainting algorithm
            if method.lower() == "ns":
                inpaint_method = cv2.INPAINT_NS
                radius = 10
            else:  # Default to Telea
                inpaint_method = cv2.INPAINT_TELEA
                radius = 8
            
            # Perform inpainting
            inpainted = cv2.inpaint(image, mask, radius, inpaint_method)
            
            logger.debug(f"Inpainted text box with {method} method")
            return inpainted
            
        except Exception as e:
            logger.error(f"Inpainting failed for text box: {e}")
            return image
    
    def inpaint_multiple_textboxes(self, image: np.ndarray, text_boxes: List[TextBox],
                                 method: str = "telea") -> np.ndarray:
        """
        Inpaint multiple text boxes sequentially
        
        Args:
            image: Source image
            text_boxes: List of text boxes to inpaint
            method: Inpainting method
            
        Returns:
            Inpainted image
        """
        result_image = image.copy()
        
        for text_box in text_boxes:
            result_image = self.inpaint_textbox(result_image, text_box, method)
        
        return result_image
    
    def inpaint_combined_mask(self, image: np.ndarray, text_boxes: List[TextBox],
                            method: str = "telea") -> np.ndarray:
        """
        Inpaint all text boxes using a combined mask (faster for many boxes)
        
        Args:
            image: Source image
            text_boxes: List of text boxes to inpaint
            method: Inpainting method
            
        Returns:
            Inpainted image
        """
        try:
            # Create combined mask
            combined_mask = self.mask_generator.create_combined_mask(image, text_boxes)
            
            # Choose inpainting parameters
            if method.lower() == "ns":
                inpaint_method = cv2.INPAINT_NS
                radius = 10
            else:
                inpaint_method = cv2.INPAINT_TELEA
                radius = 8
            
            # Perform inpainting
            inpainted = cv2.inpaint(image, combined_mask, radius, inpaint_method)
            
            logger.info(f"Inpainted {len(text_boxes)} text boxes with combined mask")
            return inpainted
            
        except Exception as e:
            logger.error(f"Combined inpainting failed: {e}")
            return self.inpaint_multiple_textboxes(image, text_boxes, method)
    
    def inpaint_adaptive(self, image: np.ndarray, text_boxes: List[TextBox]) -> np.ndarray:
        """
        Adaptive inpainting that chooses the best method for each text box
        
        Args:
            image: Source image
            text_boxes: List of text boxes to inpaint
            
        Returns:
            Inpainted image
        """
        result_image = image.copy()
        
        for text_box in text_boxes:
            # Analyze text box characteristics to choose method
            method = self._choose_inpaint_method(image, text_box)
            result_image = self.inpaint_textbox(result_image, text_box, method)
        
        return result_image
    
    def _choose_inpaint_method(self, image: np.ndarray, text_box: TextBox) -> str:
        """
        Choose the best inpainting method based on text box characteristics
        
        Args:
            image: Source image
            text_box: Text box to analyze
            
        Returns:
            Recommended inpainting method
        """
        try:
            # Extract region of interest
            x1, y1, x2, y2 = text_box.bbox.x1, text_box.bbox.y1, text_box.bbox.x2, text_box.bbox.y2
            roi = image[y1:y2, x1:x2]
            
            if roi.size == 0:
                return "telea"
            
            # Analyze region characteristics
            if len(roi.shape) == 3:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray_roi = roi
            
            # Calculate variance (texture complexity)
            variance = np.var(gray_roi)
            
            # Calculate edge density
            edges = cv2.Canny(gray_roi, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Choose method based on characteristics
            if variance > 1000 or edge_density > 0.1:
                # Complex texture or many edges - use NS method
                return "ns"
            else:
                # Simple texture - use Telea method (faster)
                return "telea"
                
        except Exception as e:
            logger.warning(f"Method selection failed: {e}")
            return "telea"
    
    def enhance_inpainting_result(self, original: np.ndarray, inpainted: np.ndarray,
                                text_boxes: List[TextBox]) -> np.ndarray:
        """
        Enhance inpainting result by blending and smoothing
        
        Args:
            original: Original image
            inpainted: Inpainted image
            text_boxes: Text boxes that were inpainted
            
        Returns:
            Enhanced inpainted image
        """
        try:
            result = inpainted.copy()
            
            for text_box in text_boxes:
                x1, y1, x2, y2 = text_box.bbox.x1, text_box.bbox.y1, text_box.bbox.x2, text_box.bbox.y2
                
                # Extract regions
                original_roi = original[y1:y2, x1:x2]
                inpainted_roi = result[y1:y2, x1:x2]
                
                if original_roi.size == 0 or inpainted_roi.size == 0:
                    continue
                
                # Apply Gaussian blur to smooth the inpainted region
                blurred_roi = cv2.GaussianBlur(inpainted_roi, (3, 3), 0)
                
                # Create a soft mask for blending
                mask = np.ones(original_roi.shape[:2], dtype=np.float32)
                mask = cv2.GaussianBlur(mask, (5, 5), 0)
                
                if len(original_roi.shape) == 3:
                    mask = np.stack([mask] * 3, axis=2)
                
                # Blend the blurred region
                enhanced_roi = (blurred_roi * mask + inpainted_roi * (1 - mask)).astype(np.uint8)
                result[y1:y2, x1:x2] = enhanced_roi
            
            return result
            
        except Exception as e:
            logger.warning(f"Enhancement failed: {e}")
            return inpainted
    
    def preview_inpainting_mask(self, image: np.ndarray, text_boxes: List[TextBox]) -> np.ndarray:
        """
        Create a preview of what will be inpainted (for debugging)
        
        Args:
            image: Source image
            text_boxes: Text boxes to be inpainted
            
        Returns:
            Image with inpainting masks highlighted
        """
        preview = image.copy()
        
        for text_box in text_boxes:
            mask = self.mask_generator.create_smart_mask(image, text_box)
            
            # Highlight mask areas in red
            mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            mask_colored[:, :, 0] = 0  # Remove blue
            mask_colored[:, :, 1] = 0  # Remove green
            
            # Overlay on preview
            preview = cv2.addWeighted(preview, 0.7, mask_colored, 0.3, 0)
        
        return preview