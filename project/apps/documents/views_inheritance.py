from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
import json
import os
import base64
from io import BytesIO
from PIL import Image
import magic  # Для визначення MIME типів

from .models import DocumentUpload, DocumentPhoto
from .forms import DispoliveReportForm as ReviewForm, DocumentPhotoForm
from .services.pdf_utils import pdf_page_to_base64_png
from .services.gpt_client import parse_form_page_to_new_parser
from .services.dispolive_logger import get_dispolive_logger

from dispolive_de.parser_new import build_payload
from dispolive_de.api_client import create_driver_report


class BaseDocumentUploadView(LoginRequiredMixin, View):
    """
    Базовий клас для завантаження документів з підтримкою різних MIME типів.
    Реалізує принцип DRY через універсальну логіку обробки.
    """
    template_name = None  # Override в нащадках
    upload_type = None    # Override в нащадках: 'pdf', 'photo', 'document'
    
    # Налаштування для нащадків
    accepted_mime_types = []  # Список прийнятих MIME типів
    mobile_optimized = False  # Чи оптимізовано для мобільних
    show_camera_button = False  # Чи показувати кнопку камери
    max_file_size = 10 * 1024 * 1024  # 10MB за замовчуванням
    
    def get_context_data(self, **kwargs):
        """Отримання контексту для шаблону"""
        context = kwargs
        context.update({
            'uploads': self.get_recent_uploads(),
            'upload_type': self.upload_type,
            'accepted_mime_types': self.get_accepted_mime_types(),
            'mobile_optimized': self.is_mobile_optimized(),
            'show_camera_button': self.show_camera_button,
            'max_file_size_mb': self.max_file_size / (1024 * 1024),
        })
        
        # Додаємо форму для фото, якщо потрібно
        if self.upload_type in ['photo', 'document']:
            context['form'] = DocumentPhotoForm()
            
        return context
    
    def get_accepted_mime_types(self):
        """Повертає список прийнятих MIME типів"""
        return self.accepted_mime_types
    
    def is_mobile_optimized(self):
        """Перевіряє чи оптимізовано для мобільних"""
        return self.mobile_optimized
    
    def get_recent_uploads(self, limit=50):
        """Отримання останніх завантажень для поточного користувача"""
        queryset = DocumentUpload.objects.filter(user=self.request.user)
        
        # Фільтруємо за типом завантаження
        if self.upload_type == 'photo':
            queryset = queryset.filter(photos__isnull=False).distinct()
        elif self.upload_type == 'pdf':
            queryset = queryset.filter(file__isnull=False).distinct()
            
        return queryset.only(
            'id', 'original_name', 'created_at', 'processing_status'
        ).order_by("-created_at")[:limit]
    
    def process_document(self, upload_obj, file_obj=None, file_path=None):
        """
        Універсальна обробка документів для всіх MIME типів.
        
        Args:
            upload_obj: DocumentUpload instance
            file_obj: UploadedFile object (для нових завантажень)
            file_path: Path to file (для існуючих файлів)
            
        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        try:
            # Визначаємо шлях до файлу
            if file_path:
                actual_file_path = file_path
            elif file_obj:
                actual_file_path = file_obj.path if hasattr(file_obj, 'path') else file_obj.temporary_file_path()
            else:
                raise ValueError("Не вказано файл для обробки")
            
            # Визначаємо MIME тип
            mime_type = self._get_mime_type(actual_file_path)
            
            # Перевіряємо чи підтримується цей MIME тип
            if mime_type not in self.get_accepted_mime_types():
                return False, f"Непідтримуваний тип файлу: {mime_type}"
            
            # Конвертуємо в base64 залежно від типу
            base64_data = self._convert_to_base64(actual_file_path, mime_type)
            
            # Парсимо через GPT (єдиний алгоритм для всіх типів)
            prescription_json = parse_form_page_to_new_parser(base64_data)
            
            # Зберігаємо результат
            upload_obj.parsed_data = prescription_json
            upload_obj.processing_status = "pending_review"
            upload_obj.file_type = mime_type  # Зберігаємо тип файлу
            upload_obj.save(update_fields=["parsed_data", "processing_status", "file_type"])
            
            return True, None
            
        except Exception as e:
            upload_obj.processing_status = "error"
            upload_obj.processing_error = str(e)
            upload_obj.save(update_fields=["processing_status", "processing_error"])
            return False, str(e)
    
    def _get_mime_type(self, file_path):
        """Визначення MIME типу файлу"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except:
            # Fallback до розширення файлу
            ext = os.path.splitext(file_path)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.heic': 'image/heic',
                '.heif': 'image/heif',
            }
            return mime_types.get(ext, 'application/octet-stream')
    
    def _convert_to_base64(self, file_path, mime_type):
        """Конвертація файлу в base64 залежно від MIME типу"""
        if mime_type == 'application/pdf':
            return pdf_page_to_base64_png(file_path, page_number=1)
        elif mime_type.startswith('image/'):
            return self._image_to_base64(file_path, mime_type)
        else:
            raise ValueError(f"Непідтримуваний MIME тип для конвертації: {mime_type}")
    
    def _image_to_base64(self, image_path, mime_type):
        """Конвертація зображення в base64 з підтримкою різних форматів"""
        img = Image.open(image_path)
        
        # Обробка HEIC/HEIF (може потребувати додаткових бібліотек)
        if mime_type in ['image/heic', 'image/heif']:
            try:
                # Конвертація в JPEG для подальшої обробки
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=95)
                return base64.b64encode(buffered.getvalue()).decode()
            except Exception as e:
                raise ValueError(f"Помилка конвертації HEIC/HEIF: {str(e)}")
        
        # Стандартні формати зображень
        buffered = BytesIO()
        
        # Зберігаємо в JPEG для оптимізації
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        img.save(buffered, format="JPEG", quality=95)
        return base64.b64encode(buffered.getvalue()).decode()
    
    def handle_ajax_response(self, success, upload_obj=None, error=None):
        """Обробка AJAX відповіді"""
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
    
    def validate_file(self, file_obj):
        """Валідація файлу"""
        # Перевірка розміру
        if file_obj.size > self.max_file_size:
            return False, f"Розмір файлу перевищує {self.max_file_size / (1024 * 1024):.1f}MB"
        
        # Перевірка MIME типу
        mime_type = self._get_mime_type(file_obj.temporary_file_path())
        if mime_type not in self.get_accepted_mime_types():
            return False, f"Непідтримуваний тип файлу: {mime_type}"
        
        return True, None


