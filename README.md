# ELISA: An Intelligent Voice Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Rasa Version](https://img.shields.io/badge/Rasa-3.x-orange.svg)](https://rasa.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) <!-- Add a LICENSE file (e.g., MIT) -->

ELISA (Electronic Linguistic Intelligent Software Assistant) is a modular, desktop-based voice assistant designed for hands-free operation and task automation. It leverages a suite of open-source technologies to provide a customizable and locally-controllable voice interaction experience.

<!-- Optional: Add a GIF or short video demo here -->
<!-- ![ELISA Demo](./docs/elisa_demo.gif) -->

## ✨ Features

*   **🗣️ Voice Activated:** Uses "Elisa" as the wake word for hands-free activation.
*   **🎤 Speech-to-Text:** Accurate transcription of voice commands using Whisper.cpp.
*   **🧠 Natural Language Understanding:** Powered by Rasa for intent recognition and entity extraction.
*   **💬 Conversational Dialogue:** Manages multi-turn conversations and context using Rasa Core.
*   **🔊 Text-to-Speech:** Natural sounding voice responses using Mozilla TTS.
*   **🖥️ Desktop Control & Information:**
    *   Open desktop applications.
    *   Perform web searches.
    *   Type dictated text into any active window.
    *   Get the current date and time.
    *   Look up word meanings (via Wikipedia).
    *   Fetch current weather updates.
*   **⏰ Reminder System:**
    *   Set reminders for tasks at specific times.
    *   List active reminders.
    *   Update reminder times.
    *   Remove reminders.
    *   (Includes audible and desktop notifications for reminders).
*   **🌐 Web-Based UI:** Provides visual feedback on the assistant's status (idle, listening, processing, speaking) and logs key interactions.
*   **🛠️ Modular & Extensible:** Designed for easier customization and addition of new skills.
*   **🐧 Cross-Platform Considerations:** Core components are Python-based. OS-specific actions (app launching, notifications) include logic for Linux and foundational support for Windows/macOS.

## 🔧 Technologies Used

*   **Core Language:** Python 3.8+
*   **NLU/Dialogue:** Rasa Open Source 3.x
*   **Wake Word Detection:** Picovoice Porcupine
*   **Speech-to-Text (STT):** OpenAI Whisper (via Whisper.cpp - C++ port)
*   **Text-to-Speech (TTS):** Mozilla TTS (Glow-TTS + Multiband-MelGAN)
*   **Audio Handling:** PyAudio/PyAudioWPatch, WebRTCVAD (for VAD), SimpleAudio (for playback)
*   **Scheduling:** APScheduler (for reminders)
*   **Keyboard Automation:** Pynput
*   **Web UI:** HTML, CSS, JavaScript
*   **Backend-UI Communication:** WebSockets (Python `websockets` library)
*   **APIs & Libraries:** `requests` (for weather/IP), `wikipedia`

## ⚙️ System Architecture Overview

ELISA operates through a sequence of interconnected modules:

1.  **Wake Word Detection (Porcupine):** Constantly listens for "Elisa".
2.  **Audio Capture & VAD:** Records user speech after wake word, stopping on silence.
3.  **Speech-to-Text (Whisper.cpp):** Transcribes recorded audio to text.
4.  **Rasa NLU:** Processes text to identify intent and extract entities.
5.  **Rasa Core (Dialogue Management):** Predicts the next action based on NLU output and conversation context.
6.  **Rasa Action Server:** Executes custom Python code for tasks (e.g., opening apps, fetching weather, setting reminders).
7.  **Text-to-Speech (Mozilla TTS):** Converts ELISA's textual responses into audible speech.
8.  **WebSocket Server & UI:** Provides real-time status updates and logs to a web-based interface.

*(Consider adding a link to a more detailed architecture diagram here, e.g., in a `docs/` folder)*

## 🚀 Getting Started

### Prerequisites

