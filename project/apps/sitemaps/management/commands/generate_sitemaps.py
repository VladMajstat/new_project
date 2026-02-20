import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
from lxml import etree
from urllib.parse import urlparse


class Command(BaseCommand):
    help = 'Generates static sitemap.xml and all related sitemap files.'

    def handle(self, *args, **options):
        if not settings.STATIC_ROOT:
            self.stdout.write(self.style.ERROR("STATIC_ROOT не настроен в settings.py"))
            return

        output_dir = str(settings.STATIC_ROOT)  # Убедимся, что это строка
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Получаем текущий домен
        domain = settings.DOMAIN

        self.stdout.write(f"Использую внутренний домен для запроса: {domain}")
        # 🟢 КОНЕЦ ИСПРАВЛЕНИЯ 🟢

        sitemap_urls = []

        index_url = domain + reverse('django.contrib.sitemaps.views.sitemap_index')
        self.stdout.write(f"Загружаю индекс: {index_url}")

        try:
            r = requests.get(index_url)
            r.raise_for_status()  # Проверка на ошибки

            index_path = os.path.join(output_dir, 'sitemap.xml')
            with open(index_path, 'wb') as f:
                f.write(r.content)

            self.stdout.write(self.style.SUCCESS(f"Сохранен: {index_path}"))

            root = etree.fromstring(r.content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for loc in root.xpath('//ns:loc', namespaces=ns):
                sitemap_url = loc.text
                sitemap_urls.append(sitemap_url)

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при загрузке sitemap.xml: {e}"))
            return

        for url in sitemap_urls:
            url_data = urlparse(url)
            section_path = url_data.path  # '/sitemap-static.xml'

            internal_section_url = domain + section_path

            # (3) Получаем имя файла (как и раньше)
            filename = section_path.lstrip('/')  # 'sitemap-static.xml'

            self.stdout.write(f"Найден URL: {url}")
            self.stdout.write(f"Загружаю внутренний: {internal_section_url}")

            try:
                r_section = requests.get(internal_section_url)
                r_section.raise_for_status()

                section_path = os.path.join(output_dir, filename)
                with open(section_path, 'wb') as f:
                    f.write(r_section.content)

                self.stdout.write(self.style.SUCCESS(f"  -> Сохранен: {section_path}"))

            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"  -> Ошибка: {e}"))

        self.stdout.write(self.style.SUCCESS("\nГенерация Sitemap завершена."))

