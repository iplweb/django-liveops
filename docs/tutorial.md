# Tutorial: Build a live CSV importer

This tutorial walks through building a real importer that reads rows from a CSV
file, with live progress, stages, and a result summary.

## 1. Define the model

```python
# my_app/models.py
from django.db import models
from live_operations.models import LiveOperation
from live_operations.progress import Progress


class ScoreImport(LiveOperation):
    """Import CSV file of scored publications."""

    csv_path = models.CharField(max_length=500)

    stages = ["Load", "Validate", "Save"]

    class Meta:
        app_label = "my_app"

    def run(self, p: Progress):
        import csv

        # Stage 1: read the CSV
        with p.stage("Load"):
            p.status("Loading file...")
            with open(self.csv_path) as f:
                rows = list(csv.DictReader(f))
            p.log(f"Loaded {len(rows)} rows")

        # Stage 2: validate
        with p.stage("Validate"):
            valid, errors = [], []
            for row in p.track(rows, label="Validation"):
                if row.get("score"):
                    valid.append(row)
                else:
                    errors.append(row["id"])
            if errors:
                p.log(f"Skipped {len(errors)} rows without a score")

        # Stage 3: save
        with p.stage("Save"):
            saved = 0
            for row in p.track(valid, label="Saving"):
                Publication.objects.update_or_create(
                    pk=row["id"],
                    defaults={"score": int(row["score"])},
                )
                saved += 1

        p.result({"saved": saved, "errors": len(errors)})
```

## 2. Create the result template

`my_app/templates/my_app/score_import_result.html`:

```html
<p>Imported <strong>{{ saved }}</strong> rows.</p>
{% if errors %}
<p class="warning">Skipped {{ errors }} rows without a score.</p>
{% endif %}
```

## 3. Create the host template (optional)

By default, `live_operations/operation.html` is used. To customise, create
`my_app/templates/my_app/score_import.html`:

```html
{% extends "base.html" %}
{% load live_operations static %}
{% block content %}
<h1>Score import</h1>
{% live_operation object %}
<script src="{% static 'live_operations/live-operations.js' %}"></script>
{% endblock %}
```

## 4. Form (optional)

```python
# my_app/forms.py
from django import forms
from .models import ScoreImport


class ScoreImportForm(forms.ModelForm):
    class Meta:
        model = ScoreImport
        fields = ["csv_path"]
```

## 5. Views

```python
# my_app/views.py
from live_operations.views import CreateLiveOperationView, LiveOperationView
from .models import ScoreImport
from .forms import ScoreImportForm


class ImportCreateView(CreateLiveOperationView):
    model = ScoreImport
    form_class = ScoreImportForm
    template_name = "my_app/import_form.html"


class ImportLiveView(LiveOperationView):
    model = ScoreImport
```

## 6. URLs

```python
# my_app/urls.py
from django.urls import include, path
from . import views

app_name = "live_operations"

urlpatterns = [
    path("import/new/", views.ImportCreateView.as_view(), name="create"),
    path("import/<uuid:pk>/", views.ImportLiveView.as_view(), name="live"),
]
```

Include in project URLs:

```python
urlpatterns = [
    ...
    path("my-app/", include("my_app.urls")),
    path("live/", include("live_operations.urls")),  # cancel/restart built-ins
]
```

## 7. Client-side scripts

In your base template, include htmx, the channels_broadcast client, and
live-operations.js (in this order):

```html
{% load static %}
<script src="https://unpkg.com/htmx.org@1.9/dist/htmx.min.js"></script>
<script src="{% static 'channels_broadcast/js/notifications.js' %}"></script>
<script src="{% static 'live_operations/live-operations.js' %}"></script>
```

Then in the operation host page:

```html
{% load live_operations static %}
{% live_operation object %}
```

## 8. Run it

Submit the form → operation is created → enqueued → page redirects to the live
host page → WebSocket connects → progress updates appear live → result rendered
in-place.

No reload. No polling.
