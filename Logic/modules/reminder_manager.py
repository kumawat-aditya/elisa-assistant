from TTS.api import TTS
import simpleaudio as sa
import sys
import os
import json
import subprocess
from datetime import datetime
from pytz import timezone
from scheduler_core import scheduler  # ✅ Now this works cleanly
import platform
import shutil

# Base directory is the parent of utils/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # /rasa

REMINDER_FILE = os.path.join(BASE_DIR, "data", "reminders", "reminders.json")
RESPONSE_WAV = os.path.join(BASE_DIR, "..", "audio", "temporary", "response.wav")
NOTIFICATION_WAV = os.path.join(BASE_DIR, "..", "audio", "permanent", "notification.wav")
AUDIO_TEMP_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'audio', 'temporary'))


def notify(response):
    tts = TTS(model_name="tts_models/en/ljspeech/glow-tts", progress_bar=False)

    # Redirect stdout and stderr to suppress logs
    with open(os.devnull, 'w') as f:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = f, f
        try:
            tts.tts_to_file(text=response, file_path=RESPONSE_WAV)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr  # Restore stdout and stderr 

    # Play the generated speech
    sa.WaveObject.from_wave_file(NOTIFICATION_WAV).play().wait_done()
    sa.WaveObject.from_wave_file(RESPONSE_WAV).play().wait_done()

def remind(task_name, early=False):
    msg = f"⏰ Reminder: '{task_name}'"
    if early:
        msg = f"⚠️ Upcoming in 10 mins: '{task_name}'"
        notify("Upcoming in 10 mins: " + task_name)
    else:
        notify("Reminder: " + task_name)
    print(msg)
    # You can add system notification or audio here too

    os_platform = platform.system().lower()
    try:
        if os_platform == "linux":
            # Check if notify-send is available
            if shutil.which("notify-send"):
                 subprocess.run(['notify-send', 'Elisa Reminder', msg], timeout=5)
            else:
                print("notify-send command not found for Linux desktop notification.")
        elif os_platform == "windows":
            # For Windows, we can use PowerShell's BurntToast module (requires user install)
            # or a simpler solution using 'msg *' (for local user, might be intrusive)
            # or a more complex solution with win10toast_click or similar libraries.
            # Simplest fallback: just print to console and rely on audio notification.
            # Example using a library (if you choose to add one like 'plyer'):
            # from plyer import notification
            # notification.notify(title='Elisa Reminder', message=msg, app_name='Elisa Assistant', timeout=10)
            print("Desktop notification for Windows: Consider using a library like 'plyer' or 'win10toast' for richer notifications.")
            # Basic attempt with powershell (might not always work without specific setup)
            try:
                ps_command = f'powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\'{msg}\', \'Elisa Reminder\')"'
                # subprocess.run(ps_command, shell=True, timeout=5, check=False) # This creates a modal dialog, maybe not ideal
                # For toast, more complex, e.g. using a helper script or BurntToast
            except Exception as e_ps:
                print(f"PowerShell notification attempt failed: {e_ps}")

        elif os_platform == "darwin": # macOS
             # Check if terminal-notifier is available (brew install terminal-notifier)
            if shutil.which("terminal-notifier"):
                subprocess.run(['terminal-notifier', '-title', 'Elisa Reminder', '-message', msg], timeout=5)
            else: # Fallback to osascript
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

    # Remove old duplicate if exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        remind,  # Now using the global `remind` function
        trigger='date',
        run_date=reminder_time,
        id=job_id,
        replace_existing=True,
        args=[task_name, early]  # Pass task_name and early as arguments
    )

def remove_reminder(task_name: str):
    """Removes both early and on-time reminders from the scheduler by task_name."""
    removed = False
    for suffix in ["early", "on_time"]:
        job_id = f"{task_name}_{suffix}"
        job = scheduler.get_job(job_id)
        if job:
            scheduler.remove_job(job_id)
            print(f"[Scheduler] Removed job: {job_id}")
            removed = True
    return removed