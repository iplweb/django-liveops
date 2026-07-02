"""Root URL configuration for the test suite.

Wraps tests.urls in an include() so that the liveops namespace
(declared via app_name in tests/urls.py) is properly registered and
reverse("liveops:live", ...) works in model.get_absolute_url().
"""

from django.urls import include, path

urlpatterns = [
    path("", include("tests.urls")),
]
