"""Root URL configuration for the test suite.

Mounts the generic liveops router (``liveops.urls``, app_name="liveops")
at the root so ``reverse("liveops:live", op_type=..., pk=...)`` works in
``model.get_absolute_url()``, and the app-specific create/list views
(``tests.urls``, app_name="tests") under ``/demo/``.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("liveops.urls")),
    path("demo/", include("tests.urls")),
]
