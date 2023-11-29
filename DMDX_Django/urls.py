from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('supplies.urls')),
    path('celery-progress/', include('celery_progress.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
