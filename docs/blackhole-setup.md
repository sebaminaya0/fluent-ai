# BlackHole Installation and Setup Guide

## 1. Installation Instructions

### Install BlackHole via Homebrew
```bash
brew install blackhole-2ch
```

**Note:** This installs BlackHole 2ch (2-channel) audio driver. After installation, you may need to restart your Mac for the audio driver to be fully recognized by the system.

### Alternative Installation Methods
- Download directly from [BlackHole GitHub releases](https://github.com/ExistentialAudio/BlackHole/releases)
- Use the installer package (.pkg) for manual installation

## 2. Creating BlackHole + Mic Aggregate Device

### Using Audio MIDI Setup:

1. **Open Audio MIDI Setup**:
   - Press `Cmd + Space` and search for "Audio MIDI Setup"
   - Or go to Applications → Utilities → Audio MIDI Setup

2. **Create Aggregate Device**:
   - Click the "+" button in the bottom left
   - Select "Create Aggregate Device"

3. **Configure the Aggregate Device**:
   - Name it: "BlackHole + Mic (Aggregate)"
   - Check the boxes for:
     - Your built-in microphone (usually "Built-in Microphone")
     - BlackHole 2ch
   - Set the sample rate to 44100 Hz (recommended)
   - Ensure "Drift Correction" is enabled for both devices

4. **Set as Default**:
   - You can now select this aggregate device in your audio applications
   - This allows you to simultaneously record from your microphone and capture system audio

### Usage Tips:
- Use this aggregate device in audio recording software to capture both your voice and system audio
- The aggregate device combines multiple audio sources into a single virtual device
- Make sure to select the correct input/output devices in your recording application

## 3. Verification Script

A verification script is available at `scripts/check_blackhole.zsh` that:
- Checks if BlackHole is installed and detected by the system
- Uses `system_profiler SPAudioDataType | grep -i blackhole`
- Exits with code 0 if found, code 1 if not found

### Running the Verification Script:
```bash
./scripts/check_blackhole.zsh
```

### Expected Output:
- ✅ Success: Shows BlackHole devices found
- ❌ Failure: Shows installation instructions

## Troubleshooting

### If BlackHole is not detected:
1. Restart your Mac after installation
2. Check Security & Privacy settings (System Preferences → Security & Privacy → Privacy → Microphone)
3. Verify installation with: `system_profiler SPAudioDataType | grep -i blackhole`

### If Aggregate Device is not working:
1. Delete and recreate the aggregate device
2. Ensure both devices have the same sample rate
3. Check that "Drift Correction" is enabled
4. Restart the audio application using the aggregate device
