from demo.views import autologin_view, healthz_view
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # set_language view
    path("accounts/", include("django.contrib.auth.urls")),
    # Docker healthcheck endpoint (no side effects — see healthz_view).
    path("healthz/", healthz_view, name="healthz"),
    # Generic liveops router (op_type): live/cancel/restart for every op type.
    path("live/", include("liveops.urls")),
    # Demo landing + per-type create + the redirect-on-success target.
    path("", include("demo.urls")),
    path("__login__/", autologin_view, name="autologin"),
]
