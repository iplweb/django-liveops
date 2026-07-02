# django-live-operations — demo

## One command (browser demo)

```bash
make demo
```

Opens `http://localhost:8000`. The `web` container runs `seed_demo` on
startup, creating an `admin` / `admin` superuser. Log in at the login page
(`/accounts/login/`, credentials shown on it) or skip the prompt via
`http://localhost:8000/__login__/`, then click **+ New import** and watch 5
stages of live progress (WebSocket, no reload).

What you'll see:
- Stage stepper advances through Load → Validate → Match → Save → Report.
- Progress bar resets per stage.
- Log lines stream in real time.
- When done: a result table appears (total/ok/skipped/errors) — no page reload.
- A language switcher in the nav — the UI is translated into English, Polish,
  Ukrainian, Lithuanian, Estonian, German, French, Simplified Chinese, and
  Japanese. (Live-pushed log/status lines render in the server's language; the
  static chrome and stage stepper follow the selected language.)

## Zero-infra text path (no Docker, no Redis, no browser)

```bash
make demo-text
```

Runs `DemoImport` synchronously in `TextProgress` mode (stdout). tqdm bar
if installed, else plain percent prints. No Redis, no ASGI, no browser needed.
Useful for CI smoke tests.

## Stack

| Service | Role |
|---------|------|
| `redis:7` | Channel layer broker |
| `web`   | Daphne ASGI on :8000 (migrate + seed on start) |
| `worker` | Celery worker consuming liveop tasks |

## Auto-login

`/__login__/` logs you in as the first superuser (dev only, `DEBUG=True`).
This is how `make demo` skips the login form.
