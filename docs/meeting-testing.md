# FluentAI Production Testing Guide

## 🎯 Testing Real-time Translation in Meetings

This guide will help you test that FluentAI is properly sharing translated audio in video meetings.

## 📋 Prerequisites

1. **BlackHole 2ch** installed and configured
2. **FluentAI** running with live monitor
3. **Meeting software** (Zoom, Teams, Meet, etc.)
4. **Audio monitoring tools** (optional but recommended)

## 🔧 Step 1: Verify BlackHole Configuration

### Check Audio Devices
```bash
# Run this to see all audio devices
uv run -c "
import sounddevice as sd
devices = sd.query_devices()
print('Available Audio Devices:')
for i, device in enumerate(devices):
    print(f'  {i}: {device[\"name\"]} - {device[\"max_input_channels\"]} in, {device[\"max_output_channels\"]} out')
"
```

### Expected Output:
```
Available Audio Devices:
  0: MacBook Pro Microphone - 1 in, 0 out
  1: BlackHole 2ch - 2 in, 2 out  ← This is what we need
  2: MacBook Pro Speakers - 0 in, 2 out
```

## 🔧 Step 2: Configure Meeting Software

### For Zoom:
1. **Settings** → **Audio**
2. **Microphone**: Select "BlackHole 2ch"
3. **Test Microphone**: Should show audio levels when FluentAI is running

### For Microsoft Teams:
1. **Settings** → **Devices**
2. **Microphone**: Select "BlackHole 2ch"
3. **Test call**: Use Teams test call feature

### For Google Meet:
1. **Settings** (gear icon) → **Audio**
2. **Microphone**: Select "BlackHole 2ch"
3. **Test**: Click microphone test

### For Discord:
1. **Settings** → **Voice & Video**
2. **Input Device**: Select "BlackHole 2ch"
3. **Input Sensitivity**: May need to adjust

## 🔧 Step 3: Run FluentAI with Production Settings

### Start FluentAI with optimal settings:
```bash
# For Spanish to English translation
uv run live_monitor.py

# Or use the CLI directly
uv run -m fluentai.cli.translate_rt --src es --dst en --verbose
```

### Monitor for issues:
- Watch queue activity in live monitor
- Check for audio processing in logs
- Verify BlackHole device is receiving audio

## 🧪 Step 4: Test in Meeting

### Test Sequence:
1. **Join a test meeting** (or create one with a friend)
2. **Verify microphone selection** (BlackHole 2ch should be selected)
3. **Start FluentAI** with live monitor
4. **Speak in Spanish** into your microphone
5. **Confirm participants hear English** translation

### What Other Participants Should Hear:
- **Your Spanish speech** → **English translation via TTS**
- **Clear audio quality** (not your original voice)
- **Minimal delay** (2-3 seconds is normal)

## 🔧 Step 5: Advanced Testing Tools

### Audio Loopback Test (Without Meeting)
```bash
# Test BlackHole loopback
uv run test_blackhole_audio.py
```

### Real-time Audio Monitoring
```bash
# Monitor what's going through BlackHole
uv run -c "
import sounddevice as sd
import numpy as np

def audio_callback(indata, frames, time, status):
    volume = np.sqrt(np.mean(indata**2))
    print(f'BlackHole Input Level: {\"█\" * int(volume * 50)}')

# Monitor BlackHole input (what meeting software receives)
with sd.InputStream(device=1, callback=audio_callback, channels=2):
    print('Monitoring BlackHole input (what meeting software receives)...')
    input('Press Enter to stop...')
"
```

## 🛠️ Troubleshooting Common Issues

### Issue 1: Meeting Software Can't See BlackHole
**Solution:**
```bash
# Restart Core Audio
sudo killall coreaudiod
```

### Issue 2: No Audio in Meeting
**Checklist:**
- [ ] BlackHole selected in meeting software
- [ ] FluentAI running and processing audio
- [ ] Live monitor showing audio segments played
- [ ] Microphone permissions granted

### Issue 3: Poor Audio Quality
**Solutions:**
- Adjust VAD sensitivity in FluentAI
- Check background noise levels
- Verify microphone positioning

### Issue 4: High Latency
**Optimizations:**
- Use faster Whisper model (tiny/base)
- Reduce audio buffer sizes
- Check CPU usage

## 📊 Production Monitoring

### Key Metrics to Watch:
- **Audio Segments Captured**: Should increase when speaking
- **Audio Segments Processed**: Should match captured (no backlog)
- **Audio Segments Played**: Should match processed
- **Queue Sizes**: Should stay low (< 3 items)

### Performance Indicators:
- **Good**: Queue sizes 0-1, fast processing
- **Warning**: Queue sizes 2-3, slight delay
- **Critical**: Queue sizes > 5, significant backlog

## 🔐 Security Considerations

### Privacy:
- Audio is processed locally (Whisper)
- Translation via Hugging Face models
- TTS via Google TTS (requires internet)

### Network:
- Minimal bandwidth usage
- No audio data transmitted except TTS

## 🚀 Production Deployment

### Recommended Setup:
1. **Dedicated machine** for FluentAI
2. **High-quality microphone** for better recognition
3. **Stable internet** for TTS service
4. **Backup audio setup** in case of issues

### Monitoring Script:
```bash
#!/bin/bash
# production_monitor.sh
while true; do
    echo "Starting FluentAI..."
    uv run live_monitor.py
    echo "FluentAI stopped. Restarting in 5 seconds..."
    sleep 5
done
```

## 📞 Meeting Integration Examples

### Zoom Integration:
1. Set BlackHole as microphone
2. Start FluentAI before joining meeting
3. Mute/unmute controls FluentAI indirectly

### Teams Integration:
1. Configure BlackHole in Teams settings
2. Use Teams noise cancellation alongside FluentAI
3. Test with Teams test call feature

### Meet Integration:
1. Select BlackHole in Meet audio settings
2. Monitor with Meet's built-in audio indicators
3. Use Meet's recording for testing

## ✅ Final Verification Checklist

- [ ] BlackHole device visible in meeting software
- [ ] FluentAI processing audio (live monitor shows activity)
- [ ] Test participant can hear English translation
- [ ] Audio quality is acceptable
- [ ] Latency is reasonable (< 5 seconds)
- [ ] No audio dropouts or glitches
- [ ] System stable for extended use

## 📝 Testing Log Template

```
Date: ___________
Meeting Software: ___________
FluentAI Version: ___________

✅ BlackHole configured in meeting software
✅ FluentAI running with live monitor
✅ Audio segments being captured: ___/min
✅ Audio segments being processed: ___/min
✅ Audio segments being played: ___/min
✅ Test participant confirms hearing translation
✅ Audio quality acceptable (1-10): ___
✅ Latency acceptable (seconds): ___

Issues encountered:
- ___________
- ___________

Notes:
- ___________
- ___________
```

---

**Remember**: Always test with a friendly participant first before using in important meetings!
