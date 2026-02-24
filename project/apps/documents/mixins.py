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
from PIL import Image, ImageEnhance, ImageStat
import pytesseract
import logging

from .models import DocumentUpload, DocumentPhoto
from .services.pdf_utils import pdf_page_to_base64_png, pdf_page_crop_to_base64_png
from .services.gpt_client import parse_form_page_to_new_parser


logger = logging.getLogger(__name__)

"""
Note: We intentionally avoid crop-based extraction here to keep a single
source of truth (the full page) and rely on the prompt for accuracy.
"""
# Minimal box for Arzt-Nr. only
ARZT_BOX = (0.36, 0.33, 0.62, 0.40)

class DocumentProcessingMixin:

    def _remove_vertical_lines(self, img: Image.Image) -> Image.Image:
        """Remove strong vertical table lines from a grayscale image."""
        if img.mode != "L":
            img = img.convert("L")
        w, h = img.size
        pix = img.load()

        mean = ImageStat.Stat(img).mean[0]
        dark_thresh = max(30, mean - 40)

        dark_cols = []
        for x in range(w):
            dark_count = 0
            for y in range(h):
                if pix[x, y] < dark_thresh:
                    dark_count += 1
            if dark_count / h > 0.7:
                dark_cols.append(x)

        for x in dark_cols:
            for y in range(h):
                pix[x, y] = 255
        return img

    def _remove_horizontal_lines(self, img: Image.Image) -> Image.Image:
        """Remove strong horizontal table lines from a grayscale image."""
        if img.mode != "L":
            img = img.convert("L")
        w, h = img.size
        pix = img.load()

        mean = ImageStat.Stat(img).mean[0]
        dark_thresh = max(30, mean - 40)

        dark_rows = []
        for y in range(h):
            dark_count = 0
            for x in range(w):
                if pix[x, y] < dark_thresh:
                    dark_count += 1
            if dark_count / w > 0.7:
                dark_rows.append(y)

        for y in dark_rows:
            for x in range(w):
                pix[x, y] = 255
        return img

    def _enhance_numeric(self, img: Image.Image) -> Image.Image:
        """Stronger enhancement for numeric rows (codes/IDs)."""
        if img.mode != "L":
            img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(3.0)
        img = ImageEnhance.Sharpness(img).enhance(3.0)
        img = self._remove_vertical_lines(img)
        img = self._remove_horizontal_lines(img)
        # Simple binarization (adaptive)
        pix = img.load()
        w, h = img.size
        mean = ImageStat.Stat(img).mean[0]
        thresh = max(90, mean - 30)
        for y in range(h):
            for x in range(w):
                pix[x, y] = 0 if pix[x, y] < thresh else 255
        return img

    def _ocr_digits_from_b64(self, img_b64: str) -> str:
        """OCR a crop and return the first 9-digit sequence, or empty."""
        try:
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes)).convert("L")
            config = "--psm 6 -c tessedit_char_whitelist=0123456789"
            raw = pytesseract.image_to_string(img, config=config)
            digits = ''.join(ch for ch in raw if ch.isdigit())
            for i in range(0, len(digits) - 8):
                cand = digits[i:i+9]
                if len(cand) == 9:
                    return cand
            return ""
        except Exception:
            return ""

    def _crop_base64_region(self, img_b64: str, box: tuple[float, float, float, float], scale: int = 1, enhance: bool = False, numeric_enhance: bool = False) -> str:
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
        if enhance:
            cropped = cropped.convert("L")
            cropped = ImageEnhance.Contrast(cropped).enhance(2.5)
            cropped = ImageEnhance.Sharpness(cropped).enhance(2.5)
            cropped = self._remove_vertical_lines(cropped)
            cropped = self._remove_horizontal_lines(cropped)
        if numeric_enhance:
            cropped = self._enhance_numeric(cropped)
        buffered = BytesIO()
        cropped.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()

    def _trip_direction_hints(self, img_b64: str) -> dict:
        """Detect trip direction checkboxes in the top-right block."""
        try:
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes)).convert("L")
            w, h = img.size
            mid = w // 2
            left_box = img.crop((0, 0, mid, h))
            right_box = img.crop((mid, 0, w, h))

            def _mark(box: Image.Image) -> bool:
                mean = ImageStat.Stat(box).mean[0]
                thresh = max(25, mean - 25)
                pix = box.load()
                dark = 0
                total = box.width * box.height
                for y in range(box.height):
                    for x in range(box.width):
                        if pix[x, y] < thresh:
                            dark += 1
                return (dark / max(1, total)) > 0.015

            return {
                "outbound": _mark(left_box),
                "return": _mark(right_box),
            }
        except Exception:
            return {"outbound": False, "return": False}

    def _photo_to_base64(self, image_path: str) -> str:
        """Convert photo to base64 string."""
        img = Image.open(image_path)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()

    def process_and_parse_document(self, upload_obj: DocumentUpload, file_path: str, is_photo: bool = False) -> tuple[bool, Optional[str]]:
        """Process document (PDF or Photo) and parse with GPT."""
        try:
            if is_photo:
                img_b64 = self._photo_to_base64(file_path)
            else:
                img_b64 = pdf_page_to_base64_png(file_path, page_number=1)
            arzt_b64 = self._crop_base64_region(img_b64, ARZT_BOX, scale=5, enhance=True, numeric_enhance=True)
            prescription_json = parse_form_page_to_new_parser(img_b64)

            # OCR fallback for Arzt-Nr. only
            try:
                if isinstance(prescription_json, dict) and isinstance(prescription_json.get("data"), dict):
                    d = prescription_json["data"]
                    arzt = ''.join(ch for ch in str(d.get("arzt_nr") or '') if ch.isdigit())
                    if len(arzt) != 9:
                        ocr_arzt = self._ocr_digits_from_b64(arzt_b64)
                        logger.info("OCR arzt_nr: %s", ocr_arzt)
                        if ocr_arzt and len(ocr_arzt) == 9:
                            d["arzt_nr"] = ocr_arzt
            except Exception:
                pass

            upload_obj.parsed_data = prescription_json
            upload_obj.processing_status = "pending_review"
            upload_obj.save(update_fields=["parsed_data", "processing_status"])
            return True, None

        except Exception as e:
            upload_obj.processing_status = "error"
            upload_obj.processing_error = str(e)
            upload_obj.save(update_fields=["processing_status", "processing_error"])
            return False, str(e)


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

    def get_recent_uploads(self, user, photo_only: bool = False, limit: int = 20):
        qs = DocumentUpload.objects.filter(user=user)
        if photo_only:
            qs = qs.filter(photos__isnull=False).distinct()
        return qs.order_by("-created_at")[:limit]

    def handle_ajax_response(self, success: bool, upload_obj: DocumentUpload, error: str | None):
        if success:
            redirect_url = redirect("documents:review", pk=upload_obj.pk).url
            return JsonResponse({
                "success": True,
                "redirect": redirect_url,
                "redirect_url": redirect_url,
            })
        return JsonResponse({
            "success": False,
            "error": error or "Unknown error",
        }, status=500)
