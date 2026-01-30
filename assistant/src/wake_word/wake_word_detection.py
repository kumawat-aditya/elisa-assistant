import openwakeword
from openwakeword.model import Model

import pyaudio
import struct
import numpy as np
import time

# One-time download of all pre-trained models (or only select models)
openwakeword.utils.download_models()

# Instantiate the model(s)
model = Model(
    wakeword_models=[],  # Leave empty to load all pre-trained models
)
# last_trigger_time = 0
# cooldown_seconds = 2  # ignore further detections for 3 seconds

def list_devices(p):
    print("Available audio devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"  [{i}] {info['name']!r} - in:{info['maxInputChannels']} out:{info['maxOutputChannels']} defaultRate:{int(info['defaultSampleRate'])}")

def find_compatible_input_device(p, required_rate):
    fallback = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) <= 0:
            continue
        try:
            if p.is_format_supported(rate=required_rate,
                                      input_device=i,
                                      input_channels=1,
                                      input_format=pyaudio.paInt16):
                return i, info
        except ValueError:
            pass
        if fallback is None:
            fallback = (i, info)
    return fallback


def listen_for_wake_word(callback):
    print("Initializing wake word detection with open wake word...")
    last_trigger_time = 0
    cooldown_seconds = 1.0
    is_listening = True  # flag to prevent re-entry during callback

    try:
        p = pyaudio.PyAudio()
        list_devices(p)

        found = find_compatible_input_device(p, required_rate=16000)
        if found is None:
            print("Warning: No input-capable audio device found. Using default.")
            device_index = None
        else:
            device_index, device_info = found
            print(f"Selected device [{device_index}]: {device_info['name']}")

        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=3200,
                        input_device_index=device_index)

        print("Listening for wake word...")

        while True:
            if not is_listening:
                time.sleep(0.1)
                continue

            try:
                data = stream.read(3200, exception_on_overflow=False)
            except Exception as e:
                print(f"Stream read error: {e}")
                continue

            frame = np.frombuffer(data, dtype=np.int16)
            prediction = model.predict(frame)
            
            score = prediction.get('alexa', 0)

            current_time = time.time()
            if score > 0.5 and (current_time - last_trigger_time > cooldown_seconds):
                print("Wake word detected!")
                last_trigger_time = current_time
                is_listening = False  # prevent further detection

                # Flush buffer by reading frames before stopping the stream
                for _ in range(5):
                    try:
                        stream.read(3200, exception_on_overflow=False)
                    except Exception as e:
                        print(f"Flush read error: {e}")

                # Now stop the stream
                stream.stop_stream()

                # Execute callback
                callback()

                # Restart the stream
                stream.start_stream()
                is_listening = True

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"Error during wake word detection: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
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
