"""
ASGI config for DMDX_Django project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DMDX_Django.settings')

django_asgi_app = get_asgi_application()

from django.conf import settings

if getattr(settings, 'ENABLE_CHANNELS', False):
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.urls import path

    from DMDX_Django.consumers import DeliveryConsumer, NPDocumentConsumer

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter([
                path('wss/add_new_delivery_loading/', DeliveryConsumer.as_asgi()),
                path('wss/np_document_updates/', NPDocumentConsumer.as_asgi()),
            ])
        ),
    })
else:
    application = django_asgi_app
