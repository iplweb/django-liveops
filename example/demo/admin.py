from django.contrib import admin

from demo.models import DemoImport
from live_operations.admin import LiveOperationAdmin


@admin.register(DemoImport)
class DemoImportAdmin(LiveOperationAdmin):
    """Read-only admin for the demo operation (see LiveOperationAdmin)."""