*   **Python:** Version 3.8, 3.9, or 3.10.
*   **C++ Compiler:** Required for building Whisper.cpp (e.g., `g++` on Linux, MSVC with CMake tools on Windows).
*   **CMake:** For building Whisper.cpp.
*   **PortAudio:** Required by PyAudio (e.g., `sudo apt-get install portaudio19-dev` on Debian/Ubuntu).
*   **PicoVoice Account & AccessKey:** For Porcupine wake word. Get a free AccessKey from [Picovoice Console](https://console.picovoice.ai/).
*   **(Optional but Recommended) `ffmpeg`:** Whisper.cpp can use ffmpeg for wider audio format support, though ELISA primarily uses WAV.
*   **(Linux Desktop Notifications) `libnotify-bin`:** For `notify-send` (e.g., `sudo apt-get install libnotify-bin`).
*   **(Optional Windows Notifications):** Consider installing a library like `plyer` (`pip install plyer`) or `win10toast-click` if you enhance Windows notifications in `reminder_manager.py`.

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/[YourUsername]/elisa-assistant.git
    cd elisa-assistant
    ```

2.  **Create and Activate a Python Virtual Environment:**
    ```bash
    python -m venv venv
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows (cmd):
    # venv\Scripts\activate.bat
    # On Windows (PowerShell):
    # .\venv\Scripts\Activate.ps1
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure you have a `requirements.txt` file with all necessary Python packages like `rasa`, `TTS`, `pvporcupine`, `pyaudio`, etc.)*

