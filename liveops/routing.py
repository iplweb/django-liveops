"""
ASGI WebSocket URL patterns for liveops.

Include these in your project's ASGI routing instead of (or in addition to)
channels_broadcast's own routing. LiveOperationConsumer is a drop-in
replacement for NotificationsConsumer at the same path.

Usage in your ASGI app::

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from liveops.routing import websocket_urlpatterns

    application = ProtocolTypeRouter({
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
"""

from django.urls import path

from liveops.consumers import LiveOperationConsumer

websocket_urlpatterns = [
    path("asgi/notifications/", LiveOperationConsumer.as_asgi()),
]
