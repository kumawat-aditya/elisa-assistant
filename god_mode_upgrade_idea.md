## 1. System Analysis

### What's Working Well

- Clean layer separation (Assistant / NLU / Logic) with no shared imports
- Unidirectional data flow prevents circular dependencies
- Multi-backend audio fallback chain is pragmatic
- APScheduler + SQLite for reminders is solid
- Duckling for deterministic time parsing is the right call

### Architectural Problems (Honest Assessment)

**[CRITICAL] Rasa is the wrong tool at this scale.**
Rasa is a 500MB+ conversational AI framework built for enterprise chatbots. You're using it as a glorified intent router. Every voice command incurs: tokenization → featurization → DIET classification → entity extraction → tracker state update → action server HTTP roundtrip. That's 300–700ms of overhead before your logic even runs. Rasa's tracker store, slot filling, and dialogue management are also barely used — `sender` is hardcoded to `"user1"`.

**[CRITICAL] The WebSocket / UI is dead code.**
Every single `ui_logger` and `ui_controller` call in main.py is commented out. The WebSocket server starts but no state ever flows through it. The "UI" is an orphaned HTML file with no live connection to the system.

**[HIGH] String-based action dispatch is a maintenance trap.**
`if action == "OPEN_APP": ... if action == "SEARCH_BROWSER": ...` — no schema, no types, no discoverability. Adding a capability means touching actions.py (NLU layer), `logic_integration.py` (bridge), logic.py (router), and a service file. Four files for one feature.

**[HIGH] Synchronous serial pipeline maximizes latency.**
Wake Word → VAD → STT → HTTP → Rasa → HTTP → Actions → HTTP → Logic → HTTP → TTS → Audio. Every step is blocking. On a slow day this pipeline easily exceeds 3–4 seconds end-to-end.

**[MEDIUM] Subprocess STT adds process overhead.**
`whisper-cli` is called as a subprocess per recognition cycle. The model is loaded and unloaded every time. A persistent in-process Whisper (via `whisper-cpp-python` or `faster-whisper`) would eliminate this.

**[MEDIUM] Shared mutable audio file is a race condition.**
`shared/audio/temporary/response.wav` is overwritten per response. Fine for single-user, but it's a global side effect that will cause issues the moment you add background workers or parallel responses.

**[LOW] Three virtual environments** for a single-machine local assistant adds setup friction with minimal isolation benefit. The layers don't need process-level Python package isolation from each other.

---

## 2. Expanded Feature Space

### A. Core Intelligence Upgrades

**Memory System (4 tiers)**

- **Working memory**: In-process dict of the last N turns. Zero latency. Not persisted.
- **Session memory**: SQLite rows keyed by `session_id`. Survives process restarts. Holds conversation context, user preferences from current session.
- **Long-term memory (episodic)**: ChromaDB or SQLite-vec. Stores facts extracted from past conversations: "user prefers Celsius", "mom's number is...", "remind about gym on Mondays". Retrieved by semantic similarity at query time.
- **Procedural memory**: Learned command patterns — if the user corrects ELISA three times for the same misinterpretation, the correction is stored as a rule override.

**Multi-step Reasoning / Planning Engine**
Replace the linear intent→action pipeline with an LLM-backed planner that decomposes complex requests into sub-tasks. "Open Chrome, search for today's weather in Tokyo, and remind me to check the forecast at 9am" becomes a plan graph executed sequentially. Local models (Ollama + Llama 3.2, Mistral Nemo) handle planning entirely offline.

**Autonomous Task Execution**
A task queue where ELISA can execute multi-step background jobs. "Download that PDF and summarize it for me" triggers a worker that: fetches URL → saves file → extracts text → runs local summarizer → queues TTS response. No blocking the main voice loop.

**Tool/Plugin Registry**
Replace the `if action == "OPEN_APP"` dispatch table with a typed capability registry:

```python
@capability("open_app", params={"app_name": str})
def open_application(app_name: str) -> CapabilityResult: ...
```

Capabilities self-register, are discoverable at runtime, and appear automatically in the planner's tool inventory. New capabilities = new decorated functions, zero changes elsewhere.

---

### B. Developer Control Layer

