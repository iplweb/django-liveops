"""
Celery task-registration hook.

Celery's ``app.autodiscover_tasks()`` imports ``<app>.tasks`` for every app in
INSTALLED_APPS. The live-operations worker task is a ``@shared_task`` defined in
``runner.py``; importing it here makes a Celery worker running against any
project that includes ``liveops`` register the task automatically —
otherwise the worker never imports ``runner`` and rejects jobs with
"Received unregistered task of type 'liveops.runner._celery_task'".

The import is guarded: when the ``celery`` extra is not installed, ``runner``
never defines ``_celery_task`` and there is nothing (and no worker) to register.
"""

try:
    from liveops.runner import _celery_task  # noqa: F401
except ImportError:
    pass
