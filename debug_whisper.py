#!/usr/bin/env python3
"""
Debug script to check what Whisper is transcribing
"""
import queue
import time
import tempfile
import os
import whisper

def debug_whisper_transcription():
    """Debug what Whisper is actually transcribing"""
    print("=== Debugging Whisper Transcription ===")
    
    # Load Whisper model
    print("Loading Whisper model...")
    model = whisper.load_model("base", device="cpu")
    print("✅ Whisper model loaded")
    
    # Test with captured audio
    from audio_capture_thread import AudioCaptureThread
    
    asr_queue = queue.Queue(maxsize=10)
    
    # Capture some audio
    print("\nStarting audio capture...")
    capture_thread = AudioCaptureThread(
        asr_queue=asr_queue,
        sample_rate=16000,
        vad_aggressiveness=2,
        voice_threshold_ms=200,
        silence_threshold_ms=400
    )
    capture_thread.start()
    
    time.sleep(2)
    print("Please speak clearly for 3 seconds...")
    time.sleep(3)
    
    capture_thread.stop()
    print(f"✅ Captured {asr_queue.qsize()} audio segments")
    
    # Process each captured segment
    segment_num = 0
    while not asr_queue.empty():
        segment_num += 1
        audio_segment = asr_queue.get()
        
        print(f"\n--- Processing Segment {segment_num} ---")
        print(f"Duration: {audio_segment['duration']:.2f}s")
        print(f"Samples: {audio_segment['samples']}")
        print(f"Sample rate: {audio_segment['sample_rate']}")
        print(f"WAV data size: {len(audio_segment['wav_data'])} bytes")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_segment['wav_data'])
            temp_file_path = temp_file.name
        
        try:
            # Transcribe with Whisper
            print(f"Transcribing {temp_file_path}...")
            result = model.transcribe(temp_file_path, language='es')
            
            print(f"Raw result: {result}")
            print(f"Text: '{result['text']}'")
            print(f"Text length: {len(result['text'])}")
            print(f"Text stripped: '{result['text'].strip()}'")
            print(f"Stripped length: {len(result['text'].strip())}")
            
            if result['text'].strip():
                print("✅ SUCCESS: Got transcription!")
            else:
                print("❌ FAILED: Empty transcription")
                
            # Show segments if available
            if 'segments' in result:
                print(f"Segments: {len(result['segments'])}")
                for i, segment in enumerate(result['segments']):
                    print(f"  Segment {i+1}: '{segment['text']}'")
                    
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            
        finally:
            # Clean up
            os.unlink(temp_file_path)

if __name__ == "__main__":
    debug_whisper_transcription()
