from django.urls import path
from .views import upload, review, clear_history, dispolive_log, photo_upload

app_name = 'documents'

urlpatterns = [
    path('upload/', upload, name='upload'),
    path('review/<int:pk>/', review, name='review'),
    path('clear-history/', clear_history, name='clear_history'),
    path('logs/dispolive/', dispolive_log, name='dispolive_log'),
    path('photo-upload/', photo_upload, name='photo_upload'), 
]
