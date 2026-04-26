# Background service-health monitor — pings each backend every 10s and
# emits service_status events to the UI. Pure best-effort; never raises.

from __future__ import annotations

import threading
import time
from typing import Tuple

import requests

from session.websocket import ui_controller


SERVICES: list[Tuple[str, str]] = [
    ("rasa", "http://localhost:5005/status"),
    ("logic", "http://localhost:8021/health"),
    ("tts", "http://localhost:5002/api/voices"),
    ("duckling", "http://localhost:8000/"),
]

POLL_SECONDS = 10
TIMEOUT = 1.5


def _check(url: str) -> bool:
    try:
        r = requests.get(url, timeout=TIMEOUT)
        return r.status_code < 500
    except Exception:
        return False


def _loop():
    while True:
        for name, url in SERVICES:
            ok = _check(url)
            ui_controller.set_service_status(name, "up" if ok else "down")
        time.sleep(POLL_SECONDS)


_started = False
_lock = threading.Lock()


def start_health_monitor():
    """Idempotent — starts a single daemon thread."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
        threading.Thread(target=_loop, daemon=True, name="elisa-health").start()
