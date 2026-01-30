#!/bin/bash

# ============================================================================
# ELISA Voice Assistant - Startup Script
# ============================================================================
# Starts all required services for ELISA voice assistant.
#
# Services:
#   1. Docker containers (TTS, Duckling) via docker-compose
#   2. Logic Layer (FastAPI on port 8021)
#   3. NLU Server - Rasa (port 5005)
#   4. NLU Actions Server - Rasa (port 5055)
#   5. Web UI HTTP Server (port 35109)
#   6. Main Assistant (assistant/src/main.py)
# ============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

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
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

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

echo ""
echo "============================================================================"
echo "                    ELISA Voice Assistant - Startup"
echo "============================================================================"
echo ""

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
log_success "Docker services started (TTS: 5002, Duckling: 8000)"

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

# Activate logic environment if available
if command -v pyenv &>/dev/null; then
    eval "$(pyenv init -)"
    pyenv activate logic-env 2>/dev/null || true
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

# Activate rasa environment if available
if [ -f "$PROJECT_ROOT/rasa_env/bin/activate" ]; then
    source "$PROJECT_ROOT/rasa_env/bin/activate"
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

# Wait for Rasa to initialize
log_info "Waiting for NLU to initialize..."
sleep 5

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
echo "    • Web UI            : http://localhost:35109"
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

# Activate app environment if available
if command -v pyenv &>/dev/null; then
    eval "$(pyenv init -)"
    pyenv activate app-env 2>/dev/null || true
fi

python main.py

# If main.py exits, cleanup
cleanup
