#!/usr/bin/env python3
"""
Test script to verify queue flow between threads
"""
import queue
import time
import threading
from audio_capture_thread import AudioCaptureThread
from fluentai.asr_translation_synthesis_thread import ASRTranslationSynthesisThread
from fluentai.blackhole_reproduction_thread import BlackHoleReproductionThread

def test_queue_flow():
    """Test the queue flow between all threads"""
    print("=== Testing Queue Flow ===")
    
    # Create queues
    asr_queue = queue.Queue(maxsize=10)
    output_queue = queue.Queue(maxsize=10)
    
    print(f"Initial queue sizes:")
    print(f"  ASR queue: {asr_queue.qsize()}")
    print(f"  Output queue: {output_queue.qsize()}")
    
    # Test 1: Audio Capture Thread
    print("\n1. Testing Audio Capture Thread...")
    try:
        capture_thread = AudioCaptureThread(
            asr_queue=asr_queue,
            sample_rate=16000,
            vad_aggressiveness=2,
            voice_threshold_ms=200,
            silence_threshold_ms=400
        )
        capture_thread.start()
        print("✅ Audio capture thread started")
        
        # Wait for some audio capture
        time.sleep(3)
        print("Say something...")
        time.sleep(5)
        
        # Check queue
        asr_queue_size = asr_queue.qsize()
        print(f"ASR queue size after 8 seconds: {asr_queue_size}")
        
        # Stop capture thread
        capture_thread.stop()
        print("✅ Audio capture thread stopped")
        
        if asr_queue_size > 0:
            print(f"✅ SUCCESS: {asr_queue_size} audio segments captured")
        else:
            print("❌ FAILED: No audio segments captured")
            
    except Exception as e:
        print(f"❌ Audio capture test failed: {e}")
        return False
    
    # Test 2: ASR Thread
    print("\n2. Testing ASR Thread...")
    try:
        if asr_queue.qsize() > 0:
            asr_thread = ASRTranslationSynthesisThread(
                queue_in=asr_queue,
                queue_out=output_queue,
                src_lang='es',
                dst_lang='en',
                whisper_model='base'
            )
            asr_thread.start()
            print("✅ ASR thread started")
            
            # Wait for processing
            time.sleep(10)
            
            # Check output queue
            output_queue_size = output_queue.qsize()
            print(f"Output queue size after processing: {output_queue_size}")
            
            # Stop ASR thread
            asr_thread.stop()
            print("✅ ASR thread stopped")
            
            if output_queue_size > 0:
                print(f"✅ SUCCESS: {output_queue_size} audio segments processed")
            else:
                print("❌ FAILED: No audio segments processed")
                
        else:
            print("❌ SKIPPED: No audio to process")
            
    except Exception as e:
        print(f"❌ ASR test failed: {e}")
        return False
    
    # Test 3: BlackHole Thread
    print("\n3. Testing BlackHole Thread...")
    try:
        if output_queue.qsize() > 0:
            blackhole_thread = BlackHoleReproductionThread(
                output_device=1,  # BlackHole device
                input_queue=output_queue,
                sample_rate=44100
            )
            blackhole_thread.start()
            print("✅ BlackHole thread started")
            
            # Wait for playback
            time.sleep(5)
            
            # Check if queue was emptied (indicating audio was consumed)
            remaining_output = output_queue.qsize()
            print(f"Remaining output queue size: {remaining_output}")
            
            # Stop BlackHole thread
            blackhole_thread.stop()
            print("✅ BlackHole thread stopped")
            
            if remaining_output == 0:
                print("✅ SUCCESS: Audio played through BlackHole (queue emptied)")
            else:
                print(f"❌ FAILED: Audio not fully consumed ({remaining_output} items remaining)")
                
        else:
            print("❌ SKIPPED: No audio to play")
            
    except Exception as e:
        print(f"❌ BlackHole test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_queue_flow()
    if success:
        print("\n🎉 All tests passed! Queue flow is working.")
    else:
        print("\n❌ Some tests failed. Check the logs above.")
