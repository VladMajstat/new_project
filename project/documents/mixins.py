"""
Mixins for document processing views.
Implements DRY principle by consolidating common logic for PDF and Photo uploads.
"""
import base64
from io import BytesIO
from typing import Dict, Any, Optional
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from PIL import Image

from .models import DocumentUpload, DocumentPhoto
from .services.pdf_utils import pdf_page_to_base64_png
from .services.gpt_client import parse_form_page_to_new_parser


class DocumentProcessingMixin:
    """
    Mixin for common document processing logic.
    Used by both PDF and Photo upload views.
    """
    
    def process_and_parse_document(self, upload_obj: DocumentUpload, 
                                   file_path: str, 
                                   is_photo: bool = False) -> tuple[bool, Optional[str]]:
        """
        Process document (PDF or Photo) and parse with GPT.
        
        Args:
            upload_obj: DocumentUpload instance
            file_path: Path to file (PDF or image)
            is_photo: True if processing photo, False if PDF
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Convert to base64
            if is_photo:
                img_b64 = self._photo_to_base64(file_path)
            else:
                img_b64 = pdf_page_to_base64_png(file_path, page_number=1)
            
            # Parse with GPT
            prescription_json = parse_form_page_to_new_parser(img_b64)
            # Enforce transport-type consistency based on parsed JSON
            b11 = prescription_json.get('block11_transport_type', {})
            b12 = prescription_json.get('block12_transport_mode', {})
            if b11.get('taxi_mietwagen', False):
                b11['ktw_medizinisch'] = False
            if not b11.get('ktw_medizinisch', False):
                b12['rollstuhl'] = False
                b12['tragestuhl'] = False
                b12['liegend'] = False
            prescription_json['block11_transport_type'] = b11
            prescription_json['block12_transport_mode'] = b12


            # Enforce transport-type consistency: if KTW isn't selected, clear transport position.
            b11 = prescription_json.get('block11_transport_type', {})
            b12 = prescription_json.get('block12_transport_mode', {})
            if b11.get('taxi_mietwagen', False) and b11.get('ktw_medizinisch', False):
                b11['ktw_medizinisch'] = False
            if not b11.get('ktw_medizinisch', False):
                b12['rollstuhl'] = False
                b12['tragestuhl'] = False
                b12['liegend'] = False
            prescription_json['block11_transport_type'] = b11
            prescription_json['block12_transport_mode'] = b12
            
            # Save parsed data
            upload_obj.parsed_data = prescription_json
            upload_obj.processing_status = "pending_review"
            upload_obj.save(update_fields=["parsed_data", "processing_status"])
            
            return True, None
            
        except Exception as e:
            upload_obj.processing_status = "error"
            upload_obj.processing_error = str(e)
            upload_obj.save(update_fields=["processing_status", "processing_error"])
            return False, str(e)
    
    def _photo_to_base64(self, image_path: str) -> str:
        """Convert photo to base64 string."""
        img = Image.open(image_path)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    def handle_ajax_response(self, success: bool, upload_obj: DocumentUpload = None, 
                           error: str = None) -> JsonResponse:
        """
        Handle AJAX response for document upload.
        
        Args:
            success: Whether upload was successful
            upload_obj: DocumentUpload instance (if successful)
            error: Error message (if failed)
            
        Returns:
            JsonResponse with appropriate data
        """
        if success and upload_obj:
            return JsonResponse({
                'success': True,
                'redirect_url': f'/documents/review/{upload_obj.pk}/'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': error or 'Unknown error'
            }, status=500)
    
    def get_recent_uploads(self, user, photo_only: bool = False, limit: int = 50):
        """
        Get recent uploads for user.
        
        Args:
            user: User instance
            photo_only: If True, filter only photo uploads
            limit: Maximum number of uploads to return
            
        Returns:
            QuerySet of DocumentUpload objects
        """
        queryset = DocumentUpload.objects.filter(user=user)
        
        if photo_only:
            queryset = queryset.filter(photos__isnull=False).distinct()
        
        return queryset.only(
            'id', 'original_name', 'created_at', 'processing_status'
        ).order_by("-created_at")[:limit]


class DocumentUploadMixin(DocumentProcessingMixin):
    """
    Mixin specifically for document upload views.
    Extends DocumentProcessingMixin with upload-specific logic.
    """
    
    def create_upload_object(self, user, original_name: str, file=None) -> DocumentUpload:
        """
        Create DocumentUpload object.
        
        Args:
            user: User instance
            original_name: Original filename
            file: File object (optional, for PDF uploads)
            
        Returns:
            DocumentUpload instance
        """
        return DocumentUpload.objects.create(
            user=user,
            file=file,
            original_name=original_name,
            processing_status="processing",
            processing_error=""
        )
    
    def create_photo_upload_object(self, user, photo_form) -> tuple[DocumentUpload, DocumentPhoto]:
        """
        Create DocumentUpload and DocumentPhoto objects.
        
        Args:
            user: User instance
            photo_form: Validated DocumentPhotoForm
            
        Returns:
            Tuple of (DocumentUpload, DocumentPhoto)
        """
        # Create upload object
        upload_obj = DocumentUpload.objects.create(
            user=user,
            original_name=f"Photo {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            processing_status="processing",
            processing_error=""
        )
        
        # Save photo linked to document
        photo = photo_form.save(commit=False)
        photo.document = upload_obj
        photo.user = user
        photo.save()
        
        return upload_obj, photo
