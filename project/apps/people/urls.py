from django.urls import path
from . import views

urlpatterns = [
    path('hrs/<str:name>/', views.hr_profile, name='hr_profile'),
    path('hrs/<str:name>/edit/', views.hr_edit, name='hr_edit'),
    path('candidates/<int:pk>/', views.candidate_profile, name='candidate_profile'),
    path('candidates/<int:pk>/edit/', views.candidate_edit, name='candidate_edit'),
    path('candidates/add', views.candidate_add, name='candidate_add'),
    path('candidates/<int:pk>/delete/', views.candidate_delete, name='candidate_delete'),
    path('candidates/', views.candidates_list, name='candidates_list'),
    path('candidates/department/<slug:slug>/', views.candidates_list, name='candidates_by_department'),
    path('candidates/comments/<int:pk>/', views.candidate_comments_api, name='candidate_comments_api'),
    path('candidates/update-status/<int:pk>/', views.update_candidate_status, name='update_candidate_status'),
]