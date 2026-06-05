"""Unit tests for the non-UI TranslationController."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.app_controller import TranslationController  # noqa: E402


class FakeLoader:
    """Minimal model loader returning a fake translator pipeline."""

    def __init__(self, available=True):
        self.available = available

    def get_model(self, src, dst):
        if not self.available:
            return None
        return lambda text, **kwargs: [{"translation_text": f"<{src}->{dst}> {text}"}]


def test_translate_returns_text():
    ctrl = TranslationController(FakeLoader())
    assert ctrl.translate("hola", "es", "en") == "<es->en> hola"


def test_translate_returns_none_when_no_model():
    ctrl = TranslationController(FakeLoader(available=False))
    assert ctrl.translate("hola", "es", "xx") is None


def test_determine_target_language_auto():
    ctrl = TranslationController(FakeLoader())
    assert ctrl.determine_target_language("es", "auto") == "en"
    assert ctrl.determine_target_language("en", "auto") == "es"
    assert ctrl.determine_target_language("de", "auto") == "es"
    assert ctrl.determine_target_language("fr", "auto") == "es"


def test_determine_target_language_explicit():
    ctrl = TranslationController(FakeLoader())
    assert ctrl.determine_target_language("es", "fr") == "fr"
    # Invalid combination (de->fr is not supported) returns None.
    assert ctrl.determine_target_language("de", "fr") is None


def test_validate_text():
    ctrl = TranslationController(FakeLoader())
    assert ctrl.validate_text("hola mundo", "es") is True
    assert ctrl.validate_text("x", "es") is False  # too short
    assert ctrl.validate_text("hello", "xx") is False  # unsupported language
    assert ctrl.validate_text("日本語テキストです", "ja") is False  # non-latin


def test_detect_tts_language():
    ctrl = TranslationController(FakeLoader())
    assert ctrl.detect_tts_language("hola, ¿cómo estás?") == "es"
    assert ctrl.detect_tts_language("der die das und ich") == "de"
    assert ctrl.detect_tts_language("je vous remercie avec où") == "fr"
    assert ctrl.detect_tts_language("zzz 1234") == "en"  # no indicator substrings
