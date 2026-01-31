import pyaudio
import wave
import webrtcvad
import collections
import subprocess
import uuid
import os
import sys
import time
import numpy as np

# Try to import sounddevice for PipeWire/PulseAudio compatible playback
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Fallback to simpleaudio
try:
    import simpleaudio as sa
    SIMPLEAUDIO_AVAILABLE = True
except ImportError:
    SIMPLEAUDIO_AVAILABLE = False

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from session.websocket import create_ui_logger

# Create UI logger for this module
ui_logger = create_ui_logger("VoiceRecognition")

# === CONFIGURABLE SETTINGS ===
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAME_DURATION = 30  # in ms
CHUNK = int(RATE * FRAME_DURATION / 1000)
MAX_SILENCE_FRAMES = int(1000 / FRAME_DURATION * 1.0)  # 1 sec silence
VAD_AGGRESSIVENESS = 2  # 0-3, 3 is most aggressive

# Paths (based on new structure)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # assistant/
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # elisa-assistant/
AUDIO_TEMP_DIR = os.path.join(PROJECT_ROOT, 'shared', 'audio', 'temporary')
AUDIO_PERM_DIR = os.path.join(PROJECT_ROOT, 'shared', 'audio', 'permanent')
WHISPER_CLI = os.path.join(PROJECT_ROOT, 'stt', 'whisper.cpp', 'build', 'bin', 'whisper-cli')
MODEL_PATH = os.path.join(PROJECT_ROOT, 'stt', 'whisper.cpp', 'models', 'ggml-medium.en.bin')
BEEP_PATH = os.path.join(AUDIO_PERM_DIR, 'beep.wav')

# Ensure TEMP_DIR exists
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)

# === DEBUG PRINT FUNCTION ===
def debug(msg):
    print(f"🔍 DEBUG: {msg}")

# === FIND WORKING INPUT DEVICE ===
def find_working_input_device(p):
    """Find an input device that supports the required sample rate."""
    # First try to find a device that explicitly supports our sample rate
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                # Try to check if format is supported
                if p.is_format_supported(
                    rate=float(RATE),
                    input_device=i,
                    input_channels=CHANNELS,
                    input_format=FORMAT
                ):
                    return i
        except (ValueError, OSError):
            continue
    
    # Fallback: try each input device by actually opening a stream
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                # Try to open a test stream
                test_stream = p.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=i,
                    frames_per_buffer=CHUNK,
                    start=False
                )
                test_stream.close()
                return i
        except (ValueError, OSError):
            continue
    
    return None  # Will use default

# === PLAY WAV FILE (PipeWire/PulseAudio compatible) ===
def play_wav_file(filepath):
    """Play a WAV file using the best available method for the system."""
    
    # Method 1: Try paplay (PulseAudio/PipeWire command line) - MOST RELIABLE on modern Linux
    try:
        result = subprocess.run(['paplay', filepath], capture_output=True, timeout=30)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # Method 2: Try pw-play (PipeWire command line)
    try:
        result = subprocess.run(['pw-play', filepath], capture_output=True, timeout=30)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # Method 3: Try sounddevice (works with PipeWire/PulseAudio)
    if SOUNDDEVICE_AVAILABLE:
        try:
            with wave.open(filepath, 'rb') as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                
                # Convert to numpy array
                dtype = np.int16
                audio_array = np.frombuffer(audio_data, dtype=dtype)
                
                if n_channels > 1:
                    audio_array = audio_array.reshape(-1, n_channels)
                
                sd.play(audio_array, sample_rate)
                sd.wait()
                return True
        except Exception as e:
            pass
    
    # Method 4: Try aplay (ALSA)
    try:
        result = subprocess.run(['aplay', '-q', filepath], capture_output=True, timeout=30)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # Method 5: Try simpleaudio as last resort
    if SIMPLEAUDIO_AVAILABLE:
        try:
            sa.WaveObject.from_wave_file(filepath).play().wait_done()
            return True
        except Exception:
            pass
    
    return False

# === PLAY BEEP SOUND ===
def play_beep(path=BEEP_PATH):
    debug("Playing beep sound")
    if not play_wav_file(path):
        print(f"⚠️ Beep sound failed: No audio playback method available")

# === RECORD AUDIO USING VAD ===
def vad_record(audio_temp_path):
    debug("Setting up VAD and PyAudio")
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    p = pyaudio.PyAudio()

    # Find a working input device
    device_index = find_working_input_device(p)
    
    if device_index is not None:
        device_info = p.get_device_info_by_index(device_index)
        debug(f"Using audio device [{device_index}]: {device_info['name']}")
    else:
        debug("Using default audio device")

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK)

    frames = []
    ring_buffer = collections.deque(maxlen=MAX_SILENCE_FRAMES)
    triggered = False
    debug("Listening started. Waiting for speech...")

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        is_speech = vad.is_speech(data, RATE)

        if not triggered:
            ring_buffer.append((data, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.8 * ring_buffer.maxlen:
                debug("Speech detected! Starting to record...")
                triggered = True
                frames.extend([f for f, s in ring_buffer])
                ring_buffer.clear()
        else:
            frames.append(data)
            ring_buffer.append((data, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                debug("Silence detected. Ending recording...")
                break

    stream.stop_stream()
    stream.close()
    p.terminate()
    debug(f"Saving audio to {audio_temp_path}")

    wf = wave.open(audio_temp_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    debug("Audio saved successfully")

# === RECOGNIZE USING WHISPER.CLI ===
def recognize_with_whisper_cpp(audio_path, model_path=MODEL_PATH):
    debug(f"Running whisper-cli with model {model_path} on file {audio_path}")
    
    output_txt_path = audio_path + ".txt"

    command = [
        WHISPER_CLI,
        "-m", model_path,
        "-f", audio_path,
        "-otxt",   # Output to text file
        "-l", "en", # Language
        "-nt"      # No timestamps
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        debug("Transcription completed by whisper-cli")

        if os.path.exists(output_txt_path):
            with open(output_txt_path, "r") as f:
                transcription = f.read().strip()
            os.remove(output_txt_path)  # Clean up
            debug("Transcription read and cleaned up")
            return transcription
        else:
            debug("❌ Transcription file not found")
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ whisper-cli failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return None

# === MAIN FUNCTION TO RECORD AND RECOGNIZE ===
def recognize_speech():
    audio_temp_filename = f"temp_{uuid.uuid4().hex}.wav"
    audio_temp_path = os.path.join(AUDIO_TEMP_DIR, audio_temp_filename)
    debug("=== Speech recognition started ===")

    try:
        play_beep()
        ui_logger.set_state("listening")
        ui_logger.log_info("Starting voice recording...")
        vad_record(audio_temp_path)
        ui_logger.log_success("Audio recorded successfully.")
        ui_logger.set_state("processing")
        result = recognize_with_whisper_cpp(audio_temp_path)
        if result:
            print(f"✅ Recognized: {result}")
        else:
            print("❌ No recognizable speech.")
        return result
    except Exception as e:
        print(f"⚠️ Error during recognition: {e}")
        return None
    finally:
        if os.path.exists(audio_temp_path):
            os.remove(audio_temp_path)
            debug("Temporary audio file removed")

# # === TEST MAIN FUNCTION ===
# def main():
#     print("🔊 Starting speech recognizer for testing...")
#     result = recognize_speech()
#     if result:
#         print(f"\n🗣️ Final Output: {result}")
#     else:
#         print("\n🚫 No speech detected or recognized.")

# # Run the main function if this script is executed
# if __name__ == "__main__":
#     main()
