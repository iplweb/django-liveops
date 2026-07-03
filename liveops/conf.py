from django.conf import settings

_DEFAULTS = {
    "BASE_TEMPLATE": "base.html",
    "RUNNER": "eager",
    "THROTTLE_HZ": 10,
    # Live operations list: push a per-user "list changed" signal on
    # create/start/finish so open list pages refresh. Set False to opt out.
    "LIST_LIVE": True,
}


def get_setting(key: str, default=None):
    """Read a value from settings.LIVEOPS dict with fallback to _DEFAULTS."""
    live_ops = getattr(settings, "LIVEOPS", {})
    if key in live_ops:
        return live_ops[key]
    if default is not None:
        return default
    return _DEFAULTS.get(key)
