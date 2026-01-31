#!/usr/bin/env python3
"""
Record Wake Word Samples
========================
Interactive script to record audio samples for wake word training.

Usage:
    python record_samples.py --type positive --wake-word "elisa"
    python record_samples.py --type negative
"""

import os
import sys
import argparse
import uuid
import wave
import time
import pyaudio
import webrtcvad
import collections

# Audio settings (must match wake_word_detection.py)
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAME_DURATION = 30  # ms
CHUNK = int(RATE * FRAME_DURATION / 1000)
MAX_SILENCE_FRAMES = int(1000 / FRAME_DURATION * 1.5)  # 1.5 sec silence
VAD_AGGRESSIVENESS = 2

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
POSITIVE_DIR = os.path.join(DATA_DIR, 'positive')
NEGATIVE_DIR = os.path.join(DATA_DIR, 'negative')


class SampleRecorder:
    """Records audio samples using VAD for automatic endpoint detection."""
    
    def __init__(self, sample_type: str, wake_word: str = None):
        self.sample_type = sample_type
        self.wake_word = wake_word
        self.output_dir = POSITIVE_DIR if sample_type == 'positive' else NEGATIVE_DIR
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize VAD
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
    
    def record_single_sample(self) -> str:
        """Record a single audio sample with VAD-based endpoint detection."""
        
        stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        frames = []
        ring_buffer = collections.deque(maxlen=MAX_SILENCE_FRAMES)
        triggered = False
        
        print("🎤 Listening... (speak now)")
        
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            is_speech = self.vad.is_speech(data, RATE)
            
            if not triggered:
                ring_buffer.append((data, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > 0.8 * ring_buffer.maxlen:
                    triggered = True
                    frames.extend([f for f, s in ring_buffer])
                    ring_buffer.clear()
                    print("🔴 Recording...")
            else:
                frames.append(data)
                ring_buffer.append((data, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    print("✅ Done!")
                    break
        
        stream.stop_stream()
        stream.close()
        
        # Generate unique filename
        prefix = self.wake_word.lower().replace(" ", "_") if self.wake_word else "sample"
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(self.output_dir, filename)
        
        # Save audio
        wf = wave.open(filepath, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return filepath
    
    def run_session(self, num_samples: int = None):
        """Run an interactive recording session."""
        
        print("\n" + "=" * 60)
        print("🎙️  WAKE WORD SAMPLE RECORDER")
        print("=" * 60)
        print(f"Sample Type: {'POSITIVE' if self.sample_type == 'positive' else 'NEGATIVE'}")
        if self.wake_word:
            print(f"Wake Word: \"{self.wake_word}\"")
        print(f"Output Directory: {self.output_dir}")
        print("-" * 60)
        
        if self.sample_type == 'positive':
            print("\n📝 INSTRUCTIONS:")
            print(f"   Say \"{self.wake_word}\" clearly when prompted.")
            print("   Vary your tone, speed, and distance from the mic.")
            print("   Press Ctrl+C to stop recording session.\n")
        else:
            print("\n📝 INSTRUCTIONS:")
            print("   Say random words/phrases that are NOT the wake word.")
            print("   Include background sounds, music, similar words.")
            print("   Press Ctrl+C to stop recording session.\n")
        
        input("Press ENTER to start recording...")
        
        count = 0
        existing = len(os.listdir(self.output_dir))
        
        try:
            while True:
                if num_samples and count >= num_samples:
                    break
                
                count += 1
                print(f"\n--- Sample #{existing + count} ---")
                
                if self.sample_type == 'positive':
                    print(f"🗣️  Say: \"{self.wake_word}\"")
                else:
                    print("🗣️  Say any random phrase (NOT the wake word)")
                
                time.sleep(0.5)
                filepath = self.record_single_sample()
                print(f"💾 Saved: {os.path.basename(filepath)}")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Recording session ended.")
        
        finally:
            self.p.terminate()
        
        total = len(os.listdir(self.output_dir))
        print(f"\n📊 Total samples in {self.sample_type} folder: {total}")
        print("=" * 60)
    
    def cleanup(self):
        """Clean up resources."""
        self.p.terminate()


def main():
    parser = argparse.ArgumentParser(
        description="Record audio samples for wake word training",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--type', '-t',
        choices=['positive', 'negative'],
        required=True,
        help="Type of samples to record"
    )
    
    parser.add_argument(
        '--wake-word', '-w',
        type=str,
        default="elisa",
        help="The wake word to record (for positive samples)"
    )
    
    parser.add_argument(
        '--count', '-c',
        type=int,
        default=None,
        help="Number of samples to record (default: unlimited)"
    )
    
    args = parser.parse_args()
    
    if args.type == 'positive' and not args.wake_word:
        parser.error("--wake-word is required for positive samples")
    
    recorder = SampleRecorder(
        sample_type=args.type,
        wake_word=args.wake_word if args.type == 'positive' else None
    )
    
    try:
        recorder.run_session(num_samples=args.count)
    finally:
        recorder.cleanup()


if __name__ == "__main__":
    main()
