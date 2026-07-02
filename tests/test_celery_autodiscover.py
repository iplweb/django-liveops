"""
Regression test for Celery task autodiscovery.

Celery's ``app.autodiscover_tasks()`` imports ``<app>.tasks`` for every app in
INSTALLED_APPS. The live-operations Celery task is defined in ``runner.py`` (as
a ``@shared_task``), so without a ``live_operations/tasks.py`` re-export a
worker running ``celery -A <proj> worker`` never imports it and rejects the
job with "Received unregistered task of type
'live_operations.runner._celery_task'".

These tests pin the contract that makes the ``celery`` runner work end-to-end.
"""

import importlib

import pytest


def test_tasks_module_is_importable():
    """Celery autodiscover imports ``<app>.tasks`` — the module must exist."""
    mod = importlib.import_module("live_operations.tasks")
    assert mod is not None


def test_tasks_module_registers_the_shared_task():
    """Importing ``live_operations.tasks`` must register the worker task."""
    celery = pytest.importorskip("celery")

    # Simulate what a worker's autodiscover does: import the tasks module.
    importlib.import_module("live_operations.tasks")

    # After that import, the task must be in the current app's registry under
    # the exact name the web side enqueues with.
    app = celery.current_app
    assert "live_operations.runner._celery_task" in app.tasks
