# Positive Samples Directory

This folder should contain WAV audio files of the wake word being spoken.

## Requirements

- Format: 16-bit PCM WAV
- Sample Rate: 16000 Hz
- Channels: Mono (1)
- Duration: 1-2 seconds per clip

## Recording Tips

- Record in various environments
- Use different tones and speeds
- Vary distance from microphone
- Include natural pronunciation variations

Use the recording script to collect samples:

```bash
python ../scripts/record_samples.py --type positive --wake-word "elisa"
```
