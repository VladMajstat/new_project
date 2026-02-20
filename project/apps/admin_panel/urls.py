from django.urls import path
from django.conf import settings

from . import views


if settings.FEATURES['PEOPLE']:
    urlpatterns = [
        path('hrs/', views.hrs_list, name='hrs_list'),
        path('hrs/add', views.hr_add, name='hr_add'),
        path('hrs/<int:pk>/delete/', views.hr_delete, name='hr_delete'),
    ]
else:
    urlpatterns = [
        path('', views.admin_panel, name='admin_panel'),
    ]
