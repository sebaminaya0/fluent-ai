#!/usr/bin/env python3
"""
Test script for FluentAI CLI functionality

This script demonstrates the CLI capabilities without requiring 
actual audio hardware or full thread initialization.
"""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """Test CLI help functionality."""
    print("Testing CLI help...")

    try:
        result = subprocess.run([
            "uv", "run", "python", "-m", "fluentai.cli.translate_rt", "--help"
        ], capture_output=True, text=True, cwd=Path.cwd())

        if result.returncode == 0:
            print("✅ CLI help working correctly")
            print("Usage information:")
            print(result.stdout)
        else:
            print("❌ CLI help failed")
            print("Error:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Error running CLI help: {e}")
        return False

    return True

def test_cli_validation():
    """Test CLI argument validation."""
    print("\nTesting CLI argument validation...")

    # Test missing required arguments
    try:
        result = subprocess.run([
            "uv", "run", "python", "-m", "fluentai.cli.translate_rt"
        ], capture_output=True, text=True, cwd=Path.cwd())

        if result.returncode != 0 and "required" in result.stderr:
            print("✅ Required argument validation working")
        else:
            print("❌ Required argument validation failed")
            return False

    except Exception as e:
        print(f"❌ Error testing validation: {e}")
        return False

    # Test same source and destination
    try:
        result = subprocess.run([
            "uv", "run", "python", "-m", "fluentai.cli.translate_rt",
            "--src", "en", "--dst", "en"
        ], capture_output=True, text=True, cwd=Path.cwd())

        if result.returncode != 0:
            print("✅ Same source/destination validation working")
        else:
            print("❌ Same source/destination validation failed")
            return False

    except Exception as e:
        print(f"❌ Error testing same language validation: {e}")
        return False

    return True

def test_configuration_loading():
    """Test configuration loading."""
    print("\nTesting configuration loading...")

    # Check if languages.yaml exists
    config_path = Path("conf/languages.yaml")
    if not config_path.exists():
        print("❌ Language configuration file not found")
        return False

    print("✅ Language configuration file exists")

    # Test loading configuration with valid languages
    try:
        result = subprocess.run([
            "uv", "run", "python", "-c",
            """
import yaml
from pathlib import Path

config_path = Path("conf/languages.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

print("Available languages:", list(config.keys()))
for lang, settings in config.items():
    print(f"  {lang}: whisper={settings.get('whisper')}, tts={settings.get('tts')}")
            """
        ], capture_output=True, text=True, cwd=Path.cwd())

        if result.returncode == 0:
            print("✅ Configuration loading working")
            print(result.stdout)
        else:
            print("❌ Configuration loading failed")
            print("Error:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        return False

    return True

def test_thread_initialization():
    """Test thread initialization (without actually starting them)."""
    print("\nTesting thread initialization...")

    # Test initialization with dry-run approach
    try:
        result = subprocess.run([
            "uv", "run", "python", "-c",
            """
import sys
import os
sys.path.insert(0, os.getcwd())

from fluentai.cli.translate_rt import RealTimeTranslator

# Test initialization without starting
try:
    translator = RealTimeTranslator(
        src_lang='es',
        dst_lang='en', 
        voice='female',
        vad_aggressiveness=2
    )
    print("✅ RealTimeTranslator initialized successfully")
    print(f"Source language: {translator.src_lang}")
    print(f"Destination language: {translator.dst_lang}")
    print(f"Language config loaded: {len(translator.language_config)} languages")
    
except Exception as e:
    print(f"❌ RealTimeTranslator initialization failed: {e}")
    sys.exit(1)
            """
        ], capture_output=True, text=True, cwd=Path.cwd())

        if result.returncode == 0:
            print("✅ Thread initialization working")
            print(result.stdout)
        else:
            print("❌ Thread initialization failed")
            print("Error:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Error testing thread initialization: {e}")
        return False

    return True

def main():
    """Run all tests."""
    print("FluentAI CLI Test Suite")
    print("=" * 50)

    tests = [
        test_cli_help,
        test_cli_validation,
        test_configuration_loading,
        test_thread_initialization
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
