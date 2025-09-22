"""
ASGI config for iTech project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iTech.settings')
django.setup()


from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import iTech.routing

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# Get the ASGI application
application = ProtocolTypeRouter({
    "http": django_asgi_app,  # Use the standard Django ASGI app for HTTP
    "websocket": AuthMiddlewareStack(
        URLRouter(
            iTech.routing.websocket_urlpatterns
        )
    ),
})
