"""
Reusable admin for LiveOperation subclasses.

``LiveOperation`` is abstract, so this module registers nothing on its own.
Integrators register their concrete operation models with ``LiveOperationAdmin``:

    from django.contrib import admin
    from live_operations.admin import LiveOperationAdmin
    from myapp.models import MyOperation

    @admin.register(MyOperation)
    class MyOperationAdmin(LiveOperationAdmin):
        pass

The admin is read-only by design: operations are historical records produced
by the framework, not rows you hand-edit (editing terminal/live state could
corrupt an operation). Adding via the admin is disabled; deletion stays allowed
for cleanup.
"""

from __future__ import annotations

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class LiveOperationAdmin(admin.ModelAdmin):
    """Read-only admin base for concrete ``LiveOperation`` subclasses."""

    list_display = (
        "short_id",
        "owner",
        "state",
        "created_on",
        "started_on",
        "finished_on",
        "finished_successfully",
    )
    list_filter = ("finished_successfully", "cancelled")
    date_hierarchy = "created_on"
    ordering = ("-created_on",)
    search_fields = ("id",)

    # ---- computed columns / detail fields ---------------------------------- #

    @admin.display(description=_("ID"))
    def short_id(self, obj):
        return str(obj.pk)[:8]

    @admin.display(description=_("State"))
    def state(self, obj):
        return obj.get_state()

    @admin.display(description=_("Result"))
    def result_pretty(self, obj):
        if not obj.result_context:
            return "—"
        return format_html(
            "<pre style='margin:0'>{}</pre>",
            json.dumps(obj.result_context, indent=2, ensure_ascii=False),
        )

    @admin.display(description=_("Stages"))
    def stage_states_pretty(self, obj):
        if not obj.stage_states:
            return "—"
        return format_html(
            "<pre style='margin:0'>{}</pre>",
            json.dumps(obj.stage_states, indent=2, ensure_ascii=False),
        )

    # ---- read-only enforcement --------------------------------------------- #

    # Fields declared on the abstract LiveOperation base. Anything else on a
    # concrete subclass (e.g. the demo's ``label``) is subclass-specific and
    # gets surfaced in the detail view automatically.
    _BASE_FIELDS = frozenset(
        {
            "id",
            "owner",
            "language",
            "created_on",
            "started_on",
            "finished_on",
            "finished_successfully",
            "cancelled",
            "cancel_requested",
            "status_text",
            "percent",
            "log",
            "log_seq",
            "current_stage",
            "stage_states",
            "traceback",
            "result_context",
        }
    )

    def get_fields(self, request, obj=None):
        extra = [
            f.name for f in self.model._meta.fields if f.name not in self._BASE_FIELDS
        ]
        return [
            "id",
            "owner",
            "state",
            *extra,  # subclass-specific fields (e.g. the demo's `label`)
            "language",
            "created_on",
            "started_on",
            "finished_on",
            "finished_successfully",
            "cancelled",
            "cancel_requested",
            "current_stage",
            "stage_states_pretty",
            "result_pretty",
            "traceback",
        ]

    def get_readonly_fields(self, request, obj=None):
        # Every concrete DB field plus the computed display fields — nothing
        # in the detail view is editable.
        model_fields = [f.name for f in self.model._meta.fields]
        computed = ["state", "result_pretty", "stage_states_pretty"]
        return tuple(model_fields + computed)

    def has_add_permission(self, request):
        return False
