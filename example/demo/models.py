"""
DemoImport — a concrete LiveOperation that simulates a 5-stage file import.

Each stage does a short time.sleep loop so the browser demo shows live progress.
"""

import time

from django.db import models
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, gettext_noop

from liveops.models import LiveOperation

# Stage names double as JSON keys in op.stage_states (identity) AND as display
# text in the stepper. So keep them as stable English strings via gettext_noop
# — that marks them for translation extraction without turning them into lazy
# proxies (which JSONField can't serialize). The stepper translates them for
# display via {% trans stage_name %}.
_STAGE_ITEMS = {
    gettext_noop("Load"): 20,
    gettext_noop("Validate"): 30,
    gettext_noop("Match"): 25,
    gettext_noop("Save"): 40,
    gettext_noop("Report"): 5,
}


class DemoImport(LiveOperation):
    stages = ["Load", "Validate", "Match", "Save", "Report"]

    # One user-supplied parameter, purely to show how a form value reaches
    # run(). The demo just echoes it in the first status line.
    label = models.CharField(
        gettext_lazy("Label"),
        max_length=100,
        blank=True,
        default="",
        help_text=gettext_lazy("A name for this import (shown while it runs)."),
    )

    class Meta:
        app_label = "demo"

    def run(self, p):
        if self.label:
            p.status(_("Starting import: %(label)s") % {"label": self.label})

        total_items = sum(_STAGE_ITEMS.values())
        ok = 0
        skipped = 0
        errors = 0

        for stage_name in self.stages:
            count = _STAGE_ITEMS[stage_name]
            with p.stage(stage_name):
                p.status(_("Stage: %(name)s") % {"name": _(stage_name)}, level="info")
                for i in p.track(range(count), total=count, label=stage_name):
                    time.sleep(0.05)
                    if i % 7 == 0:
                        skipped += 1
                        p.log(
                            _("[%(stage)s] skipped record %(i)s")
                            % {"stage": _(stage_name), "i": i}
                        )
                    elif i % 11 == 0:
                        errors += 1
                        p.log(
                            _("[%(stage)s] record error %(i)s")
                            % {"stage": _(stage_name), "i": i}
                        )
                    else:
                        ok += 1

        p.result(
            {
                "total": total_items,
                "ok": ok,
                "skipped": skipped,
                "errors": errors,
            }
        )


class DemoBase(LiveOperation):
    """Shared base for the small demo operations.

    They all render their result via one generic template instead of a
    per-class ``*_result.html`` (``result_template_name`` is picked up by
    ``liveops.naming.result_template_name``).
    """

    result_template_name = "demo/generic_result.html"

    class Meta:
        abstract = True


class QuickTask(DemoBase):
    """No stages — a single progress bar then a result. The simplest shape."""

    class Meta:
        app_label = "demo"

    def run(self, p):
        p.status(_("Crunching numbers…"))
        total = 0
        for i in p.track(range(30), total=30, label="crunch"):
            time.sleep(0.04)
            total += i
        p.result({"sum": total, "items": 30})


class FailingTask(DemoBase):
    """Raises mid-run to demonstrate the error state + Retry button."""

    class Meta:
        app_label = "demo"

    def run(self, p):
        for i in p.track(range(10), total=10, label="work"):
            time.sleep(0.12)
            if i == 5:
                raise RuntimeError(
                    "Boom at item 5 — this failure is intentional (demo)."
                )
        p.result({"never": "reached"})


class ChainEnd(DemoBase):
    """Second link of the chain demo (started by ChainStart)."""

    class Meta:
        app_label = "demo"

    def run(self, p):
        p.status(_("Second operation running…"))
        for _i in p.track(range(15), total=15, label="phase 2"):
            time.sleep(0.05)
        p.result({"message": "chain complete"})


class ChainStart(DemoBase):
    """Runs, then chains to a second operation — no page reload (p.chain_to)."""

    class Meta:
        app_label = "demo"

    def run(self, p):
        p.status(_("First operation running…"))
        for _i in p.track(range(15), total=15, label="phase 1"):
            time.sleep(0.05)
        nxt = ChainEnd.objects.create(owner=self.owner)
        p.chain_to(nxt)


class RedirectingTask(DemoBase):
    """On success, auto-redirects to a dedicated page via get_success_url().

    Demonstrates skipping the live/list page entirely: the browser lands on
    ``demo:done`` the moment this finishes OK.
    """

    class Meta:
        app_label = "demo"

    def run(self, p):
        p.status(_("Working — will redirect when done…"))
        for _i in p.track(range(20), total=20, label="work"):
            time.sleep(0.05)
        p.result({"done": True})

    def get_success_url(self):
        from django.urls import reverse

        return reverse("demo:done")
