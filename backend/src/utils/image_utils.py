# utils/image_utils.py
import cv2
import numpy as np
from PIL import Image
import io
import base64
from typing import Optional, List, Tuple, Union
import logging
from pathlib import Path

from models.schemas import TextBox, BoundingBox
from utils.exceptions import ImageValidationError, ProcessingError
from config import settings

logger = logging.getLogger(__name__)

class ImageUtils:
    """Utility functions for image processing and manipulation"""
    
    @staticmethod
    def validate_image(content_type: str, file_size: int) -> bool:
        """Validate image file type and size"""
        try:
            if content_type not in settings.SUPPORTED_IMAGE_FORMATS:
                logger.warning(f"Unsupported image format: {content_type}")
                return False
            
            if file_size > settings.MAX_IMAGE_SIZE:
                logger.warning(f"Image too large: {file_size} bytes (max: {settings.MAX_IMAGE_SIZE})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False
    
    @staticmethod
    def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
        """
        Load image from bytes into OpenCV format
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Image as numpy array in BGR format
            
        Raises:
            ImageValidationError: If image cannot be loaded
        """
        try:
            # Convert bytes to PIL Image
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert PIL to OpenCV (BGR)
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            logger.info(f"Loaded image: {cv_image.shape}")
            return cv_image
            
        except Exception as e:
            raise ImageValidationError(f"Failed to load image from bytes", str(e))
    
    @staticmethod
    def load_image_from_file(file_path: Union[str, Path]) -> np.ndarray:
        """
        Load image from file path
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image as numpy array in BGR format
        """
        try:
            image = cv2.imread(str(file_path))
            if image is None:
                raise ImageValidationError(f"Could not load image from {file_path}")
            
            logger.info(f"Loaded image from file: {image.shape}")
            return image
            
        except Exception as e:
            raise ImageValidationError(f"Failed to load image from file", str(e))
    
    @staticmethod
    def save_image_to_bytes(image: np.ndarray, format: str = 'PNG') -> bytes:
        """
        Convert OpenCV image to bytes
        
        Args:
            image: OpenCV image (BGR)
            format: Output format ('PNG', 'JPEG')
            
        Returns:
            Image as bytes
        """
        try:
            # Convert BGR to RGB for PIL
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            # Save to bytes
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format=format)
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            raise ProcessingError(f"Failed to convert image to bytes", str(e))
    
    @staticmethod
    def save_image_to_file(image: np.ndarray, file_path: Union[str, Path]) -> None:
        """Save OpenCV image to file"""
        try:
            success = cv2.imwrite(str(file_path), image)
            if not success:
                raise ProcessingError(f"Failed to save image to {file_path}")
            
            logger.info(f"Saved image to {file_path}")
            
        except Exception as e:
            raise ProcessingError(f"Failed to save image to file", str(e))
    
    @staticmethod
    def resize_image(image: np.ndarray, max_width: int = None, max_height: int = None, 
                    maintain_aspect: bool = True) -> np.ndarray:
        """
        Resize image while optionally maintaining aspect ratio
        
        Args:
            image: Input image
            max_width: Maximum width
            max_height: Maximum height  
            maintain_aspect: Whether to maintain aspect ratio
            
        Returns:
            Resized image
        """
        try:
            h, w = image.shape[:2]
            
            if max_width is None and max_height is None:
                return image
            
            if maintain_aspect:
                # Calculate scale factor
                scale_w = max_width / w if max_width else float('inf')
                scale_h = max_height / h if max_height else float('inf')
                scale = min(scale_w, scale_h, 1.0)  # Don't upscale
                
                new_w = int(w * scale)
                new_h = int(h * scale)
            else:
                new_w = max_width or w
                new_h = max_height or h
            
            if new_w == w and new_h == h:
                return image
            
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h}")
            
            return resized
            
        except Exception as e:
            logger.error(f"Image resize failed: {e}")
            return image
    
    @staticmethod
    def draw_text_boxes(image: np.ndarray, text_boxes: List[TextBox], 
                       color: Tuple[int, int, int] = (0, 255, 0), 
                       thickness: int = 2) -> np.ndarray:
        """
        Draw bounding boxes on image for visualization
        
        Args:
            image: Input image
            text_boxes: List of text boxes to draw
            color: BGR color for boxes
            thickness: Line thickness
            
        Returns:
            Image with drawn bounding boxes
        """
        try:
            result = image.copy()
            
            for i, text_box in enumerate(text_boxes):
                bbox = text_box.bbox
                
                # Draw rectangle
                cv2.rectangle(result, 
                            (bbox.x1, bbox.y1), 
                            (bbox.x2, bbox.y2), 
                            color, thickness)
                
                # Add text label
                label = f"{i}: {text_box.text[:20]}..."
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                
                # Background for text
                cv2.rectangle(result, 
                            (bbox.x1, bbox.y1 - label_size[1] - 5),
                            (bbox.x1 + label_size[0], bbox.y1),
                            color, -1)
                
                # Text
                cv2.putText(result, label,
                          (bbox.x1, bbox.y1 - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                          (255, 255, 255), 1)
            
            logger.debug(f"Drew {len(text_boxes)} text boxes on image")
            return result
            
        except Exception as e:
            logger.error(f"Failed to draw text boxes: {e}")
            return image
    
    @staticmethod
    def crop_region(image: np.ndarray, bbox: BoundingBox, padding: int = 0) -> np.ndarray:
        """
        Crop a region from image
        
        Args:
            image: Source image
            bbox: Bounding box to crop
            padding: Additional padding around box
            
        Returns:
            Cropped image region
        """
        try:
            h, w = image.shape[:2]
            
            x1 = max(0, bbox.x1 - padding)
            y1 = max(0, bbox.y1 - padding) 
            x2 = min(w, bbox.x2 + padding)
            y2 = min(h, bbox.y2 + padding)
            
            return image[y1:y2, x1:x2]
            
        except Exception as e:
            logger.error(f"Failed to crop region: {e}")
            return image
    
    @staticmethod
    def enhance_image_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        Enhance image for better OCR results
        
        Args:
            image: Input image
            
        Returns:
            Enhanced image
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Apply slight blur to reduce noise
            enhanced = cv2.bilateralFilter(enhanced, 5, 50, 50)
            
            # Convert back to BGR if original was color
            if len(image.shape) == 3:
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return image
    
    @staticmethod
    def convert_pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format"""
        try:
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            raise ProcessingError(f"Failed to convert PIL to OpenCV", str(e))
    
    @staticmethod
    def convert_cv2_to_pil(cv_image: np.ndarray) -> Image.Image:
        """Convert OpenCV image to PIL format"""
        try:
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb_image)
        except Exception as e:
            raise ProcessingError(f"Failed to convert OpenCV to PIL", str(e))
    
    @staticmethod
    def image_to_base64(image: np.ndarray, format: str = 'PNG') -> str:
        """Convert image to base64 string"""
        try:
            image_bytes = ImageUtils.save_image_to_bytes(image, format)
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            raise ProcessingError(f"Failed to convert image to base64", str(e))
    
    @staticmethod
    def base64_to_image(base64_string: str) -> np.ndarray:
        """Convert base64 string to image"""
        try:
            image_bytes = base64.b64decode(base64_string)
            return ImageUtils.load_image_from_bytes(image_bytes)
        except Exception as e:
            raise ProcessingError(f"Failed to convert base64 to image", str(e))
    
    @staticmethod
    def get_image_info(image: np.ndarray) -> dict:
        """Get basic information about an image"""
        try:
            height, width = image.shape[:2]
            channels = image.shape[2] if len(image.shape) == 3 else 1
            
            return {
                'width': width,
                'height': height, 
                'channels': channels,
                'dtype': str(image.dtype),
                'size_bytes': image.nbytes,
                'aspect_ratio': width / height
            }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {}
    
    @staticmethod
    def validate_text_box_bounds(text_box: TextBox, image_shape: Tuple[int, int]) -> bool:
        """Validate that text box is within image bounds"""
        try:
            height, width = image_shape[:2]
            bbox = text_box.bbox
            
            return (0 <= bbox.x1 < width and 
                   0 <= bbox.y1 < height and
                   0 <= bbox.x2 <= width and
                   0 <= bbox.y2 <= height and
                   bbox.x1 < bbox.x2 and
                   bbox.y1 < bbox.y2)
        except Exception:
            return False