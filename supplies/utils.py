import logging
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)

def get_csrf_token(request):
    """
    Утиліта для отримання CSRF токена
    """
    try:
        token = get_token(request)
        return token
    except Exception as e:
        logger.error(f"Error getting CSRF token: {e}")
        return None

def validate_csrf_token(request):
    """
    Утиліта для валідації CSRF токена
    """
    try:
        from django.middleware.csrf import CsrfViewMiddleware
        middleware = CsrfViewMiddleware(lambda req: None)
        middleware.process_view(request, None, (), {})
        return True
    except Exception as e:
        logger.warning(f"CSRF validation failed: {e}")
        return False

@csrf_exempt
@require_http_methods(["GET"])
def csrf_token_view(request):
    """
    API endpoint для отримання CSRF токена
    """
    try:
        token = get_csrf_token(request)
        if token:
            return JsonResponse({'csrfToken': token})
        else:
            return JsonResponse({'error': 'Failed to generate CSRF token'}, status=500)
    except Exception as e:
        logger.error(f"Error in csrf_token_view: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

