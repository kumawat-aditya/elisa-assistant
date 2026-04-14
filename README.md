# ELISA

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Rasa](https://img.shields.io/badge/Rasa-3.x-5A17EE?logo=rasa&logoColor=white)](https://rasa.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.txt)

**A self-hosted, modular voice assistant engineered for privacy, separation of concerns, and local-first intelligence.**

[Why ELISA?](#-why-elisa) · [Architecture](#-architecture-at-a-glance) · [Tech Stack](#-tech-stack-matrix) · [Quick Start](#-quick-start) · [Project Structure](#-repository-navigation) · [Development](#-development) · [Docs](#-documentation)

</div>

---

## 🧠 Why ELISA?

Most voice assistants send every word you say to a remote server. ELISA takes the opposite approach.

ELISA is a self-hosted voice assistant where **every stage of the pipeline — wake word detection, speech-to-text, intent classification, business logic execution, and speech synthesis — runs on your own hardware**. No cloud APIs sit in the critical path. No audio leaves your network.

The system is built on three engineering principles:

1. **Local-First Processing** — Wake word detection (OpenWakeWord), STT (Whisper.cpp), NLU (Rasa + spaCy), entity parsing (Duckling), and TTS (Coqui) all execute locally. Network calls exist only for optional services like weather APIs.
2. **Strict Separation of Concerns** — Runtime orchestration, language understanding, and business logic are isolated into independent services with well-defined HTTP boundaries. Each can be developed, tested, deployed, and scaled independently.
3. **Deterministic Entity Extraction** — Time expressions like "in 30 minutes" or "tomorrow at 5pm" pass through Facebook's Duckling engine, ensuring rule-based precision rather than probabilistic entity extraction for structured data types.

---

## 🏗️ Architecture at a Glance

ELISA is structured as a **multi-service layered system** where each layer owns a single domain:

```
┌─────────────────────────────────────────────────────────────┐
│                    ASSISTANT LAYER                          │
│  Wake Word → VAD Recording → Whisper STT → Response TTS    │
│                    (Runtime Orchestrator)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      NLU LAYER (Rasa)                       │
│  Intent Classification → Entity Extraction → Dialogue Mgmt  │
│  Custom Actions → Duckling Integration                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   LOGIC LAYER (FastAPI)                      │
│  App Launcher → Weather → Reminders → Search → Definitions  │
│  APScheduler → Response Templates → Desktop Control          │
└─────────────────────────────────────────────────────────────┘
```

The Assistant sends transcribed text to Rasa (`:5005`). Rasa classifies intent and extracts entities, then its Custom Actions forward structured commands to the Logic API (`:8021`). The Logic layer executes the action and returns a response that flows back up the chain to TTS and audio output.

> For the full architectural deep-dive, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). For inter-service communication protocols and data contracts, see [docs/SYSTEM_COMMUNICATION.md](docs/SYSTEM_COMMUNICATION.md).

---

## 🔩 Tech Stack Matrix

| Technology                   | Role                                                          | Port   | Layer          |
| ---------------------------- | ------------------------------------------------------------- | ------ | -------------- |
| **OpenWakeWord**             | Hotword activation (uses "Alexa" model, configurable)         | —      | Assistant      |
| **WebRTC VAD**               | Voice Activity Detection for speech boundary detection        | —      | Assistant      |
| **Whisper.cpp**              | Local speech-to-text (C++ inference, `medium.en` model)       | —      | Assistant      |
| **Rasa 3.x**                 | Intent classification, entity extraction, dialogue management | `5005` | NLU            |
| **Rasa Actions**             | Custom action server bridging NLU decisions to Logic API      | `5055` | NLU            |
| **spaCy** (`en_core_web_md`) | Tokenization, featurization, named entity recognition         | —      | NLU            |
| **Duckling**                 | Deterministic parsing of time, date, and duration expressions | `8000` | NLU (Docker)   |
| **DIET Classifier**          | Joint intent classification and entity recognition            | —      | NLU            |
| **FastAPI**                  | Business logic HTTP API (action router + service modules)     | `8021` | Logic          |
| **APScheduler**              | Persistent reminder scheduling (SQLite-backed job store)      | —      | Logic          |
| **Coqui TTS**                | Neural text-to-speech synthesis (GlowTTS, LJSpeech)           | `5002` | Infra (Docker) |
| **Docker Compose**           | Container orchestration for TTS and Duckling services         | —      | Infra          |
| **WebSocket**                | Real-time assistant state streaming to web UI                 | `8765` | Assistant → UI |

---

## 🚀 Quick Start

### Prerequisites

| Requirement             | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| Python 3.9+             | Runtime for all three service layers         |
| Docker & Docker Compose | TTS and Duckling containers                  |
| CMake + C++ compiler    | Building Whisper.cpp from source             |
| PortAudio               | Audio I/O for wake word and speech recording |

```bash
# Linux (Debian/Ubuntu)
sudo apt install portaudio19-dev cmake build-essential
```

### Step-by-Step Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/kumawat-aditya/elisa-assistant.git
cd elisa-assistant
```

#### 2. Start Infrastructure (Docker)

```bash
cd infra && docker-compose up -d && cd ..
```

This starts **Coqui TTS** (`:5002`) and **Duckling** (`:8000`).

#### 3. Setup NLU Layer

```bash
python3 -m venv nlu_env
source nlu_env/bin/activate
pip install -r nlu/requirements.txt
python -m spacy download en_core_web_md
cd nlu && rasa train && cd ..
deactivate
```

#### 4. Setup Logic Layer

```bash
python3 -m venv logic_env
source logic_env/bin/activate
pip install -r logic/requirements.txt
deactivate
```

#### 5. Setup Assistant Layer

```bash
python3 -m venv app_env
source app_env/bin/activate
pip install -r assistant/requirements.txt
deactivate
```

#### 6. Build Whisper.cpp

```bash
cd stt
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
sh ./models/download-ggml-model.sh medium.en
cmake -B build
cmake --build build -j$(nproc)
cd ../..
```

#### 7. Launch Everything

```bash
./scripts/start.sh
```

The start script orchestrates all services in the correct order and provides a status summary:

| Service           | URL                      |
| ----------------- | ------------------------ |
| TTS (Docker)      | `http://localhost:5002`  |
| Duckling (Docker) | `http://localhost:8000`  |
| Logic API         | `http://localhost:8021`  |
| NLU Server        | `http://localhost:5005`  |
| NLU Actions       | `http://localhost:5055`  |
| Web UI            | `http://localhost:35109` |

Press `Ctrl+C` to gracefully shut down all services.

---

## 📂 Repository Navigation

```
elisa-assistant/
│
├── assistant/                  # LAYER 1: Runtime Orchestration
│   ├── src/
│   │   ├── main.py             # Entry point — wake word → STT → NLU → TTS loop
│   │   ├── wake_word/          # OpenWakeWord listener with PyAudio streams
│   │   ├── stt/                # VAD recording + Whisper.cpp CLI transcription
│   │   ├── tts/                # Coqui TTS API client + multi-backend playback
│   │   ├── nlu_client/         # HTTP client for Rasa webhook API
│   │   └── session/            # WebSocket server for real-time UI state broadcast
│   ├── tests/
│   └── requirements.txt
│
├── nlu/                        # LAYER 2: Natural Language Understanding (Rasa)
│   ├── config.yml              # NLU pipeline: spaCy → DIET → Duckling → Fallback
│   ├── domain.yml              # Intents, entities, slots, response templates
│   ├── endpoints.yml           # Action server endpoint configuration
│   ├── data/
│   │   ├── nlu.yml             # Training examples with entity annotations
│   │   ├── rules.yml           # Deterministic intent → action mappings
│   │   └── stories.yml         # Multi-turn conversation flows
│   ├── actions/
│   │   ├── actions.py          # Rasa SDK custom actions (12 action classes)
│   │   └── logic_integration.py # HTTP bridge to Logic API
│   ├── models/                 # Trained model artifacts (gitignored)
│   └── requirements.txt
│
├── logic/                      # LAYER 3: Business Logic (FastAPI)
│   ├── src/
│   │   ├── main.py             # FastAPI app with /process endpoint
│   │   ├── routes/
│   │   │   └── logic.py        # Action router dispatching to service modules
│   │   ├── services/
│   │   │   ├── app_launcher.py # Cross-platform application launcher
│   │   │   ├── weather_info.py # OpenWeatherMap API integration
│   │   │   ├── reminder_manager.py # Reminder CRUD + scheduling + notifications
│   │   │   └── response_loader.py  # YAML-based response template engine
│   │   ├── scheduler/
│   │   │   └── scheduler_core.py   # APScheduler with SQLite job store
│   │   └── data/
│   │       ├── responses.yml       # Randomized response templates
│   │       └── reminders/          # Persistent reminder storage
│   ├── tests/
│   └── requirements.txt
│
├── stt/                        # Whisper.cpp build directory
│   └── whisper.cpp/            # Cloned repo with compiled binary
│
├── ui/                         # Web Interface
│   └── public/
│       └── index.html          # Real-time status dashboard
│
├── shared/
│   └── audio/
│       ├── permanent/          # Boot sound, beep, notification WAVs
│       └── temporary/          # Transient TTS output (overwritten per response)
│
├── infra/
│   └── docker-compose.yml      # Coqui TTS + Duckling container definitions
│
├── config/                     # External configuration
├── scripts/
│   ├── start.sh                # Full-system orchestration script (Linux)
│   └── start.ps1               # PowerShell equivalent (Windows)
├── logs/                       # Runtime logs (gitignored)
├── docs/                       # Extended documentation
│   ├── ARCHITECTURE.md         # System design deep-dive
│   └── SYSTEM_COMMUNICATION.md # Protocols, data contracts, state management
│
├── README.md
└── LICENSE.txt                 # MIT License
```

**Why this structure?** Each top-level directory maps to an independently deployable service with its own virtual environment, dependencies, and test suite. The `shared/` directory provides the only filesystem-level coupling (audio files), while all inter-service communication uses HTTP REST. This makes it straightforward to containerize any layer or swap a component (e.g., replace Whisper with another STT engine) without cascading changes.

---

## 🛠 Development

### Running Services Individually

**Logic API:**

```bash
source logic_env/bin/activate
cd logic/src && uvicorn main:app --reload --port 8021
```

**NLU Server:**

```bash
source nlu_env/bin/activate
cd nlu && rasa run --enable-api --cors "*"
```

**NLU Actions Server:**

```bash
source nlu_env/bin/activate
cd nlu && rasa run actions
```

**Assistant:**

```bash
source app_env/bin/activate
cd assistant/src && python main.py
```

### Retraining the NLU Model

```bash
source nlu_env/bin/activate
cd nlu
rasa train          # Train new model
rasa shell          # Interactive testing
rasa test           # Evaluate against test stories
```

### Supported Commands

| Category          | Examples                                            |
| ----------------- | --------------------------------------------------- |
| **Greetings**     | "Hey", "Hello", "Good morning"                      |
| **Time/Date**     | "What time is it?", "What's today's date?"          |
| **App Launching** | "Open Chrome", "Launch VS Code"                     |
| **Web Search**    | "Search Python tutorials", "Google best laptops"    |
| **Dictation**     | "Type hello world"                                  |
| **Definitions**   | "What is the meaning of entropy?"                   |
| **Weather**       | "What's the weather in Tokyo?"                      |
| **Reminders**     | "Remind me to call mom at 5pm", "List my reminders" |

---

## 📚 Documentation

| Document                                                     | Description                                           |
| ------------------------------------------------------------ | ----------------------------------------------------- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)                 | Full system design, component analysis, failure modes |
| [docs/SYSTEM_COMMUNICATION.md](docs/SYSTEM_COMMUNICATION.md) | Protocols, JSON data contracts, state management      |

