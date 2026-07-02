from django.contrib import admin

from live_operations.admin import LiveOperationAdmin

from demo.models import DemoImport


@admin.register(DemoImport)
class DemoImportAdmin(LiveOperationAdmin):
    """Read-only admin for the demo operation (see LiveOperationAdmin)."""
