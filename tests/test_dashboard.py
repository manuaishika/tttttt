"""Headless smoke tests: the app must run on the real processed data without exceptions."""
from pathlib import Path
import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")


def _run(**state):
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def test_app_renders_without_exceptions():
    at = _run()
    assert not at.exception
    assert any("Activity records" in m.label for m in at.metric)


def test_state_focus_and_search_do_not_crash():
    at = _run(focus_state="Karnataka")
    assert not at.exception
    at.text_input[0].input("zzzz-no-such-term").run()
    assert not at.exception          # empty result set must be handled
