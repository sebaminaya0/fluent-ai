"""Non-mocked metadata/unit tests for LazyModelLoader.

These cover the loader's static behavior (supported pairs, cache info,
key validation, progress callbacks, cleanup) without downloading models
or mocking the transformers pipeline. They were folded in from the old
root-level ``test_model_loader.py`` scratch script.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.model_loader import LazyModelLoader  # noqa: E402

EXPECTED_PAIRS = [
    ("es", "en"),
    ("en", "es"),
    ("es", "de"),
    ("de", "es"),
    ("es", "fr"),
    ("fr", "es"),
    ("en", "de"),
    ("de", "en"),
    ("en", "fr"),
    ("fr", "en"),
]


def test_initialization(tmp_path):
    loader = LazyModelLoader(cache_dir=str(tmp_path / "test_cache"), max_cache_size=5)
    assert loader.cache_dir.name == "test_cache"
    assert loader.max_cache_size == 5
    assert len(loader._translation_models) == 0
    assert len(loader._whisper_models) == 0
    loader.shutdown()


def test_supported_language_pairs():
    loader = LazyModelLoader()
    pairs = loader.get_supported_language_pairs()
    for pair in EXPECTED_PAIRS:
        assert pair in pairs, f"Expected pair {pair} not found in supported pairs"
    loader.shutdown()


def test_cache_info_initial_values():
    loader = LazyModelLoader()
    info = loader.get_cached_models_info()
    for key in (
        "translation_models_cached",
        "whisper_models_cached",
        "cache_size_limit",
        "translation_models",
        "whisper_models",
        "supported_pairs",
    ):
        assert key in info, f"Expected key {key} not found in cache info"
    assert info["translation_models_cached"] == 0
    assert info["whisper_models_cached"] == 0
    assert info["supported_pairs"] == len(EXPECTED_PAIRS)
    loader.shutdown()


def test_progress_callback():
    messages = []

    loader = LazyModelLoader()
    loader.set_progress_callback(
        lambda message, progress: messages.append((message, progress))
    )
    loader._report_progress("Test message", 50.0)

    assert messages == [("Test message", 50.0)]
    loader.shutdown()


def test_model_key_validation():
    loader = LazyModelLoader()
    for pair in (("es", "en"), ("en", "es")):
        assert pair in loader.TRANSLATION_MODELS
    for pair in (("es", "es"), ("invalid", "en"), ("es", "invalid")):
        assert pair not in loader.TRANSLATION_MODELS
    loader.shutdown()


def test_cleanup():
    loader = LazyModelLoader()
    loader.clear_cache()
    assert len(loader._translation_models) == 0
    assert len(loader._whisper_models) == 0
    loader.shutdown()
