"""Tests for the mic-in-use meeting detector."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fluentai.meeting_detector as md  # noqa: E402
from fluentai.meeting_detector import MicMonitor, _Debounce  # noqa: E402


def test_basic_queries_return_bools():
    # Safe on any platform (non-macOS -> False); just assert the contract.
    assert isinstance(md.is_available(), bool)
    assert isinstance(md.is_mic_in_use(), bool)


def test_debounce_start_after_threshold():
    d = _Debounce(start_debounce_s=3, end_debounce_s=3)
    assert d.step(True, 0) is None  # just started
    assert d.step(True, 2) is None  # 2s < 3s
    assert d.step(True, 3) == "start"  # reached threshold
    assert d.step(True, 9) is None  # already in call
    assert d.in_call is True


def test_debounce_end_after_threshold():
    d = _Debounce(3, 3)
    d.step(True, 0)
    d.step(True, 3)  # now in call
    assert d.step(False, 4) is None  # just became free (0s)
    assert d.step(False, 6) is None  # free 2s < 3s
    assert d.step(False, 7) == "end"  # free 3s -> end
    assert d.in_call is False


def test_debounce_ignores_brief_blip():
    d = _Debounce(3, 3)
    assert d.step(True, 0) is None
    assert d.step(False, 1) is None  # blip resets the start timer
    assert d.step(True, 2) is None
    assert d.step(True, 4) is None  # 4-2 = 2 < 3
    assert d.step(True, 5) == "start"  # 5-2 = 3 -> start


def test_micmonitor_fires_started(monkeypatch):
    monkeypatch.setattr(md, "is_available", lambda: True)
    monkeypatch.setattr(md, "is_mic_in_use", lambda: True)
    fired = []
    monitor = MicMonitor(
        on_call_started=lambda: fired.append("start"),
        poll_interval_s=0.01,
        start_debounce_s=0.02,
        end_debounce_s=0.02,
    )
    monitor.start()
    deadline = time.time() + 2
    while not fired and time.time() < deadline:
        time.sleep(0.02)
    monitor.stop()
    monitor.join(timeout=1)
    assert fired == ["start"]
