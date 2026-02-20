from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from .settings.base import FEATURES


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='empty.html'), name='index'),
]


if FEATURES['ACCOUNTS']:
    urlpatterns += [
        path('accounts/', include('apps.accounts.urls')),
    ]

if FEATURES['ADMIN_PANEL']:
    urlpatterns += [
        path('admin_panel/', include('apps.admin_panel.urls')),
    ]

if FEATURES['PEOPLE']:
    urlpatterns += [
        path('people/', include('apps.people.urls')),
    ]

if FEATURES['DOCUMENTS']:
    urlpatterns += [
        path('documents/', include('apps.documents.urls')),
    ]

if FEATURES['BLOG']:
    urlpatterns += [
        path('blogs/', include('apps.blogs.urls')),
    ]

if FEATURES['SITEMAP']:
    urlpatterns += [
        path('map/', include('apps.sitemaps.urls')),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)