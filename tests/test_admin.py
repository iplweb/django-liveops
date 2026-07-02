"""
Tests for the reusable LiveOperationAdmin base.

LiveOperation is abstract, so the package registers nothing; these tests
verify the base ModelAdmin is correctly configured for a concrete subclass
(read-only, sensible columns) without needing admin URLs in the test project.
"""

from django.contrib.admin.sites import AdminSite

from live_operations.admin import LiveOperationAdmin
from tests.models import DemoOp


def _admin():
    return LiveOperationAdmin(DemoOp, AdminSite())


def test_admin_is_read_only():
    a = _admin()
    assert a.has_add_permission(request=None) is False
    ro = a.get_readonly_fields(request=None)
    # Every concrete field is read-only, plus the computed displays.
    for name in ("id", "owner", "finished_successfully", "result_context"):
        assert name in ro
    assert "state" in ro


def test_admin_state_column_reflects_operation_state(db):
    from django.contrib.auth import get_user_model

    u = get_user_model().objects.create_user("admin-t", password="x")
    op = DemoOp.objects.create(owner=u)
    a = _admin()
    assert a.state(op) == "NOT_STARTED"
    assert a.short_id(op) == str(op.pk)[:8]
    # Empty result/stages render a placeholder, not a crash.
    assert a.result_pretty(op) == "—"
    assert a.stage_states_pretty(op) == "—"


def test_admin_result_pretty_renders_json(db):
    from django.contrib.auth import get_user_model

    u = get_user_model().objects.create_user("admin-t2", password="x")
    op = DemoOp.objects.create(owner=u, result_context={"ok": 3, "errors": 1})
    html = _admin().result_pretty(op)
    assert "ok" in html and "3" in html
