"""
Shared rendering helpers for liveops.

render_op_container: renders the live_operation container fragment for a
given operation, optionally annotated with an hx-swap-oob attribute for
chain_to OOB swaps.  Used by:
  - liveops templatetag
  - WebProgress.chain_to  (passes oob_target to trigger OOB container swap)
"""

from __future__ import annotations

from typing import Any, Optional


def render_op_container(
    op: Any, oob_target: Optional[str] = None, request: Any = None
) -> str:
    """Return rendered HTML for the live_operation container.

    *op*         — LiveOperation instance.
    *oob_target* — if given, the rendered element will carry
                   ``hx-swap-oob="outerHTML:#<oob_target>"`` so that the
                   client-side OOB handler replaces the old container
                   in-place (used by chain_to).
    *request*    — pass the current request when rendering on a page load, so
                   ``{% csrf_token %}`` in the cancel/restart forms produces a
                   real token and Django sets the CSRF cookie. Omitted for
                   worker-side pushes (chain_to), which have no request.
    """
    from django.template.loader import render_to_string

    return render_to_string(
        "liveops/_live_operation.html",
        {"op": op, "oob_target": oob_target},
        request=request,
    )
