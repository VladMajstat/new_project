from django.db import models
from django.conf import settings

class DocumentUpload(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='uploaded_documents')
    file = models.FileField(upload_to='uploads/pdfs/')
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    extracted_text = models.TextField(blank=True, default="")
    parsed_data = models.JSONField(null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        default="uploaded",
        choices=[
            ("uploaded", "uploaded"),
            ("processing", "processing"),
            ("pending_review", "pending_review"),
            ("done", "done"),
            ("error", "error"),
        ],
    )
    dispolive_payload = models.JSONField(null=True, blank=True)

    processing_error = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.original_name or "Unnamed Document"