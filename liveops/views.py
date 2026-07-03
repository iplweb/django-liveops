"""
CBV mixins for LiveOperation views.

BaseLiveOperationMixin — login-required + owner-scoped queryset + optional
group gate (LIVEOPS["REQUIRED_GROUP"], superusers exempt).  All views inherit
from it.

live/cancel/restart are GENERIC: they resolve the concrete model from the
URL ``op_type`` (OpTypeObjectMixin) and are wired once via ``liveops.urls``.
Consumer apps only subclass CreateLiveOperationView / LiveOperationListView
(which need a model/form) under their own namespace; their success redirect
targets ``liveops:live`` through ``get_absolute_url()``.
"""

from __future__ import annotations

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView
from django.views.generic.detail import SingleObjectMixin

from liveops.conf import get_setting


class BaseLiveOperationMixin(AccessMixin):
    """
    Owner-scoped, login-required base for all LiveOperation views.

    - Unauthenticated → redirect to login (via AccessMixin.handle_no_permission).
    - Authenticated but wrong group → 403.
    - Queryset always filtered to owner=request.user (prevents cross-user leaks).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        required_group = get_setting("REQUIRED_GROUP")
        # Superusers are exempt from the group gate (matches Django admin /
        # django-braces GroupRequiredMixin semantics). Without this, a
        # superuser not explicitly in REQUIRED_GROUP would get a 403.
        if (
            required_group
            and not request.user.is_superuser
            and not request.user.groups.filter(name=required_group).exists()
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model._default_manager.filter(owner=self.request.user)


class OpTypeObjectMixin:
    """Resolve the concrete LiveOperation instance from the URL ``op_type``.

    ``op_type`` is ``<app_label>.<model_name>`` (see
    ``LiveOperation.op_type_key``). Resolution is one ``apps.get_model`` plus
    one owner-scoped ``get`` — O(1), no scanning of the model registry. This
    is what lets a single central set of URLs (live/cancel/restart) serve
    every LiveOperation subclass in the project.

    Sets ``self.model`` so the standard DetailView/SingleObjectMixin
    machinery (template names, context) keeps working.
    """

    def get_object(self, queryset=None):
        from django.apps import apps

        from liveops.models import LiveOperation

        op_type = self.kwargs["op_type"]
        try:
            app_label, model_name = op_type.split(".", 1)
            model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as exc:
            raise Http404(f"Unknown operation type: {op_type!r}") from exc

        if not (isinstance(model, type) and issubclass(model, LiveOperation)):
            raise Http404(f"Not a LiveOperation: {op_type!r}")

        self.model = model
        return get_object_or_404(model, pk=self.kwargs["pk"], owner=self.request.user)


class CreateLiveOperationView(BaseLiveOperationMixin, CreateView):
    """Create a new LiveOperation, assign owner, enqueue, redirect to live page."""

    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        self.object.enqueue()
        return redirect(self.object.get_absolute_url())


class LiveOperationView(OpTypeObjectMixin, BaseLiveOperationMixin, DetailView):
    """
    Live host page for a running or finished operation.

    Template order: object.get_host_template_name() → liveops/operation.html.
    For finished operations the result is rendered inline (deep-link / refresh).
    """

    def get_template_names(self):
        return [self.object.get_host_template_name(), "liveops/operation.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["base_template"] = get_setting("BASE_TEMPLATE")
        return ctx


class LiveOperationListView(BaseLiveOperationMixin, ListView):
    """List all operations owned by the current user.

    A live-refresh request (htmx, ``HX-Request`` header) gets only the table
    fragment so ``liveops.js`` can swap it into ``#liveop-list`` in place.
    """

    context_object_name = "operations"

    def get_queryset(self):
        # A concrete LiveOperation subclass must declare its own Meta (for
        # app_label), which drops the abstract base's ordering. Order here so
        # the list is newest-first regardless of the subclass's Meta.
        return super().get_queryset().order_by("-created_on")

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["liveops/_operation_list_table.html"]
        return ["liveops/operation_list.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["base_template"] = get_setting("BASE_TEMPLATE")
        ctx["list_live"] = get_setting("LIST_LIVE")
        return ctx


class CancelView(OpTypeObjectMixin, BaseLiveOperationMixin, SingleObjectMixin, View):
    """POST-only: set cancel_requested=True and redirect to live page."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        operation = self.get_object()
        operation.cancel_requested = True
        operation.save(update_fields=["cancel_requested"])
        return redirect(operation.get_absolute_url())


class RestartView(OpTypeObjectMixin, BaseLiveOperationMixin, SingleObjectMixin, View):
    """POST-only: reset terminal state, re-enqueue, redirect to live page."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        operation = self.get_object()
        # Model hook: let the subclass clean up child records (e.g. import
        # result rows) before we wipe the operation's own state.
        operation.on_restart()
        operation.finished_on = None
        operation.started_on = None
        operation.finished_successfully = False
        operation.cancelled = False
        operation.cancel_requested = False
        operation.traceback = None
        operation.result_context = None
        operation.current_stage = -1
        operation.stage_states = {}
        operation.log = []
        operation.percent = 0
        operation.log_seq = 0
        operation.save(
            update_fields=[
                "finished_on",
                "started_on",
                "finished_successfully",
                "cancelled",
                "cancel_requested",
                "traceback",
                "result_context",
                "current_stage",
                "stage_states",
                "log",
                "percent",
                "log_seq",
            ]
        )
        operation.enqueue()
        return redirect(operation.get_absolute_url())
