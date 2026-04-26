# ============================================================================
# ELISA — God Mode WebSocket Layer
# ----------------------------------------------------------------------------
# Non-invasive observability bridge between the running assistant and the UI.
#
#   * PrintInterceptor   - wraps sys.stdout, mirrors every print() to the UI
#   * ElisaLogHandler    - hooks Python `logging`, mirrors every record
#   * Ring buffers       - last 500 logs / 50 turns / metrics, replayed via
#                          a "snapshot" message when a new client connects
#   * Async queued send  - main pipeline never blocks on UI I/O
#   * Ping/keepalive     - keeps idle browser connections alive
#
# Backward compatibility is preserved: the legacy UILogger / create_ui_logger /
# set_ui_state / add_ui_log helpers continue to work.
# ============================================================================

from __future__ import annotations

import asyncio
import inspect
import io
import json
import logging
import os
import queue
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Set

import websockets


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
LOG_BUFFER_SIZE = 500
CONVERSATION_BUFFER_SIZE = 50
METRIC_BUFFER_SIZE = 200
SCHEMA_VERSION = 1


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_path(path: str) -> str:
    """Return a workspace-relative-ish file path for log tagging."""
    if not path:
        return "<unknown>"
    try:
        path = os.path.abspath(path)
    except Exception:
        return path
    parts = path.replace("\\", "/").split("/")
    for marker in ("assistant", "logic", "nlu"):
        if marker in parts:
            idx = parts.index(marker)
            return "/".join(parts[idx:])
    return "/".join(parts[-2:])


# ----------------------------------------------------------------------------
# PrintInterceptor — wraps sys.stdout
# ----------------------------------------------------------------------------
class PrintInterceptor(io.TextIOBase):
    """Tee sys.stdout to the UI controller without altering terminal output."""

    def __init__(self, original_stdout, controller: "ElisaUIController"):
        self.original = original_stdout
        self.controller = controller
        self._line_buffer = ""
        self._lock = threading.Lock()

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        try:
            return self.original.isatty()
        except Exception:
            return False

    def fileno(self):
        return self.original.fileno()

    def write(self, text):
        try:
            self.original.write(text)
        except Exception:
            pass

        if not text:
            return 0

        try:
            with self._lock:
                self._line_buffer += text
                while "\n" in self._line_buffer:
                    line, self._line_buffer = self._line_buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if line.strip() == "":
                        continue
                    self._emit(line)
        except Exception:
            pass

        return len(text)

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass
        with self._lock:
            if self._line_buffer.strip():
                line = self._line_buffer
                self._line_buffer = ""
                self._emit(line)

    def _emit(self, line: str):
        info = self._caller_frame()
        self.controller._queue_log(
            level="PRINT",
            message=line,
            source_file=info["file"],
            lineno=info["line"],
            func=info["func"],
            module=info["module"],
        )

    @staticmethod
    def _caller_frame() -> Dict[str, Any]:
        try:
            frame = inspect.currentframe()
            while frame is not None:
                fname = frame.f_code.co_filename
                if (
                    "websocket.py" in fname
                    or fname.endswith(("io.py", "codecs.py"))
                    or "<frozen" in fname
                ):
                    frame = frame.f_back
                    continue
                return {
                    "file": _short_path(fname),
                    "line": frame.f_lineno,
                    "func": frame.f_code.co_name,
                    "module": frame.f_globals.get("__name__", "?"),
                }
        except Exception:
            pass
        return {"file": "<unknown>", "line": 0, "func": "?", "module": "?"}


