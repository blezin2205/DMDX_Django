import logging
from datetime import timedelta

from django.db.models import Q
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .models import CustomUser

logger = logging.getLogger(__name__)

class CSRFErrorMiddleware(MiddlewareMixin):
    """
    Middleware для кращого оброблення CSRF помилок
    """
    
    def process_exception(self, request, exception):
        # In modern Django versions CSRF failures usually surface as PermissionDenied
        # and the failure view returns a 403. We heuristically detect CSRF-related
        # PermissionDenied to provide a JSON response for AJAX requests.
        is_csrf_failure = isinstance(exception, PermissionDenied) and 'csrf' in str(exception).lower()
        if is_csrf_failure:
            logger.warning(
                f"CSRF Error for user {request.user} on {request.path}: {exception}",
                extra={
                    'user': str(request.user),
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'referer': request.META.get('HTTP_REFERER', ''),
                    'remote_addr': request.META.get('REMOTE_ADDR', ''),
                }
            )
            
            # Якщо це AJAX запит, повертаємо JSON відповідь
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'CSRF token missing or incorrect',
                    'message': 'Будь ласка, оновіть сторінку та спробуйте знову',
                    'csrf_error': True
                }, status=403)
            
            # Для звичайних запитів повертаємо стандартну помилку
            return JsonResponse({
                'error': 'CSRF token missing or incorrect',
                'message': 'Будь ласка, оновіть сторінку та спробуйте знову'
            }, status=403)
        
        return None


class LastSeenMiddleware(MiddlewareMixin):
    """Оновлює last_seen для авторизованих користувачів (не частіше ніж раз на 90 с)."""

    THROTTLE_SECONDS = 90
    SKIP_PREFIXES = ('/static/', '/media/', '/favicon')

    def __call__(self, request):
        response = self.get_response(request)
        self._touch_last_seen(request)
        return response

    def _touch_last_seen(self, request):
        if not settings.ENABLE_LAST_SEEN_TRACKING:
            return
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return
        if request.path.startswith(self.SKIP_PREFIXES):
            return
        now = timezone.now()
        cutoff = now - timedelta(seconds=self.THROTTLE_SECONDS)
        CustomUser.objects.filter(pk=user.pk).filter(
            Q(last_seen__isnull=True) | Q(last_seen__lt=cutoff)
        ).update(last_seen=now)

