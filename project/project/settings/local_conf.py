import os
from .base import *

from dotenv import load_dotenv


load_dotenv()
conf_dir = os.path.dirname(__file__)

DEBUG = int(os.environ.get('DEBUG', 1))

if DEBUG:
    load_dotenv(os.path.join(conf_dir, '.env'))
    from .development import *
else:
    load_dotenv(os.path.join(conf_dir, '.env.prod'))
    from .producation import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}

