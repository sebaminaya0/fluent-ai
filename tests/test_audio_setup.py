"""Tests for fluentai.audio_setup (BlackHole install + CoreAudio routing).

CoreAudio is mocked so these run deterministically on any platform/CI.
"""

import pytest

from fluentai import audio_setup


def test_find_device_id_by_name(monkeypatch):
    names = {1: "MacBook Pro Microphone", 2: "BlackHole 2ch", 3: "Speakers"}
    monkeypatch.setattr(audio_setup, "_all_device_ids", lambda: list(names))
    monkeypatch.setattr(audio_setup, "_device_name", lambda d: names[d])

    assert audio_setup.find_device_id_by_name("BlackHole") == 2
    assert audio_setup.find_device_id_by_name("blackhole") == 2  # case-insensitive
    assert audio_setup.find_device_id_by_name("Nonexistent") is None


def test_off_macos_is_safe(monkeypatch):
    monkeypatch.setattr(audio_setup, "_IS_MACOS", False)
    assert audio_setup.is_blackhole_installed() is False
    assert audio_setup.ensure_blackhole_installed() is False

    state = audio_setup.enter_meeting_routing()
    assert state.active is False
    # Restoring an inactive/None state must never raise.
    audio_setup.exit_meeting_routing(state)
    audio_setup.exit_meeting_routing(None)


def test_enter_routing_inactive_without_blackhole(monkeypatch):
    monkeypatch.setattr(audio_setup, "_IS_MACOS", True)
    monkeypatch.setattr(
        audio_setup, "_default_input_sounddevice_index", lambda: (1, "Mic")
    )
    monkeypatch.setattr(audio_setup, "get_default_input_id", lambda: 89)
    monkeypatch.setattr(audio_setup, "find_device_id_by_name", lambda s: None)

    state = audio_setup.enter_meeting_routing()

    assert state.active is False  # no BlackHole -> don't touch the system
    assert state.real_mic_index == 1
    assert state.blackhole_id is None


def test_enter_switches_to_blackhole_and_exit_restores(monkeypatch):
    monkeypatch.setattr(audio_setup, "_IS_MACOS", True)
    monkeypatch.setattr(audio_setup, "reinitialize_portaudio", lambda: None)
    monkeypatch.setattr(audio_setup, "_resolve_real_mic", lambda: (1, "Built-in Mic"))
    # Distinct ids: real mic -> 11, BlackHole -> 42.
    monkeypatch.setattr(
        audio_setup,
        "find_device_id_by_name",
        lambda s: 42 if "blackhole" in s.lower() else 11,
    )

    switched = []
    monkeypatch.setattr(
        audio_setup,
        "set_default_input_id",
        lambda dev: (switched.append(dev) or True),
    )

    state = audio_setup.enter_meeting_routing()
    assert state.active is True
    assert state.blackhole_id == 42
    assert state.real_mic_index == 1
    assert switched == [42]  # default input -> BlackHole

    audio_setup.exit_meeting_routing(state)
    assert switched == [42, 11]  # restored to the real mic
    assert state.active is False


def test_ensure_installed_is_idempotent_when_present(monkeypatch):
    monkeypatch.setattr(audio_setup, "_IS_MACOS", True)
    monkeypatch.setattr(audio_setup, "is_blackhole_installed", lambda: True)
    # Should short-circuit without attempting any download/install.
    assert audio_setup.ensure_blackhole_installed() is True


def test_is_real_mic_name_excludes_virtual_inputs():
    assert audio_setup._is_real_mic_name("MacBook Pro Microphone") is True
    assert audio_setup._is_real_mic_name("Sebastián’s AirPods Pro") is True
    assert audio_setup._is_real_mic_name("BlackHole 2ch") is False
    assert audio_setup._is_real_mic_name("Aggregate Device") is False
    assert audio_setup._is_real_mic_name("") is False


def test_routing_never_captures_or_restores_blackhole(monkeypatch):
    # The bug: when the default input was already BlackHole, routing captured
    # BlackHole (silence) and restored the default back to BlackHole forever.
    monkeypatch.setattr(audio_setup, "_IS_MACOS", True)
    monkeypatch.setattr(audio_setup, "reinitialize_portaudio", lambda: None)
    # _resolve_real_mic must return a real mic even if the default is BlackHole.
    monkeypatch.setattr(
        audio_setup, "_resolve_real_mic", lambda: (4, "MacBook Pro Microphone")
    )
    monkeypatch.setattr(
        audio_setup,
        "find_device_id_by_name",
        lambda s: 42 if "blackhole" in s.lower() else 11,
    )
    switched = []
    monkeypatch.setattr(
        audio_setup,
        "set_default_input_id",
        lambda dev: (switched.append(dev) or True),
    )

    state = audio_setup.enter_meeting_routing()
    assert state.active is True
    assert state.real_mic_index == 4  # capture the real mic, never BlackHole
    assert state.real_mic_name == "MacBook Pro Microphone"
    assert state.blackhole_id == 42
    assert state.saved_default_input_id == 11  # restore to the real mic, not 42
    assert switched == [42]  # default switched to BlackHole for the call

    audio_setup.exit_meeting_routing(state)
    assert switched == [42, 11]  # restored to the real mic (self-heal)


def test_routing_aborts_when_no_real_mic(monkeypatch):
    monkeypatch.setattr(audio_setup, "_IS_MACOS", True)
    monkeypatch.setattr(audio_setup, "reinitialize_portaudio", lambda: None)
    monkeypatch.setattr(audio_setup, "_resolve_real_mic", lambda: (None, ""))
    monkeypatch.setattr(audio_setup, "find_device_id_by_name", lambda s: 42)
    monkeypatch.setattr(
        audio_setup, "set_default_input_id", lambda dev: pytest.fail("must not switch")
    )

    state = audio_setup.enter_meeting_routing()
    assert state.active is False  # don't hijack the default with no mic to capture


def test_looks_like_pkg_rejects_html_and_accepts_xar(tmp_path):
    # The original bug: an email-gate HTML page was treated as a .pkg.
    html = tmp_path / "page.html"
    html.write_bytes(b"<html><head><title>Download</title></head></html>" * 500)
    assert audio_setup._looks_like_pkg(str(html)) is False

    pkg = tmp_path / "BlackHole.pkg"
    pkg.write_bytes(b"xar!" + b"\x00" * 20_000)  # xar magic + bulk
    assert audio_setup._looks_like_pkg(str(pkg)) is True

    assert audio_setup._looks_like_pkg(str(tmp_path / "missing.pkg")) is False
