"""Test URL configuration — app-specific create/list for DemoOp.

live/cancel/restart are NOT here — they come generically from
``liveops.urls`` (mounted in ``tests/root_urls.py``). Create/list stay
app-specific because they need a form/model + custom templates.
"""

from django.urls import path

from tests.views import CreateDemoOpView, ListDemoOpView

app_name = "tests"

urlpatterns = [
    path("", ListDemoOpView.as_view(), name="index"),
    path("new/", CreateDemoOpView.as_view(), name="new"),
]