class PDFUploadView(BaseDocumentUploadView):
    """
    View для завантаження PDF файлів.
    Наслідує BaseDocumentUploadView та обмежує до PDF.
    """
    template_name = 'documents/upload_inheritance.html'
    upload_type = 'pdf'
    accepted_mime_types = ['application/pdf']
    mobile_optimized = False
    show_camera_button = False
    
    def get(self, request):
        """GET запит - показуємо форму завантаження PDF"""
        context = self.get_context_data()
        return render(request, self.template_name, context)
    
    def post(self, request):
        """POST запит - обробка завантаження PDF"""
        if not request.FILES.get("file"):
            return redirect("documents:upload")
        
        file_obj = request.FILES["file"]
        
        # Валідація файлу
        is_valid, error = self.validate_file(file_obj)
        if not is_valid:
            messages.error(request, error)
            return redirect("documents:upload")
        
        # Створюємо об'єкт завантаження
        upload_obj = DocumentUpload.objects.create(
            user=request.user,
            file=file_obj,
            original_name=file_obj.name,
            processing_status="processing",
            processing_error=""
        )
        
        # Обробляємо документ
        success, error = self.process_document(
            upload_obj=upload_obj,
            file_obj=file_obj
        )
        
        if success:
            return redirect("documents:review", pk=upload_obj.pk)
        else:
            messages.error(request, f"Помилка обробки: {error}")
            return redirect("documents:upload")


