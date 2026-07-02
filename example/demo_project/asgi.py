"""
ASGI config for demo_project.

Routing:
  http      → Django ASGI app
  websocket → AllowedHostsOriginValidator
               → AuthMiddlewareStack
                 → URLRouter([path("asgi/notifications/", LiveOperationConsumer)])

LiveOperationConsumer extends channels_broadcast.NotificationsConsumer,
so the same path handles both channels_broadcast token subscription and
liveop snapshot-on-connect (§19.1).
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

from live_operations.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_project.settings")

# Unlike `runserver`, Daphne does not serve static files. Wrap the Django ASGI
# app in ASGIStaticFilesHandler so the demo's /static/ assets (htmx,
# live-operations.js, channels_broadcast) are served under Daphne in DEBUG.
# In real deployments a web server / CDN serves static instead.
django_asgi_app = ASGIStaticFilesHandler(get_asgi_application())

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
