# ELISA

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python\&logoColor=white)](https://python.org)
[![Rasa](https://img.shields.io/badge/Rasa-3.x-5A17EE?logo=rasa\&logoColor=white)](https://rasa.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi\&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker\&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.txt)

**Modular, local-first voice assistant built with Rasa, FastAPI, and Whisper**

[Features](#-features) • [Architecture](#-architecture) • [Project Structure](#-project-structure) • [Quick Start](#-quick-start) • [Development](#-development)

</div>

---

## Overview

ELISA is a self-hosted voice assistant designed with clear separation of concerns across runtime orchestration, NLU processing, and business logic.

The system is structured as independent services communicating over HTTP and WebSocket, making it easier to maintain, extend, and debug.

Core principles:

* Modular architecture
* Local processing (no cloud dependency required)
* Clear service boundaries
* Reproducible setup with Docker

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

* Main runtime entry point
* Wake word detection
* Audio recording
* STT integration
* Rasa API client
* WebSocket communication with UI

### 2️⃣ NLU Layer (`nlu/`)

* Intent classification
* Entity extraction
* Dialogue handling
* Custom actions
* Duckling integration

### 3️⃣ Logic Layer (`logic/`)

* Business logic modules
* Reminder scheduling
* Desktop control
* External API integrations
* Response formatting

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

* Python 3.9+
* Docker & Docker Compose
* CMake + C++ compiler
* PortAudio

Linux example:

```bash
sudo apt install portaudio19-dev
```

---

## Installation

### 1. Clone

```bash
git clone https://github.com/Adikumaw/elisa-assistant.git
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

* Greetings
* Time / Date queries
* App launching
* Web search
* Dictation
* Word definitions
* Weather queries
* Reminder creation / listing

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

* `docs/setup.txt`
* `docs/docker_how_to.txt`
* `docs/venv_how_to.txt`

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
