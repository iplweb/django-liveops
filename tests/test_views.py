"""
Tests for Phase 3 views + op_type routing.

Covers: create form GET/POST, live page rendering (channel + token attributes),
finished-op inline result, cancel POST/GET, anonymous redirect, cross-user 404,
restart hook, and generic op_type resolution (unknown type / cross-type 404).
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from tests.models import DemoOp, NextOp

User = get_user_model()


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="pass")


@pytest.fixture
def auth_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def anon_client():
    return Client()


@pytest.fixture
def demo_op(user):
    return DemoOp.objects.create(owner=user)


@pytest.fixture
def finished_op(user):
    from django.utils import timezone

    return DemoOp.objects.create(
        owner=user,
        finished_on=timezone.now(),
        finished_successfully=True,
        result_context={"message": "done"},
    )


# ------------------------------------------------------------------ #
# Create view                                                          #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_create_get_returns_200(auth_client):
    response = auth_client.get("/demo/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_create_post_creates_op_owner_set_and_redirects(auth_client, user):
    response = auth_client.post("/demo/new/", data={})
    assert response.status_code == 302
    op = DemoOp.objects.filter(owner=user).first()
    assert op is not None
    assert op.owner == user
    # Eager runner ran the op synchronously; terminal state committed
    assert op.finished_on is not None


@pytest.mark.django_db
def test_create_post_redirect_points_to_live_page(auth_client, user):
    response = auth_client.post("/demo/new/", data={})
    op = DemoOp.objects.filter(owner=user).first()
    # Redirect targets the generic op_type-based live URL.
    assert response["Location"] == op.get_absolute_url()
    assert response["Location"] == f"/tests.demoop/{op.pk}/"


# ------------------------------------------------------------------ #
# Live page                                                            #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_live_page_returns_200(auth_client, demo_op):
    response = auth_client.get(demo_op.get_absolute_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_live_page_has_channel_attribute(auth_client, demo_op):
    response = auth_client.get(demo_op.get_absolute_url())
    content = response.content.decode()
    assert f'data-liveop-channel="liveop.{demo_op.pk}"' in content


@pytest.mark.django_db
def test_live_page_has_non_empty_token(auth_client, demo_op):
    response = auth_client.get(demo_op.get_absolute_url())
    content = response.content.decode()
    assert 'data-liveop-token="' in content
    # Token must be a non-trivial signed value
    token = response.context["object"].subscription_token
    assert len(token) > 20


@pytest.mark.django_db
def test_live_page_contains_region_divs(auth_client, demo_op):
    response = auth_client.get(demo_op.get_absolute_url())
    content = response.content.decode()
    for region in ("op-status", "op-progress", "op-log", "op-result"):
        assert region in content, f"region {region!r} missing from live page"


@pytest.mark.django_db
def test_finished_op_renders_result_inline(auth_client, finished_op):
    response = auth_client.get(finished_op.get_absolute_url())
    assert response.status_code == 200
    content = response.content.decode()
    # op-result div present and contains the result data
    assert "op-result" in content
    assert "message=done" in content


# ------------------------------------------------------------------ #
# Cancel view                                                          #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_cancel_post_sets_flag(auth_client, demo_op):
    response = auth_client.post(demo_op.get_absolute_url() + "cancel/")
    assert response.status_code == 302
    demo_op.refresh_from_db()
    assert demo_op.cancel_requested is True


@pytest.mark.django_db
def test_cancel_get_returns_405(auth_client, demo_op):
    response = auth_client.get(demo_op.get_absolute_url() + "cancel/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_control_forms_have_working_csrf(user):
    """The live page must render a real CSRF token in the cancel/restart forms
    and set the CSRF cookie, so those POSTs are accepted.

    Regression: the ``{% live_operation %}`` templatetag rendered the fragment
    without the request, so ``{% csrf_token %}`` produced an empty token and no
    cookie was set — every cancel/restart POST failed CSRF.
    """
    import re

    from django.test import Client
    from django.utils import timezone

    op = DemoOp.objects.create(owner=user, started_on=timezone.now())  # STARTED
    c = Client(enforce_csrf_checks=True)
    c.force_login(user)

    resp = c.get(op.get_absolute_url())
    assert resp.status_code == 200
    html = resp.content.decode()
    # Both control forms present (Retry rendered too, just hidden until error).
    assert "op-controls-cancel" in html
    assert "op-controls-restart" in html
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    assert m, "no CSRF token rendered in the control forms"

    # POST cancel with the page's token — must be accepted (302), not 403.
    resp2 = c.post(
        op.get_absolute_url() + "cancel/",
        {"csrfmiddlewaretoken": m.group(1)},
    )
    assert resp2.status_code == 302
    op.refresh_from_db()
    assert op.cancel_requested is True


# ------------------------------------------------------------------ #
# Access control                                                       #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_anonymous_user_redirected_to_login(anon_client, demo_op):
    response = anon_client.get(demo_op.get_absolute_url())
    assert response.status_code == 302


@pytest.mark.django_db
def test_other_user_cannot_see_op(other_user, demo_op):
    c = Client()
    c.force_login(other_user)
    response = c.get(demo_op.get_absolute_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_other_user_cannot_cancel_op(other_user, demo_op):
    c = Client()
    c.force_login(other_user)
    response = c.post(demo_op.get_absolute_url() + "cancel/")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# op_type routing (generic resolution)                                #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_unknown_op_type_returns_404(auth_client, demo_op):
    response = auth_client.get(f"/nope.notamodel/{demo_op.pk}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_wrong_op_type_for_pk_returns_404(auth_client, demo_op):
    """A valid op_type that does not own this pk resolves to 404.

    demo_op is a DemoOp; asking for it under NextOp's op_type must not leak
    it — the owner-scoped get on the NextOp table finds nothing.
    """
    wrong = NextOp.op_type_key()  # "tests.nextop"
    response = auth_client.get(f"/{wrong}/{demo_op.pk}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_malformed_op_type_returns_404(auth_client):
    response = auth_client.get(f"/notdotted/{uuid.uuid4()}/")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# RestartView — state reset + on_restart hook                         #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_restart_clears_all_state_fields(auth_client, user):
    """RestartView resets all terminal + progress fields, not just timestamps.

    The eager runner re-runs DemoOp immediately, so some fields (finished_on,
    started_on, finished_successfully) get new values from the re-run.  We
    verify they changed from their original values and that the fields the
    re-run does NOT touch (stage_states, log, log_seq, current_stage) are
    cleanly zeroed.
    """
    from django.utils import timezone

    original_finished_on = timezone.now()
    op = DemoOp.objects.create(
        owner=user,
        started_on=original_finished_on,
        finished_on=original_finished_on,
        finished_successfully=True,
        cancelled=False,
        cancel_requested=False,
        traceback="Traceback...",
        result_context={"x": 1},
        current_stage=2,
        stage_states={"Alpha": "done", "Beta": "active"},
        log=["line 1", "line 2"],
        percent=80,
        log_seq=5,
    )
    response = auth_client.post(op.get_absolute_url() + "restart/")
    assert response.status_code == 302

    op.refresh_from_db()

    # Fields not re-set by the DemoOp re-run must be cleanly zeroed.
    assert op.cancelled is False
    assert op.cancel_requested is False
    assert op.traceback is None
    assert op.current_stage == -1
    assert op.stage_states == {}
    assert op.log == []
    assert op.log_seq == 0
    # percent: cleared to 0 by restart; WebProgress doesn't persist it to DB.
    assert op.percent == 0

    # DemoOp re-ran (eager): finished_on must be a new value, not the original.
    assert op.finished_on is not None
    assert op.finished_on != original_finished_on


@pytest.mark.django_db
def test_restart_calls_on_restart_hook(auth_client, user, monkeypatch):
    """RestartView invokes model.on_restart() before resetting state.

    Proven by patching DemoOp.on_restart (op_type resolves to the real
    DemoOp class) and asserting it was called with this operation.
    """
    from django.utils import timezone

    op = DemoOp.objects.create(
        owner=user,
        finished_on=timezone.now(),
        finished_successfully=True,
    )
    called = []
    monkeypatch.setattr(DemoOp, "on_restart", lambda self: called.append(self.pk))

    response = auth_client.post(op.get_absolute_url() + "restart/")
    assert response.status_code == 302
    assert called == [op.pk]


# ------------------------------------------------------------------ #
# Group gate — superuser exemption                                    #
# ------------------------------------------------------------------ #


@pytest.mark.django_db
def test_superuser_exempt_from_required_group(settings):
    """With LIVEOPS[REQUIRED_GROUP] set, a superuser (not in the group) passes."""
    settings.LIVEOPS = {**getattr(settings, "LIVEOPS", {}), "REQUIRED_GROUP": "ops"}
    su = User.objects.create_superuser(username="root", password="pass")
    op = DemoOp.objects.create(owner=su)
    c = Client()
    c.force_login(su)
    response = c.get(op.get_absolute_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_member_blocked_by_required_group(settings, user, demo_op):
    """A regular user not in REQUIRED_GROUP is forbidden (403)."""
    settings.LIVEOPS = {**getattr(settings, "LIVEOPS", {}), "REQUIRED_GROUP": "ops"}
    c = Client()
    c.force_login(user)
    response = c.get(demo_op.get_absolute_url())
    assert response.status_code == 403
