from django.contrib import admin
from .models import DocumentUpload

@admin.register(DocumentUpload)
class DocumentUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'user', 'created_at')
    search_fields = ('original_name', 'user__username', 'user__email')
    list_filter = ('created_at',)