**Structured Observability**
Replace `print()` with structured JSON logs (via `structlog`) that include: `session_id`, `pipeline_stage`, `latency_ms`, `input_text`, `intent`, `confidence`, `entities`, `action`, `response_text`. Ship logs to a local file rotated daily. The command center reads these live.

**Distributed Tracing**
Each voice request gets a `trace_id`. Every service call (STT → NLU → Logic → TTS) tags itself with the same `trace_id`. You can reconstruct the full latency breakdown for any past request. Use OpenTelemetry with a local Jaeger collector (single Docker container).

**Replay System**
Every request is serialized to a `replay_log.jsonl` file: `{trace_id, timestamp, raw_audio_path, transcript, intent, entities, action, response}`. A `replay_cli.py` tool re-feeds any past `trace_id` through the pipeline from any stage (e.g., replay from NLU with corrected transcript, skipping STT). Invaluable for debugging misclassifications.

**Simulation / Test Mode**
A `--simulate` flag on the assistant layer bypasses microphone and TTS. Accepts text input via stdin or a test fixture file. The pipeline runs identically to production but I/O is mocked. Test suites can assert on intent classification, entity extraction, action called, and response text without any audio hardware.

**Confidence Thresholds + Fallback Inspector**
When NLU confidence < threshold, instead of guessing, ELISA asks for clarification and logs the low-confidence event. The command center surfaces a "review queue" of all requests where ELISA wasn't sure — you can label them correct/incorrect to build a correction dataset.

---

### C. Command Center UI (Expanded)

Forget the current WebSocket HTML file. Build a proper **local web application** — a genuine JARVIS-style command center. This is the most high-value surface for the entire system.

**Architecture shift**: Instead of WebSocket push-only from assistant, use **Server-Sent Events (SSE)** for real-time state streaming and a **REST API** for control actions. Much simpler, no connection management.

**Panels:**

