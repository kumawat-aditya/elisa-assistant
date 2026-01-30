
--------------------------------------------------------------------------------

# **ELISA Assistant Setup Guide**

This guide sets up ELISA's environment, including TTS, logic layer, Rasa, Duckling, and Whisper. All Docker containers will run on a dedicated `elisa-network` for internal communication.

--------------------------------------------------------------------------------

## **1. TTS (Text-to-Speech)**

### CPU Version

```bash
cd tts
docker run --rm -it -p 5002:5002 --entrypoint /bin/bash ghcr.io/coqui-ai/tts-cpu:v0.22.0
python3 TTS/server/server.py --list_models         # List available models
python3 TTS/server/server.py --model_name tts_models/en/ljspeech/glow-tts
```

### GPU Version

```bash
docker run -it -p 5002:5002 --gpus all --entrypoint /bin/bash ghcr.io/coqui-ai/tts:v0.22.0
python3 TTS/server/server.py --list_models
python3 TTS/server/server.py --model_name tts_models/en/ljspeech/glow-tts --use_cuda true
```

> **Note:** Make sure your system meets [NVIDIA Docker requirements](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).
> On Arch Linux: `sudo pacman -S nvidia-container-toolkit`

--------------------------------------------------------------------------------

## **3. Logic Layer (FastAPI)**

### Python Setup

```bash
pyenv install 3.10.12
pyenv virtualenv 3.10.12 logic-env
pyenv activate logic-env
pip install --upgrade pip
pip install -r requirements.txt
```

### Run the API

```bash
# Standard mode
uvicorn main:app --host 0.0.0.0 --port 8021

# Debug mode
uvicorn main:app --host 0.0.0.0 --port 8021 --log-level debug
```

> **Tip:** To fix library versions, pin all packages in `requirements.txt` using `==`, e.g.,
> `fastapi==0.100.0`
> Then run `pip freeze > requirements.txt` after confirming a working environment.

--------------------------------------------------------------------------------

## **4. Duckling (NER for Dates/Times)**

```bash
docker run -d --name duckling -p 8022:8000 rasa/duckling:0.2.0.2-r3
```

--------------------------------------------------------------------------------

## **5. Rasa Layer (rasa server)**

### Python Installation (Only if recreating the project from scratch)

```bash
cd python
tar -xzf Python-3.9.18.tgz
cd Python-3.9.18
./configure --prefix=$(pwd)/../python39
make -j$(nproc)
make install
```
### This will create python 3.9.18 version in python/python39 directory.

### Python Setup

```bash
./python/python39/bin/python3.9 --version
./python/python39/bin/python3.9 -m venv ./rasa_env
source ./rasa_env/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r rasa/requirements.txt
python -m spacy download en_core_web_md
source ./rasa_env/bin/deactivate
```

### Run the API

```bash
source ./rasa_env/bin/activate
cd rasa

# Rasa train
rasa train

# Rasa run server
rasa runecho "why choose services named folder for this. and why not make the core, logic, whisper, rasa, audio, at the same folder level they are kind of same level layers. and why use app folder for core under services. and run the start_assistant.sh"

# Rasa run actions
cd actions
rasa run actions

# Rasa run shell
rasa shell
```

--------------------------------------------------------------------------------

## **6. Whisper.cpp (Speech Recognition)**

### Clone & Download Model

```bash
cd app
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
sh ./models/download-ggml-model.sh medium.en
```

### Build (CPU / CUDA)

```bash
# Requirements: cmake, base-devel, gcc-fortran
# Add CUDA to PATH if not already
export PATH=/opt/cuda/bin:$PATH
export LD_LIBRARY_PATH=/opt/cuda/lib64:$LD_LIBRARY_PATH
source ~/.bashrc  # or ~/.profile

# CPU build
cmake -B build -DGGML_OPENMP=ON
cmake --build build --config Release -j$(nproc)

# CUDA build
cmake -B build -DGGML_CUDA=ON -DCUDAToolkit_ROOT=/opt/cuda -DCUDA_HOST_COMPILER=/usr/bin/g++-14
cmake --build build -j$(nproc)
```

### Test Run

```bash
./build/bin/whisper-cli -m models/ggml-medium.en.bin -f samples/jfk.wav
```

--------------------------------------------------------------------------------

## **7. App Environment**

```bash
pyenv install 3.10.12
pyenv virtualenv 3.10.12 app-env
pyenv activate app-env
pip install -r requirements.txt
```

> Again, pin versions in `requirements.txt` to avoid breaking changes in the future.

--------------------------------------------------------------------------------

## **8. Audio Recording Test**

```bash
arecord -D plughw:0,0 -f S16_LE -r 16000 record1.wav
```

---

## **9. Best Practices for Version Locking**

1. **Docker Images:** Always use specific tags instead of `latest`. Example:

   ```bash
   rasa/rasa:3.7.0-full
   ghcr.io/coqui-ai/tts-cpu:1.0.0
   ```
2. **Python Packages:** Pin versions in `requirements.txt` using `==`.
3. **System Dependencies:** Record exact versions (cmake, gcc, CUDA) in a README.

---

✅ This setup ensures:

* All Docker containers communicate over `elisa-network`.
* Future updates of third-party libraries or images don’t break your project.
* Both CPU and GPU setups are covered.
* Proper order: Network → TTS → Logic → Duckling → Rasa → Whisper → App environment.

---

If you want, I can also **rewrite this as a fully automated setup script** (`setup.sh`) that installs everything in the right order, sets up virtual environments, pins versions, and even handles Docker network setup. This would make onboarding much faster.

Do you want me to do that next?
