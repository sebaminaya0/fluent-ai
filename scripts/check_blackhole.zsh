#!/bin/zsh

# Script to check if BlackHole audio driver is installed
# This script checks the system audio profile for BlackHole devices

echo "Checking for BlackHole audio driver installation..."

# Check if BlackHole is installed by searching system audio profile
if system_profiler SPAudioDataType | grep -i blackhole > /dev/null 2>&1; then
    echo "✅ BlackHole audio driver is installed and detected"
    echo "BlackHole devices found:"
    system_profiler SPAudioDataType | grep -i blackhole
    exit 0
else
    echo "❌ BlackHole audio driver not found"
    echo "Please install BlackHole using: brew install blackhole-2ch"
    exit 1
fi
