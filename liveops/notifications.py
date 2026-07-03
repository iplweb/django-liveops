"""
Per-user "operations list changed" signal.

The operations list page subscribes to the authenticated user's audience
channel (via channels_broadcast). When one of that user's operations is
created, starts, or finishes, ``notify_list_changed`` pushes a lightweight
signal to that channel so any open list page re-fetches its table.

Coarse by design: fired only at lifecycle transitions (create / start /
finish), never per progress tick. Best-effort — a missing channel layer or a
disabled setting never breaks the operation itself.
"""

from __future__ import annotations

from typing import Any


def notify_list_changed(operation: Any) -> None:
    """Ping the operation owner's channel so open list pages refresh."""
    from liveops.conf import get_setting

    if not get_setting("LIST_LIVE"):
        return

    owner = getattr(operation, "owner", None)
    if owner is None:
        return

    try:
        from channels_broadcast.core import _send, get_channel_name_for_user

        _send(
            get_channel_name_for_user(owner),
            {"type": "chat_message", "liveop_list_changed": True},
        )
    except Exception:
        # No channel layer / broadcast unavailable — the list just won't
        # auto-refresh; the operation itself is unaffected.
        pass
