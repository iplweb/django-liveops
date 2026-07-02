from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiveOperationsConfig(AppConfig):
    name = "live_operations"
    label = "live_operations"
    verbose_name = _("Live Operations")
    default_auto_field = "django.db.models.BigAutoField"
