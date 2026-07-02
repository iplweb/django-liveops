from demo.views import autologin_view
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # set_language view
    path("accounts/", include("django.contrib.auth.urls")),
    # demo.urls declares app_name="live_operations" — all liveop URL reversals work.
    path("", include("demo.urls")),
    path("__login__/", autologin_view, name="autologin"),
]
