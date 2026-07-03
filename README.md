# django-liveops

[![CI](https://github.com/iplweb/django-liveops/actions/workflows/ci.yml/badge.svg)](https://github.com/iplweb/django-liveops/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/django-liveops.svg)](https://pypi.org/project/django-liveops/)
[![Python](https://img.shields.io/pypi/pyversions/django-liveops.svg)](https://pypi.org/project/django-liveops/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A standalone, reusable Django package for long-running operations with a live
WebSocket + HTMX user interface — no page reloads, no polling.

## Installation

```bash
pip install django-liveops
# optional extras:
pip install django-liveops[redis]    # Redis channel layer (production)
pip install django-liveops[celery]   # Celery worker runner
pip install django-liveops[cli]      # tqdm progress bar for text mode
```

Requires Python 3.11+ and Django 5.2+. See the
[Getting Started guide](https://iplweb.github.io/django-liveops/getting-started/)
for the full setup (channels, ASGI, settings).

The developer writes one method:

```python
from liveops.models import LiveOperation
from liveops.progress import Progress


class MyImport(LiveOperation):
    def run(self, p: Progress):
        for row in p.track(rows, label="Processing"):
            process(row)
            p.log(f"done: {row}")
        p.result()
```

The framework handles channels, tokens, OOB-swaps, snapshot-on-connect,
throttling, and cooperative cancellation.

## Try the demo

A self-contained demo project lives in [`example/`](example/).

```bash
# Browser demo — Daphne + Redis + Celery worker, live WebSocket progress.
# Opens http://localhost:8000 (needs Docker).
make demo

# Zero-infra text demo — runs synchronously, prints progress to stdout.
# No Docker, no Redis, no browser.
make demo-text
```

Both targets also work from inside `example/` (`cd example && make demo`);
the root `make` just delegates there. See [`example/README.md`](example/README.md)
for what you'll see and how the demo is wired.

## Documentation

Full docs are published at
**<https://iplweb.github.io/django-liveops/>** (source in `docs/`).

## License

MIT — see [LICENSE](LICENSE).
