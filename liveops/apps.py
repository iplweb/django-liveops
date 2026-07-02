from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiveOperationsConfig(AppConfig):
    name = "liveops"
    label = "liveops"
    verbose_name = _("Live Operations")
    default_auto_field = "django.db.models.BigAutoField"
