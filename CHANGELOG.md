# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `LiveOperation.get_success_url()` — return a URL to auto-redirect the
  browser to when the operation finishes successfully (default `None` keeps
  the user on the live page). Flows through the `liveop_finished` signal as
  `success_url`; `liveops.js` navigates there on `FINISHED_OK`. Lets a
  consumer skip the operations index and land on a dedicated page.
- Demo (`example/`): a catalogue of operation types — staged import, quick
  task, failing task, chained task, and redirect-on-success — reachable from
  a landing page, so every shape of the framework can be tried in the browser.

### Fixed
- Demo URLs updated to the 0.2.0 op_type routing (they still used the old
  per-pk `liveops` patterns and would `NoReverseMatch`).

## [0.2.0]

### Changed
- **BREAKING — central op_type routing.** The `liveops:live`, `liveops:cancel`
  and `liveops:restart` URLs now carry an `op_type` segment
  (`<app_label>.<model_name>`), and `LiveOperation.get_absolute_url()` includes
  it. `liveops.urls` now ships these three **generic** patterns — mount them
  **once** in the project root (`path("live/", include("liveops.urls"))`) and
  they serve *every* `LiveOperation` subclass via an O(1) `apps.get_model`
  lookup. Consumer apps no longer subclass `LiveOperationView` /
  `CancelView` / `RestartView` per model, and no longer register their own
  `liveops`-namespaced URLs for them (only `create`/`list`, which need a
  form/model, stay app-specific).
  - Migration: replace per-app `live/cancel/restart` URL entries with a single
    `include("liveops.urls")`; drop the per-model view subclasses.

### Added
- `LiveOperation.op_type_key()` — stable, reversible key used for routing.
- `LiveOperation.on_restart()` — model hook called by `RestartView` before it
  resets state and re-enqueues (override to clean up child records).
- Superusers are now exempt from the `LIVEOPS["REQUIRED_GROUP"]` gate
  (matches Django admin / django-braces semantics).

## [0.1.0]

### Added
- Initial release of **django-liveops**.
- `LiveOperation` abstract model + ergonomic `run(self, p)` API.
- `Progress` with pluggable backends: `WebProgress` (WebSocket + HTML
  out-of-band swaps, no reload, no polling) and `TextProgress` (tqdm/CLI).
- Live progress API: `status`, `percent`, `track` (tqdm-style), `log`,
  `stage` (multi-stage stepper), `result`, `error`, `check_cancelled`,
  `chain_to` (chain operations without reload); web-only `swap`/`html`.
- Transport via `django-channels-broadcast` (`addMessage` OOB-swap plugin);
  HTML in a JSON envelope; snapshot-on-connect (terminal state = source of
  truth); subscription tokens binding a user to one operation channel.
- Reusable class-based views + `{% live_operation %}` templatetag +
  auto-derived templates/channel names.
- `run_liveop` management command (text/CLI mode).
- Example demo project with one-command Docker stack (`make demo`).
- Full MkDocs documentation and a three-tier test suite (consumer unit,
  `Progress` unit, worker→Redis round-trip via testcontainers).