# ----------------------------------------------------------------------------
# ElisaLogHandler — hooks Python's logging system
# ----------------------------------------------------------------------------
class ElisaLogHandler(logging.Handler):
    def __init__(self, controller: "ElisaUIController"):
        super().__init__()
        self.controller = controller

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            self.controller._queue_log(
                level=record.levelname,
                message=msg,
                source_file=_short_path(record.pathname),
                lineno=record.lineno,
                func=record.funcName,
                module=record.module,
                logger=record.name,
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Main controller
# ----------------------------------------------------------------------------
class ElisaUIController:
    """Singleton, thread-safe, async-broadcasted observability bus."""

    _instance: Optional["ElisaUIController"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.connected_clients: Set[Any] = set()
        self.server = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.server_thread: Optional[threading.Thread] = None
        self.message_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=10000)

        self._log_buffer: Deque[Dict[str, Any]] = deque(maxlen=LOG_BUFFER_SIZE)
        self._conv_buffer: Deque[Dict[str, Any]] = deque(maxlen=CONVERSATION_BUFFER_SIZE)
        self._metric_buffer: Deque[Dict[str, Any]] = deque(maxlen=METRIC_BUFFER_SIZE)
        self._buffer_lock = threading.Lock()

        self._pipeline_stage = "idle"
        self._pipeline_data: Dict[str, Any] = {}
        self._state = "idle"
        self._services: Dict[str, str] = {
            "rasa": "unknown",
            "logic": "unknown",
            "tts": "unknown",
            "duckling": "unknown",
        }
        self._started_at = time.time()

        self._print_interceptor: Optional[PrintInterceptor] = None
        self._log_handler: Optional[ElisaLogHandler] = None
        self._original_stdout = None
        self._interceptors_installed = False

        self._sys_logger = logging.getLogger("elisa.ws")
        self._sys_logger.propagate = False  # don't loop into ElisaLogHandler

    # Interceptors -----------------------------------------------------------
    def install_interceptors(self):
        if self._interceptors_installed:
            return

        self._original_stdout = sys.stdout
        self._print_interceptor = PrintInterceptor(sys.stdout, self)
        sys.stdout = self._print_interceptor

        self._log_handler = ElisaLogHandler(self)
        self._log_handler.setLevel(logging.DEBUG)
        self._log_handler.setFormatter(logging.Formatter("%(message)s"))
        root = logging.getLogger()
        if root.level == logging.NOTSET or root.level > logging.INFO:
            root.setLevel(logging.INFO)
        root.addHandler(self._log_handler)

        self._interceptors_installed = True

    def uninstall_interceptors(self):
        if not self._interceptors_installed:
            return
        try:
            if self._original_stdout is not None:
                sys.stdout = self._original_stdout
        except Exception:
            pass
        try:
            if self._log_handler is not None:
                logging.getLogger().removeHandler(self._log_handler)
        except Exception:
            pass
        self._interceptors_installed = False

    # Public emitters --------------------------------------------------------
    def set_pipeline_stage(self, stage: str, data: Optional[Dict[str, Any]] = None):
        self._pipeline_stage = stage
        self._pipeline_data = data or {}
        self._queue({
            "type": "pipeline_stage",
            "stage": stage,
            "data": data or {},
            "timestamp": _now_iso(),
        })

    def set_state(self, state: str, module_name: Optional[str] = None):
        self._state = state
        self._queue({
            "type": "state_change",
            "state": state,
            "module": module_name or "system",
            "timestamp": _now_iso(),
        })

    def send_conversation_turn(self, role: str, text: str,
                               metadata: Optional[Dict[str, Any]] = None):
        turn = {
            "role": role,
            "text": text,
            "metadata": metadata or None,
            "timestamp": _now_iso(),
        }
        with self._buffer_lock:
            self._conv_buffer.append(turn)
        self._queue({"type": "conversation_turn", **turn})

    def send_metric(self, metric_name: str, value: float, unit: str = ""):
        m = {
            "name": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": _now_iso(),
        }
        with self._buffer_lock:
            self._metric_buffer.append(m)
        self._queue({"type": "metric", **m})

    def set_service_status(self, service: str, status: str):
        self._services[service] = status
        self._queue({
            "type": "service_status",
            "service": service,
            "status": status,
            "timestamp": _now_iso(),
        })

    def send_error(self, source: str, message: str, exc: Optional[BaseException] = None):
        payload: Dict[str, Any] = {
            "type": "error",
            "source": source,
            "message": message,
            "timestamp": _now_iso(),
        }
        if exc is not None:
            payload["traceback"] = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
        self._queue(payload)

    def send_custom_data(self, data_type: str, data: Any,
                         module_name: Optional[str] = None):
        self._queue({
            "type": data_type,
            "data": data,
            "module": module_name or "system",
            "timestamp": _now_iso(),
        })

    def add_log(self, level: str, message: str, module_name: Optional[str] = None):
        self._queue_log(
            level=level.upper(),
            message=message,
            source_file="<legacy>",
            lineno=0,
            func="?",
            module=module_name or "system",
        )

    # Internal queueing ------------------------------------------------------
    def _queue_log(self, level: str, message: str, source_file: str,
                   lineno: int, func: str, module: str, logger: str = ""):
        entry = {
            "level": level.upper(),
            "message": message,
            "source_file": source_file,
            "line": lineno,
            "func": func,
            "module": module,
            "logger": logger,
            "timestamp": _now_iso(),
        }
        with self._buffer_lock:
            self._log_buffer.append(entry)
        self._queue({"type": "log", **entry})

    def _queue(self, message: Dict[str, Any]):
        try:
            self.message_queue.put_nowait(message)
        except queue.Full:
            try:
                self.message_queue.get_nowait()
                self.message_queue.put_nowait(message)
            except Exception:
                pass

    # Snapshot ---------------------------------------------------------------
    def _build_snapshot(self) -> Dict[str, Any]:
        with self._buffer_lock:
            logs = list(self._log_buffer)
            convs = list(self._conv_buffer)
            metrics = list(self._metric_buffer)
        return {
            "type": "snapshot",
            "schema_version": SCHEMA_VERSION,
            "state": self._state,
            "pipeline_stage": self._pipeline_stage,
            "pipeline_data": self._pipeline_data,
            "services": dict(self._services),
            "uptime_seconds": int(time.time() - self._started_at),
            "log_buffer": logs,
            "conversation_buffer": convs,
            "metric_buffer": metrics,
            "timestamp": _now_iso(),
        }

    # WebSocket plumbing -----------------------------------------------------
    async def _send(self, ws, payload: Dict[str, Any]) -> bool:
        try:
            await ws.send(json.dumps(payload, default=str))
            return True
        except Exception:
            return False

    async def _broadcast(self, payload: Dict[str, Any]):
        if not self.connected_clients:
            return
        text = json.dumps(payload, default=str)
        dead = []
        for ws in list(self.connected_clients):
            try:
                await ws.send(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connected_clients.discard(ws)

    async def _process_queue(self):
        while True:
            try:
                drained = []
                for _ in range(200):
                    try:
                        drained.append(self.message_queue.get_nowait())
                    except queue.Empty:
                        break
                for msg in drained:
                    await self._broadcast(msg)
                if not drained:
                    await asyncio.sleep(0.03)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._sys_logger.error("queue processor error: %s", e)
                await asyncio.sleep(0.5)

    async def _keepalive(self, ws):
        try:
            while True:
                await asyncio.sleep(25)
                try:
                    await ws.send(json.dumps({"type": "ping", "timestamp": _now_iso()}))
                except Exception:
                    return
        except asyncio.CancelledError:
            return

    async def _handle_client(self, ws, *_args):
        # Accepts both old (ws, path) and new (ws,) websockets API.
        self.connected_clients.add(ws)
        self._sys_logger.info("ws client connected (total=%d)", len(self.connected_clients))

        await self._send(ws, {
            "type": "connection_established",
            "schema_version": SCHEMA_VERSION,
            "timestamp": _now_iso(),
        })
        await self._send(ws, self._build_snapshot())

        ka_task = asyncio.ensure_future(self._keepalive(ws))
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                t = data.get("type")
                if t == "ping":
                    await self._send(ws, {"type": "pong", "timestamp": _now_iso()})
                elif t == "request_snapshot":
                    await self._send(ws, self._build_snapshot())
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self._sys_logger.error("ws client error: %s", e)
        finally:
            ka_task.cancel()
            self.connected_clients.discard(ws)
            self._sys_logger.info("ws client disconnected (total=%d)", len(self.connected_clients))

    # Server lifecycle -------------------------------------------------------
    def start_server(self, host: str = "localhost", port: int = 8765):
        if self.server_thread and self.server_thread.is_alive():
            return self.server_thread

        def run_server_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            async def server_main():
                self.server = await websockets.serve(
                    self._handle_client,
                    host,
                    port,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=2 ** 22,
                )
                self._sys_logger.info("ws server listening on ws://%s:%d", host, port)
                asyncio.ensure_future(self._process_queue())

            try:
                self.loop.run_until_complete(server_main())
                self.loop.run_forever()
            except Exception as e:
                self._sys_logger.error("ws server error: %s", e)
            finally:
                try:
                    if self.server:
                        self.server.close()
                except Exception:
                    pass
                try:
                    self.loop.close()
                except Exception:
                    pass

        self.server_thread = threading.Thread(target=run_server_loop, daemon=True, name="elisa-ws")
        self.server_thread.start()
        return self.server_thread

    def stop_server(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=3)


# ----------------------------------------------------------------------------
# Singleton + legacy helpers (kept for backward compatibility)
# ----------------------------------------------------------------------------
ui_controller = ElisaUIController()


def set_ui_state(state, module_name=None):
    ui_controller.set_state(state, module_name)


def add_ui_log(level, message, module_name=None):
    ui_controller.add_log(level, message, module_name)


def send_ui_data(data_type, data, module_name=None):
    ui_controller.send_custom_data(data_type, data, module_name)


class UILogger:
    """Thin module-scoped wrapper preserved for existing imports."""

    def __init__(self, module_name):
        self.module_name = module_name

    def set_state(self, state):
        set_ui_state(state, self.module_name)

    def log_info(self, message):
        add_ui_log("info", message, self.module_name)

    def log_success(self, message):
        add_ui_log("success", message, self.module_name)

    def log_warning(self, message):
        add_ui_log("warning", message, self.module_name)

    def log_error(self, message):
        add_ui_log("error", message, self.module_name)

    def send_data(self, data_type, data):
        send_ui_data(data_type, data, self.module_name)


def create_ui_logger(module_name):
    return UILogger(module_name)
