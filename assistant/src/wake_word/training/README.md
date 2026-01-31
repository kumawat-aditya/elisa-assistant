# Wake Word Training System

This directory contains the tools and data structure for training custom wake words for ELISA voice assistant using OpenWakeWord.

## Directory Structure

```
training/
├── README.md                  # This file
├── requirements.txt           # Python dependencies for training
├── data/
│   ├── positive/              # Audio clips containing the wake word
│   └── negative/              # Audio clips NOT containing the wake word
├── models/                    # Trained model output directory
└── scripts/
    ├── record_samples.py      # Record wake word samples
    ├── augment_data.py        # Data augmentation utilities
    ├── train_model.py         # Training script
    └── test_model.py          # Test trained model
```

## Prerequisites

1. **Python Environment**: Ensure you're using the `app_env` virtual environment
2. **Dependencies**: Install training requirements:
   ```bash
   source app_env/bin/activate
   pip install -r training/requirements.txt
   ```

## Quick Start Guide

### Step 1: Collect Positive Samples

Record at least **50-100 samples** of your custom wake word:

```bash
python scripts/record_samples.py --type positive --wake-word "elisa"
```

**Guidelines for positive samples:**

- Record in various environments (quiet room, with background noise)
- Use different speakers if possible
- Vary your tone, speed, and distance from microphone
- Each sample should be 1-2 seconds long
- Include natural variations of pronunciation

### Step 2: Collect Negative Samples

Record or collect **200-500 samples** of general speech that does NOT contain the wake word:

```bash
python scripts/record_samples.py --type negative
```

**Guidelines for negative samples:**

- Include common words and phrases
- Add background noise samples
- Include music and TV audio
- Record words that sound similar to your wake word

### Step 3: Augment Data (Optional but Recommended)

Increase dataset size with audio augmentation:

```bash
python scripts/augment_data.py
```

This applies:

- Speed variations (0.9x - 1.1x)
- Pitch shifting
- Background noise mixing
- Volume normalization

### Step 4: Train the Model

Run the training script:

```bash
python scripts/train_model.py \
    --wake-word "elisa" \
    --epochs 100 \
    --output models/elisa_v1.onnx
```

**Training Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--epochs` | 100 | Number of training epochs |
| `--batch-size` | 32 | Training batch size |
| `--learning-rate` | 0.001 | Initial learning rate |
| `--validation-split` | 0.2 | Fraction of data for validation |

### Step 5: Test the Model

Evaluate your trained model:

```bash
python scripts/test_model.py --model models/elisa_v1.onnx
```

## Audio Requirements

| Property    | Value                |
| ----------- | -------------------- |
| Sample Rate | 16000 Hz             |
| Channels    | Mono (1)             |
| Format      | 16-bit PCM WAV       |
| Duration    | 1-2 seconds per clip |

## Using Your Custom Model

After training, update `wake_word_detection.py`:

```python
from openwakeword.model import Model

# Load your custom model
model = Model(
    wakeword_models=["path/to/your/model.onnx"],
    inference_framework="onnx"
)
```

## Tips for Better Accuracy

1. **More Data = Better Model**: Aim for at least 100 positive and 500 negative samples
2. **Diverse Recordings**: Use different microphones, rooms, and speakers
3. **Clean Audio**: Remove silence at start/end of clips
4. **Balanced Dataset**: Maintain a 1:5 ratio of positive to negative samples
5. **Regular Testing**: Test model performance with new unseen samples

## Troubleshooting

### Low Detection Rate

- Increase positive samples
- Ensure consistent pronunciation in samples
- Check audio quality (no clipping, proper levels)

### False Positives

- Add more negative samples
- Include similar-sounding words in negative set
- Increase detection threshold

### Training Crashes

- Reduce batch size if running out of memory
- Check audio file format consistency
- Ensure all samples have same sample rate

## References

- [OpenWakeWord Documentation](https://github.com/dscripka/openWakeWord)
- [Audio Augmentation Best Practices](https://github.com/iver56/audiomentations)
- [Wake Word Training Guide](https://github.com/dscripka/openWakeWord/blob/main/docs/training_models.md)
