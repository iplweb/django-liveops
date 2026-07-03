"""Concrete view subclasses for DemoOp — used only in the test suite.

Only create + list are app-specific now. live/cancel/restart are served
generically by ``liveops.urls`` (resolved via op_type), so the test app no
longer subclasses those.
"""

from django import forms

from liveops.views import CreateLiveOperationView, LiveOperationListView
from tests.models import DemoOp


class DemoOpForm(forms.ModelForm):
    class Meta:
        model = DemoOp
        fields: list = []


class CreateDemoOpView(CreateLiveOperationView):
    model = DemoOp
    form_class = DemoOpForm


class ListDemoOpView(LiveOperationListView):
    model = DemoOp