**Live Neural Flow Panel**
Animated pipeline visualization showing the active stage in real-time: `[Wake Word] → [VAD] → [STT] → [NLU] → [Logic] → [TTS]`. Each stage lights up when active, shows the data flowing through it (e.g., the transcript appears under the STT stage as it's produced). This is what makes it feel like JARVIS.

**Conversation Feed**
A scrolling feed of all voice interactions. Each entry shows: timestamp, transcript, detected intent + confidence bar, entities as colored chips, action executed, response text, total latency. Click any entry to expand the full trace.

**System Health Panel**
Real-time service status (NLU server, Logic API, TTS, Duckling). Shows latency per service with sparkline graphs. CPU/RAM usage for each service process. STT model load time. Audio device status.

**The Forge (NLU Training Control)**
This is the crown jewel. A panel where you can:

- See all intents and their training example counts
- View recent low-confidence classifications in a review queue
- Click a misclassified utterance → assign the correct intent → it writes to `nlu.yml`
- One-click "Retrain" button that triggers `rasa train` in the background with a live log stream
- Diff view showing what changed since the last training run
- Model performance chart over time (accuracy on test set per train run)

**Memory Explorer**
Browse all stored facts in long-term memory. Search by semantic query. Delete individual entries. See which memories were retrieved for the last N requests and whether they were used.

**Task Queue Monitor**
List of all background tasks (running, queued, completed, failed). Retry failed tasks. Cancel running ones. See the full execution log for each task.

**Reminder Control Panel**
Visual calendar + list view of all scheduled reminders. Edit/delete/snooze. Create reminders directly from the UI.

**Plugin Manager**
List all registered capabilities with their parameter schemas, last used timestamp, and call count. Enable/disable capabilities. Install new plugin files by dropping a Python file into a `plugins/` directory — the system hot-reloads without restart.

**Tech stack**: SvelteKit + TailwindCSS + shadcn-svelte. Served locally by a FastAPI route in the Logic layer (or a dedicated `ui_server.py`). Feels fast, looks modern, 0 cloud dependency.

---

### D. System-Level Features

**Event Bus (Replace Direct HTTP Calls)**
The current chain `Assistant → [HTTP] → Rasa → [HTTP] → Actions → [HTTP] → Logic` is three synchronous blocking HTTP calls. Replace with an internal event bus (Redis Streams, or pure Python with `asyncio.Queue` for single-machine deployment). Events flow: `InputEvent → NLUEvent → ActionEvent → ResponseEvent`. Each service subscribes to the events it cares about. This enables parallel processing and non-blocking I/O.

**Background Worker Pool**
`asyncio`-based worker pool that processes heavy tasks without blocking the voice loop. Workers handle: reminder notifications, scheduled summaries, file operations, web scraping. Results are posted back as events.

**Local Automation Engine**
Go beyond `pynput` keyboard injection. Build a proper automation layer using `pyautogui` + `subprocess` + D-Bus (Linux) / AppleScript (macOS). Capabilities: screenshot + describe (vision model), window focus management, clipboard read/write, file system operations (create, move, search), notification dispatch.

**Plugin Ecosystem**

```
plugins/
  spotify_control.py     # @capability("play_music")
  obsidian_notes.py      # @capability("create_note")
  calendar_sync.py       # @capability("check_calendar")
  home_assistant.py      # @capability("control_device")
```

Each plugin file is a self-contained Python module that registers capabilities on import. The system scans `plugins/` on startup and on file change (watchdog). No restart required.

**Multi-Agent Architecture (Advanced)**
Multiple specialized sub-agents run as async workers: a `ResearchAgent` that can browse the web and summarize, a `CodeAgent` that can read/write files and run scripts, a `CalendarAgent` that manages scheduling conflicts. The main planner delegates to the appropriate agent based on task type. Agents communicate through the event bus.

---

### E. Experimental / "Crazy" Ideas

**Self-Correcting NLU Pipeline**
When ELISA acts on a command and the user immediately says "no, that's wrong" or "stop" — this is an implicit negative label. Capture these correction events, build a local dataset of `(utterance, wrong_intent, correct_intent)` tuples. Weekly, a background job fine-tunes the NLU model on accumulated corrections. ELISA literally gets better at understanding you over time.

**Voice Personality Switching**
Multiple TTS voice profiles (Coqui supports multiple models/speakers). Profile switching via command: "ELISA, switch to professional mode". Each profile has: different Coqui speaker ID, different response template style (terse vs verbose), different wake word sensitivity threshold.

**Behavioral Adaptation Engine**
Track `(time_of_day, day_of_week, command_category, frequency)` over 30 days. Pattern mine to predict likely next action. At 8am on weekdays, ELISA proactively says "Good morning — traffic to downtown is light today" because you've opened a maps search at that time 20 of the last 25 weekdays.

**Contextual Awareness Across Sessions**
Cross-session entity memory: "the meeting" always refers to the last calendar event discussed. "him/her/they" resolve to the last named person mentioned regardless of session boundary. This requires named-entity coreference resolution, implementable with a small local spaCy component.

**LLM Fallback with Local Model**
When NLU confidence is below threshold AND the intent doesn't match any known pattern, route to a local Ollama model with a system prompt describing ELISA's capabilities and the full conversation context. The LLM either handles the request directly or maps it to a known capability. Zero cloud calls.

**"Dream Mode" — Nightly Knowledge Consolidation**
While the system is idle, a background process reviews the day's interactions, extracts factual assertions (via local LLM), deduplicates against existing memory, and promotes high-confidence facts to long-term memory. Like a brain consolidating memories during sleep.

**Proactive Interrupt System**
ELISA monitors system state in the background (calendar, reminders, weather, news RSS) and can interrupt with time-sensitive information. "Your 3pm meeting starts in 10 minutes and traffic is heavier than usual." Implemented as a priority event that pre-empts the idle listening loop.

---

## 3. Prioritized Roadmap

### Phase 1 — Foundation Rebuild (Do This First)

**Goal: Clean architecture, working observability, new UI shell. Remove all dead code.**

| #   | Task                                                        | Why                                                                                                                                                                                                                                                                                                  |
| --- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Replace Rasa with a lightweight NLU stack                   | Rasa is the #1 latency and complexity source. Replace with: `faster-whisper` (in-process STT) + `sentence-transformers` (intent matching via cosine similarity on labeled embeddings) + `Duckling` (keep for time parsing). Drops 500ms+ latency, eliminates 3 services, removes Actions server hop. |
| 2   | Replace string dispatch with typed capability registry      | One decorator, zero maintenance overhead for new features.                                                                                                                                                                                                                                           |
| 3   | Add `structlog` structured logging across all layers        | Foundation for everything observability-related.                                                                                                                                                                                                                                                     |
| 4   | Replace WebSocket with SSE + REST control API               | Simpler, more reliable, enough for the Command Center.                                                                                                                                                                                                                                               |
| 5   | Build Command Center MVP (SvelteKit)                        | Live pipeline visualization, conversation feed, system health.                                                                                                                                                                                                                                       |
| 6   | Implement session memory (SQLite)                           | Per-session context for basic pronoun + entity resolution.                                                                                                                                                                                                                                           |
| 7   | Replace subprocess Whisper with `faster-whisper` in-process | 2–3x speed improvement, no process overhead.                                                                                                                                                                                                                                                         |
| 8   | Add simulation/test mode                                    | CI-testable pipeline from day one.                                                                                                                                                                                                                                                                   |

**Estimated scope: 3–4 weeks of focused work.**

---

### Phase 2 — Intelligence + Control

**Goal: Memory system, planning engine, The Forge, plugin ecosystem.**

| #   | Task                                         | Why                                                              |
| --- | -------------------------------------------- | ---------------------------------------------------------------- |
| 1   | Long-term memory with ChromaDB               | Persistent user facts, preference learning.                      |
| 2   | Ollama LLM integration (fallback + planning) | Handles ambiguous requests, enables multi-step planning.         |
| 3   | Plugin capability registry + hot reload      | Extensibility without core code changes.                         |
| 4   | The Forge panel (NLU training control)       | Closes the feedback loop — ELISA improves from your corrections. |
| 5   | Replay system                                | Debug past conversations in seconds.                             |
| 6   | Background worker pool                       | Non-blocking task execution.                                     |
| 7   | Local automation engine upgrade              | Beyond keyboard injection — window management, clipboard, files. |
| 8   | Multi-level log viewer in Command Center     | Full trace inspection in the UI.                                 |

**Estimated scope: 4–6 weeks.**

---

### Phase 3 — Advanced Systems

**Goal: Self-improvement, agents, behavioral adaptation.**

| #   | Task                                   | Why                                                            |
| --- | -------------------------------------- | -------------------------------------------------------------- |
| 1   | Self-correcting NLU from user feedback | ELISA improves itself from use.                                |
| 2   | Multi-agent architecture               | Delegate to specialized sub-agents (research, code, calendar). |
| 3   | Behavioral adaptation engine           | Proactive suggestions based on usage patterns.                 |
| 4   | Cross-session coreference resolution   | "Him/her/they/it" resolved across session boundaries.          |
| 5   | Dream mode (nightly consolidation)     | Long-term memory quality improvements automatically.           |
| 6   | Voice personality switching            | Multiple personas, configurable behavior modes.                |
| 7   | Proactive interrupt system             | Calendar-aware, traffic-aware, context-aware interruptions.    |

---

## 4. Proposed Clean Architecture

### Service Map (Phase 1 Target)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │  Wake Word       │    │  VAD + Faster-  │    │  Text Input    │  │
│  │  (OpenWakeWord)  │───▶│  Whisper (STT)  │    │  (CLI / UI)    │  │
│  └─────────────────┘    └────────┬────────┘    └───────┬────────┘  │
└────────────────────────────────────┼────────────────────┼────────────┘
                                     │ InputEvent          │
                                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CORE PROCESS (single process)               │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐   │
│   │                    Event Bus (asyncio)                      │   │
│   └──┬──────────────────┬────────────────────┬─────────────────┘   │
│      │ InputEvent        │ ActionEvent         │ ResponseEvent       │
│      ▼                   ▼                     ▼                     │
│   ┌──────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│   │  NLU     │    │  Planner       │    │  Response Builder    │   │
│   │  Engine  │───▶│  (LLM-backed   │───▶│  (template + TTS)   │   │
│   │  (local) │    │  or rule-based)│    │                      │   │
│   └──────────┘    └───────┬────────┘    └──────────────────────┘   │
│                            │ CapabilityCall                          │
│                            ▼                                         │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                 Capability Registry                          │  │
│   │  open_app | search | weather | reminder | type | ...        │  │
│   │  + plugins/  (hot-reloaded)                                 │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                   Memory System                              │  │
│   │  Working (dict) → Session (SQLite) → Long-term (ChromaDB)  │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │ SSE stream           │ REST control API
         ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COMMAND CENTER (SvelteKit)                      │
│  Neural Flow | Conversation Feed | The Forge | Memory | Plugins     │
└─────────────────────────────────────────────────────────────────────┘
         │ (Docker)
         ▼
┌────────────────────┐    ┌────────────────┐
│  Coqui TTS :5002   │    │ Duckling :8000 │
└────────────────────┘    └────────────────┘
```

### Key Design Decisions Explained

**Single process for the core** (Phase 1): Assistant + NLU + Logic collapse into one Python process using `asyncio`. Services communicate through in-process event queues, not HTTP. This drops 2–3 serialization/network roundtrips per request (easily 200–400ms). HTTP is kept only for Coqui TTS and Duckling (Docker containers). The FastAPI server is retained as the **external API surface** for the Command Center and plugin control — not as an internal service bus.

**Rasa replacement strategy**: Use `sentence-transformers` (`all-MiniLM-L6-v2`, 80MB, runs in-process) to embed utterances and compare against labeled intent examples using cosine similarity. Entities are extracted with spaCy NER + Duckling. This is 95% of what Rasa DIET + Pipeline does, without the 500MB framework overhead and without a separate process. When confidence is low, fall through to the local LLM (Ollama).

**Event bus with `asyncio.Queue`**: For a single-machine system, Redis is overkill. `asyncio.Queue` with typed event dataclasses gives full pub/sub semantics at zero infrastructure cost. Migrate to Redis Streams only if you want multi-machine or mobile client support later.

**SSE over WebSocket**: Your current WebSocket-to-UI design failed because managing async WebSocket lifecycle inside synchronous assistant code is painful (the commented-out evidence speaks for itself). SSE is one-directional (server → browser), uses plain HTTP/1.1, requires zero connection management code, and every modern browser handles reconnection automatically.

---

## 5. Implementation Plan

### Step 1: Strip and Scaffold

Delete websocket.py. Remove all commented-out `ui_logger` and `ui_controller` calls from main.py. This clarifies what the system actually does. Create the new directory structure:

```
core/
  src/
    main.py              # asyncio entry point
    bus.py               # typed events + asyncio.Queue
    nlu/
      engine.py          # sentence-transformers classifier
      entities.py        # spaCy + Duckling client
    capabilities/
      registry.py        # @capability decorator + discovery
      builtin/           # existing logic/* services, migrated
    memory/
      working.py
      session.py
      longterm.py
    planner/
      rule_planner.py    # Phase 1: direct intent→capability mapping
      llm_planner.py     # Phase 2: Ollama-backed planner
    input/
      wake_word.py
      stt.py             # faster-whisper wrapper
    output/
      tts_client.py
      response_builder.py
    api/
      server.py          # FastAPI: SSE endpoint + REST control
      sse.py
  plugins/               # user-installed capabilities
  tests/
ui/
  (SvelteKit project)
infra/
  docker-compose.yml     # Coqui + Duckling only
```

### Step 2: Implement the Event Bus

```python
# core/src/bus.py
from dataclasses import dataclass
from typing import Any
import asyncio

@dataclass
class InputEvent:
    trace_id: str
    text: str
    source: str  # "voice" | "text"

@dataclass
class NLUEvent:
    trace_id: str
    intent: str
    confidence: float
    entities: dict[str, Any]

@dataclass
class ActionEvent:
    trace_id: str
    capability: str
    params: dict[str, Any]

@dataclass
class ResponseEvent:
    trace_id: str
    text: str
    speak: bool = True

class EventBus:
    def __init__(self):
        self._queues: dict[type, list[asyncio.Queue]] = {}

    def subscribe(self, event_type: type) -> asyncio.Queue:
        q = asyncio.Queue()
        self._queues.setdefault(event_type, []).append(q)
        return q

    async def publish(self, event: Any):
        for q in self._queues.get(type(event), []):
            await q.put(event)
```

### Step 3: Replace Rasa NLU

Install: `sentence-transformers`, `spacy` (already present), keep `Duckling` Docker. Build `nlu/engine.py`:

```python
# Intent classification: encode utterance, find nearest labeled example
# Entity extraction: spaCy NER + regex + Duckling HTTP call
# Confidence threshold: if max_similarity < 0.65, emit LowConfidenceEvent
```

Training data migrates from Rasa's `nlu.yml` to a plain `intents.json`:

```json
{
  "intent": "open_app",
  "examples": ["open chrome", "launch firefox", "start vscode"]
}
```

No training step needed — it's retrieval-based. Retraining = adding examples to `intents.json`.

### Step 4: Capability Registry

```python
# core/src/capabilities/registry.py
from functools import wraps

_registry: dict[str, dict] = {}

def capability(name: str, **meta):
    def decorator(fn):
        _registry[name] = {"fn": fn, "meta": meta}
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def get_capability(name: str):
    return _registry.get(name)
```

Migrate every `if action == "..."` block in logic.py to decorated functions in `capabilities/builtin/`.

### Step 5: SSE API + Command Center Backend

Add to FastAPI:

```python
# GET /stream  →  SSE endpoint  →  yields pipeline state events
# POST /command  →  inject text command (for UI testing)
# GET /traces  →  list recent traces
# GET /traces/{trace_id}  →  full trace detail
# GET /capabilities  →  list registered capabilities
# POST /retrain  →  trigger NLU reindex
```

### Step 6: Build Command Center UI

Scaffold with SvelteKit. Serve from ui directory. FastAPI mounts it as a static directory with `StaticFiles`. No separate UI server — the Logic API already serves on `:8021`.

Start with 3 panels: Live Pipeline (SVG animated visualization), Conversation Feed (SSE-driven list), System Status (health checks). Add The Forge in Phase 2.

### Step 7: Observability

Add `structlog` with a JSON renderer. Every pipeline event logs:

```json
{
  "trace_id": "abc123",
  "stage": "nlu",
  "intent": "open_app",
  "confidence": 0.91,
  "latency_ms": 43,
  "entities": { "app_name": "chrome" }
}
```

Log file rotated daily in logs. The SSE stream also forwards these events to the Command Center in real-time.

---

## 6. "Insane Mode" Ideas

If you want to go beyond a personal assistant into a genuine **local AI command center**:

**ELISA-as-Agent-Orchestrator**: Deploy multiple Ollama models simultaneously (a fast one for quick responses, a larger one for complex reasoning). ELISA routes requests to the appropriate model based on task type, with model switching mid-conversation if complexity escalates.

**Screen Awareness**: Periodically capture a screenshot, run a local vision model (LLaVA via Ollama) to describe the active application and context. "You're in VS Code with a Python file open — should I help debug the highlighted function?" Contextual awareness without cloud APIs.

**Voice-to-Code**: Speak code changes in natural language. "In the current file, rename the variable `x` to `result` and add a docstring to the main function." The assistant uses tree-sitter to parse the active file, applies targeted edits, and writes them back. A local coding agent in your voice.

**Local Knowledge Graph**: As ELISA extracts facts over months of use, build a knowledge graph (NetworkX + SQLite) of entities and relationships. "What did I ask you to remind me about last Monday?" traverses the graph rather than doing a full text search. Entity relationships (Person → works at → Company, Project → deadline → Date) enable complex queries.

**Emotional State Modeling**: Track response times, correction frequency, and command patterns to infer user stress/focus level. When you've corrected ELISA 5 times in the last 30 minutes, it switches to a shorter, more direct response style. When you're on a flow streak (complex coding commands, no corrections), it stops offering unsolicited suggestions.

---

This is the path from hobby project to product-grade local AI command center. Phase 1 alone eliminates the biggest pain points (Rasa overhead, dead WebSocket code, string dispatch chaos) and gives you a system that's actually debuggable and extensible. Everything in Phase 2 and 3 builds on that foundation rather than patching around it.
