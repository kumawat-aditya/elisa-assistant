"""Demo emitter for UI smoke testing — runs the WS server and emits fake events.

Run with: python scripts/ui_demo.py
Then open http://localhost:35109/ in a browser (start UI server first).
"""
from __future__ import annotations

import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "assistant", "src"))

from session.websocket import ui_controller  # noqa: E402


STAGES = ["wake_word", "vad", "stt", "nlu", "logic", "tts", "output"]
FILES = [
    "assistant/src/main.py",
    "assistant/src/wake_word/wake_word_detection.py",
    "assistant/src/stt/voice_recognition.py",
    "assistant/src/tts/synthesizer.py",
    "assistant/src/nlu_client/nlu_client.py",
]
LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "PRINT"]


def main() -> None:
    ui_controller.install_interceptors()
    ui_controller.start_server("localhost", 8765)
    print("Demo WS server running on ws://localhost:8765")
    print("Open the UI at http://localhost:35109/")

    # Mark services up
    for svc in ("rasa", "logic", "tts", "duckling"):
        ui_controller.set_service_status(svc, "up")

    tick = 0
    while True:
        tick += 1

        # Random log
        f = random.choice(FILES)
        lvl = random.choices(LEVELS, weights=[1, 5, 1, 0.3, 2])[0]
        msg = f"tick {tick} — {random.choice(['scanning audio buffer', 'forward pass complete', 'received frame', 'cache miss', 'decoded chunk'])}"
        ui_controller._queue_log(
            level=lvl, message=msg, source_file=f,
            lineno=random.randint(20, 400), func="demo", module="demo",
        )

        # Cycle pipeline every 6 ticks
        if tick % 6 == 0:
            stage = STAGES[(tick // 6) % len(STAGES)]
            data = {"score": round(random.random(), 3)} if stage == "wake_word" else {}
            ui_controller.set_pipeline_stage(stage, data)
            if stage == "stt":
                ui_controller.send_metric("stt_latency_ms", random.randint(80, 260), "ms")
            elif stage == "nlu":
                ui_controller.send_metric("nlu_latency_ms", random.randint(20, 120), "ms")
            elif stage == "tts":
                ui_controller.send_metric("tts_latency_ms", random.randint(150, 500), "ms")

        # Periodic conversation turn
        if tick % 18 == 0:
            ui_controller.send_conversation_turn(
                "user",
                random.choice(["what time is it", "set a timer for 5 minutes", "play some music", "weather please"]),
                metadata={"intent": "ask_time", "confidence": round(0.55 + random.random() * 0.45, 2)},
            )
        if tick % 18 == 9:
            ui_controller.send_conversation_turn(
                "assistant",
                random.choice(["it is 3 pm", "timer set", "playing now", "75 and sunny"]),
                metadata={"latency_ms": random.randint(120, 450), "phase": "complete"},
            )

        if tick % 60 == 0:
            ui_controller.set_pipeline_stage("idle", {})

        time.sleep(0.4)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopping demo")
