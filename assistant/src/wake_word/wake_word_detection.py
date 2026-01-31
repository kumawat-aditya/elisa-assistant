import openwakeword
from openwakeword.model import Model

import pyaudio
import numpy as np
import time
import warnings

# Suppress ALSA warnings
warnings.filterwarnings("ignore")

# === AUDIO SETTINGS (matching voice_recognition.py) ===
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 3200  # frames per buffer for wake word detection

# One-time download of all pre-trained models (or only select models)
openwakeword.utils.download_models()

# Instantiate the model with specific wake word
model = Model(
    wakeword_models=["alexa"],  # Use 'alexa' as the wake word
)


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


def listen_for_wake_word(callback):
    print("Initializing wake word detection with open wake word...")
    last_trigger_time = 0
    cooldown_seconds = 3.0  # Increased cooldown to prevent re-triggering from TTS audio

    while True:
        p = None
        stream = None
        
        try:
            p = pyaudio.PyAudio()

            # Try to find a working device
            device_index = find_working_input_device(p)
            
            if device_index is not None:
                device_info = p.get_device_info_by_index(device_index)
                print(f"Using audio device [{device_index}]: {device_info['name']}")
            else:
                print("Using default audio device")
            
            # Open stream with found device (or default if None)
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            input_device_index=device_index,
                            frames_per_buffer=CHUNK)

            print("Listening for wake word...")
            
            # Wait a bit after restarting to let TTS audio settle
            # This prevents the wake word model from picking up residual TTS audio
            time.sleep(0.5)
            
            # Clear the audio buffer by reading and discarding initial frames
            for _ in range(10):
                try:
                    stream.read(CHUNK, exception_on_overflow=False)
                except:
                    pass

            while True:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                except Exception as e:
                    print(f"Stream read error: {e}")
                    continue

                frame = np.frombuffer(data, dtype=np.int16)
                prediction = model.predict(frame)
                
                score = prediction.get('alexa', 0)
                
                # Debug: Show scores above a minimum threshold
                if score > 0.3:
                    print(f"  [Wake word score: {score:.2f}]", end="\r")

                current_time = time.time()
                # Using higher threshold (0.8) to reduce false positives
                if score > 0.8 and (current_time - last_trigger_time > cooldown_seconds):
                    print(f"\nWake word detected! (score: {score:.2f})")
                    last_trigger_time = current_time

                    # Flush buffer by reading frames before stopping the stream
                    for _ in range(5):
                        try:
                            stream.read(CHUNK, exception_on_overflow=False)
                        except Exception as e:
                            pass  # Ignore flush errors

                    # IMPORTANT: Fully close the stream and PyAudio BEFORE callback
                    # This releases the audio device for voice_recognition to use
                    stream.stop_stream()
                    stream.close()
                    stream = None
                    p.terminate()
                    p = None
                    
                    # Reset the wake word model's internal audio buffer
                    # This prevents the model from triggering on residual TTS audio
                    model.reset()
                    
                    # Small delay to ensure device is released
                    time.sleep(0.3)

                    # Execute callback (voice recognition will use the device)
                    callback()
                    
                    # Break inner loop to reinitialize audio after callback
                    break

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"Error during wake word detection: {e}")
            time.sleep(1)  # Wait before retry
        finally:
            # Ensure cleanup
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            if p is not None:
                try:
                    p.terminate()
                except:
                    pass


# def main():
#     def wake_word_detected():
#         print("Wake word detected!")

#     print("Starting Open Wake Word detection test...")
#     listen_for_wake_word(wake_word_detected)

# if __name__ == "__main__":
#     main()
