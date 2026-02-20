from .base import  *


STATIC_ROOT = os.path.join(BASE_DIR, 'staticroot')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'project', 'static')
]

