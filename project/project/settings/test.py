from .local_conf import *  # noqa: F403,F401

# Enable django-solo tests
INSTALLED_APPS += ["solo", "solo.tests"]  # noqa: F405
