import sys
import os
import requests
import subprocess
import wave
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

# TTS API server URL
TTS_API_URL = "http://localhost:5002/api/tts"

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # assistant/
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # elisa-assistant/


def play_wav_file(filepath):
    """Play a WAV file using the best available method for the system."""
    
    # Method 1: Try paplay (PulseAudio/PipeWire command line) - MOST RELIABLE on modern Linux
    try:
        result = subprocess.run(['paplay', filepath], capture_output=True, timeout=60)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        pass
    
    # Method 2: Try pw-play (PipeWire command line)
    try:
        result = subprocess.run(['pw-play', filepath], capture_output=True, timeout=60)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
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
            print(f"sounddevice playback failed: {e}")
    
    # Method 4: Try aplay (ALSA)
    try:
        result = subprocess.run(['aplay', '-q', filepath], capture_output=True, timeout=60)
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        pass
    
    # Method 5: Try simpleaudio as last resort
    if SIMPLEAUDIO_AVAILABLE:
        try:
            sa.WaveObject.from_wave_file(filepath).play().wait_done()
            return True
        except Exception as e:
            print(f"simpleaudio playback failed: {e}")
    
    print(f"⚠️ No audio playback method available for {filepath}")
    return False


def speak_response(response):
    # Create the directory if it doesn't exist
    output_dir = os.path.join(PROJECT_ROOT, 'shared', 'audio', 'temporary')
    os.makedirs(output_dir, exist_ok=True)

    # Set the full path to the output file
    output_file = os.path.join(output_dir, "response.wav")

    # Prepare the request payload
    data = {
        "text": response
    }

    try:
        # Send POST request to the TTS server
        res = requests.post(TTS_API_URL, data=data)
        res.raise_for_status()

        # Save the audio content to file
        with open(output_file, 'wb') as f:
            f.write(res.content)

        # Play the generated speech using best available method
        play_wav_file(output_file)

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with TTS server: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Example usage
    speak_response("Hello, this is a test using the Coqui TTS API!")
