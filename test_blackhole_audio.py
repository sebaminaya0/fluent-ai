#!/usr/bin/env python3
"""
Test script to verify BlackHole audio output with a simple tone
"""
import numpy as np
import sounddevice as sd
import time

def test_blackhole_audio():
    """Test BlackHole audio output with a simple tone"""
    print("=== Testing BlackHole Audio Output ===")
    
    # List available devices
    print("Available audio devices:")
    devices = sd.query_devices()
    print(devices)
    
    # Find BlackHole device
    blackhole_device = None
    for i, device in enumerate(devices):
        if 'BlackHole' in device['name']:
            blackhole_device = i
            print(f"Found BlackHole device: {i} - {device['name']}")
            break
    
    if blackhole_device is None:
        print("❌ BlackHole device not found!")
        return False
    
    # Test 1: Simple tone generation
    print("\n1. Testing simple tone generation...")
    sample_rate = 44100
    duration = 3.0  # 3 seconds
    frequency = 440  # A4 note
    
    # Generate a simple sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)  # 30% volume
    
    # Reshape for mono output
    audio_data = audio_data.reshape(-1, 1)
    
    print(f"Generated {len(audio_data)} samples at {sample_rate}Hz")
    print(f"Audio data shape: {audio_data.shape}")
    print(f"Audio data dtype: {audio_data.dtype}")
    print(f"Audio data range: [{audio_data.min():.3f}, {audio_data.max():.3f}]")
    
    try:
        print(f"Playing tone to BlackHole device {blackhole_device}...")
        sd.play(audio_data, samplerate=sample_rate, device=blackhole_device)
        
        # Wait for playback to complete
        for i in range(int(duration) + 1):
            print(f"Playing... {i+1}/{int(duration)+1} seconds")
            time.sleep(1)
        
        sd.wait()  # Wait for playback to finish
        print("✅ Tone playback completed")
        
    except Exception as e:
        print(f"❌ Error playing tone: {e}")
        return False
    
    # Test 2: Test with stream (like the BlackHole thread)
    print("\n2. Testing with OutputStream...")
    
    try:
        # Convert to float32 for OutputStream compatibility
        audio_data_f32 = audio_data.astype(np.float32)
        
        with sd.OutputStream(device=blackhole_device, samplerate=sample_rate, channels=1, dtype=np.float32, latency="low") as stream:
            print("✅ BlackHole OutputStream opened successfully")
            
            # Write audio in chunks
            chunk_size = 1024
            for i in range(0, len(audio_data_f32), chunk_size):
                chunk = audio_data_f32[i:i+chunk_size]
                if len(chunk) > 0:
                    stream.write(chunk)
                    print(f"Wrote chunk {i//chunk_size + 1}: {len(chunk)} samples")
                    time.sleep(0.01)  # Small delay between chunks
            
            print("✅ Audio streaming completed")
            
    except Exception as e:
        print(f"❌ Error with OutputStream: {e}")
        return False
    
    print("\n🎉 BlackHole audio output test completed!")
    print("If you have audio monitoring software (like BlackHole's loopback)")
    print("or if BlackHole is set as input in a video call, you should have heard a tone.")
    
    return True

if __name__ == "__main__":
    success = test_blackhole_audio()
    if success:
        print("\n✅ BlackHole audio output appears to be working!")
    else:
        print("\n❌ BlackHole audio output test failed!")
