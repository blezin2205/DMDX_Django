from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('supplies.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Тільки локально: debug_toolbar з’являється в INSTALLED_APPS лише коли DEBUG і немає DYNO (див. settings.py).
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
