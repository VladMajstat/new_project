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
import logging

from .models import DocumentUpload, DocumentPhoto
from .services.pdf_utils import pdf_page_to_base64_png, pdf_page_crop_to_base64_png
from .services.gpt_client import parse_form_page_to_new_parser, parse_insurance_status, parse_ordering_party_phone, parse_betriebsstaetten_nr
from .services.normalization import normalize_block13_doctor_contact, normalize_insurance_block


logger = logging.getLogger(__name__)

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
            try:
                logger.info("Insurance block1: %s", prescription_json.get("block1_insurance"))
                logger.info("Insurance block2: %s", prescription_json.get("block2_patient"))
            except Exception:
                pass

            # Normalize ordering party
            prescription_json = normalize_block13_doctor_contact(prescription_json)

            # Ordering party phone retry if empty
            try:
                b13 = prescription_json.get("block13_doctor_contact", {}) or {}
                if not (b13.get("auftraggeberTelefon") or "").strip():
                    phone_only = parse_ordering_party_phone(img_b64)
                    if phone_only:
                        b13["auftraggeberTelefon"] = phone_only
                        prescription_json["block13_doctor_contact"] = b13
                logger.info("Ordering party phone retry result: %s", b13.get("auftraggeberTelefon", ""))
            except Exception:
                pass

            # Normalize insurance
            prescription_json = normalize_insurance_block(prescription_json)

            # Insurance status retry if empty
            try:
                b2 = prescription_json.get("block2_patient", {}) or {}
                if not (b2.get("status") or "").strip():
                    status_only = parse_insurance_status(img_b64)
                    logger.info("Insurance status retry result: %s", status_only)
                    if status_only:
                        b2["status"] = status_only
                        prescription_json["block2_patient"] = b2
                        prescription_json = normalize_insurance_block(prescription_json)
            except Exception:
                pass

            # Betriebsstaetten-Nr retry if missing or invalid
            try:
                b3 = prescription_json.get("block3_doctor_ids", {}) or {}
                current = str(b3.get("betriebsstaetten_nr", "") or "")
                digits = "".join(ch for ch in current if ch.isdigit())
                if len(digits) != 9:
                    # crop around Betriebsstaetten-Nr row (relative coords)
                    bs_crop = (
                        pdf_page_crop_to_base64_png(file_path, 1, 350, (0.06, 0.39, 0.60, 0.48))
                        if not is_photo else
                        self._crop_base64_region(img_b64, (0.06, 0.39, 0.60, 0.48), scale=2)
                    )
                    bs_only = parse_betriebsstaetten_nr(bs_crop)
                    bs_digits = "".join(ch for ch in (bs_only or "") if ch.isdigit())
                    if len(bs_digits) != 9:
                        # fallback to full page
                        bs_only = parse_betriebsstaetten_nr(img_b64)
                        bs_digits = "".join(ch for ch in (bs_only or "") if ch.isdigit())
                    if len(bs_digits) == 9:
                        b3["betriebsstaetten_nr"] = bs_digits
                        prescription_json["block3_doctor_ids"] = b3
                logger.info("Betriebsstaetten retry result: %s", b3.get("betriebsstaetten_nr", ""))
            except Exception:
                pass

            try:
                logger.info("Insurance block1 AFTER: %s", prescription_json.get("block1_insurance"))
                logger.info("Insurance block2 AFTER: %s", prescription_json.get("block2_patient"))
            except Exception:
                pass
            
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

    def _crop_base64_region(self, img_b64: str, box: tuple[float, float, float, float], scale: int = 1) -> str:
        """Crop base64 PNG/JPEG by relative box (x0,y0,x1,y1)."""
        img_bytes = base64.b64decode(img_b64)
        img = Image.open(BytesIO(img_bytes))
        w, h = img.size
        x0, y0, x1, y1 = box
        left = max(0, int(w * x0))
        top = max(0, int(h * y0))
        right = min(w, int(w * x1))
        bottom = min(h, int(h * y1))
        cropped = img.crop((left, top, right, bottom))
        if scale > 1:
            cropped = cropped.resize((cropped.width * scale, cropped.height * scale), Image.BICUBIC)
        buffered = BytesIO()
        cropped.save(buffered, format="JPEG")
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
