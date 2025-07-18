#!/usr/bin/env python3
"""
Test script for LazyModelLoader.

This script tests the basic functionality of the LazyModelLoader class
without requiring full model downloads.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fluentai.model_loader import LazyModelLoader


def test_initialization():
    """Test LazyModelLoader initialization."""
    print("Testing LazyModelLoader initialization...")

    loader = LazyModelLoader(cache_dir="./test_cache", max_cache_size=5)

    # Check basic properties
    assert loader.cache_dir.name == "test_cache"
    assert loader.max_cache_size == 5
    assert len(loader._translation_models) == 0
    assert len(loader._whisper_models) == 0

    print("✅ Initialization test passed")
    return loader


def test_supported_language_pairs():
    """Test getting supported language pairs."""
    print("Testing supported language pairs...")

    loader = LazyModelLoader()
    pairs = loader.get_supported_language_pairs()

    # Check that we have the expected pairs
    expected_pairs = [
        ('es', 'en'), ('en', 'es'),
        ('es', 'de'), ('de', 'es'),
        ('es', 'fr'), ('fr', 'es'),
        ('en', 'de'), ('de', 'en'),
        ('en', 'fr'), ('fr', 'en'),
    ]

    for pair in expected_pairs:
        assert pair in pairs, f"Expected pair {pair} not found in supported pairs"

    print(f"✅ Found {len(pairs)} supported language pairs")
    return loader


def test_cache_info():
    """Test cache information functionality."""
    print("Testing cache information...")

    loader = LazyModelLoader()
    info = loader.get_cached_models_info()

    # Check structure
    expected_keys = [
        'translation_models_cached', 'whisper_models_cached',
        'cache_size_limit', 'translation_models', 'whisper_models',
        'supported_pairs'
    ]

    for key in expected_keys:
        assert key in info, f"Expected key {key} not found in cache info"

    # Check initial values
    assert info['translation_models_cached'] == 0
    assert info['whisper_models_cached'] == 0
    assert info['supported_pairs'] == 10  # Number of supported pairs

    print("✅ Cache info test passed")
    return loader


def test_progress_callback():
    """Test progress callback functionality."""
    print("Testing progress callback...")

    messages = []

    def test_callback(message, progress):
        messages.append((message, progress))

    loader = LazyModelLoader()
    loader.set_progress_callback(test_callback)

    # Test progress reporting
    loader._report_progress("Test message", 50.0)

    assert len(messages) == 1
    assert messages[0][0] == "Test message"
    assert messages[0][1] == 50.0

    print("✅ Progress callback test passed")
    return loader


def test_model_key_validation():
    """Test model key validation."""
    print("Testing model key validation...")

    loader = LazyModelLoader()

    # Test valid pairs
    valid_pairs = [('es', 'en'), ('en', 'es'), ('de', 'fr')]
    for src, tgt in valid_pairs[:2]:  # Test first two which should be valid
        assert (src, tgt) in loader.TRANSLATION_MODELS

    # Test invalid pairs
    invalid_pairs = [('es', 'es'), ('invalid', 'en'), ('es', 'invalid')]
    for src, tgt in invalid_pairs:
        assert (src, tgt) not in loader.TRANSLATION_MODELS

    print("✅ Model key validation test passed")
    return loader


def test_cleanup():
    """Test cleanup functionality."""
    print("Testing cleanup...")

    loader = LazyModelLoader()

    # Test clear cache
    loader.clear_cache()
    assert len(loader._translation_models) == 0
    assert len(loader._whisper_models) == 0

    # Test shutdown
    loader.shutdown()

    print("✅ Cleanup test passed")


def main():
    """Run all tests."""
    print("🧪 Running LazyModelLoader tests...")
    print("=" * 50)

    try:
        # Run tests
        test_initialization()
        test_supported_language_pairs()
        test_cache_info()
        test_progress_callback()
        test_model_key_validation()
        test_cleanup()

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
