import sys
import os
from TTS.api import TTS
import simpleaudio as sa

def speak_response(response):

    tts = TTS(model_name="tts_models/en/ljspeech/glow-tts", progress_bar=False)

    # Create the directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'audio', 'temporary')
    os.makedirs(output_dir, exist_ok=True)

    # Set the full path to the output file
    output_file = os.path.join(output_dir, "response.wav")

    # Redirect stdout and stderr to suppress logs
    with open(os.devnull, 'w') as f:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = f, f
        try:
            tts.tts_to_file(text=response, file_path=output_file)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr  # Restore stdout and stderr

    # Play the generated speech
    sa.WaveObject.from_wave_file(output_file).play().wait_done()
