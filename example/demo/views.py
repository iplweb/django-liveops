from django.contrib.auth import get_user_model, login
from django.forms import modelform_factory
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from demo.models import (
    ChainStart,
    DemoImport,
    FailingTask,
    QuickTask,
    RedirectingTask,
)
from liveops.views import CreateLiveOperationView

# The demo operation catalogue. Each entry is one LiveOperation subclass the
# landing page offers to run, so you can eyeball every shape the framework
# supports: staged, plain, failing, chaining, redirect-on-success.
DEMO_OPS = [
    {
        "kind": "import",
        "model": DemoImport,
        "fields": ["label"],
        "name": _("Staged import"),
        "desc": _("5 stages — live stepper, per-stage progress bar and log."),
    },
    {
        "kind": "quick",
        "model": QuickTask,
        "fields": [],
        "name": _("Quick task"),
        "desc": _("No stages — one progress bar, then a result. Simplest shape."),
    },
    {
        "kind": "failing",
        "model": FailingTask,
        "fields": [],
        "name": _("Failing task"),
        "desc": _("Raises mid-run — shows the error state and the Retry button."),
    },
    {
        "kind": "chain",
        "model": ChainStart,
        "fields": [],
        "name": _("Chained task"),
        "desc": _("Runs, then chains to a second operation — no page reload."),
    },
    {
        "kind": "redirect",
        "model": RedirectingTask,
        "fields": [],
        "name": _("Redirect on success"),
        "desc": _("On success auto-redirects to a custom page (get_success_url)."),
    },
]
_BY_KIND = {d["kind"]: d for d in DEMO_OPS}


class DemoIndexView(TemplateView):
    """Landing page: a card per demo operation type with a Run button."""

    template_name = "demo/demo_index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["demo_ops"] = DEMO_OPS
        return ctx


class CreateDemoView(CreateLiveOperationView):
    """One create view for every demo type — resolved from the ``kind`` URL kwarg.

    live/cancel/restart are served generically by ``liveops.urls`` (op_type),
    so the demo only needs a create view per type — here collapsed into one.
    """

    template_name = "demo/demo_create.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.spec = _BY_KIND[kwargs["kind"]]
        self.model = self.spec["model"]

    def get_form_class(self):
        return modelform_factory(self.model, fields=self.spec["fields"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["spec"] = self.spec
        return ctx


class DoneView(TemplateView):
    """Where RedirectingTask lands the user on success (get_success_url)."""

    template_name = "demo/done.html"


def healthz_view(request):
    """Liveness probe for the Docker healthcheck.

    Deliberately does no DB writes, no template render, and no login — unlike
    /__login__/, which would create a new session row on every poll. Plain 200.
    """
    return HttpResponse("ok", content_type="text/plain")


def autologin_view(request):
    """Dev-only: log in as the first superuser without a password prompt."""
    if not __debug__:
        return HttpResponseForbidden("Not available in production.")

    from django.conf import settings

    if not settings.DEBUG:
        return HttpResponseForbidden("Not available when DEBUG=False.")

    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first()
    if user is None:
        return HttpResponseForbidden("No superuser found. Run: manage.py seed_demo")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect(request.GET.get("next", "/"))
