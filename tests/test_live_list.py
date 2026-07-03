"""
Tests for the live operations list: per-user "list changed" signal, the
lifecycle hooks that emit it, the opt-out setting, and the view's fragment
response for htmx refreshes.
"""

import pytest
from django.contrib.auth import get_user_model

from liveops import notifications
from tests.models import DemoOp

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("list-user", password="x")


def _capture_sends(monkeypatch):
    """Intercept channels_broadcast._send (used by notify_list_changed)."""
    sent = []
    monkeypatch.setattr(
        "channels_broadcast.core._send",
        lambda channel, message: sent.append((channel, message)),
    )
    return sent


def test_notify_list_changed_sends_payload(user, monkeypatch):
    sent = _capture_sends(monkeypatch)
    notifications.notify_list_changed(DemoOp.objects.create(owner=user))
    assert len(sent) == 1
    _, message = sent[0]
    assert message["liveop_list_changed"] is True
    assert message["type"] == "chat_message"  # routes through the consumer


def test_notify_list_changed_noop_when_disabled(user, monkeypatch, settings):
    settings.LIVEOPS = {"LIST_LIVE": False, "BASE_TEMPLATE": "base.html"}
    sent = _capture_sends(monkeypatch)
    notifications.notify_list_changed(DemoOp.objects.create(owner=user))
    assert sent == []


def test_enqueue_and_run_emit_list_changed(user, monkeypatch, settings):
    settings.LIVEOPS = {
        "RUNNER": "eager",
        "LIST_LIVE": True,
        "BASE_TEMPLATE": "base.html",
    }
    sent = _capture_sends(monkeypatch)
    op = DemoOp.objects.create(owner=user)
    op.enqueue()  # eager: create → start → finish
    signals = [m for _, m in sent if m.get("liveop_list_changed")]
    assert len(signals) == 3


def test_list_view_full_page_vs_hx_fragment(user, client):
    client.force_login(user)
    DemoOp.objects.create(owner=user)

    full = client.get("/").content.decode()
    frag = client.get("/", HTTP_HX_REQUEST="true").content.decode()

    # Full page carries the live wrapper + the table; the htmx fragment is just
    # the table (so it swaps into #liveop-list in place).
    assert 'id="liveop-list"' in full
    assert "<table" in full
    assert "<table" in frag
    assert 'id="liveop-list"' not in frag


def test_list_live_setting_toggles_wiring(user, client, settings):
    client.force_login(user)
    DemoOp.objects.create(owner=user)

    settings.LIVEOPS = {"LIST_LIVE": True, "BASE_TEMPLATE": "base.html"}
    on = client.get("/").content.decode()
    assert "data-liveop-list" in on and "liveops.js" in on

    settings.LIVEOPS = {"LIST_LIVE": False, "BASE_TEMPLATE": "base.html"}
    off = client.get("/").content.decode()
    assert "data-liveop-list" not in off
