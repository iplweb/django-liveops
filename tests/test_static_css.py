"""
Smoke tests for the liveops.css static file.

Asserts:
- File ships at the expected static path inside the package.
- File styles the semantic component classes the templates render.
"""

from pathlib import Path

import liveops

STATIC_CSS = Path(liveops.__file__).parent / "static" / "liveops" / "liveops.css"


def test_css_file_exists():
    """liveops.css is present in the package static directory."""
    assert STATIC_CSS.exists(), f"Expected CSS file at {STATIC_CSS}"
    assert STATIC_CSS.is_file()


def test_css_styles_progress_components():
    """Progress bar track + fill are styled."""
    content = STATIC_CSS.read_text()
    assert ".progress-bar" in content
    assert ".progress-fill" in content
    assert "transition" in content


def test_css_styles_stage_states():
    """Stage pill and its active/done/failed/cancelled variants are styled."""
    content = STATIC_CSS.read_text()
    assert ".op-stage" in content
    assert ".op-stage--active" in content
    assert ".op-stage--done" in content
    assert ".op-stage--failed" in content
    assert ".op-stage--cancelled" in content


def test_css_styles_regions_and_controls():
    """Status/log regions and cancel/restart controls are styled."""
    content = STATIC_CSS.read_text()
    assert "#op-status" in content
    assert "#op-log" in content
    assert ".op-controls-cancel" in content
    assert ".op-controls-restart" in content


def test_css_hides_empty_regions():
    """Empty regions collapse so unused areas don't reserve space."""
    content = STATIC_CSS.read_text()
    assert ":empty" in content
    assert "#op-status:empty" in content
