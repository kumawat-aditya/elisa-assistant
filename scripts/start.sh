#!/bin/bash

# ============================================================================
# ELISA Voice Assistant - Startup Script
# ============================================================================
# Starts all required services for ELISA voice assistant.
# On first run (or with --setup), automatically bootstraps the entire project:
#   • Creates Python virtual environments and installs all dependencies
#   • Builds whisper.cpp and downloads the STT model
#   • Downloads spaCy language model for Rasa
#   • Trains the Rasa NLU model if no trained model exists
#
# Services started:
#   1. Docker containers (TTS, Duckling) via docker-compose
#   2. Logic Layer (FastAPI on port 8021)
#   3. NLU Server - Rasa (port 5005)
#   4. NLU Actions Server - Rasa (port 5055)
#   5. Web UI HTTP Server (port 35109)
#   6. Main Assistant (assistant/src/main.py)
#
# Usage:
#   ./start.sh              # auto-detects first run and sets up if needed
#   ./start.sh --setup      # force re-run setup even if already done
#   ./start.sh --skip-setup # skip setup entirely (fastest restart)
#
# Prerequisites (must be installed manually — cannot be automated):
#   • Docker installed and daemon running
#   • Python 3.9 available as python3.9  (required by Rasa 3.6.21)
#   • System packages: build-essential cmake portaudio19-dev python3.9-dev
#     Install with: sudo apt-get install build-essential cmake portaudio19-dev python3.9-dev
# ============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# ── Flags ──────────────────────────────────────────────────────────────────
FORCE_SETUP=false
SKIP_SETUP=false
for arg in "$@"; do
    case "$arg" in
        --setup)       FORCE_SETUP=true ;;
        --skip-setup)  SKIP_SETUP=true  ;;
    esac
done

# PIDs for cleanup
LOGIC_PID=""
NLU_SERVER_PID=""
NLU_ACTIONS_PID=""
HTTP_SERVER_PID=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $1"; }
log_setup()   { echo -e "${MAGENTA}[SETUP]${NC} $1"; }

