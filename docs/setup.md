# ELISA Setup Guide

This guide provides detailed instructions for setting up ELISA Voice Assistant.

## Prerequisites

| Requirement    | Version   | Installation                                      |
| -------------- | --------- | ------------------------------------------------- |
| Python         | 3.9+      | [python.org](https://python.org/downloads)        |
| Docker         | Latest    | [docker.com](https://docker.com)                  |
| Docker Compose | Latest    | Included with Docker                              |
| CMake          | 3.x+      | `sudo apt install cmake` / `sudo pacman -S cmake` |
| C++ Compiler   | GCC/Clang | `sudo apt install build-essential` / `base-devel` |
| PortAudio      | Latest    | `sudo apt install portaudio19-dev` / `portaudio`  |

> **Note:** All virtual environments use Python's built-in `venv` module, which works on both Windows and Linux.

---

## Step 1: Clone Repository

```bash
git clone https://github.com/Adikumaw/elisa-assistant.git
cd elisa-assistant
```

---

## Step 2: Docker Services (TTS & Duckling)

### Start Services

```bash
cd infra
docker-compose up -d
cd ..
```

### Verify Services

```bash
# Check if running
docker ps

# Expected output:
# elisa-tts       - Port 5002
# elisa-duckling  - Port 8000
```

### GPU TTS (Optional)

Edit `infra/docker-compose.yml` to enable GPU support (see comments in file).

---

## Step 3: NLU Layer (Rasa)

### Linux / macOS

```bash
# Create virtual environment
python3 -m venv nlu_env
source nlu_env/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r nlu/requirements.txt
python -m spacy download en_core_web_md

# Train Rasa model
cd nlu
rasa train
cd ..

deactivate
```

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv nlu_env
.\nlu_env\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r nlu\requirements.txt
python -m spacy download en_core_web_md

# Train Rasa model
cd nlu
rasa train
cd ..

deactivate
```

---

## Step 4: Logic Layer (FastAPI)

### Linux / macOS

```bash
# Create virtual environment
python3 -m venv logic_env
source logic_env/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r logic/requirements.txt

deactivate
```

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv logic_env
.\logic_env\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r logic\requirements.txt

deactivate
```

---

## Step 5: Assistant Layer

### Linux / macOS

```bash
# Create virtual environment
python3 -m venv app_env
source app_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r assistant/requirements.txt

deactivate
```

### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv app_env
.\app_env\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r assistant\requirements.txt

deactivate
```

---

## Step 6: Speech-to-Text (Whisper.cpp)

```bash
# Clone Whisper.cpp
cd stt
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Download model
sh ./models/download-ggml-model.sh medium.en

# Build (CPU)
cmake -B build -DGGML_OPENMP=ON
cmake --build build --config Release -j$(nproc)

# OR Build with CUDA (GPU)
# cmake -B build -DGGML_CUDA=ON
# cmake --build build -j$(nproc)

# Test
./build/bin/whisper-cli -m models/ggml-medium.en.bin -f samples/jfk.wav

cd ../..
```

---

## Step 7: Run ELISA

### Using Start Script (Recommended)

**Linux / macOS:**

```bash
./scripts/start.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\start.ps1
```

### Manual Startup (6 terminals)

**Terminal 1: Docker services**

```bash
cd infra && docker-compose up
```

**Terminal 2: Logic Layer**

```bash
source logic_env/bin/activate   # Linux/macOS
# .\logic_env\Scripts\Activate.ps1  # Windows
cd logic/src
uvicorn main:app --host 0.0.0.0 --port 8021
```

**Terminal 3: NLU Server**

```bash
source nlu_env/bin/activate
cd nlu && rasa run --enable-api --cors "*"
```

**Terminal 4: NLU Actions**

```bash
source nlu_env/bin/activate
cd nlu && rasa run actions
```

**Terminal 5: Web UI**

```bash
python -m http.server 35109 --directory ui/public
```

**Terminal 6: Assistant**

```bash
source app_env/bin/activate
cd assistant/src
python main.py
```

python main.py

````

---

## Service Ports

| Service         | Port  | URL                    |
| --------------- | ----- | ---------------------- |
| TTS Docker      | 5002  | http://localhost:5002  |
| Duckling Docker | 8000  | http://localhost:8000  |
| Logic Layer     | 8021  | http://localhost:8021  |
| NLU Server      | 5005  | http://localhost:5005  |
| NLU Actions     | 5055  | http://localhost:5055  |
| Web UI          | 35109 | http://localhost:35109 |

---

## Troubleshooting

### Docker Issues

```bash
# Check logs
docker logs elisa-tts
docker logs elisa-duckling

# Restart services
cd infra && docker-compose restart
````

### Rasa Training Fails

```bash
# Clear cache and retrain
cd nlu
rm -rf .rasa
rasa train
```

### Audio Issues

```bash
# List audio devices
arecord -l

# Test recording
arecord -D plughw:0,0 -f S16_LE -r 16000 test.wav
```
