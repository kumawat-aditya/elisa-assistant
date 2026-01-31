#!/usr/bin/env python3
"""
Audio Data Augmentation
=======================
Apply various augmentations to increase training dataset size.

Usage:
    python augment_data.py
    python augment_data.py --factor 5
"""

import os
import sys
import argparse
import numpy as np
import soundfile as sf
from pathlib import Path
from tqdm import tqdm

try:
    from audiomentations import (
        Compose,
        AddGaussianNoise,
        TimeStretch,
        PitchShift,
        Shift,
        Normalize,
        Gain,
        ClippingDistortion,
        AddBackgroundNoise
    )
    AUDIOMENTATIONS_AVAILABLE = True
except ImportError:
    AUDIOMENTATIONS_AVAILABLE = False
    print("⚠️  audiomentations not installed. Using basic augmentation.")

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
POSITIVE_DIR = os.path.join(DATA_DIR, 'positive')
NEGATIVE_DIR = os.path.join(DATA_DIR, 'negative')

# Audio settings
SAMPLE_RATE = 16000


def load_audio(filepath: str) -> tuple:
    """Load audio file and return samples with sample rate."""
    data, sr = sf.read(filepath)
    if sr != SAMPLE_RATE:
        # Simple resampling (for proper resampling, use librosa)
        print(f"⚠️  {filepath} has sample rate {sr}, expected {SAMPLE_RATE}")
    return data.astype(np.float32), sr


def save_audio(filepath: str, data: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """Save audio data to file."""
    sf.write(filepath, data, sample_rate)


def create_augmentation_pipeline():
    """Create audiomentations pipeline."""
    if not AUDIOMENTATIONS_AVAILABLE:
        return None
    
    return Compose([
        # Time stretching (0.85x to 1.15x speed)
        TimeStretch(min_rate=0.85, max_rate=1.15, p=0.5),
        
        # Pitch shifting (-2 to +2 semitones)
        PitchShift(min_semitones=-2, max_semitones=2, p=0.5),
        
        # Add Gaussian noise
        AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.015, p=0.3),
        
        # Random volume change
        Gain(min_gain_in_db=-6, max_gain_in_db=6, p=0.5),
        
        # Time shift
        Shift(min_shift=-0.1, max_shift=0.1, p=0.3),
        
        # Normalize to consistent volume
        Normalize(p=1.0),
    ])


def basic_augmentation(data: np.ndarray, aug_type: str) -> np.ndarray:
    """Apply basic augmentation without audiomentations library."""
    
    if aug_type == 'noise':
        # Add Gaussian noise
        noise = np.random.normal(0, 0.005, data.shape)
        return data + noise.astype(np.float32)
    
    elif aug_type == 'volume_up':
        # Increase volume
        return data * 1.3
    
    elif aug_type == 'volume_down':
        # Decrease volume
        return data * 0.7
    
    elif aug_type == 'shift':
        # Time shift
        shift = int(len(data) * 0.1)
        return np.roll(data, shift)
    
    return data


def augment_directory(input_dir: str, augmentation_factor: int = 3):
    """Augment all audio files in a directory."""
    
    files = list(Path(input_dir).glob("*.wav"))
    original_files = [f for f in files if "_aug" not in f.stem]
    
    if not original_files:
        print(f"No WAV files found in {input_dir}")
        return
    
    print(f"Found {len(original_files)} original files in {input_dir}")
    print(f"Creating {augmentation_factor} augmented versions each...")
    
    if AUDIOMENTATIONS_AVAILABLE:
        augmenter = create_augmentation_pipeline()
    else:
        augmenter = None
        aug_types = ['noise', 'volume_up', 'volume_down', 'shift']
    
    created_count = 0
    
    for filepath in tqdm(original_files, desc="Augmenting"):
        try:
            data, sr = load_audio(str(filepath))
            
            for i in range(augmentation_factor):
                if augmenter:
                    # Use audiomentations
                    augmented = augmenter(samples=data, sample_rate=sr)
                else:
                    # Use basic augmentation
                    aug_type = aug_types[i % len(aug_types)]
                    augmented = basic_augmentation(data, aug_type)
                
                # Generate output filename
                output_name = f"{filepath.stem}_aug{i+1}.wav"
                output_path = filepath.parent / output_name
                
                # Skip if already exists
                if output_path.exists():
                    continue
                
                save_audio(str(output_path), augmented, sr)
                created_count += 1
        
        except Exception as e:
            print(f"\n⚠️  Error processing {filepath.name}: {e}")
    
    print(f"\n✅ Created {created_count} augmented samples")


def main():
    parser = argparse.ArgumentParser(
        description="Augment audio data for wake word training"
    )
    
    parser.add_argument(
        '--factor', '-f',
        type=int,
        default=3,
        help="Number of augmented copies per original (default: 3)"
    )
    
    parser.add_argument(
        '--positive-only',
        action='store_true',
        help="Only augment positive samples"
    )
    
    parser.add_argument(
        '--negative-only',
        action='store_true',
        help="Only augment negative samples"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🔧 AUDIO DATA AUGMENTATION")
    print("=" * 60)
    
    if not args.negative_only:
        print("\n📂 Processing POSITIVE samples...")
        augment_directory(POSITIVE_DIR, args.factor)
    
    if not args.positive_only:
        print("\n📂 Processing NEGATIVE samples...")
        augment_directory(NEGATIVE_DIR, args.factor)
    
    print("\n" + "=" * 60)
    print("✅ Augmentation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