cleanup() {
    echo ""
    log_warn "Shutting down services..."
    
    [ -n "$HTTP_SERVER_PID" ] && kill $HTTP_SERVER_PID 2>/dev/null && log_info "Stopped UI Server"
    [ -n "$NLU_ACTIONS_PID" ] && kill $NLU_ACTIONS_PID 2>/dev/null && log_info "Stopped NLU Actions"
    [ -n "$NLU_SERVER_PID" ] && kill $NLU_SERVER_PID 2>/dev/null && log_info "Stopped NLU Server"
    [ -n "$LOGIC_PID" ] && kill $LOGIC_PID 2>/dev/null && log_info "Stopped Logic Layer"
    
    log_success "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

# Check required system-level binaries and warn if missing
check_system_deps() {
    log_setup "Checking system dependencies..."
    local missing=()

    command -v python3.9 &>/dev/null || missing+=("python3.9")
    command -v cmake     &>/dev/null || missing+=("cmake")
    command -v make      &>/dev/null || missing+=("make (build-essential)")
    command -v docker    &>/dev/null || missing+=("docker")
    command -v curl      &>/dev/null || missing+=("curl")

    # Check for portaudio header (needed by PyAudio)
    if ! dpkg -s portaudio19-dev &>/dev/null 2>&1 && \
       ! [ -f /usr/include/portaudio.h ] && \
       ! [ -f /usr/local/include/portaudio.h ]; then
        missing+=("portaudio19-dev")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing system dependencies: ${missing[*]}"
        echo ""
        echo "  Install them with:"
        echo "    sudo apt-get install build-essential cmake python3.9 python3.9-dev portaudio19-dev"
        echo ""
        echo "  For Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi

    log_success "System dependencies OK"
}

# Create a venv with a specific python binary if it doesn't already exist
ensure_venv() {
    local env_dir="$1"
    local python_bin="$2"   # e.g. python3.9 or python3
    local label="$3"

    if [ ! -f "$env_dir/bin/activate" ]; then
        log_setup "Creating $label virtual environment ($env_dir)..."
        "$python_bin" -m venv "$env_dir"
        log_success "$label venv created"
    else
        log_info "$label venv already exists — skipping creation"
    fi
}

# Install requirements into a venv if the sentinel file is outdated
install_requirements() {
    local env_dir="$1"
    local req_file="$2"
    local label="$3"
    local sentinel="$env_dir/.requirements_installed"

    # Re-install if requirements.txt is newer than the sentinel
    if [ ! -f "$sentinel" ] || [ "$req_file" -nt "$sentinel" ]; then
        log_setup "Installing $label requirements..."
        source "$env_dir/bin/activate"
        pip install --upgrade pip -q
        pip install -r "$req_file" -q
        touch "$sentinel"
        deactivate 2>/dev/null || true
        log_success "$label requirements installed"
    else
        log_info "$label requirements up to date — skipping"
    fi
}

# Build whisper.cpp if the whisper-cli binary is missing
build_whisper() {
    local whisper_dir="$PROJECT_ROOT/stt/whisper.cpp"
    local binary="$whisper_dir/build/bin/whisper-cli"

    if [ -f "$binary" ]; then
        log_info "whisper-cli already built — skipping"
        return
    fi

    log_setup "Building whisper.cpp (this takes a few minutes)..."
    cd "$whisper_dir"
    cmake -B build -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -q
    cmake --build build --config Release -j"$(nproc)"
    cd "$PROJECT_ROOT"
    log_success "whisper.cpp built successfully"
}

# Download the STT model if not present
download_whisper_model() {
    local model_dir="$PROJECT_ROOT/stt/whisper.cpp/models"
    local model_file="$model_dir/ggml-medium.en.bin"

    if [ -f "$model_file" ]; then
        log_info "Whisper model already present — skipping download"
        return
    fi

    log_setup "Downloading whisper ggml-medium.en model (~1.5 GB)..."
    bash "$model_dir/download-ggml-model.sh" medium.en
    log_success "Whisper model downloaded"
}

# Download the spaCy language model needed by Rasa
download_spacy_model() {
    local sentinel="$PROJECT_ROOT/nlu_env/.spacy_model_installed"

    if [ -f "$sentinel" ]; then
        log_info "spaCy en_core_web_md already installed — skipping"
        return
    fi

    log_setup "Downloading spaCy en_core_web_md model..."
    source "$PROJECT_ROOT/nlu_env/bin/activate"
    python -m spacy download en_core_web_md -q
    touch "$sentinel"
    deactivate 2>/dev/null || true
    log_success "spaCy model installed"
}

# Train the Rasa NLU model if no trained model exists
train_nlu_model() {
    local model_dir="$PROJECT_ROOT/nlu/models"
    # Check for any .tar.gz model file
    if compgen -G "$model_dir/*.tar.gz" &>/dev/null; then
        log_info "Rasa model already trained — skipping training"
        return
    fi

    log_setup "Training Rasa NLU model (this can take 5-10 minutes on first run)..."
    source "$PROJECT_ROOT/nlu_env/bin/activate"
    cd "$PROJECT_ROOT/nlu"
    rasa train --quiet
    cd "$PROJECT_ROOT"
    deactivate 2>/dev/null || true
    log_success "Rasa NLU model trained"
}

# Decide whether to run setup at all
should_run_setup() {
    $FORCE_SETUP && return 0
    $SKIP_SETUP  && return 1

    # Auto-detect: setup is needed if any venv or key artifact is missing
    [ ! -f "$PROJECT_ROOT/app_env/bin/activate" ]   && return 0
    [ ! -f "$PROJECT_ROOT/logic_env/bin/activate" ]  && return 0
    [ ! -f "$PROJECT_ROOT/nlu_env/bin/activate" ]    && return 0
    [ ! -f "$PROJECT_ROOT/stt/whisper.cpp/build/bin/whisper-cli" ] && return 0
    [ ! -f "$PROJECT_ROOT/stt/whisper.cpp/models/ggml-medium.en.bin" ] && return 0
    compgen -G "$PROJECT_ROOT/nlu/models/*.tar.gz" &>/dev/null || return 0

    return 1  # everything present, skip setup
}

# ============================================================================
# FIRST-TIME SETUP ENTRY POINT
# ============================================================================
run_setup() {
    echo ""
    echo "============================================================================"
    echo "                 ELISA Voice Assistant - First-Time Setup"
    echo "============================================================================"
    echo ""

    check_system_deps

    # Python virtual environments
    ensure_venv "$PROJECT_ROOT/app_env"   "python3"   "Assistant"
    ensure_venv "$PROJECT_ROOT/logic_env" "python3"   "Logic"
    ensure_venv "$PROJECT_ROOT/nlu_env"   "python3.9" "NLU (Rasa)"

    install_requirements "$PROJECT_ROOT/app_env"   "$PROJECT_ROOT/assistant/requirements.txt" "Assistant"
    install_requirements "$PROJECT_ROOT/logic_env" "$PROJECT_ROOT/logic/requirements.txt"     "Logic"
    install_requirements "$PROJECT_ROOT/nlu_env"   "$PROJECT_ROOT/nlu/requirements.txt"       "NLU"

    # STT (whisper.cpp)
    build_whisper
    download_whisper_model

    # NLU (Rasa)
    download_spacy_model
    train_nlu_model

    echo ""
    echo "============================================================================"
    log_success "Setup complete! Starting services..."
    echo "============================================================================"
    echo ""
}

trap cleanup SIGINT SIGTERM

echo ""
echo "============================================================================"
echo "                    ELISA Voice Assistant - Startup"
echo "============================================================================"
echo ""

# ============================================================================
# Setup (first run or --setup flag)
# ============================================================================
if should_run_setup; then
    run_setup
fi

# ============================================================================
# Step 1: Start Docker Services
# ============================================================================
log_step "Starting Docker services..."

if ! docker info &>/dev/null; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

cd "$PROJECT_ROOT/infra"
docker-compose up -d
log_success "Docker services started (TTS: 5002, Duckling: 8022)"

# Wait for Docker services
sleep 3

# ============================================================================
# Step 2: Create logs directory
# ============================================================================
mkdir -p "$PROJECT_ROOT/logs"

# ============================================================================
# Step 3: Start Logic Layer (FastAPI)
# ============================================================================
log_step "Starting Logic Layer (FastAPI on port 8021)..."

cd "$PROJECT_ROOT/logic/src"

# Activate logic_env virtual environment
if [ -f "$PROJECT_ROOT/logic_env/bin/activate" ]; then
    source "$PROJECT_ROOT/logic_env/bin/activate"
    log_info "Activated logic_env"
else
    log_warn "logic_env not found - using system Python"
fi

uvicorn main:app --host 0.0.0.0 --port 8021 > "$PROJECT_ROOT/logs/logic.log" 2>&1 &
LOGIC_PID=$!
log_success "Logic Layer started (PID: $LOGIC_PID)"

sleep 2

# ============================================================================
# Step 4: Start NLU Server (Rasa)
# ============================================================================
log_step "Starting NLU Server (Rasa on port 5005)..."

cd "$PROJECT_ROOT/nlu"

# Activate nlu_env virtual environment
if [ -f "$PROJECT_ROOT/nlu_env/bin/activate" ]; then
    source "$PROJECT_ROOT/nlu_env/bin/activate"
    log_info "Activated nlu_env"
else
    log_warn "nlu_env not found - using system Python"
fi

rasa run --enable-api --cors "*" > "$PROJECT_ROOT/logs/nlu_server.log" 2>&1 &
NLU_SERVER_PID=$!
log_success "NLU Server started (PID: $NLU_SERVER_PID)"

# ============================================================================
# Step 5: Start NLU Actions Server (Rasa)
# ============================================================================
log_step "Starting NLU Actions Server (Rasa on port 5055)..."

cd "$PROJECT_ROOT/nlu"
rasa run actions > "$PROJECT_ROOT/logs/nlu_actions.log" 2>&1 &
NLU_ACTIONS_PID=$!
log_success "NLU Actions started (PID: $NLU_ACTIONS_PID)"

# Wait for Rasa to initialize (Rasa takes 15-30 seconds to fully start)
log_info "Waiting for NLU to initialize..."
MAX_WAIT=40
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:5005/status > /dev/null 2>&1; then
        log_success "NLU Server is ready!"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $((WAITED % 10)) -eq 0 ]; then
        log_info "Still waiting for NLU... (${WAITED}s / ${MAX_WAIT}s)"
    fi
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warn "NLU Server may not be fully ready yet. Continuing anyway..."
fi

