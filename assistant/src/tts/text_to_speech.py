import sys
import os
import requests
import simpleaudio as sa

# TTS API server URL
TTS_API_URL = "http://localhost:5002/api/tts"

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # assistant/
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # elisa-assistant/

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

        # Play the generated speech
        sa.WaveObject.from_wave_file(output_file).play().wait_done()

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with TTS server: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Example usage
    speak_response("Hello, this is a test using the Coqui TTS API!")
