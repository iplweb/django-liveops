"""
URL configuration for liveops — the central, generic operation router.

These patterns serve EVERY ``LiveOperation`` subclass in the project. The
``op_type`` segment (``<app_label>.<model_name>``, see
``LiveOperation.op_type_key``) lets the generic views resolve the concrete
model with an O(1) lookup — no per-app URL wiring, no registry scan.

Mount ONCE in your project's root URLconf::

    path("live/", include("liveops.urls")),

Then ``operation.get_absolute_url()`` reverses ``liveops:live`` for any
subclass automatically.

Create/list views stay app-specific (they need a form/model and custom
templates) — wire those under your own app's namespace; their success
redirect targets ``liveops:live`` via ``get_absolute_url()``.

NOTE: no WebSocket path here (§19.1 — WS uses channels_broadcast's fixed
path /asgi/notifications/ + subscription_token, not a per-pk URL).
"""

from django.urls import path

from liveops.views import CancelView, LiveOperationView, RestartView

app_name = "liveops"

urlpatterns = [
    path("<str:op_type>/<uuid:pk>/", LiveOperationView.as_view(), name="live"),
    path(
        "<str:op_type>/<uuid:pk>/cancel/",
        CancelView.as_view(),
        name="cancel",
    ),
    path(
        "<str:op_type>/<uuid:pk>/restart/",
        RestartView.as_view(),
        name="restart",
    ),
]