# ============================================================================
# Step 6: Start Web UI Server
# ============================================================================
log_step "Starting Web UI Server (port 35109)..."

cd "$PROJECT_ROOT"
python -m http.server 35109 --directory "$PROJECT_ROOT/ui/public" > "$PROJECT_ROOT/logs/ui_server.log" 2>&1 &
HTTP_SERVER_PID=$!
log_success "UI Server started (PID: $HTTP_SERVER_PID)"

# ============================================================================
# Status Summary
# ============================================================================
echo ""
echo "============================================================================"
log_success "All services are running!"
echo "============================================================================"
echo ""
echo "  Services:"
echo "    • TTS Docker        : http://localhost:5002"
echo "    • Duckling Docker   : http://localhost:8000"
echo "    • Logic Layer       : http://localhost:8021"
echo "    • NLU Server        : http://localhost:5005"
echo "    • NLU Actions       : http://localhost:5055"
echo "    • Web UI (God Mode) : http://localhost:35109/  ← open in browser"
echo "    • UI WebSocket bus  : ws://localhost:8765       (started by assistant)"
echo ""
echo "  Logs: $PROJECT_ROOT/logs/"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "============================================================================"
echo ""

# ============================================================================
# Step 7: Start Main Assistant
# ============================================================================
log_step "Starting Main Assistant..."

cd "$PROJECT_ROOT/assistant/src"

# Activate app_env virtual environment
if [ -f "$PROJECT_ROOT/app_env/bin/activate" ]; then
    source "$PROJECT_ROOT/app_env/bin/activate"
    log_info "Activated app_env"
else
    log_warn "app_env not found - using system Python"
fi

python main.py

# If main.py exits, cleanup
cleanup
