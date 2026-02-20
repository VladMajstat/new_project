"""
Service for processing uploaded photos:
- EXIF orientation correction
- Image optimization
- Size reduction
"""
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class PhotoProcessor:
    """Process and optimize document photos"""
    
    MAX_SIZE = (2000, 2000)  # Max dimensions
    QUALITY = 85  # JPEG quality
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    
    @staticmethod
    def process_photo(image_file):
        """
        Process uploaded photo:
        1. Correct EXIF orientation
        2. Resize if needed
        3. Optimize quality
        
        Returns: processed InMemoryUploadedFile
        """
        try:
            # Open image
            img = Image.open(image_file)
            
            # Correct EXIF orientation (critical for iPhone photos)
            img = ImageOps.exif_transpose(img)
            
            # Convert to RGB if needed (for PNG with alpha)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if larger than max size
            img.thumbnail(PhotoProcessor.MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Save to BytesIO with optimization
            output = BytesIO()
            img.save(
                output,
                format='JPEG',
                quality=PhotoProcessor.QUALITY,
                optimize=True
            )
            output.seek(0)
            
            # Create new InMemoryUploadedFile
            processed_file = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{image_file.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output),
                None
            )
            
            return processed_file
            
        except Exception as e:
            raise ValueError(f"Error processing photo: {str(e)}")
    
    @staticmethod
    def validate_photo(image_file):
        """
        Validate uploaded photo
        Returns: (is_valid, error_message)
        """
        # Check file size
        if image_file.size > PhotoProcessor.MAX_FILE_SIZE:
            return False, f"File too large. Max size: {PhotoProcessor.MAX_FILE_SIZE / (1024*1024)}MB"
        
        # Check MIME type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic', 'image/heif']
        if hasattr(image_file, 'content_type'):
            if image_file.content_type not in allowed_types:
                return False, f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        
        # Try to open as image
        try:
            img = Image.open(image_file)
            img.verify()
            image_file.seek(0)  # Reset file pointer after verify
            return True, None
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
