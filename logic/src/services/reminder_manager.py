import sys
import os
import json
import subprocess
import platform
import shutil
import requests
import simpleaudio as sa
from datetime import datetime
from pytz import timezone
from scheduler.scheduler_core import scheduler  # Updated import path

# Base directory structure
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # logic/src/
LOGIC_DIR = os.path.dirname(SRC_DIR)  # logic/
PROJECT_ROOT = os.path.dirname(LOGIC_DIR)  # elisa-assistant/

REMINDER_FILE = os.path.join(SRC_DIR, "data", "reminders", "reminders.json")
RESPONSE_WAV = os.path.join(PROJECT_ROOT, "shared", "audio", "temporary", "response.wav")
NOTIFICATION_WAV = os.path.join(PROJECT_ROOT, "shared", "audio", "permanent", "notification.wav")
AUDIO_TEMP_DIR = os.path.join(PROJECT_ROOT, "shared", "audio", "temporary")

# URL of the running Coqui TTS API server
TTS_API_URL = "http://localhost:5002/api/tts"

def notify(response):
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(RESPONSE_WAV), exist_ok=True)

    # Prepare the payload
    data = {
        "text": response
    }

    try:
        # Send request to TTS API
        res = requests.post(TTS_API_URL, data=data)
        res.raise_for_status()

        # Save the response content as a wav file
        with open(RESPONSE_WAV, 'wb') as f:
            f.write(res.content)

        # Play notification sound first, if exists
        if os.path.exists(NOTIFICATION_WAV):
            sa.WaveObject.from_wave_file(NOTIFICATION_WAV).play().wait_done()

        # Play the response audio
        sa.WaveObject.from_wave_file(RESPONSE_WAV).play().wait_done()

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with TTS server: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def remind(task_name, early=False):
    msg = f"⏰ Reminder: '{task_name}'"
    if early:
        msg = f"⚠️ Upcoming in 10 mins: '{task_name}'"
        notify("Upcoming in 10 mins: " + task_name)
    else:
        notify("Reminder: " + task_name)
    print(msg)

    os_platform = platform.system().lower()
    try:
        if os_platform == "linux":
            if shutil.which("notify-send"):
                subprocess.run(['notify-send', 'Elisa Reminder', msg], timeout=5)
        elif os_platform == "windows":
            print("Desktop notification for Windows: Consider using a library like 'plyer' or 'win10toast'.")
        elif os_platform == "darwin":
            if shutil.which("terminal-notifier"):
                subprocess.run(['terminal-notifier', '-title', 'Elisa Reminder', '-message', msg], timeout=5)
            else:
                subprocess.run(['osascript', '-e', f'display notification "{msg}" with title "Elisa Reminder"'], timeout=5)
        else:
            print(f"Desktop notifications not configured for OS: {os_platform}")
    except Exception as e:
        print(f"Error sending desktop notification: {e}")

def load_reminders():
    if not os.path.exists(REMINDER_FILE):
        return {}
    with open(REMINDER_FILE, "r") as file:
        return json.load(file)

def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as file:
        json.dump(reminders, file, indent=4)

def schedule_reminder(task_name, iso_time_str, early=False):
    reminder_time = datetime.fromisoformat(iso_time_str)

    if reminder_time.tzinfo is None:
        reminder_time = reminder_time.replace(tzinfo=timezone("Asia/Kolkata"))

    job_id = f"{task_name}_{'early' if early else 'on_time'}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        remind,
        trigger='date',
        run_date=reminder_time,
        id=job_id,
        replace_existing=True,
        args=[task_name, early]
    )

def remove_reminder(task_name: str):
    removed = False
    for suffix in ["early", "on_time"]:
        job_id = f"{task_name}_{suffix}"
        job = scheduler.get_job(job_id)
        if job:
            scheduler.remove_job(job_id)
            print(f"[Scheduler] Removed job: {job_id}")
            removed = True
    return removed
