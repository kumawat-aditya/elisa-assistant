# ELISA - Electronic Linguistic Intelligent Software Assistant

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Rasa](https://img.shields.io/badge/Rasa-3.x-5A17EE?style=for-the-badge&logo=rasa&logoColor=white)](https://rasa.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE.txt)

**A modular, privacy-focused voice assistant with microservices architecture**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## ✨ Features

| Category               | Capabilities                                                       |
| ---------------------- | ------------------------------------------------------------------ |
| **🗣️ Voice Interface** | Wake word detection, VAD-based recording, natural speech synthesis |
| **🧠 NLU**             | Intent recognition, entity extraction, multi-turn dialogue         |
| **🖥️ Desktop Control** | Open apps, web search, dictation, date/time queries                |
| **⏰ Reminders**       | Set, list, update, remove with notifications                       |
| **🌤️ Information**     | Weather updates, word definitions (Wikipedia)                      |
| **🌐 Web UI**          | Real-time status, WebSocket communication                          |

---

## 🏗️ Architecture

ELISA uses a **microservices architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ELISA ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  TTS Docker  │  │   Duckling   │  │   Web UI     │  │   Whisper    │   │
│  │  Port 5002   │  │  Port 8000   │  │  Port 35109  │  │   (local)    │   │
│  └──────▲───────┘  └──────▲───────┘  └──────▲───────┘  └──────▲───────┘   │
│         │                 │                 │                 │            │
│  ───────┴─────────────────┴─────────────────┴─────────────────┴─────────   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        ASSISTANT LAYER                              │   │
│  │  assistant/src/                                                     │   │
│  │      ├── main.py          ← Entry point & orchestrator              │   │
│  │      ├── wake_word/       ← OpenWakeWord detection                  │   │
│  │      ├── stt/             ← Whisper.cpp integration                 │   │
│  │      ├── tts/             ← TTS Docker client                       │   │
│  │      ├── nlu_client/      ← Rasa HTTP client                        │   │
│  │      └── session/         ← WebSocket for UI                        │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│  ────────────────────────────────────┼──────────────────────────────────   │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          NLU LAYER (Port 5005)                      │   │
│  │  nlu/                                                                │   │
│  │      ├── Rasa Server      ← Intent & entity recognition             │   │
│  │      ├── actions/         ← Custom actions → Logic Layer            │   │
│  │      ├── data/            ← Training data (nlu.yml, stories.yml)    │   │
│  │      └── models/          ← Trained NLU models                      │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│  ────────────────────────────────────┼──────────────────────────────────   │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        LOGIC LAYER (Port 8021)                      │   │
│  │  logic/src/                                                          │   │
│  │      ├── main.py          ← FastAPI entry point                     │   │
│  │      ├── routes/          ← Action routing (logic.py)               │   │
│  │      ├── services/        ← Business logic modules                  │   │
│  │      ├── scheduler/       ← APScheduler for reminders               │   │
│  │      └── data/            ← Responses, reminder storage             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Voice → Wake Word → STT (Whisper) → NLU (Rasa) → Logic (FastAPI) → Response → TTS → Audio Output
```

---

## 📁 Project Structure

```
elisa-assistant/
│
├── assistant/                 # Main runtime (voice interface)
│   ├── src/
│   │   ├── main.py           # Entry point & orchestrator
│   │   ├── wake_word/        # Wake word detection
│   │   ├── stt/              # Speech-to-text (Whisper)
│   │   ├── tts/              # Text-to-speech client
│   │   ├── nlu_client/       # Rasa integration
│   │   └── session/          # WebSocket for UI
│   ├── tests/
│   └── requirements.txt
│
├── logic/                     # Business logic (FastAPI)
│   ├── src/
│   │   ├── main.py           # FastAPI server
│   │   ├── routes/           # Action routing
│   │   ├── services/         # App launcher, weather, reminders
│   │   ├── scheduler/        # APScheduler
│   │   └── data/             # Responses, reminder storage
│   ├── tests/
│   └── requirements.txt
│
├── nlu/                       # NLU layer (Rasa)
│   ├── actions/              # Custom Rasa actions
│   ├── data/                 # Training data
│   ├── models/               # Trained models
│   ├── config.yml
│   ├── domain.yml
│   └── requirements.txt
│
├── stt/                       # Speech-to-text (Whisper.cpp)
│   ├── whisper.cpp/          # Whisper source/binary
│   └── models/               # Whisper models
│
├── ui/                        # Web interface
│   ├── public/               # HTML, images
│   └── src/                  # CSS, JavaScript
│
├── shared/                    # Shared resources
│   └── audio/
│       ├── permanent/        # Boot, beep, notification sounds
│       └── temporary/        # Runtime recordings
│
├── config/
│   └── .env.example
│
├── infra/
│   └── docker-compose.yml    # TTS & Duckling services
│
├── scripts/
│   └── start.sh              # Startup script
│
├── docs/                      # Documentation
├── logs/                      # Runtime logs (gitignored)
│
├── README.md
└── LICENSE.txt
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (pyenv recommended)
- **Docker & Docker Compose**
- **CMake & C++ compiler** (for Whisper.cpp)
- **PortAudio** (`sudo pacman -S portaudio` / `sudo apt install portaudio19-dev`)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Adikumaw/elisa-assistant.git
cd elisa-assistant

# 2. Start Docker services (TTS & Duckling)
cd infra && docker-compose up -d && cd ..

# 3. Setup NLU (Rasa)
python3.9 -m venv nlu_env
source nlu_env/bin/activate
pip install -r nlu/requirements.txt
python -m spacy download en_core_web_md
cd nlu && rasa train && cd ..
deactivate

# 4. Setup Logic Layer
pyenv virtualenv 3.10.12 logic-env
pyenv activate logic-env
pip install -r logic/requirements.txt
pyenv deactivate

# 5. Setup Assistant
pyenv virtualenv 3.10.12 app-env
pyenv activate app-env
pip install -r assistant/requirements.txt
pyenv deactivate

# 6. Build Whisper.cpp
cd stt/whisper.cpp
sh ./models/download-ggml-model.sh medium.en
cmake -B build && cmake --build build -j$(nproc)
cd ../..

# 7. Run ELISA
./scripts/start.sh
```

### Quick Run (After Setup)

```bash
./scripts/start.sh
```

Access the Web UI at: **http://localhost:35109**

---

## 🐳 Docker Services

| Service  | Image                              | Port | Purpose                     |
| -------- | ---------------------------------- | ---- | --------------------------- |
| TTS      | `ghcr.io/coqui-ai/tts-cpu:v0.22.0` | 5002 | Text-to-Speech              |
| Duckling | `rasa/duckling:0.2.0.2-r3`         | 8000 | Date/Time entity extraction |

```bash
# Start services
cd infra && docker-compose up -d

# Stop services
cd infra && docker-compose down

# View logs
docker-compose logs -f
```

---

## 📜 Supported Commands

| Category        | Examples                                              |
| --------------- | ----------------------------------------------------- |
| **Greetings**   | "Hello", "Hi Elisa", "Good morning"                   |
| **Time/Date**   | "What time is it?", "What's the date?"                |
| **Apps**        | "Open Firefox", "Launch VS Code"                      |
| **Search**      | "Search for Python tutorials"                         |
| **Dictation**   | "Type what I say Hello world"                         |
| **Definitions** | "What is the meaning of serendipity?"                 |
| **Weather**     | "What's the weather like?", "Weather in London"       |
| **Reminders**   | "Remind me to call John at 5 PM", "List my reminders" |

---

## 🛠️ Development

### Running Individual Services

```bash
# Logic Layer
cd logic/src && uvicorn main:app --host 0.0.0.0 --port 8021 --reload

# NLU Server
cd nlu && rasa run --enable-api --cors "*"

# NLU Actions
cd nlu && rasa run actions

# Web UI
python -m http.server 35109 --directory ui/public

# Assistant
cd assistant/src && python main.py
```

### Training NLU

```bash
cd nlu
rasa train
rasa shell  # Interactive testing
```

---

## 📚 Documentation

- [Setup Guide](docs/setup.txt) - Detailed installation instructions
- [Docker Reference](docs/docker_how_to.txt) - Docker commands
- [Virtual Environment](docs/venv_how_to.txt) - pyenv/venv setup

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📝 License

This project is licensed under the [MIT License](LICENSE.txt).

---

<div align="center">

**Built with ❤️ by [Adikumaw](https://github.com/Adikumaw)**

</div>
