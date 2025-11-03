# inpaint/mask_generator.py
import cv2
import numpy as np
from typing import List, Tuple
import logging
from models.schemas import TextBox, BoundingBox
from config import settings

logger = logging.getLogger(__name__)

class MaskGenerator:
    """Generates masks for text regions to be inpainted"""
    
    @staticmethod
    def create_text_mask(image: np.ndarray, text_box: TextBox, padding: int = None) -> np.ndarray:
        """
        Create a mask for a single text box
        
        Args:
            image: Source image
            text_box: Text box to create mask for
            padding: Additional padding around text box
            
        Returns:
            Binary mask for the text region
        """
        if padding is None:
            padding = settings.inpaint_padding
        
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        # Get bounding box coordinates
        x1, y1, x2, y2 = text_box.bbox.x1, text_box.bbox.y1, text_box.bbox.x2, text_box.bbox.y2
        
        # Add padding
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.shape[1], x2 + padding)
        y2 = min(image.shape[0], y2 + padding)
        
        # Create rectangular mask
        mask[y1:y2, x1:x2] = 255
        
        return mask
    
    @staticmethod
    def create_adaptive_mask(image: np.ndarray, text_box: TextBox) -> np.ndarray:
        """
        Create an adaptive mask that better follows text contours
        
        Args:
            image: Source image
            text_box: Text box to create mask for
            
        Returns:
            Adaptive binary mask
        """
        # Extract region of interest
        x1, y1, x2, y2 = text_box.bbox.x1, text_box.bbox.y1, text_box.bbox.x2, text_box.bbox.y2
        roi = image[y1:y2, x1:x2].copy()
        
        if roi.size == 0:
            return MaskGenerator.create_text_mask(image, text_box)
        
        try:
            # Convert to grayscale
            if len(roi.shape) == 3:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray_roi = roi
            
            # Apply adaptive thresholding to find text
            adaptive_thresh = cv2.adaptiveThreshold(
                gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Morphological operations to clean up the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            adaptive_thresh = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
            adaptive_thresh = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_OPEN, kernel)
            
            # Create full-size mask
            full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            full_mask[y1:y2, x1:x2] = adaptive_thresh
            
            # Add some padding around detected text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            full_mask = cv2.dilate(full_mask, kernel, iterations=2)
            
            return full_mask
            
        except Exception as e:
            logger.warning(f"Adaptive mask generation failed: {e}, falling back to rectangular mask")
            return MaskGenerator.create_text_mask(image, text_box)
    
    @staticmethod
    def create_combined_mask(image: np.ndarray, text_boxes: List[TextBox]) -> np.ndarray:
        """
        Create a combined mask for multiple text boxes
        
        Args:
            image: Source image
            text_boxes: List of text boxes
            
        Returns:
            Combined binary mask
        """
        combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        for text_box in text_boxes:
            mask = MaskGenerator.create_text_mask(image, text_box)
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        return combined_mask
    
    @staticmethod
    def create_smart_mask(image: np.ndarray, text_box: TextBox) -> np.ndarray:
        """
        Create a smart mask that considers text color and background
        
        Args:
            image: Source image
            text_box: Text box to create mask for
            
        Returns:
            Smart binary mask
        """
        try:
            x1, y1, x2, y2 = text_box.bbox.x1, text_box.bbox.y1, text_box.bbox.x2, text_box.bbox.y2
            roi = image[y1:y2, x1:x2].copy()
            
            if roi.size == 0:
                return MaskGenerator.create_text_mask(image, text_box)
            
            # Convert to different color spaces for analysis
            if len(roi.shape) == 3:
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            else:
                gray_roi = roi
                hsv_roi = None
            
            # Analyze the region to determine if text is dark on light or light on dark
            mean_intensity = np.mean(gray_roi)
            
            # Create mask based on intensity analysis
            if mean_intensity > 127:
                # Likely dark text on light background
                threshold_mask = cv2.threshold(gray_roi, 0, 255, 
                                             cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            else:
                # Likely light text on dark background  
                threshold_mask = cv2.threshold(gray_roi, 0, 255,
                                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Morphological operations to refine the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            threshold_mask = cv2.morphologyEx(threshold_mask, cv2.MORPH_CLOSE, kernel)
            
            # Create full-size mask
            full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            full_mask[y1:y2, x1:x2] = threshold_mask
            
            # Dilate slightly to ensure complete coverage
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            full_mask = cv2.dilate(full_mask, kernel, iterations=1)
            
            return full_mask
            
        except Exception as e:
            logger.warning(f"Smart mask generation failed: {e}, falling back to rectangular mask")
            return MaskGenerator.create_text_mask(image, text_box)
    
    @staticmethod
    def refine_mask(mask: np.ndarray, image: np.ndarray) -> np.ndarray:
        """
        Refine a mask using edge information from the original image
        
        Args:
            mask: Initial mask
            image: Original image
            
        Returns:
            Refined mask
        """
        try:
            # Convert image to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Find edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Dilate edges slightly
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Subtract edge areas from mask to preserve important boundaries
            refined_mask = cv2.bitwise_and(mask, cv2.bitwise_not(edges))
            
            return refined_mask
            
        except Exception as e:
            logger.warning(f"Mask refinement failed: {e}")
            return mask