from django.conf import settings

def site_features(request):
    return {
        'FEATURES': settings.FEATURES
    }