---

## 🤝 Contributing

Contributions are welcome. Please open an issue before making major changes to discuss the approach.

---

## 📝 License

[MIT License](LICENSE.txt)

---

<div align="center">

Built by [Aditya Kumawat](https://github.com/kumawat-aditya)

</div>
# ELISA

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Rasa](https://img.shields.io/badge/Rasa-3.x-5A17EE?logo=rasa&logoColor=white)](https://rasa.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.txt)

**Modular, local-first voice assistant built with Rasa, FastAPI, and Whisper**

[Features](#-features) • [Architecture](#-architecture) • [Project Structure](#-project-structure) • [Quick Start](#-quick-start) • [Development](#-development)

</div>

---

## Overview

ELISA is a self-hosted voice assistant designed with clear separation of concerns across runtime orchestration, NLU processing, and business logic.

The system is structured as independent services communicating over HTTP and WebSocket, making it easier to maintain, extend, and debug.

Core principles:

- Modular architecture
- Local processing (no cloud dependency required)
- Clear service boundaries
- Reproducible setup with Docker

---

# ✨ Features

| Layer                     | Capabilities                                                                   |
| ------------------------- | ------------------------------------------------------------------------------ |
| **Voice Interface**       | Wake word detection, VAD-based recording, Whisper speech-to-text, TTS playback |
| **NLU (Rasa)**            | Intent recognition, entity extraction, dialogue management                     |
| **Logic Layer (FastAPI)** | App launcher, reminders, weather, search, definitions                          |
| **Scheduler**             | Persistent reminders using APScheduler                                         |
| **Web UI**                | Real-time status via WebSocket                                                 |
| **Entity Parsing**        | Duckling for time/date recognition                                             |

---

# 🏗️ Architecture

ELISA follows a **multi-service layered architecture**:

```
User Voice
    ↓
Wake Word Detection
    ↓
Speech-to-Text (Whisper.cpp)
    ↓
NLU Server (Rasa - Port 5005)
    ↓
Logic API (FastAPI - Port 8021)
    ↓
Text-to-Speech (Docker - Port 5002)
    ↓
Audio Output
```

---

## Service Responsibilities

### 1️⃣ Assistant Layer (`assistant/`)

- Main runtime entry point
- Wake word detection
- Audio recording
- STT integration
- Rasa API client
- WebSocket communication with UI

### 2️⃣ NLU Layer (`nlu/`)

- Intent classification
- Entity extraction
- Dialogue handling
- Custom actions
- Duckling integration

### 3️⃣ Logic Layer (`logic/`)

- Business logic modules
- Reminder scheduling
- Desktop control
- External API integrations
- Response formatting

---

# 📁 Project Structure

```
elisa-assistant/
│
├── assistant/                 # Runtime orchestration
│   ├── src/
│   │   ├── main.py
│   │   ├── wake_word/
│   │   ├── stt/
│   │   ├── tts/
│   │   ├── nlu_client/
│   │   └── session/
│   ├── tests/
│   └── requirements.txt
│
├── logic/                     # FastAPI business logic
│   ├── src/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── scheduler/
│   │   └── data/
│   ├── tests/
│   └── requirements.txt
│
├── nlu/                       # Rasa NLU
│   ├── actions/
│   ├── data/
│   ├── models/
│   ├── config.yml
│   ├── domain.yml
│   └── requirements.txt
│
├── stt/                       # Whisper.cpp integration
│
├── ui/                        # Web interface
│
├── shared/
│   └── audio/
│
├── infra/
│   └── docker-compose.yml
│
├── scripts/
├── docs/
├── logs/                      # gitignored
├── config/
│
├── README.md
└── LICENSE.txt
```

---

# 🚀 Quick Start

## Prerequisites

- Python 3.9+
- Docker & Docker Compose
- CMake + C++ compiler
- PortAudio

Linux example:

```bash
sudo apt install portaudio19-dev
```

---

## Installation

### 1. Clone

```bash
git clone https://github.com/kumawat-aditya/elisa-assistant.git
cd elisa-assistant
```

---

### 2. Start Infrastructure Services

```bash
cd infra
docker-compose up -d
cd ..
```

---

### 3. Setup NLU

```bash
python3 -m venv nlu_env
source nlu_env/bin/activate
pip install -r nlu/requirements.txt
python -m spacy download en_core_web_md
cd nlu && rasa train && cd ..
deactivate
```

---

### 4. Setup Logic Layer

```bash
python3 -m venv logic_env
source logic_env/bin/activate
pip install -r logic/requirements.txt
deactivate
```

---

### 5. Setup Assistant

```bash
python3 -m venv app_env
source app_env/bin/activate
pip install -r assistant/requirements.txt
deactivate
```

---

### 6. Build Whisper.cpp

```bash
cd stt
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
sh ./models/download-ggml-model.sh medium.en
cmake -B build
cmake --build build -j$(nproc)
cd ../..
```

---

### 7. Run

```bash
./scripts/start.sh
```

Web UI:

```
http://localhost:35109
```

---

# 🐳 Docker Services

| Service  | Purpose                  | Port |
| -------- | ------------------------ | ---- |
| TTS      | Speech synthesis         | 5002 |
| Duckling | Date/time entity parsing | 8000 |

Start / Stop:

```bash
docker-compose up -d
docker-compose down
```

---

# 📜 Supported Commands

- Greetings
- Time / Date queries
- App launching
- Web search
- Dictation
- Word definitions
- Weather queries
- Reminder creation / listing

---

# 🛠 Development

## Run Services Individually

Logic API:

```bash
cd logic/src
uvicorn main:app --reload --port 8021
```

NLU Server:

```bash
cd nlu
rasa run --enable-api --cors "*"
```

NLU Actions:

```bash
rasa run actions
```

Assistant:

```bash
cd assistant/src
python main.py
```

---

## Training NLU

```bash
cd nlu
rasa train
rasa shell
```

---

# 📚 Documentation

- `docs/setup.txt`
- `docs/docker_how_to.txt`
- `docs/venv_how_to.txt`

---

# 🤝 Contributing

Contributions are welcome. Please open an issue before major changes.

---

# 📝 License

MIT License

---

<div align="center">

Built by Aditya Kumawat

</div>