class PhotoUploadView(BaseDocumentUploadView):
    """
    View для завантаження фото.
    Розширює базовий функціонал, підтримує фото + PDF.
    Оптимізовано для мобільних пристроїв.
    """
    template_name = 'documents/photo_upload_inheritance.html'
    upload_type = 'photo'
    accepted_mime_types = [
        'image/jpeg', 'image/png', 'image/heic', 'image/heif',
        'application/pdf'  # <-- Підтримуємо PDF!
    ]
    mobile_optimized = True
    show_camera_button = True
    max_file_size = 15 * 1024 * 1024  # 15MB для фото
    
    def get(self, request):
        """GET запит - показуємо форму з кнопками камери/галереї"""
        context = self.get_context_data()
        return render(request, self.template_name, context)
    
    def post(self, request):
        """POST запит - обробка завантаження фото/PDF"""
        # Перевіряємо чи це завантаження через форму або через AJAX
        if 'image' in request.FILES:
            # Завантаження через стандартну форму
            return self._handle_form_upload(request)
        else:
            # Завантаження через drag & drop або інший спосіб
            return self._handle_direct_upload(request)
    
    def _handle_form_upload(self, request):
        """Обробка завантаження через форму DocumentPhotoForm"""
        form = DocumentPhotoForm(request.POST, request.FILES)
        
        if not form.is_valid():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            context = self.get_context_data(form=form)
            return render(request, self.template_name, context)
        
        # Створюємо об'єкт завантаження
        upload_obj = DocumentUpload.objects.create(
            user=request.user,
            original_name=f"Photo {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            processing_status="processing",
            processing_error=""
        )
        
        # Зберігаємо фото
        photo = form.save(commit=False)
        photo.document = upload_obj
        photo.user = request.user
        photo.save()
        
        # Обробляємо документ
        success, error = self.process_document(
            upload_obj=upload_obj,
            file_path=photo.image.path
        )
        
        # Обробка відповіді
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.handle_ajax_response(success, upload_obj, error)
        
        if success:
            return redirect("documents:review", pk=upload_obj.pk)
        else:
            messages.error(request, f"Помилка обробки: {error}")
            return redirect('documents:photo_upload')
    
    def _handle_direct_upload(self, request):
        """Обробка прямого завантаження файлу"""
        if 'file' not in request.FILES:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Файл не надано'}, status=400)
            return redirect('documents:photo_upload')
        
        file_obj = request.FILES['file']
        
        # Валідація файлу
        is_valid, error = self.validate_file(file_obj)
        if not is_valid:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
            return redirect('documents:photo_upload')
        
        # Створюємо об'єкт завантаження
        upload_obj = DocumentUpload.objects.create(
            user=request.user,
            original_name=file_obj.name,
            processing_status="processing",
            processing_error=""
        )
        
        # Якщо це фото, створюємо DocumentPhoto
        if file_obj.content_type.startswith('image/'):
            DocumentPhoto.objects.create(
                document=upload_obj,
                user=request.user,
                image=file_obj
            )
        else:
            # Якщо це PDF, зберігаємо як файл
            upload_obj.file = file_obj
            upload_obj.save()
        
        # Обробляємо документ
        success, error = self.process_document(
            upload_obj=upload_obj,
            file_obj=file_obj
        )
        
        # Обробка відповіді
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.handle_ajax_response(success, upload_obj, error)
        
        if success:
            return redirect("documents:review", pk=upload_obj.pk)
        else:
            messages.error(request, f"Помилка обробки: {error}")
            return redirect('documents:photo_upload')


class UniversalDocumentUploadView(PhotoUploadView):
    """
    Універсальний view для всіх типів документів.
    Поєднує функціонал PDF та фото завантаження.
    """
    template_name = 'documents/universal_upload.html'
    upload_type = 'document'
    accepted_mime_types = [
        'application/pdf',
        'image/jpeg', 'image/png', 'image/heic', 'image/heif',
        'image/tiff', 'image/bmp', 'image/webp'
    ]
    mobile_optimized = True
    show_camera_button = True
    max_file_size = 20 * 1024 * 1024  # 20MB


# Function-based view wrappers для backward compatibility
upload = PDFUploadView.as_view()
photo_upload = PhotoUploadView.as_view()
universal_upload = UniversalDocumentUploadView.as_view()


@login_required
def review(request, pk):
    """Перегляд результатів обробки документа"""
    upload = get_object_or_404(DocumentUpload, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)            # ?????????????????????? ???????? ?????????? ?????????? ?? ?????????????????? parsed_data
            updated_data = form.to_parsed_data()
            existing = upload.parsed_data or {}
            existing_flags = []
            if isinstance(existing, dict):
                existing_flags = existing.get("flags") or []
            if isinstance(updated_data, dict):
                updated_data["flags"] = existing_flags
            upload.parsed_data = updated_data
            
            # Створюємо звіт в системі
            try:
                payload = build_payload(upload.parsed_data)
                create_driver_report(payload)
                messages.success(request, 'Документ успішно оброблено та відправлено в систему')
            except Exception as e:
                messages.error(request, f'Помилка відправки в систему: {str(e)}')
            
            return redirect('documents:upload')
    else:
        # Використовуємо from_parsed_data для правильного маппінгу даних з GPT
        form = ReviewForm.from_parsed_data(upload.parsed_data)
    
    # Prepare Dispolive payload for display (preview from parsed_data)
    dispolive_payload_json = None
    try:
        preview_payload = build_payload(upload.parsed_data or {})
        dispolive_payload_json = json.dumps(preview_payload, indent=2, ensure_ascii=False)
    except Exception as e:
        logger = get_dispolive_logger()
        logger.warning("Failed to build payload preview for upload_id=%s: %s", upload.pk, str(e))
    
    context = {
        'upload': upload,
        'form': form,
        'parsed_data': upload.parsed_data or {},
        'dispolive_payload': dispolive_payload_json,
        'error_message': upload.processing_error if upload.processing_status == "error" else ""
    }
    
    return render(request, 'documents/review.html', context)


@login_required
def upload_status(request, pk):
    """API endpoint для перевірки статусу завантаження"""
    upload = get_object_or_404(DocumentUpload, pk=pk, user=request.user)
    
    return JsonResponse({
        'status': upload.processing_status,
        'error': upload.processing_error,
        'created_at': upload.created_at.isoformat(),
        'updated_at': upload.updated_at.isoformat()
    })
