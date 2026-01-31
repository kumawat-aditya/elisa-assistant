#!/usr/bin/env python3
"""
Wake Word Model Training
========================
Train a custom wake word model using OpenWakeWord.

Usage:
    python train_model.py --wake-word "elisa"
    python train_model.py --wake-word "elisa" --epochs 100 --output ../models/elisa_v1.onnx

Note: This script provides the training pipeline structure.
For actual training, OpenWakeWord uses specific training procedures.
See: https://github.com/dscripka/openWakeWord/blob/main/docs/training_models.md
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
MODELS_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
POSITIVE_DIR = os.path.join(DATA_DIR, 'positive')
NEGATIVE_DIR = os.path.join(DATA_DIR, 'negative')

# Audio settings
SAMPLE_RATE = 16000
AUDIO_LENGTH = 1.5  # seconds
NUM_SAMPLES = int(SAMPLE_RATE * AUDIO_LENGTH)

# Model settings
EMBEDDING_DIM = 96
NUM_CLASSES = 2


def check_prerequisites():
    """Check if all required packages are available."""
    issues = []
    
    if not TF_AVAILABLE:
        issues.append("TensorFlow not installed: pip install tensorflow")
    
    if not LIBROSA_AVAILABLE:
        issues.append("Librosa not installed: pip install librosa")
    
    return issues


def count_samples():
    """Count available samples in data directories."""
    positive = len(list(Path(POSITIVE_DIR).glob("*.wav")))
    negative = len(list(Path(NEGATIVE_DIR).glob("*.wav")))
    return positive, negative


def load_audio_file(filepath: str) -> np.ndarray:
    """Load and preprocess audio file."""
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa is required for audio loading")
    
    # Load audio
    audio, sr = librosa.load(filepath, sr=SAMPLE_RATE)
    
    # Pad or trim to fixed length
    if len(audio) < NUM_SAMPLES:
        audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    else:
        audio = audio[:NUM_SAMPLES]
    
    return audio


def extract_features(audio: np.ndarray) -> np.ndarray:
    """Extract mel spectrogram features."""
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa is required for feature extraction")
    
    # Compute mel spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=SAMPLE_RATE,
        n_mels=80,
        n_fft=512,
        hop_length=160,
        win_length=400
    )
    
    # Convert to log scale
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)
    
    return log_mel


def load_dataset():
    """Load and prepare training dataset."""
    print("Loading dataset...")
    
    X = []
    y = []
    
    # Load positive samples
    positive_files = list(Path(POSITIVE_DIR).glob("*.wav"))
    print(f"  Loading {len(positive_files)} positive samples...")
    
    for filepath in positive_files:
        try:
            audio = load_audio_file(str(filepath))
            features = extract_features(audio)
            X.append(features)
            y.append(1)  # Positive class
        except Exception as e:
            print(f"  ⚠️  Error loading {filepath.name}: {e}")
    
    # Load negative samples
    negative_files = list(Path(NEGATIVE_DIR).glob("*.wav"))
    print(f"  Loading {len(negative_files)} negative samples...")
    
    for filepath in negative_files:
        try:
            audio = load_audio_file(str(filepath))
            features = extract_features(audio)
            X.append(features)
            y.append(0)  # Negative class
        except Exception as e:
            print(f"  ⚠️  Error loading {filepath.name}: {e}")
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"  Dataset shape: {X.shape}")
    print(f"  Positive: {np.sum(y == 1)}, Negative: {np.sum(y == 0)}")
    
    return X, y


def create_model(input_shape: tuple) -> "tf.keras.Model":
    """Create wake word detection model."""
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required for model creation")
    
    model = tf.keras.Sequential([
        # Input layer
        tf.keras.layers.Input(shape=input_shape),
        
        # Add channel dimension
        tf.keras.layers.Reshape((*input_shape, 1)),
        
        # Convolutional layers
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),
        
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),
        
        tf.keras.layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),
        
        # Dense layers
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        
        # Output layer
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    return model


def train_model(
    wake_word: str,
    epochs: int = 100,
    batch_size: int = 32,
    validation_split: float = 0.2,
    output_path: str = None
):
    """Train the wake word model."""
    
    # Check prerequisites
    issues = check_prerequisites()
    if issues:
        print("❌ Missing prerequisites:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    # Count samples
    pos_count, neg_count = count_samples()
    print(f"\n📊 Dataset Statistics:")
    print(f"   Positive samples: {pos_count}")
    print(f"   Negative samples: {neg_count}")
    
    if pos_count < 10:
        print("\n⚠️  Warning: Very few positive samples. Recommend at least 50+")
    if neg_count < 50:
        print("⚠️  Warning: Very few negative samples. Recommend at least 200+")
    
    if pos_count == 0 or neg_count == 0:
        print("\n❌ Cannot train without both positive and negative samples!")
        return False
    
    # Load data
    X, y = load_dataset()
    
    # Shuffle data
    indices = np.random.permutation(len(X))
    X = X[indices]
    y = y[indices]
    
    # Create model
    print("\n🏗️  Creating model...")
    input_shape = X.shape[1:]  # (n_mels, time_steps)
    model = create_model(input_shape)
    model.summary()
    
    # Callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5
        )
    ]
    
    # Train
    print(f"\n🚀 Training for {epochs} epochs...")
    history = model.fit(
        X, y,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save model
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(MODELS_DIR, f"{wake_word}_{timestamp}.h5")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.save(output_path)
    print(f"\n💾 Model saved to: {output_path}")
    
    # Save training info
    info_path = output_path.replace('.h5', '_info.json').replace('.onnx', '_info.json')
    training_info = {
        'wake_word': wake_word,
        'epochs': epochs,
        'batch_size': batch_size,
        'positive_samples': int(np.sum(y == 1)),
        'negative_samples': int(np.sum(y == 0)),
        'final_accuracy': float(history.history['accuracy'][-1]),
        'final_val_accuracy': float(history.history['val_accuracy'][-1]),
        'trained_at': datetime.now().isoformat()
    }
    
    with open(info_path, 'w') as f:
        json.dump(training_info, f, indent=2)
    
    print(f"📋 Training info saved to: {info_path}")
    
    # Print results
    print("\n" + "=" * 60)
    print("📈 TRAINING RESULTS")
    print("=" * 60)
    print(f"   Final Accuracy:     {history.history['accuracy'][-1]:.4f}")
    print(f"   Final Val Accuracy: {history.history['val_accuracy'][-1]:.4f}")
    print("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Train a custom wake word model"
    )
    
    parser.add_argument(
        '--wake-word', '-w',
        type=str,
        required=True,
        help="The wake word to train for"
    )
    
    parser.add_argument(
        '--epochs', '-e',
        type=int,
        default=100,
        help="Number of training epochs (default: 100)"
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=32,
        help="Training batch size (default: 32)"
    )
    
    parser.add_argument(
        '--validation-split', '-v',
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2)"
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help="Output model path"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🎯 WAKE WORD MODEL TRAINING")
    print("=" * 60)
    print(f"   Wake Word: {args.wake_word}")
    print(f"   Epochs: {args.epochs}")
    print(f"   Batch Size: {args.batch_size}")
    print("=" * 60)
    
    success = train_model(
        wake_word=args.wake_word.lower().replace(" ", "_"),
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=args.validation_split,
        output_path=args.output
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
