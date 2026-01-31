# Negative Samples Directory

This folder should contain WAV audio files that do NOT contain the wake word.

## Requirements

- Format: 16-bit PCM WAV
- Sample Rate: 16000 Hz
- Channels: Mono (1)
- Duration: 1-2 seconds per clip

## What to Include

- Common words and phrases
- Background noise samples
- Music and TV audio
- Words that sound similar to the wake word
- Silence and ambient sounds

Use the recording script to collect samples:

```bash
python ../scripts/record_samples.py --type negative
```
