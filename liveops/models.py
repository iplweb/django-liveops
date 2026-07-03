"""
LiveOperation — abstract base model for long-running operations.

State machine (get_state):
  NOT_STARTED  → STARTED (started_on set)
               → FINISHED_OK (finished_on + finished_successfully=True)
               → FINISHED_ERROR (finished_on + finished_successfully=False)
               → CANCELLED (cancelled=True)

§19.3: only terminal state is persisted to DB in v1 (no PERSIST_PROGRESS).
status_text/percent/log/log_seq are placeholder fields; in v1 default they
are written only by p.result() / p.error() (via result_context), not during
live progress.
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.html import escape
from django.utils.translation import gettext as _


class LiveOperation(models.Model):
    """Abstract base. Concrete subclasses must implement ``run(self, p)``."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    # Timestamps
    created_on = models.DateTimeField(auto_now_add=True)
    started_on = models.DateTimeField(null=True, blank=True)
    finished_on = models.DateTimeField(null=True, blank=True)

    # Terminal state (§19.3 source of truth)
    finished_successfully = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)  # set by cancel view
    cancelled = models.BooleanField(default=False)
    traceback = models.TextField(null=True, blank=True)
    result_context = models.JSONField(null=True, blank=True)

    # Language the operation was created in. Live fragments are rendered from a
    # worker / WS consumer that has no request locale, so we re-activate this
    # language there (see runner.task_run and send_snapshot) to keep the
    # progress UI in the creator's language instead of falling back to English.
    language = models.CharField(max_length=20, blank=True, default="")

    # Placeholder progress fields — v1: not written during live run
    status_text = models.CharField(max_length=255, blank=True, default="")
    percent = models.PositiveSmallIntegerField(default=0)
    log = models.JSONField(default=list)
    log_seq = models.PositiveIntegerField(default=0)

    # Stage support (§16)
    stages: list[str] = []  # class-level declaration, not a DB field
    current_stage = models.IntegerField(default=-1)
    stage_states = models.JSONField(default=dict)

    class Meta:
        abstract = True
        ordering = ["-created_on"]

    # ------------------------------------------------------------------ #
    # Developer API                                                        #
    # ------------------------------------------------------------------ #

    def run(self, p) -> None:  # noqa: ANN001
        """Override in concrete subclasses to implement the operation logic."""
        raise NotImplementedError(f"{self.__class__.__name__}.run() is not implemented")

    # ------------------------------------------------------------------ #
    # State machine                                                        #
    # ------------------------------------------------------------------ #

    def get_state(self) -> str:
        """Return the current state as a string constant."""
        if self.cancelled:
            return "CANCELLED"
        if self.finished_on is not None:
            return "FINISHED_OK" if self.finished_successfully else "FINISHED_ERROR"
        if self.started_on is not None:
            return "STARTED"
        return "NOT_STARTED"

    # ------------------------------------------------------------------ #
    # Operation type key — routing across many subclasses                 #
    # ------------------------------------------------------------------ #

    @classmethod
    def op_type_key(cls) -> str:
        """Stable, reversible key identifying this concrete subclass in URLs.

        Format: ``<app_label>.<model_name>`` — resolvable back to the model
        via ``django.apps.apps.get_model``. This lets ONE central set of
        liveops URLs (live/cancel/restart) route every subclass with an O(1)
        lookup, instead of the consumer scanning all LiveOperation subclasses
        per request. See ``liveops.views.OpTypeObjectMixin``.
        """
        return f"{cls._meta.app_label}.{cls._meta.model_name}"

    # ------------------------------------------------------------------ #
    # Naming resolvers — delegate to liveops.naming               #
    # ------------------------------------------------------------------ #

    def get_host_template_name(self) -> str:
        from liveops import naming

        return naming.host_template_name(self.__class__)

    def get_result_template_name(self) -> str:
        from liveops import naming

        return naming.result_template_name(self.__class__)

    def get_channel_name(self) -> str:
        from liveops import naming

        return naming.channel_name(self)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def enqueue(self) -> None:
        """Dispatch this operation via the configured runner.

        Captures the currently active language (enqueue runs in the request,
        so LocaleMiddleware has activated the viewer's language) and persists
        it, so the worker can re-activate it when rendering live fragments.
        """
        from django.utils import translation

        from liveops import runner

        lang = translation.get_language()
        if lang and self.language != lang:
            self.language = lang
            if self.pk is not None:
                self.save(update_fields=["language"])

        # New/re-run operation → refresh any open list pages for this owner.
        from liveops.notifications import notify_list_changed

        notify_list_changed(self)

        return runner.enqueue(self)

    def get_absolute_url(self) -> str:
        """Return the URL of the live host page for this operation.

        The URL carries ``op_type`` (``<app_label>.<model_name>``) so the
        central generic ``liveops:live`` view can resolve the concrete model
        in one lookup — no per-subclass URL wiring, no registry scan.
        """
        from django.urls import reverse

        return reverse(
            "liveops:live",
            kwargs={"op_type": self.op_type_key(), "pk": self.pk},
        )

    def get_success_url(self) -> Optional[str]:
        """URL to auto-redirect to when the operation finishes successfully.

        Default ``None`` — the client stays on the live page and shows the
        result fragment inline. Override to return a URL (e.g.
        ``reverse("my_app:done", args=[self.pk])``) and the browser will
        navigate there as soon as the operation reaches ``FINISHED_OK``,
        instead of leaving the user on the live/list page. Lets a consumer
        skip the operations index entirely and land on a dedicated page.

        Only followed on success; error/cancelled stay on the live page.
        """
        return None

    def on_restart(self) -> None:
        """Hook called by ``RestartView`` before state reset + re-enqueue.

        No-op by default. Subclasses with child records (e.g. per-row import
        results) override this to delete them, so a restart begins from a
        clean slate. Keeps that knowledge in the model, not in the view.
        """

    # ------------------------------------------------------------------ #
    # Phase 2: subscription token + snapshot                              #
    # ------------------------------------------------------------------ #

    @property
    def subscription_token(self) -> str:
        """Signed token authorising self.owner to subscribe to this channel."""
        from liveops.security import make_subscription_token

        return make_subscription_token(self.owner, self)

    def _render_snapshot_html(self) -> str:
        """Render the appropriate HTML fragment for the current state.

        §19.3: only terminal state is in DB; running ops get a generic
        status fragment.
        """
        from django.template.loader import render_to_string

        state = self.get_state()

        if state == "FINISHED_OK":
            render_ctx: dict = dict(self.result_context or {})
            render_ctx.setdefault("operation", self)
            try:
                inner = render_to_string(self.get_result_template_name(), render_ctx)
            except Exception:
                inner = ""
            return f'<div id="op-result" hx-swap-oob="true">{inner}</div>'

        if state == "FINISHED_ERROR":
            return render_to_string(
                "liveops/_error.html",
                {"op": self},
            )

        if state == "CANCELLED":
            return (
                '<div id="op-result" hx-swap-oob="true">'
                '<div class="cancelled">{}</div>'
                "</div>"
            ).format(escape(_("Operation was cancelled.")))

        # STARTED or NOT_STARTED — send running status
        return render_to_string(
            "liveops/_status.html",
            {"text": _("Operation in progress…"), "level": "info"},
        )

    def send_snapshot(self) -> None:
        """Push current state as an HTML fragment to this operation's channel group.

        Called by LiveOperationConsumer.connect() so a freshly connected
        client immediately sees the latest state (§7.3 / §19.3).

        Uses channels_broadcast.core._send (same async/sync helper as
        channels_broadcast itself) so the send works from both sync
        workers and async consumers.
        """
        from channels_broadcast.core import _send
        from django.utils import translation

        # The consumer renders this snapshot with no request locale; re-activate
        # the operation's language so a mid-run connect matches the live pushes.
        if self.language:
            with translation.override(self.language):
                html = self._render_snapshot_html()
        else:
            html = self._render_snapshot_html()
        channel = self.get_channel_name()
        _send(channel, {"liveop_html": html})
