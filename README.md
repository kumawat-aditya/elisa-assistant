# ELISA

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Rasa](https://img.shields.io/badge/Rasa-3.x-5A17EE?logo=rasa&logoColor=white)](https://rasa.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.txt)

**A self-hosted, modular voice assistant engineered for privacy, clear service boundaries, and local-first intelligence.**

[Why ELISA?](#-why-elisa) · [Architecture](#-architecture-at-a-glance) · [Tech Stack](#-tech-stack-matrix) · [Quick Start](#-quick-start) · [Project Structure](#-repository-navigation) · [Development](#-development) · [Docs](#-documentation)

</div>

---

## 🧠 Why ELISA?

Most voice assistants depend on cloud APIs for core functionality. ELISA takes the opposite approach.

ELISA is a self-hosted voice assistant where **the full pipeline — wake word detection, speech-to-text, intent classification, entity parsing, business logic, and speech synthesis — runs locally**. External APIs are optional integrations, not part of the critical path.

The system is built on four engineering principles:

1. **Local-First Processing** — Wake word detection (OpenWakeWord), WebRTC VAD, STT (Whisper.cpp), NLU (Rasa + spaCy), entity parsing (Duckling), and Coqui TTS run on-device. No audio leaves the system.
2. **Strict Separation of Concerns** — Assistant runtime, NLU, and business logic operate as independent services with well-defined HTTP boundaries.
3. **Deterministic Entity Extraction** — Time expressions like “in 30 minutes” or “tomorrow at 5pm” are resolved through Duckling into structured timestamps.
4. **Runtime Observability** — The assistant publishes pipeline stages, logs, and conversation state over a WebSocket stream, enabling real-time inspection through the UI.

---

## 🏗️ Architecture at a Glance

ELISA is structured as a **multi-service layered system** with a clear execution path and a parallel observability channel:

```
┌─────────────────────────────────────────────────────────────┐
│                    ASSISTANT LAYER                          │
│  Wake Word → VAD → Whisper STT → Rasa Client → TTS          │
│  (Owns runtime flow + publishes state via WebSocket)        │
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
│                   LOGIC LAYER (FastAPI)                     │
│  App Launcher → Weather → Reminders → Search → Definitions  │
│  Scheduler → Response Templates → Desktop Control           │
└─────────────────────────────────────────────────────────────┘
```

### Communication Model

- **Command flow**: Assistant → Rasa → Logic → Assistant → TTS
- **State flow**: Assistant → WebSocket → UI

The assistant remains the runtime owner — it controls audio I/O, sequences the pipeline, and publishes a normalized state stream for observability.

> For deeper details, see `docs/ARCHITECTURE.md` and `docs/SYSTEM_COMMUNICATION.md`.

---

## 🔩 Tech Stack Matrix

| Technology                   | Role                                                          | Port   | Layer          |
| ---------------------------- | ------------------------------------------------------------- | ------ | -------------- |
| **OpenWakeWord**             | Hotword activation                                            | —      | Assistant      |
| **WebRTC VAD**               | Speech boundary detection                                     | —      | Assistant      |
| **Whisper.cpp**              | Local speech-to-text                                          | —      | Assistant      |
| **Rasa 3.x**                 | Intent classification, entity extraction, dialogue management | `5005` | NLU            |
| **Rasa Actions**             | Custom action bridge to Logic API                             | `5055` | NLU            |
| **spaCy** (`en_core_web_md`) | Tokenization and feature extraction                           | —      | NLU            |
| **Duckling**                 | Deterministic time/date parsing                               | `8022` | Infra / NLU    |
| **FastAPI**                  | Business logic API                                            | `8021` | Logic          |
| **APScheduler**              | Persistent reminder scheduling                                | —      | Logic          |
| **Coqui TTS**                | Speech synthesis                                              | `5002` | Infra          |
| **WebSocket**                | Runtime state streaming                                       | `8765` | Assistant → UI |
| **Docker Compose**           | Infrastructure orchestration                                  | —      | Infra          |

---

## 🚀 Quick Start

### Prerequisites

| Requirement             | Purpose                               |
| ----------------------- | ------------------------------------- |
| Python 3.9+             | Runtime for all service layers        |
| Docker & Docker Compose | TTS and Duckling services             |
| CMake + C++ compiler    | Building Whisper.cpp                  |
| PortAudio               | Audio I/O for wake word and recording |

```bash
# Linux (Debian/Ubuntu)
sudo apt install portaudio19-dev cmake build-essential
```

### Setup & Run

```bash
git clone https://github.com/kumawat-aditya/elisa-assistant.git
cd elisa-assistant
./scripts/start.sh
```

On first run, the script will:

- set up virtual environments
- install dependencies
- build Whisper.cpp
- download models
- train a Rasa model if required

### Runtime Endpoints

| Service     | URL                    |
| ----------- | ---------------------- |
| TTS         | http://localhost:5002  |
| Duckling    | http://localhost:8022  |
| Logic API   | http://localhost:8021  |
| NLU Server  | http://localhost:5005  |
| NLU Actions | http://localhost:5055  |
| Web UI      | http://localhost:35109 |
| WebSocket   | ws://localhost:8765    |

---

## 📂 Repository Navigation

```
elisa-assistant/
│
├── assistant/                  # Runtime orchestration + WebSocket state
│   ├── src/
│   │   ├── main.py             # Entry point (pipeline control)
│   │   ├── wake_word/
│   │   ├── stt/
│   │   ├── tts/
│   │   ├── nlu_client/
│   │   └── session/            # State publishing (logs, pipeline, metrics)
│
├── nlu/                        # Rasa NLU layer
│   ├── data/
│   ├── actions/
│   ├── config.yml
│   └── domain.yml
│
├── logic/                      # FastAPI business logic
│   ├── src/
│   │   ├── routes/
│   │   ├── services/
│   │   └── scheduler/
│
├── ui/                         # Web interface (WebSocket consumer)
├── infra/                      # Docker services (TTS + Duckling)
├── shared/audio/               # Shared audio assets
├── scripts/                    # Startup scripts
├── docs/                       # Extended documentation
└── logs/                       # Runtime logs
```

**Why this structure?**
Each layer is independently deployable with minimal coupling. Communication happens over HTTP, while shared state is streamed via WebSocket. This allows components to be replaced or scaled without affecting the rest of the system.

---

## 🛠 Development

### Run Services Individually

**Logic API**

```bash
cd logic/src
uvicorn main:app --reload --port 8021
```

**NLU**

```bash
cd nlu
rasa run --enable-api --cors "*"
rasa run actions
```

**Assistant**

```bash
cd assistant/src
python main.py
```

---

### Retraining the NLU Model

```bash
cd nlu
rasa train
rasa shell
rasa test
```

---

### Supported Commands

| Category      | Examples                        |
| ------------- | ------------------------------- |
| Greetings     | "Hello", "Good morning"         |
| Time/Date     | "What time is it?"              |
| App Launching | "Open Chrome", "Launch VS Code" |
| Search        | "Search Python tutorials"       |
| Dictation     | "Type hello world"              |
| Definitions   | "What is entropy?"              |
| Weather       | "What's the weather in Tokyo?"  |
| Reminders     | "Remind me to call mom at 5pm"  |

---

## 📚 Documentation

| Document                     | Description                                 |
| ---------------------------- | ------------------------------------------- |
| docs/ARCHITECTURE.md         | System design and component interactions    |
| docs/SYSTEM_COMMUNICATION.md | Protocols, data contracts, and message flow |

---

## 🤝 Contributing

Contributions are welcome. Please open an issue before making major changes.

---

## 📝 License

MIT License

---

<div align="center">

Built by Aditya Kumawat

</div>
