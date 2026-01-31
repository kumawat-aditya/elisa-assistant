#!/usr/bin/env python3
"""
Test Wake Word Model
====================
Test a trained wake word model with live audio or test files.

Usage:
    python test_model.py --model ../models/elisa_v1.h5
    python test_model.py --model ../models/elisa_v1.onnx --live
"""

import os
import sys
import argparse
import time
from pathlib import Path

import numpy as np
import pyaudio
import wave

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

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

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
CHUNK = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1


def load_model(model_path: str):
    """Load trained model (H5 or ONNX format)."""
    if model_path.endswith('.onnx'):
        if not ONNX_AVAILABLE:
            raise ImportError("onnxruntime required for ONNX models")
        return ort.InferenceSession(model_path), 'onnx'
    else:
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow required for H5 models")
        return tf.keras.models.load_model(model_path), 'keras'


def extract_features(audio: np.ndarray) -> np.ndarray:
    """Extract mel spectrogram features."""
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa required for feature extraction")
    
    # Pad or trim to fixed length
    if len(audio) < NUM_SAMPLES:
        audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    else:
        audio = audio[:NUM_SAMPLES]
    
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


def predict(model, model_type: str, features: np.ndarray) -> float:
    """Get prediction from model."""
    # Add batch dimension
    features = np.expand_dims(features, axis=0)
    
    if model_type == 'onnx':
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name
        result = model.run([output_name], {input_name: features.astype(np.float32)})
        return float(result[0][0])
    else:
        result = model.predict(features, verbose=0)
        return float(result[0][0])


def test_on_files(model, model_type: str, threshold: float = 0.5):
    """Test model on files in data directories."""
    print("\n" + "=" * 60)
    print("📁 TESTING ON FILES")
    print("=" * 60)
    
    results = {'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0}
    
    # Test positive samples
    positive_files = list(Path(POSITIVE_DIR).glob("*.wav"))[:20]  # Limit for speed
    print(f"\n🟢 Testing {len(positive_files)} positive samples...")
    
    for filepath in positive_files:
        try:
            audio, _ = librosa.load(str(filepath), sr=SAMPLE_RATE)
            features = extract_features(audio)
            score = predict(model, model_type, features)
            
            detected = score >= threshold
            if detected:
                results['tp'] += 1
                status = "✅"
            else:
                results['fn'] += 1
                status = "❌"
            
            print(f"  {status} {filepath.name}: {score:.3f}")
        
        except Exception as e:
            print(f"  ⚠️  Error with {filepath.name}: {e}")
    
    # Test negative samples
    negative_files = list(Path(NEGATIVE_DIR).glob("*.wav"))[:20]  # Limit for speed
    print(f"\n🔴 Testing {len(negative_files)} negative samples...")
    
    for filepath in negative_files:
        try:
            audio, _ = librosa.load(str(filepath), sr=SAMPLE_RATE)
            features = extract_features(audio)
            score = predict(model, model_type, features)
            
            detected = score >= threshold
            if not detected:
                results['tn'] += 1
                status = "✅"
            else:
                results['fp'] += 1
                status = "❌"
            
            print(f"  {status} {filepath.name}: {score:.3f}")
        
        except Exception as e:
            print(f"  ⚠️  Error with {filepath.name}: {e}")
    
    # Print summary
    total = sum(results.values())
    accuracy = (results['tp'] + results['tn']) / total if total > 0 else 0
    precision = results['tp'] / (results['tp'] + results['fp']) if (results['tp'] + results['fp']) > 0 else 0
    recall = results['tp'] / (results['tp'] + results['fn']) if (results['tp'] + results['fn']) > 0 else 0
    
    print("\n" + "-" * 60)
    print("📊 RESULTS SUMMARY")
    print("-" * 60)
    print(f"   True Positives:  {results['tp']}")
    print(f"   True Negatives:  {results['tn']}")
    print(f"   False Positives: {results['fp']}")
    print(f"   False Negatives: {results['fn']}")
    print(f"\n   Accuracy:  {accuracy:.2%}")
    print(f"   Precision: {precision:.2%}")
    print(f"   Recall:    {recall:.2%}")
    print("-" * 60)


def test_live(model, model_type: str, threshold: float = 0.5):
    """Test model with live audio input."""
    print("\n" + "=" * 60)
    print("🎤 LIVE TESTING")
    print("=" * 60)
    print("   Speak the wake word to test detection.")
    print("   Press Ctrl+C to stop.")
    print("-" * 60)
    
    p = pyaudio.PyAudio()
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    print("\n🎧 Listening...")
    
    audio_buffer = []
    buffer_size = int(NUM_SAMPLES / CHUNK)
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_buffer.append(audio)
            
            # Keep buffer at fixed size
            if len(audio_buffer) > buffer_size:
                audio_buffer.pop(0)
            
            # Process when buffer is full
            if len(audio_buffer) == buffer_size:
                full_audio = np.concatenate(audio_buffer)
                features = extract_features(full_audio)
                score = predict(model, model_type, features)
                
                # Visual indicator
                bar_len = int(score * 30)
                bar = "█" * bar_len + "░" * (30 - bar_len)
                
                if score >= threshold:
                    print(f"\r🟢 [{bar}] {score:.3f} - DETECTED!", end="")
                    time.sleep(0.5)  # Brief pause after detection
                else:
                    print(f"\r⚪ [{bar}] {score:.3f}", end="")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped.")
    
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def main():
    parser = argparse.ArgumentParser(
        description="Test a trained wake word model"
    )
    
    parser.add_argument(
        '--model', '-m',
        type=str,
        required=True,
        help="Path to trained model (H5 or ONNX)"
    )
    
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.5,
        help="Detection threshold (default: 0.5)"
    )
    
    parser.add_argument(
        '--live', '-l',
        action='store_true',
        help="Test with live audio input"
    )
    
    args = parser.parse_args()
    
    # Check model exists
    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)
    
    # Load model
    print(f"Loading model: {args.model}")
    model, model_type = load_model(args.model)
    print(f"Model type: {model_type}")
    
    if args.live:
        test_live(model, model_type, args.threshold)
    else:
        test_on_files(model, model_type, args.threshold)


if __name__ == "__main__":
    main()
