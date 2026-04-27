import logging
import os
import time

from wake_word.wake_word_detection import listen_for_wake_word
from stt.voice_recognition import recognize_speech, play_wav_file
from nlu_client.rasa_integration import process_command
from tts.text_to_speech import speak_response
from session.websocket import ui_controller
from session.health import start_health_monitor

logger = logging.getLogger(__name__)


def assistant_workflow():
    ui_controller.set_pipeline_stage("idle")

    # ============================== PLAY BOOT SOUND AND GREETING =============================
    logger.info("Starting assistant workflow...")
    logger.debug("Playing boot sound...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    boot_path = os.path.join(base_dir, "../../shared/audio/permanent/boot.wav").replace("\\", "/")
    if not play_wav_file(boot_path):
        logger.warning("Failed to play boot sound: No audio playback method available")

    # =============================== GREETING =============================
    ui_controller.set_pipeline_stage("nlu", {"reason": "greeting"})
    logger.info("Starting greeting sequence...")

    try:
        nlu_t0 = time.time()
        responses, continue_conversation = process_command("wake up elisa")
        nlu_ms = int((time.time() - nlu_t0) * 1000)
        ui_controller.send_metric("nlu_latency_ms", nlu_ms, "ms")
        logger.debug("Received %d responses from Rasa", len(responses))
    except Exception as e:
        ui_controller.send_error("greeting", f"Failed to process greeting: {e}", e)
        logger.error("Failed to process greeting: %s", e)
        return

    ui_controller.set_pipeline_stage("tts", {"reason": "greeting"})
    for i, response in enumerate(responses):
        logger.debug("Speaking response %d: %s%s", i + 1, response[:50], "..." if len(response) > 50 else "")
        ui_controller.send_conversation_turn("assistant", response, {"phase": "greeting"})
        try:
            tts_t0 = time.time()
            speak_response(response)
            ui_controller.send_metric("tts_latency_ms", int((time.time() - tts_t0) * 1000), "ms")
        except Exception as e:
            ui_controller.send_error("tts", f"Failed to speak response: {e}", e)
            logger.error("Failed to speak response: %s", e)

    logger.info("Greeting sequence completed")

    # ================================ LISTEN FOR COMMAND =============================
    while True:
        command = None
        for attempt in range(3):
            ui_controller.set_pipeline_stage("vad", {"attempt": attempt + 1})
            logger.debug("Setting up voice recognition (attempt %d)...", attempt + 1)

            try:
                stt_t0 = time.time()
                command = recognize_speech()
                if command is not None:
                    ui_controller.set_pipeline_stage("stt", {"transcript": command})
                    ui_controller.send_metric("stt_latency_ms", int((time.time() - stt_t0) * 1000), "ms")
                    logger.info("Command recognized: '%s'", command)
                    break
                else:
                    logger.warning("No speech detected on attempt %d", attempt + 1)
                    if attempt < 2:
                        ui_controller.set_pipeline_stage("tts", {"reason": "retry-prompt"})
                        logger.debug("Speaking retry message...")
                        speak_response("I couldn't hear you. Please try again.")
            except Exception as e:
                ui_controller.send_error("stt", f"Error during speech recognition: {e}", e)
                logger.error("Error during speech recognition: %s", e)

        if command is None:
            ui_controller.set_pipeline_stage("tts", {"reason": "give-up"})
            speak_response("I'm sorry, I couldn't understand you. Please try again later.")
            ui_controller.set_pipeline_stage("idle")
            continue

        # User turn
        ui_controller.send_conversation_turn("user", command)

        # Process with Rasa
        ui_controller.set_pipeline_stage("nlu", {"command": command})
        logger.info("Processing command with Rasa: '%s'", command)

        try:
            nlu_t0 = time.time()
            responses, continue_conversation = process_command(command)
            nlu_ms = int((time.time() - nlu_t0) * 1000)
            ui_controller.send_metric("nlu_latency_ms", nlu_ms, "ms")
            logger.debug("Rasa processed command, got %d responses", len(responses))
        except Exception as e:
            ui_controller.send_error("nlu", f"Failed to process command: {e}", e)
            logger.error("Failed to process command with Rasa: %s", e)
            ui_controller.set_pipeline_stage("idle")
            continue

        # Speak
        ui_controller.set_pipeline_stage("tts")
        for i, response in enumerate(responses):
            logger.debug("Speaking response %d: %s%s", i + 1, response[:50], "..." if len(response) > 50 else "")
            ui_controller.send_conversation_turn("assistant", response, {"latency_ms": nlu_ms})
            try:
                tts_t0 = time.time()
                speak_response(response)
                ui_controller.send_metric("tts_latency_ms", int((time.time() - tts_t0) * 1000), "ms")
            except Exception as e:
                ui_controller.send_error("tts", f"Failed to speak response: {e}", e)
                logger.error("Failed to speak response: %s", e)

        if not continue_conversation:
            logger.info("No further conversation needed — ending session")
            ui_controller.set_pipeline_stage("idle")
            break
        else:
            logger.debug("Conversation continuing...")


def main():
    """Main function to start the assistant with UI."""

    # Install interceptors FIRST so every print() / logging call after this
    # point is mirrored to the UI with zero changes to the existing codebase.
    ui_controller.install_interceptors()

    logger.info("Starting Elisa Assistant...")

    try:
        ui_controller.start_server(host="localhost", port=8765)
        logger.info("WebSocket server started on ws://localhost:8765")
        logger.info("Open the UI: http://localhost:35109/")

        # Background health monitor for service status pills.
        start_health_monitor()

        time.sleep(1)

        ui_controller.set_pipeline_stage("wake_word")
        logger.info("Starting wake word detection...")
        listen_for_wake_word(assistant_workflow)

    except Exception as e:
        ui_controller.send_error("main", f"Failed to start assistant: {e}", e)
        logger.error("Failed to start assistant: %s", e)
        raise


if __name__ == "__main__":
    main()
