# ============================================================================
# ELISA Voice Assistant - Startup Script (Windows PowerShell)
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

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# PIDs for cleanup
$global:Jobs = @()

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "[STEP] $msg" -ForegroundColor Cyan }

function Cleanup {
    Write-Warn "Shutting down services..."
    
    foreach ($job in $global:Jobs) {
        if ($job -and $job.State -eq 'Running') {
            Stop-Job -Job $job -PassThru | Remove-Job -Force
            Write-Info "Stopped job $($job.Name)"
        }
    }
    
    Write-Success "All services stopped."
}

# Register cleanup on exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

Write-Host ""
Write-Host "============================================================================"
Write-Host "                    ELISA Voice Assistant - Startup"
Write-Host "============================================================================"
Write-Host ""

# ============================================================================
# Step 1: Start Docker Services
# ============================================================================
Write-Step "Starting Docker services..."

try {
    docker info | Out-Null
} catch {
    Write-Err "Docker is not running. Please start Docker Desktop first."
    exit 1
}

Push-Location "$ProjectRoot\infra"
docker-compose up -d
Pop-Location
Write-Success "Docker services started (TTS: 5002, Duckling: 8000)"

Start-Sleep -Seconds 3

# ============================================================================
# Step 2: Create logs directory
# ============================================================================
New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null

# ============================================================================
# Step 3: Start Logic Layer (FastAPI)
# ============================================================================
Write-Step "Starting Logic Layer (FastAPI on port 8021)..."

$logicJob = Start-Job -Name "LogicLayer" -ScriptBlock {
    param($root)
    Set-Location "$root\logic\src"
    
    # Activate venv if exists
    $venvPath = "$root\logic_env\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        & $venvPath
    }
    
    uvicorn main:app --host 0.0.0.0 --port 8021
} -ArgumentList $ProjectRoot

$global:Jobs += $logicJob
Write-Success "Logic Layer started (Job: $($logicJob.Id))"

Start-Sleep -Seconds 2

# ============================================================================
# Step 4: Start NLU Server (Rasa)
# ============================================================================
Write-Step "Starting NLU Server (Rasa on port 5005)..."

$nluServerJob = Start-Job -Name "NLUServer" -ScriptBlock {
    param($root)
    Set-Location "$root\nlu"
    
    # Activate venv if exists
    $venvPath = "$root\nlu_env\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        & $venvPath
    }
    
    rasa run --enable-api --cors "*"
} -ArgumentList $ProjectRoot

$global:Jobs += $nluServerJob
Write-Success "NLU Server started (Job: $($nluServerJob.Id))"

# ============================================================================
# Step 5: Start NLU Actions Server (Rasa)
# ============================================================================
Write-Step "Starting NLU Actions Server (Rasa on port 5055)..."

$nluActionsJob = Start-Job -Name "NLUActions" -ScriptBlock {
    param($root)
    Set-Location "$root\nlu"
    
    # Activate venv if exists
    $venvPath = "$root\nlu_env\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        & $venvPath
    }
    
    rasa run actions
} -ArgumentList $ProjectRoot

$global:Jobs += $nluActionsJob
Write-Success "NLU Actions started (Job: $($nluActionsJob.Id))"

Write-Info "Waiting for NLU to initialize..."
Start-Sleep -Seconds 5

# ============================================================================
# Step 6: Start Web UI Server
# ============================================================================
Write-Step "Starting Web UI Server (port 35109)..."

$uiServerJob = Start-Job -Name "UIServer" -ScriptBlock {
    param($root)
    python -m http.server 35109 --directory "$root\ui\public"
} -ArgumentList $ProjectRoot

$global:Jobs += $uiServerJob
Write-Success "UI Server started (Job: $($uiServerJob.Id))"

# ============================================================================
# Status Summary
# ============================================================================
Write-Host ""
Write-Host "============================================================================"
Write-Success "All services are running!"
Write-Host "============================================================================"
Write-Host ""
Write-Host "  Services:"
Write-Host "    - TTS Docker        : http://localhost:5002"
Write-Host "    - Duckling Docker   : http://localhost:8000"
Write-Host "    - Logic Layer       : http://localhost:8021"
Write-Host "    - NLU Server        : http://localhost:5005"
Write-Host "    - NLU Actions       : http://localhost:5055"
Write-Host "    - Web UI            : http://localhost:35109"
Write-Host ""
Write-Host "  Logs: $ProjectRoot\logs\"
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services"
Write-Host "============================================================================"
Write-Host ""

# ============================================================================
# Step 7: Start Main Assistant
# ============================================================================
Write-Step "Starting Main Assistant..."

Set-Location "$ProjectRoot\assistant\src"

# Activate app_env if exists
$appVenvPath = "$ProjectRoot\app_env\Scripts\Activate.ps1"
if (Test-Path $appVenvPath) {
    & $appVenvPath
    Write-Info "Activated app_env"
} else {
    Write-Warn "app_env not found - using system Python"
}

try {
    python main.py
} finally {
    Cleanup
}
