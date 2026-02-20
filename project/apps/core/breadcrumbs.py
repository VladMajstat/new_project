# apps/core/breadcrumbs.py (или любое другое место)
from functools import wraps
from django.urls import reverse


def breadcrumb(title, url_name=None, *url_args, **url_kwargs):
    """
    Декоратор для добавления хлебных крошек в request.
    Использование: @breadcrumb("Заголовок", "имя_url")
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request, 'breadcrumbs'):
                request.breadcrumbs = []

            # Определяем URL
            href = None
            if url_name:
                try:
                    href = reverse(url_name, args=url_args, kwargs=url_kwargs)
                except:
                    href = url_name


            request.breadcrumbs.append({'title': title, 'url': href})

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def add_breadcrumb(request, title, url_name=None, *url_args, **url_kwargs):
    """
    Функция для добавления крошки ВНУТРИ view (динамически).
    """
    if not hasattr(request, 'breadcrumbs'):
        request.breadcrumbs = []

    href = None
    if url_name:
        try:
            href = reverse(url_name, args=url_args, kwargs=url_kwargs)
        except:
            href = url_name

    request.breadcrumbs.append({'title': title, 'url': href})