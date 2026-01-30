# ELISA Architecture

## Overview

ELISA uses a microservices architecture with three main layers:

1. **Assistant Layer** - Voice interface and orchestration
2. **NLU Layer** - Natural Language Understanding (Rasa)
3. **Logic Layer** - Business logic execution (FastAPI)

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| TTS (Docker) | 5002 | Text-to-Speech |
| Duckling (Docker) | 8000 | Entity extraction |
| Logic Layer | 8021 | FastAPI business logic |
| NLU Server | 5005 | Rasa NLU/Dialogue |
| NLU Actions | 5055 | Rasa custom actions |
| Web UI | 35109 | HTTP server |
| WebSocket | 8765 | UI communication |

## Data Flow

```
User → Wake Word → STT → NLU → Logic → Response → TTS → Audio
```
