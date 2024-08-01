"""
ASGI config for DMDX_Django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from django.urls import path
from DMDX_Django.consumers import DeliveryConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DMDX_Django.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('wss/add_new_delivery_loading/', DeliveryConsumer.as_asgi()),
        ])
    ),
})