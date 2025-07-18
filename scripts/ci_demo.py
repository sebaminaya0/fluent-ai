#!/usr/bin/env python3
"""
Simple demo script for CI testing of FluentAI components.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_vad_import():
    """Test VAD functionality import."""
    try:
        from silence_detector import create_silence_detector, SILENCE_DETECTION_PRESETS
        print("✓ VAD imports successful")
        
        # Test detector creation
        detector = create_silence_detector('balanced', min_silence_len=400)
        print("✓ VAD detector created")
        
        # Test with dummy audio
        import numpy as np
        dummy_audio = np.zeros(1024, dtype=np.int16).tobytes()
        result = detector.process_audio_frame(dummy_audio)
        print("✓ VAD processing successful")
        
        return True
    except Exception as e:
        print(f"✗ VAD test failed: {e}")
        return False

def test_asr_import():
    """Test ASR functionality import."""
    try:
        from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread
        print("✓ ASR imports successful")
        
        # Test basic instantiation
        import queue
        q_in = queue.Queue()
        q_out = queue.Queue()
        
        thread = ASRTranslationSynthesisThread(
            q_in, q_out, 
            src_lang='es', 
            dst_lang='en',
            whisper_model='base'
        )
        print("✓ ASR thread creation successful")
        
        return True
    except Exception as e:
        print(f"✗ ASR test failed: {e}")
        return False

def test_model_loader():
    """Test model loader functionality."""
    try:
        from fluentai.model_loader import LazyModelLoader
        print("✓ Model loader imports successful")
        
        # Test basic instantiation
        loader = LazyModelLoader()
        print("✓ Model loader creation successful")
        
        # Test supported language pairs
        pairs = loader.get_supported_language_pairs()
        print(f"✓ Found {len(pairs)} supported language pairs")
        
        return True
    except Exception as e:
        print(f"✗ Model loader test failed: {e}")
        return False

def main():
    """Run all CI demo tests."""
    print("Running FluentAI CI Demo Tests")
    print("=" * 40)
    
    tests = [
        test_vad_import,
        test_asr_import,
        test_model_loader,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        print(f"\nRunning {test_func.__name__}...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All CI demo tests passed!")
        return 0
    else:
        print("✗ Some CI demo tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
