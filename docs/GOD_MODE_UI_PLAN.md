# ELISA — God Mode UI: Master Plan

> A complete blueprint for transforming the dead WebSocket stub into a living, breathing, cosmic-grade command center. The CLI prints untouched. The UI sees everything.

---

## Table of Contents

- [Design Vision](#design-vision)
- [Core Principles](#core-principles)
- [Architecture Overview](#architecture-overview)
- [Phase 1 — WebSocket Layer Upgrade](#phase-1--websocket-layer-upgrade)
- [Phase 2 — Backend State Emission](#phase-2--backend-state-emission)
- [Phase 3 — The God Mode Frontend](#phase-3--the-god-mode-frontend)
  - [Panel 1: ELISA Neural Core (Avatar)](#panel-1-elisa-neural-core-avatar)
  - [Panel 2: Live Pipeline Flow](#panel-2-live-pipeline-flow)
  - [Panel 3: Conversation Membrane](#panel-3-conversation-membrane)
  - [Panel 4: Log Observatory](#panel-4-log-observatory)
  - [Panel 5: System Vitals](#panel-5-system-vitals)
  - [Panel 6: Universe Background Engine](#panel-6-universe-background-engine)
- [Design System — The Cosmos Theme](#design-system--the-cosmos-theme)
- [WebSocket Message Schema](#websocket-message-schema)
- [File Creation Map](#file-creation-map)
- [Implementation Phases](#implementation-phases)

---

## Design Vision

The UI is a **mission control panel floating in deep space**. Not a dashboard — an observatory. Every pixel has intent. The void between panels is the vacuum of space itself. Data flows like plasma through the pipeline nodes. Logs stream like starlight being decoded in real-time.

When ELISA speaks, the avatar breathes. When she listens, the microphone ring pulses with a sonar heartbeat. When she processes, neural pathways light up across the pipeline. When she's idle, the entire UI breathes at 0.2Hz — a living system at rest.

This is not a monitoring tool. It is a window into an artificial mind.

---

## Core Principles

| Principle                     | Implementation                                                                                                        |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **CLI is King**               | `print()` and `logging` calls are NEVER replaced. A non-invasive interceptor mirrors them to the UI in parallel       |
| **UI is Optional**            | If no browser is connected, the assistant runs identically. WS server is fire-and-forget                              |
| **Zero Lag on Main Pipeline** | All WS writes are queued and processed in a daemon thread. Main pipeline never waits on UI                            |
| **Total Data Capture**        | Every `print()`, every `logging.X()` call, every state change reaches the UI with zero code changes to existing logic |
| **Module-Level Filtering**    | Every log entry is tagged with `source_file`, `function`, and `module` for surgical log filtering in the UI           |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    ASSISTANT PROCESS                      │
│                                                           │
│   main.py → wake_word → stt → nlu_client → tts           │
│        │         │        │        │          │           │
│        └─────────┴────────┴────────┴──────────┘           │
│                          │                                │
│              ElisaUIController (Singleton)                │
│              ┌────────────────────────┐                   │
│              │  message_queue (Q)     │                   │
│              │  PrintInterceptor      │  ← wraps sys.stdout│
│              │  LogHandler            │  ← hooks logging  │
│              │  StateEmitter          │  ← explicit calls │
│              └──────────┬─────────────┘                   │
│                         │ daemon thread                   │
│              WebSocket Server (:8765)                     │
└─────────────────────────│───────────────────────────────┘
                          │ ws://localhost:8765
                    ┌─────▼──────┐
                    │  Browser   │
                    │  UI :35109 │  ← static file server or
                    │            │     open index.html directly
                    └────────────┘
```

**Key insight**: The `PrintInterceptor` wraps `sys.stdout`. When `print()` is called anywhere in the process, the interceptor:

1. Writes the text to the **real stdout** (terminal unchanged)
2. Queues a `{type: "log", source: "<filename>:<lineno>"}` message to the WS queue

This means **zero changes to any existing `print()` call** while the UI receives every single one.

---

## Phase 1 — WebSocket Layer Upgrade

### What's Wrong Today

The existing `websocket.py` is 70% correct but:

- `handle_client` signature uses old `(websocket, path)` — deprecated in `websockets >= 10`
- No message schema versioning
- No ping/keepalive (browser disconnects silently after 60s idle)
- No `PrintInterceptor` — all existing `print()` calls are invisible to UI
- No `LogHandler` — Python `logging` module calls are invisible to UI
- The WS server is commented out in `main.py`

### Upgrade Plan for `assistant/src/session/websocket.py`

**New classes to add:**

```python
class PrintInterceptor(io.TextIOBase):
    """
    Wraps sys.stdout. Every print() call in the process:
    1. Passes through to the original stdout (terminal unchanged)
    2. Queues a log message to ElisaUIController

    Installed via: sys.stdout = PrintInterceptor(sys.stdout, ui_controller)
    """
    def __init__(self, original_stdout, controller):
        self.original = original_stdout
        self.controller = controller
        self._current_frame_info = None

    def write(self, text):
        # Always write to real terminal first
        self.original.write(text)

        # Queue to UI (skip empty newlines)
        if text.strip():
            frame = inspect.currentframe().f_back
            source_file = frame.f_code.co_filename if frame else "unknown"
            source_file = os.path.basename(source_file)
            self.controller._queue_message({
                "type": "log",
                "level": "print",
                "message": text.strip(),
                "module": source_file,
                "source_file": source_file,
                "lineno": frame.f_lineno if frame else 0,
                "timestamp": datetime.now().isoformat()
            })
        return len(text)

    def flush(self):
        self.original.flush()


class ElisaLogHandler(logging.Handler):
    """
    Plugs into Python's logging system. Every logging.info/warning/error call:
    1. Still goes through the normal logging chain (file handlers, console)
    2. Also queues to ElisaUIController

    Installed via: logging.getLogger().addHandler(ElisaLogHandler(ui_controller))
    """
    def emit(self, record):
        self.controller._queue_message({
            "type": "log",
            "level": record.levelname.lower(),
            "message": self.format(record),
            "module": record.module,
            "source_file": os.path.basename(record.pathname),
            "lineno": record.lineno,
            "func": record.funcName,
            "timestamp": datetime.fromtimestamp(record.created).isoformat()
        })
```

**`ElisaUIController` upgrades:**

```python
def install_interceptors(self):
    """
    Call once at startup. Non-invasive — wraps stdout and logging.
    All existing print() and logging.X() calls start flowing to UI automatically.
    """
    # Intercept print()
    sys.stdout = PrintInterceptor(sys.stdout, self)

    # Intercept logging
    handler = ElisaLogHandler(self)
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)

def set_pipeline_stage(self, stage: str, data: dict = None):
    """
    Emit the active pipeline stage.
    Stages: 'idle' | 'wake_word' | 'vad' | 'stt' | 'nlu' | 'logic' | 'tts'
    """

def send_conversation_turn(self, role: str, text: str, metadata: dict = None):
    """
    Emit a conversation turn (user transcript or assistant response).
    role: 'user' | 'assistant'
    metadata: {intent, confidence, entities, action, latency_ms}
    """

def send_metric(self, metric_name: str, value: float, unit: str = ""):
    """
    Emit a numeric metric for sparkline graphs.
    e.g., send_metric("stt_latency_ms", 320, "ms")
    """
```

**WebSocket handshake upgrade:**

On connection, the server sends a "snapshot" of current state so a freshly-opened browser immediately shows the right UI state without waiting for the next event.

```json
{
  "type": "snapshot",
  "state": "idle",
  "pipeline_stage": "wake_word",
  "log_buffer": [...last 200 log entries...],
  "conversation_buffer": [...last 20 turns...],
  "services": { "rasa": "up", "logic": "up", "tts": "up", "duckling": "up" }
}
```

**Keepalive:**

```python
# In handle_client coroutine:
asyncio.ensure_future(self._send_ping(websocket))

async def _send_ping(self, websocket):
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.ping()
        except:
            break
```

---

## Phase 2 — Backend State Emission

### Changes to `assistant/src/main.py`

Uncomment every `ui_logger` call. Replace commented-out blocks with clean calls:

```python
def main():
    # Install interceptors FIRST — before any print() calls
    ui_controller.install_interceptors()
    ui_controller.start_server(host="localhost", port=8765)
    time.sleep(1)

    listen_for_wake_word(assistant_workflow)
```

```python
def assistant_workflow():
    ui_controller.set_pipeline_stage("idle")
    # ... existing print() calls stay exactly as they are ...
    # ... they now also appear in UI automatically ...

    # Add explicit state transitions at key moments:
    ui_controller.set_pipeline_stage("stt")
    command = recognize_speech()

    ui_controller.set_pipeline_stage("nlu")
    responses, continue_conversation = process_command(command)

    # Send conversation turn to UI
    ui_controller.send_conversation_turn("user", command)

    ui_controller.set_pipeline_stage("tts")
    for response in responses:
        ui_controller.send_conversation_turn("assistant", response)
        speak_response(response)

    ui_controller.set_pipeline_stage("idle")
```

### Changes to `wake_word/wake_word_detection.py`

```python
# In the wake word callback:
ui_controller.set_pipeline_stage("wake_word", {"score": score})
```

### Changes to `stt/voice_recognition.py`

```python
# After VAD triggers:
ui_controller.set_pipeline_stage("vad")
# After whisper completes:
ui_controller.set_pipeline_stage("stt", {"transcript": text})
ui_controller.send_metric("stt_latency_ms", elapsed_ms)
```

**Total invasiveness: ~15 lines added across 3 files. Zero existing lines modified.**

---

## Phase 3 — The God Mode Frontend

**Tech Stack:**

- **Vanilla HTML + CSS + JavaScript** (zero build step, open `index.html` directly)
- **Three.js** (r165 via CDN) — cosmic background, particle engine
- **GSAP** (via CDN) — all animations, state transitions
- **CSS Custom Properties** — entire design system driven by variables
- **WebSocket API** — native browser WebSocket, no library needed
- **Chart.js** (via CDN) — sparkline graphs for metrics

**Why vanilla?** The assistant runs locally. No npm, no build step, no Node.js requirement. Drop the `ui/` folder anywhere, double-click `index.html`, done. The WS handles everything.

---

### Panel 1: ELISA Neural Core (Avatar)

**Location:** Center-top of the layout. The emotional heart of the UI.

**Visual Design:**

```
        ╭──────────────────────────────╮
        │    ✦  ✦  ✦  ✦  ✦  ✦  ✦     │
        │  ✦                       ✦  │
        │ ✦   ┌───────────────┐    ✦ │
        │✦    │  ░░░░░░░░░░░  │     ✦│
        │✦    │  ░ E L I S A ░│     ✦│
        │✦    │  ░░░░░░░░░░░  │     ✦│
        │ ✦   └───────────────┘    ✦ │
        │  ✦                       ✦  │
        │    ✦  ✦  ✦  ✦  ✦  ✦  ✦     │
        ╰──────────────────────────────╯
          [ IDLE — LISTENING FOR WAKE WORD ]
```

**Animated states:**

| State             | Visual                                                                       |
| ----------------- | ---------------------------------------------------------------------------- |
| `idle`            | Slow breathing glow (2s ease in/out), outer ring pulses cyan at 0.2Hz        |
| `wake_word`       | Ring explodes outward in a shockwave, color jumps to electric blue           |
| `vad` / listening | Multiple concentric sonar rings radiate outward, microphone icon glows green |
| `stt`             | Waveform visualizer appears below the orb, showing simulated audio spectrum  |
| `nlu`             | Neural network nodes flash inside the orb — connected dots firing            |
| `tts` / speaking  | Orb emits sound wave ripples, color shifts to violet, lips animation         |
| `error`           | Red pulse, orb cracks with fracture lines that heal after 2s                 |

**Implementation:**

- SVG-based orb with CSS `filter: blur()` drop-shadow glow
- GSAP `timeline()` for state-specific animations
- `requestAnimationFrame` loop for the idle breathing sine wave
- State machine driven by `state_change` WS messages

---

### Panel 2: Live Pipeline Flow

**Location:** Below the avatar, full width.

```
  [Wake Word] ──→ [VAD] ──→ [STT] ──→ [NLU] ──→ [Logic] ──→ [TTS] ──→ [🔊]
       ●              ○         ○         ○          ○          ○
   ACTIVE         waiting    waiting   waiting    waiting    waiting
```

**Design:**

- 7 nodes connected by animated dashed lines (CSS `stroke-dashoffset` animation)
- Active node: glowing filled circle with a bright halo, white label
- Completed nodes: filled with accent color, checkmark icon
- Waiting nodes: outline only, dim, slightly transparent
- Between active → next node: particles travel along the connector line (SVG `animateMotion`)
- Each node shows tooltip on hover: last seen data (e.g., STT node shows last transcript)

**Data shown per node:**

| Node      | Tooltip Data                             |
| --------- | ---------------------------------------- |
| Wake Word | Last score (e.g., 0.94), cooldown status |
| VAD       | Recording duration, voice frame %        |
| STT       | Last transcript, model used, latency     |
| NLU       | Intent, confidence, entities             |
| Logic     | Action called, response code             |
| TTS       | Characters spoken, audio duration        |

---

### Panel 3: Conversation Membrane

**Location:** Right column, ~40% of viewport width.

**Design concept:** The conversation exists inside a glass membrane — a frosted panel floating in space. User messages appear on the right, ELISA's responses on the left, like signals crossing the void.

```
┌─────────────────────────────────────────┐
│  ◈  CONVERSATION FEED                   │
│─────────────────────────────────────────│
│                    [ remind me at 5pm ] │  ← user bubble, right
│                    14:32:01 · user      │
│                                         │
│ [ I'll set a reminder for 5 PM today ]  │  ← elisa bubble, left
│ intent: set_reminder · 0.97 · 12ms      │  ← metadata pill row
│   entity: time=17:00                    │
│   action: REMIND_SET                    │
│ 14:32:03 · elisa                        │
│                                         │
│           ─────── now ────────          │  ← temporal divider
│                                         │
│  [ typing indicator if processing ]     │
└─────────────────────────────────────────┘
```

**Features:**

- Glassmorphism panel (`backdrop-filter: blur(12px)`, subtle border glow)
- Each turn animates in from outside the panel edge
- User bubbles: right-aligned, cool blue tint
- ELISA bubbles: left-aligned, violet/purple tint, with neural circuit pattern in background
- Metadata row collapses by default, expands on hover
- Confidence bar visualized as a thin colored line under the intent tag (green > 0.85, yellow > 0.6, red below)
- Entities rendered as colored chips (time=cyan, app=orange, query=magenta)
- Copy button per message (hidden until hover)
- Auto-scroll to bottom, with a "jump to live" button if user has scrolled up
- Timestamp displayed in relative form ("2s ago") switching to absolute after 1 minute

---

### Panel 4: Log Observatory

**Location:** Bottom strip, full width. Can be expanded to take 50% of viewport.

**This is the most complex panel and the one that makes developers lose their minds.**

#### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ◈  LOG OBSERVATORY                                    [⚙] [⛶] [✕]      │
│──────────────────────────────────────────────────────────────────────────│
│  LEVELS: [✓ DEBUG] [✓ INFO] [✓ WARN] [✓ ERROR] [✓ PRINT]               │
│  FILES:  [All ▼] main.py  wake_word_detection.py  rasa_integration.py    │
│          stt_voice_recognition.py  websocket.py  text_to_speech.py       │
│  SEARCH: [                    🔍  ] [Regex ○] [Case ○] [X Clear]        │
│  SPEED:  [⏸] [▶1x] [▶5x] [Live▶▶]         TAIL: [✓] [100 ✕]           │
│──────────────────────────────────────────────────────────────────────────│
│ 14:32:01.234 │ PRINT │ main.py:47       │ Starting wake word detection…  │
│ 14:32:01.891 │ INFO  │ websocket.py:62  │ Client connected. Total: 1     │
│ 14:32:04.112 │ PRINT │ stt:voice_rec:89 │ Command recognized: 'remind…'  │
│ 14:32:04.203 │ DEBUG │ rasa_integr:44   │ Sending to Rasa: {sender:…}    │
│ 14:32:04.891 │ PRINT │ main.py:112      │ Rasa processed command, got 1  │
│ 14:32:04.892 │ WARN  │ tts:tts.py:34    │ Retrying TTS with fallback…    │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 4.2 Features

**File-based filtering (the killer feature):**

- Every log message is tagged with `source_file` and `lineno`
- The file selector shows ALL unique files that have ever emitted a log
- Selecting a single file shows ONLY logs from that file
- Multi-select supported (Ctrl+click)
- File filter chips are color-coded — each file gets a unique hue from a deterministic hash

**Level filtering:**

- Toggle each level independently
- `PRINT` is a special level — captures raw `print()` calls
- Levels have distinct left-border colors: DEBUG=slate, INFO=cyan, WARN=amber, ERROR=red, PRINT=white

**Search:**

- Full-text regex search with live highlighting of matched text within log entries
- Regex mode toggle
- Case sensitivity toggle
- Search highlights remain visible even when new logs stream in

**Time controls:**

- Live mode: logs stream in as they arrive, auto-tail
- Pause: stops new logs from rendering (buffer continues filling in background)
- Speed playback: re-plays buffered logs at 1x, 5x speed (useful after pausing)
- "Jump to Now" button when paused

**Log entry detail:**

- Click any log line to expand it into a full-width detail view showing:
  - Full message (untruncated)
  - File + line + function name
  - Stack frame context (if available)
  - Raw JSON payload
  - Copy JSON button

**Export:**

- Download filtered logs as `.jsonl` file
- Copy last N lines to clipboard

**Visual polish:**

- Monospace font (JetBrains Mono or similar via Google Fonts CDN)
- Even rows: slightly lighter background
- New log entries flash-in with a brief left-border pulse animation (GSAP)
- Error lines have a subtle red tint across the full row
- The log panel emits a faint scanline effect overlay (CSS gradient repeat)

#### 4.3 Multi-View Modes

Toggle between views using icons in the top-right:

| Icon | Mode     | Description                                           |
| ---- | -------- | ----------------------------------------------------- |
| ≡    | Stream   | Default scrolling log stream                          |
| ⊞    | Grid     | Side-by-side panels, one per module/file              |
| 🔥   | Heatmap  | Time-bucketed heatmap showing log frequency per file  |
| ◷    | Timeline | Horizontal timeline showing log events on a time axis |

**Grid mode** is the "I need to watch two modules at once" mode. You pick 2–4 files and each gets its own scrolling log column. Feels like a mission control console.

**Heatmap mode** is the "something is spamming logs" debugging mode. 60-second rolling window, 1-second buckets, each cell colored by volume and error rate.

---

### Panel 5: System Vitals

**Location:** Left column, vertical strip.

**Design:** Thin vertical panel, dark glass. Data points float like satellite telemetry.

```
┌──────────────────────┐
│ ◈ SYSTEM VITALS      │
│──────────────────────│
│ RASA      ●  12ms    │
│ LOGIC     ●   4ms    │
│ TTS       ●  180ms   │
│ DUCKLING  ●   3ms    │
│ WS        ●  live    │
│──────────────────────│
│ LATENCY HISTORY      │
│  STT  ▁▂▃▅▄▂▁▃▅▇▅▄  │
│  NLU  ▂▂▂▂▂▁▂▂▂▂▂▂  │
│  TTS  ▄▃▄▅▄▄▃▅▄▃▄▃  │
│──────────────────────│
│ SESSIONS TODAY:  12  │
│ COMMANDS TODAY:  47  │
│ AVG LATENCY:  820ms  │
│ ERRORS TODAY:    2   │
│──────────────────────│
│ UPTIME: 03:42:11     │
│ LAST CMD: 2m ago     │
└──────────────────────┘
```

**Sparklines:** Canvas-based mini-charts (60 data points, last 5 minutes). Color gradient from green (fast) to red (slow). Drawn with raw `<canvas>` 2D API, no library needed.

**Service indicators:**

- Green dot = up (last health check passed)
- Amber dot = degraded (high latency)
- Red dot = down (last HTTP check failed)
- Each service is pinged from the browser via `fetch()` every 10s (simple health endpoints already exist on each service)

---

### Panel 6: Universe Background Engine

**This is what makes someone walk into the room and say "what is THAT?"**

**Three.js cosmic background (runs in `<canvas id="cosmos">` behind all panels):**

**Layer 1 — Starfield**

- 8,000 stars distributed in a sphere
- Three size classes: dim background stars (tiny, grey), mid-field stars (small, white), foreground stars (slightly larger, slight blue tint)
- Slow parallax drift as mouse moves (0.02x mouse delta, interpolated with lerp)
- Random twinkling: each frame, 0.1% of stars adjust opacity slightly

**Layer 2 — Nebula Clouds**

- 6 overlapping `THREE.Points` clouds with custom `ShaderMaterial`
- Colors: deep violet, midnight blue, dark magenta — all very desaturated
- Very slow rotation (full rotation every 5 minutes)
- Volumetric fake depth via layered alpha blending

**Layer 3 — Data Stream Particles**

- When a log fires, 3–5 bright particles emit from the log panel edge and arc toward the avatar
- When ELISA speaks, particles stream outward from the avatar
- When wake word fires, a shockwave ring expands from the avatar
- Particles use `THREE.BufferGeometry` for performance, pooled and recycled

**Layer 4 — Aurora Veil**

- A procedural wave of color animates slowly across the bottom 30% of the screen
- Uses a vertex-displaced `PlaneGeometry` with a time-varying `ShaderMaterial`
- Colors cycle very slowly: cyan → violet → magenta → back
- Opacity: 0.06 — barely visible but present

**Performance guardrails:**

- `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))` — no 4K texture waste
- `renderer.setAnimationLoop()` replaces `requestAnimationFrame` for proper pause behavior
- All particle systems use `BufferGeometry` — no geometry per particle
- Aurora shader uses `mediump float` precision on mobile

---

## Design System — The Cosmos Theme

### Color Palette

```css
:root {
  /* Void — the dark */
  --void-900: #020408;
  --void-800: #060d14;
  --void-700: #0a1520;
  --void-600: #0f1f30;

  /* Plasma — the primary accent */
  --plasma-500: #00f5ff; /* electric cyan */
  --plasma-400: #33f7ff;
  --plasma-glow: rgba(0, 245, 255, 0.3);

  /* Nebula — secondary accent */
  --nebula-500: #b44fff; /* deep violet */
  --nebula-400: #c87aff;
  --nebula-glow: rgba(180, 79, 255, 0.25);

  /* Pulsar — tertiary / danger */
  --pulsar-500: #ff3b7a; /* hot magenta */
  --pulsar-glow: rgba(255, 59, 122, 0.25);

  /* Quasar — success / safe */
  --quasar-500: #39ff95; /* neon green */
  --quasar-glow: rgba(57, 255, 149, 0.2);

  /* Stellar — neutral text */
  --stellar-100: #e8f4ff;
  --stellar-300: #9ab4cc;
  --stellar-500: #5a7a96;
  --stellar-700: #2a3f52;

  /* Glass — panel surfaces */
  --glass-surface: rgba(6, 20, 38, 0.72);
  --glass-border: rgba(0, 245, 255, 0.08);
  --glass-border-hover: rgba(0, 245, 255, 0.22);
}
```

### Typography

```css
/* Import via CDN */
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap");

:root {
  /* Display: panel headers, state labels */
  --font-display: "Space Grotesk", sans-serif;

  /* Data: logs, metrics, code */
  --font-mono: "JetBrains Mono", monospace;
}
```

### Glass Panel Mixin

```css
.glass-panel {
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--glass-border),
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition:
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

.glass-panel:hover {
  border-color: var(--glass-border-hover);
  box-shadow:
    0 0 0 1px var(--glass-border-hover),
    0 8px 40px rgba(0, 0, 0, 0.5),
    0 0 24px var(--plasma-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
```

### Glow Text

```css
.glow-plasma {
  color: var(--plasma-500);
  text-shadow:
    0 0 8px var(--plasma-glow),
    0 0 24px var(--plasma-glow);
}
.glow-nebula {
  color: var(--nebula-500);
  text-shadow:
    0 0 8px var(--nebula-glow),
    0 0 24px var(--nebula-glow);
}
```

### Scanline Overlay

```css
.scanlines::after {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
  pointer-events: none;
  z-index: 1000;
}
```

---

## WebSocket Message Schema

All messages follow a typed envelope:

```typescript
interface WSMessage {
  type: MessageType;
  timestamp: string; // ISO 8601
  [key: string]: any;
}

type MessageType =
  | "snapshot" // initial state dump on connect
  | "state_change" // assistant FSM state change
  | "pipeline_stage" // which pipeline node is active
  | "log" // a log/print entry
  | "conversation_turn" // user transcript or assistant response
  | "metric" // numeric metric (latency, etc)
  | "service_status" // a backend service went up/down
  | "ping" // keepalive
  | "pong"; // keepalive response
```

### `snapshot` (sent on new connection)

```json
{
  "type": "snapshot",
  "timestamp": "2026-04-26T14:32:01.234Z",
  "state": "idle",
  "pipeline_stage": "wake_word",
  "log_buffer": [],
  "conversation_buffer": [],
  "services": {
    "rasa": { "status": "up", "latency_ms": 12 },
    "logic": { "status": "up", "latency_ms": 4 },
    "tts": { "status": "up", "latency_ms": 180 },
    "duckling": { "status": "up", "latency_ms": 3 }
  },
  "uptime_seconds": 13331
}
```

### `pipeline_stage`

```json
{
  "type": "pipeline_stage",
  "timestamp": "...",
  "stage": "stt",
  "data": {
    "transcript": "remind me at 5pm",
    "latency_ms": 312
  }
}
```

### `log`

```json
{
  "type": "log",
  "timestamp": "...",
  "level": "print",
  "message": "Command recognized: 'remind me at 5pm'",
  "module": "main",
  "source_file": "main.py",
  "lineno": 89,
  "func": "assistant_workflow"
}
```

### `conversation_turn`

```json
{
  "type": "conversation_turn",
  "timestamp": "...",
  "role": "user",
  "text": "remind me at 5pm",
  "metadata": null
}
```

```json
{
  "type": "conversation_turn",
  "timestamp": "...",
  "role": "assistant",
  "text": "I'll set a reminder for 5 PM today.",
  "metadata": {
    "intent": "set_reminder",
    "confidence": 0.97,
    "entities": [{ "entity": "time", "value": "17:00:00" }],
    "action": "REMIND_SET",
    "latency_ms": 780
  }
}
```

### `metric`

```json
{
  "type": "metric",
  "timestamp": "...",
  "name": "stt_latency_ms",
  "value": 312,
  "unit": "ms"
}
```

---

## File Creation Map

```
ui/
├── index.html              ← single entry point, open in browser
├── css/
│   ├── reset.css           ← minimal CSS reset
│   ├── design-system.css   ← all custom properties, typography, glass panels
│   ├── layout.css          ← grid layout, panel positioning
│   ├── panels/
│   │   ├── avatar.css      ← neural core panel
│   │   ├── pipeline.css    ← pipeline flow panel
│   │   ├── conversation.css← conversation membrane
│   │   ├── logs.css        ← log observatory
│   │   └── vitals.css      ← system vitals
│   └── animations.css      ← all keyframe animations
├── js/
│   ├── cosmos.js           ← Three.js universe background engine
│   ├── websocket.js        ← WS client, reconnect logic, message router
│   ├── store.js            ← in-memory state (last 500 logs, 50 turns, metrics)
│   ├── panels/
│   │   ├── avatar.js       ← neural core animations (GSAP state machine)
│   │   ├── pipeline.js     ← pipeline node animations
│   │   ├── conversation.js ← conversation feed renderer
│   │   ├── logs.js         ← log observatory (filter, search, views)
│   │   └── vitals.js       ← sparklines, service polling
│   └── utils.js            ← helpers (lerp, debounce, color hash for files)
└── assets/
    └── sounds/
        └── connect.mp3     ← subtle chime when WS connects (optional)
```

**`assistant/src/session/websocket.py` — full rewrite with:**

- `PrintInterceptor` class
- `ElisaLogHandler` class
- `install_interceptors()` method
- Cleaned-up `handle_client` (new `websockets` API)
- `send_conversation_turn()`, `set_pipeline_stage()`, `send_metric()` methods
- Ping/keepalive loop
- Ring buffer for snapshot (last 200 logs, last 20 turns)

**`assistant/src/main.py` — minimal changes:**

- Add `ui_controller.install_interceptors()` and `ui_controller.start_server()` to `main()`
- Add `set_pipeline_stage()` calls at state transitions
- Add `send_conversation_turn()` calls for user/assistant turns
- All existing `print()` calls: **unchanged**

---

## Implementation Phases

### Phase A — WebSocket Hardening (Day 1–2)

1. Rewrite `websocket.py` with `PrintInterceptor`, `ElisaLogHandler`, new schema
2. Add `install_interceptors()` and ring buffer
3. Uncomment WS server start in `main.py`
4. Add pipeline stage + conversation turn emissions
5. Test: run assistant, connect via `wscat`, verify all messages flow

**Deliverable:** Every `print()` in the codebase is now visible on the WS stream. Zero CLI changes.

### Phase B — UI Shell (Day 2–3)

1. Create `ui/index.html` with layout grid
2. Create `ui/css/design-system.css` with full cosmos palette
3. Create `ui/js/websocket.js` with reconnect logic and message router
4. Create `ui/js/store.js` with ring buffers
5. Render raw JSON in each panel area to confirm data flow

**Deliverable:** A bare, dark UI that shows real data in plain text. WebSocket confirmed working end-to-end.

### Phase C — Cosmos Background (Day 3–4)

1. Create `ui/js/cosmos.js` with Three.js starfield + nebula
2. Add aurora shader
3. Add particle emission events (log fires → particles arc to avatar)
4. Performance check: must hold 60fps with all panels open

**Deliverable:** Opening the UI feels like floating in space before any data shows up.

### Phase D — Panel Implementation (Day 4–8)

1. **Avatar panel**: GSAP state machine for all 7 states
2. **Pipeline panel**: SVG nodes with particle connectors
3. **Conversation panel**: bubble renderer with metadata expansion
4. **Vitals panel**: sparklines, service health polling
5. **Log Observatory**: stream render, level filter, file filter chips, search
6. **Log Observatory multi-view**: Grid and Heatmap modes

**Deliverable:** Full functional UI. Every panel live.

### Phase E — Polish Pass (Day 8–10)

1. Micro-interactions: magnetic buttons, custom cursor
2. Entry sequence: preloader that reveals the cosmos with a split-door animation
3. Sound design: subtle chimes on state changes (optional, toggleable)
4. Responsive layout: graceful collapse at 1280px width
5. Accessibility: `prefers-reduced-motion` guards on all continuous animations
6. Performance audit: verify no layout thrash, no 4K pixel ratio waste

**Deliverable:** Something that makes you go "I built this?"

---

## God-Level Bonus Ideas

These are not in the initial scope but are in the DNA of where this goes:

| Idea                  | Description                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Voice Replay**      | Click any conversation turn → hear the TTS audio replayed from cache                                                                                   |
| **Intent Inspector**  | Click an intent label in the conversation feed → see all training examples for that intent from `nlu.yml` inline                                       |
| **Live STT Waveform** | During recording, stream VAD audio frame energy values over WS → live waveform in the avatar panel                                                     |
| **Annotation Mode**   | Right-click any conversation turn → "Mark as incorrect" → opens a mini-form to assign correct intent → writes correction to a `corrections.jsonl` file |
| **Trace Waterfall**   | Each conversation turn has a collapsible timing waterfall: Wake→VAD (Xms), VAD→STT (Xms), STT→NLU (Xms), NLU→Logic (Xms), Logic→TTS (Xms)              |
| **Screenshot Mode**   | A "cinematic" button that hides all debug panels and only shows the avatar + conversation, fullscreen. Perfect for demos.                              |
| **Theme Variants**    | Cosmos (default), Solar (warm gold/orange), Void (pure black/white), Terminal (green-on-black) — all driven by CSS custom property swaps               |
| **Multi-Instance**    | The WS server supports multiple browser tabs simultaneously. Use `BroadcastChannel` to sync UI state between tabs                                      |
| **CLI Companion**     | A `ui_status.py` script that connects to the WS and renders a Rich-powered terminal dashboard — god mode for SSH sessions                              |

---

_This plan is the foundation. Once implemented, ELISA's UI will not look like a project. It will look like a product._
