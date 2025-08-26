import pvporcupine
import pyaudio
import struct
import time
import os

ACCESS_KEY = "CiQyXwvgpRzR1cQAtp2Uw6MZ1UcAricT5dOBgiWqSimZv/GE1z2khQ=="

def listen_for_wake_word(callback):
    porcupine = None
    p = None
    stream = None

    try:
        # Construct relative path to the .ppn file inside core/
        keyword_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "elisa_en_linux_v3_0_0.ppn"))

        # Initialize Porcupine
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keyword_paths=[keyword_path]
        )

        # Initialize PyAudio
        p = pyaudio.PyAudio()
        stream = p.open(rate=porcupine.sample_rate,
                        channels=1,
                        format=pyaudio.paInt16,
                        input=True,
                        frames_per_buffer=porcupine.frame_length)

        print("Listening for wake word...")

        while True:
            try:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)  # Convert byte data to int16
                
                if porcupine.process(pcm) >= 0:  # Wake word detected
                    print("Wake word detected!")
                    stream.stop_stream()  # Pause the stream instead of closing
                    callback()
                    stream.start_stream()  # Resume listening for wake word
                    
                    time.sleep(1)  # Avoid multiple triggers
            except IOError as e:
                print(f"IOError during wake word detection: {e}")
                break
            except Exception as e:
                print(f"Error during wake word detection: {e}")
                break

    except Exception as e:
        print(f"Error initializing the stream: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if p:
            p.terminate()
        if porcupine:
            porcupine.delete()
        print("Stopped listening for wake word.")