4.  **Compile Whisper.cpp:**
    *   Navigate to the `whisper.cpp` subdirectory (assuming you've included it or have it as a submodule).
        ```bash
        cd whisper.cpp
        make # or follow specific cmake instructions for your OS
        cd ..
        ```
    *   Ensure the compiled `main` (or `whisper-cli`) executable path is correctly set in `core/voice_recognition.py` (`WHISPER_CLI` variable).

5.  **Download Whisper Model:**
    *   Download a Whisper model (e.g., `ggml-medium.bin` or `ggml-base.en.bin` for faster performance). The scripts typically look for models in `whisper.cpp/models/`.
    *   Example script for `base.en` model:
        ```bash
        cd whisper.cpp/models
        bash ./download-ggml-model.sh base.en
        cd ../..
        ```
    *   Ensure the model path is correctly set in `core/voice_recognition.py` (`MODEL_PATH` variable).

6.  **Porcupine Wake Word:**
    *   Place your custom "Elisa" `.ppn` model file (if you created one via Picovoice Console) in a suitable location (e.g., `core/porcupine_models/`).
    *   Update `KEYWORD_PATHS` in `core/wake_word_detection.py` if necessary.
    *   Add your Picovoice `ACCESS_KEY` in `core/wake_word_detection.py`.

7.  **Train Rasa Models:**
    ```bash
    cd rasa
    rasa train
    cd ..
    ```

8.  **(Optional) Weather API Key:**
    If you want weather functionality, get a free API key from [OpenWeatherMap](https://openweathermap.org/appid) and add it to `utils/weather_info.py`.

### Running ELISA

You'll need to run multiple components. It's highly recommended to use the provided startup scripts.

**Using Startup Scripts (Recommended):**

*   **On Linux/macOS:**
    1.  Ensure the script is executable: `chmod +x start_assistant.sh`
    2.  Run: `./start_assistant.sh`
    This script will:
    *   Activate the virtual environment.
    *   Start the Rasa server, Rasa actions server, and UI HTTP server in the background (logging to `logs/` directory).
    *   Run the main `core/main.py` in the foreground.
    *   Attempt to clean up background processes on `Ctrl+C`.

*   **On Windows:**
    1.  Run: `start_assistant.bat` (from Command Prompt)
    This script will:
    *   Activate the virtual environment.
    *   Start the Rasa server, Rasa actions server, and UI HTTP server in new command windows.
    *   Run the main `core/main.py` in the current window.
    *   You will need to manually close the spawned windows/processes when done.

**Manual Startup (if not using scripts - requires 4 terminals):**

1.  **Terminal 1: Activate venv & Start Rasa NLU/Core Server:**
    ```bash
    # source venv/bin/activate (or equivalent for your OS)
    cd rasa
    rasa run --enable-api --cors "*" 
    ```
2.  **Terminal 2: Activate venv & Start Rasa Action Server:**
    ```bash
    # source venv/bin/activate
    cd rasa
    rasa run actions
    ```
3.  **Terminal 3: Activate venv & Start Python HTTP Server for UI:**
    ```bash
    # source venv/bin/activate
    # (Navigate to the project root directory, e.g., elisa-assistant/)
    python -m http.server 35109 --directory ./UI 
    ```
4.  **Terminal 4: Activate venv & Start Main ELISA Application:**
    ```bash
    # source venv/bin/activate
    python core/main.py
    ```

**Accessing the UI:**
Once the UI HTTP server is running, open your browser and navigate to `http://localhost:35109` (or the port you configured). The UI should connect to the WebSocket server started by `core/main.py` (default: `ws://localhost:8765`).

## 🗣️ Usage

1.  Ensure all services are running (see "Running ELISA").
2.  Say the wake word: **"Elisa"**.
3.  You should hear a beep, and the UI should indicate it's listening.
4.  Speak your command, for example:
    *   "What time is it?"
    *   "Open Firefox."
    *   "Search for Python programming."
    *   "Type what I say Hello world this is a test."
    *   "What is the meaning of serendipity?"
    *   "What's the weather like in London?"
    *   "Remind me to call John tomorrow at 10 AM."
    *   "List my reminders."
    *   "Hey Elisa, repeat after me Today is a good day."

## 🛠️ Project Structure
```
elisa-assistant/
├── UI/ # HTML, CSS, JS for the web interface
│ ├── css/
│ ├── js/
│ └── index.html
├── core/ # Core Python backend logic
│ ├── main.py # Main application orchestrator
│ ├── wake_word_detection.py
│ ├── voice_recognition.py
│ ├── text_to_speech.py
│ ├── rasa_integration.py
│ ├── websocket.py
│ └── porcupine_models/ # (Optional) Place for .ppn file
├── rasa/ # Rasa project
│ ├── actions/ # Custom Rasa actions (actions.py)
│ │ └── utils/ # Utility scripts for actions (app_launcher.py, etc.)
│ ├── data/ # NLU training data, stories, rules
│ ├── models/ # Trained Rasa models
│ ├── config.yml
│ ├── domain.yml
│ └── credentials.yml
│ └── endpoints.yml
├── audio/ # Audio files
│ ├── permanent/ # Beep, notification sounds
│ └── temporary/ # For STT recording, TTS output (cleaned up)
├── whisper.cpp/ # Git submodule or clone of whisper.cpp
│ ├── models/ # Whisper.cpp models (e.g., ggml-medium.bin)
│ └── main # Compiled whisper executable
├── logs/ # Log files from startup scripts (created by scripts)
├── venv/ # Python virtual environment (ignored by git)
├── requirements.txt # Python dependencies
├── start_assistant.sh # Startup script for Linux/macOS
├── start_assistant.bat # Startup script for Windows
└── README.md
```


## 📜 Commands ELISA Understands (Examples)

*   **Greetings:** "Hello", "Hi Elisa", "Good morning"
*   **Goodbyes:** "Goodbye", "See you later"
*   **Affirmations/Denials:** "Yes", "No", "Correct", "Wrong"
*   **Wake Up:** "Wake up Elisa" (primarily for initial greeting via Rasa)
*   **Repeat After Me:** "Repeat after me [your phrase]"
*   **Date/Time:** "What time is it?", "What's the date?"
*   **Open Application:** "Open [application name]", "Launch [application name]"
*   **Search Browser:** "Search for [query]", "Look up [query] on the web"
*   **Type What I Say:** "Type what I say [text to type]"
*   **Word Meaning:** "What is the meaning of [word]?", "Define [word]"
    *   Supports follow-up "Yes" to open browser for more details.
*   **Weather:** "What's the weather like?", "Weather in [city]"
*   **Reminders:**
    *   "Remind me to [task] [time]" (e.g., "Remind me to buy milk tomorrow at 5 PM")
    *   "List my reminders"
    *   "Update reminder [task] to [new time]"
    *   "Remove reminder [task]"

*The NLU is trained to understand variations of these commands.*

## 🚧 Known Issues & Limitations

*   **Latency:** Speech-to-Text (Whisper.cpp) and Text-to-Speech (Mozilla TTS) can introduce noticeable delays, especially on less powerful hardware.
*   **STT Accuracy:** Performance depends on microphone quality, accent, and background noise.
*   **CPU/Resource Intensive:** Running multiple AI models locally can be demanding.
*   **Cross-Platform Actions:** Application launching and desktop notifications are more robust on Linux. Windows/macOS support is foundational.
*   **UI Simplicity:** The current web UI is primarily for status and logging.

## 🔮 Future Scope

*   Optimize STT/TTS performance (e.g., smaller models, GPU acceleration).
*   Expand the command set and "skills" (calendar, email, music).
*   Improve NLU model with more data and active learning.
*   Enhance cross-platform compatibility for all actions.
*   Allow user customization (wake word, TTS voice, custom commands).
*   Develop a more polished and interactive UI (perhaps a dedicated desktop app).
*   Investigate multi-lingual support.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to check the [issues page](https://github.com/[YourUsername]/elisa-assistant/issues). (Update link)

## 📝 License

This project is licensed under the [MIT License](LICENSE). <!-- Create a LICENSE file -->
