# Trained Models Directory

This folder contains trained wake word models.

## Supported Formats

- `.h5` - TensorFlow/Keras format
- `.onnx` - ONNX format (recommended for production)

## Using Custom Models

Update `wake_word_detection.py` to use your model:

```python
from openwakeword.model import Model

model = Model(
    wakeword_models=["path/to/your/model.onnx"],
    inference_framework="onnx"
)
```

## Model Files

Models will be saved here after training with naming format:

- `<wake_word>_<timestamp>.h5`
- `<wake_word>_<timestamp>_info.json`
