from django.urls import path
from django.contrib.sitemaps.views import index, sitemap
from .views import StaticViewSitemap


sitemaps = {
    # Ключи словаря (например, 'static') используются как значение <section>
    'static': StaticViewSitemap,
    # 'other': OtherSitemap # Здесь могут быть другие классы sitemap
}

urlpatterns = [
    # 1. URL для индекса sitemap (sitemap.xml). Не требует параметра <section>.
    path('sitemap.xml',
         index,
         {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap_index'),

    # 2. URL для секционных sitemap (sitemap-static.xml, sitemap-other.xml).
    # Этот шаблон обязательно должен содержать параметр <section> для корректного reverse-поиска.
    path('sitemap-<section>.xml',
         sitemap,
         {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]