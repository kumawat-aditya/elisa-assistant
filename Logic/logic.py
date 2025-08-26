import webbrowser
import wikipedia
import os
from modules.app_launcher import open_application
from modules.weather_info import fetch_weather, get_user_location
from modules.reminder_manager import load_reminders, save_reminders, schedule_reminder, remove_reminder
from response_loader import get_random_response
from datetime import datetime, timedelta, timezone
import random
from typing import Any, Text, Dict, List
from pynput.keyboard import Controller
import time
import difflib


def process(action: Text, data: Text):
    if(action == "OPEN_APP"):
        open_app(data)
    if(action == "SEARCH_BROWSER"):
        search_browser(data)
    if(action == "TYPE_TEXT"):
        type_text(data)
    if(action == "GET_CURRENT_TIME"):
        get_current_time()
    if(action == "GET_MEANING"):
        meaning_of(data)
    if(action  == "OPEN_BROWSER"):
        open_browser(data)
    if(action == "GET_WEATHER"):
        get_weather(data)
    if(action == "SET_REMINDER"):
        set_reminder(data)
    if(action == "LIST_REMINDERS"):
        list_reminders()
    if(action == "REMOVE_REMINDER"):
        remove_reminder(data)
    if(action == "UPDATE_REMINDER"):
        update_reminder(data)


def open_app(app_name: Text):
    try:
        if app_name:
            result = open_application(app_name.lower())
            return {"text": result, "continue": False}
        else:
            return {"text": "Please provide a valid application name.", "continue": False}
    except Exception as e:
        return {"text": f"Failed to open {app_name}. Error: {str(e)}", "continue": False}
    
def search_browser(query: Text):
    if query:
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return {"text": f"Searching for '{query}' on Firefox...", "continue": False}
    else:
        return {"text": "I couldn't find a query to search for.", "continue": False}

def type_text(text: Text):
    if text:
        keyboard = Controller()

        # Simulate real typing effect
        for char in text:
            keyboard.type(char)
            time.sleep(0.05)  # Adjust typing speed if needed
        
        keyboard.press("\n")  # Simulates pressing Enter after typing
        keyboard.release("\n")

        return {"text": f"Typing: {text}", "continue": False}
    else:
        return {"text": "I didn't catch what you want me to type.", "continue": False}

def get_current_time():
    # Get current date and time in a friendly format
    current_time = datetime.now().strftime("%A, %d %B %Y - %I:%M %p")

    # Define multiple response variations
    responses = [
        f"The current date and time is {current_time}.",
        f"Right now, it's {current_time}.",
        f"As per my clock, it's {current_time}.",
        f"Currently, it's {current_time}. Hope that helps!",
        f"Time check! It's {current_time}.",
        f"Hey! It's {current_time}. Anything else?"
    ]

    # Choose a random response
    return {"text": random.choice(responses), "continue": False}

def meaning_of(word):
    if word:
        try:
            # Fetch a short summary from Wikipedia
            meaning = wikipedia.summary(word, sentences=1)

            # Randomized response for the meaning
            success_response = get_random_response("action_meaning_of", "success", word=word, meaning=meaning)
            # Ask if user wants to know more
            know_more_response = get_random_response("action_meaning_of", "offer_deep_dive")

            return {"text": f"{success_response}. {know_more_response}", "continue": True}

        except wikipedia.exceptions.DisambiguationError as e:
            return {"text": get_random_response("action_meaning_of", "disambiguation"), "continue": False}
        except wikipedia.exceptions.PageError:
            return {"text": get_random_response("action_meaning_of", "not_found"), "continue": False}

    else:
        # Randomized response when the word is missing
        return {"text": get_random_response("action_meaning_of", "missing_word"), "continue": False}

def open_browser(term):
    if term:
        url = f"https://en.wikipedia.org/wiki/{term.replace(' ', '_')}"
        webbrowser.open(url)

        return {"text": f"Opening more details about '{term}' in your browser.", "continue": False}
    else:
        return {"text": "I don't remember which word you wanted. Could you say it again?", "continue": False}

def get_weather(location):
    if not location:
        location = get_user_location()
        if not location:
            return {"text": "I couldn't detect your location. Please provide a city name.", "continue": False}

    # Fetch weather details
    weather_data = fetch_weather(location)

    if weather_data:
        temp = weather_data["main"]["temp"]
        condition = weather_data["weather"][0]["description"]
        return {"text": f"The current temperature in {location} is {temp}°C with {condition}.", "continue": False}
    else:
        return {"text": f"Sorry, I couldn't fetch the weather for {location}. Please check the city name and try again.", "continue": False}

def set_reminder(data):

    if not data or "||" not in data:
        return {"text": "I need both the task and the time for the reminder.", "continue": False}

    task, time_value = map(str.strip, data.split("||", 1))

    try:
        reminder_time = datetime.fromisoformat(time_value)
    except Exception as e:
        # print(f"[Reminder Parse Error] Couldn't parse time: {time_value}, error: {e}")
        return {"text": "I couldn't understand the time you mentioned. Try something like 'remind me at 5pm'.", "continue": False}

    reminders = load_reminders()
    reminders[task] = reminder_time.isoformat()
    save_reminders(reminders)

    # Schedule reminders
    ten_minutes_before = reminder_time - timedelta(minutes=10)
    schedule_reminder(task, ten_minutes_before.isoformat(), early=True)
    schedule_reminder(task, reminder_time.isoformat(), early=False)

    return {"text": f"✅ Reminder set for '{task}' at {reminder_time.strftime('%I:%M %p')}.", "continue": False}

def list_reminders():
    now = datetime.now(timezone.utc)  # make `now` timezone-aware in UTC
    reminders = load_reminders()
    active_reminders = {}

    for task, time_str in reminders.items():
        try:
            reminder_time = datetime.fromisoformat(time_str)

            # Ensure both are timezone-aware
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=timezone.utc)

            if reminder_time > now:
                active_reminders[task] = time_str
        except Exception as e:
            print(f"[Reminder Check] Failed to parse time for {task}: {e}")


    # Overwrite with filtered active ones
    save_reminders(active_reminders)

    if not active_reminders:
        return {"text": "You don't have any active reminders.", "continue": False}

    message = "Here are your current reminders:\n"
    follow_up_question = "Would you like to update the time for a task or remove one?"
    for task, time in active_reminders.items():
        formatted_time = datetime.fromisoformat(time).strftime('%I:%M %p')
        message += f"• {task} at {formatted_time}\n"
    
    message = message + ". " + follow_up_question

    return {"text": message, "continue": True}

def remove_reminder(task):
    reminders = load_reminders()

    if not reminders:
        return {"text": "You don't have any reminders set.", "continue": False}

    task_names = list(reminders.keys())
    best_match = difflib.get_close_matches(task, task_names, n=1, cutoff=0.5)

    if best_match:
        matched_task = best_match[0]

        # ❌ Remove from reminder list
        reminders.pop(matched_task)
        save_reminders(reminders)

        # ❌ Remove scheduled jobs
        remove_reminder(matched_task)

        return {"text": f"✅ Removed the reminder for '{matched_task}'.", "continue": False}
    else:
        return {"text": "I couldn't find a matching reminder to remove.", "continue": False}

def update_reminder(data):

    if not data or "||" not in data:
        return {"text": "Please specify both the task and the new time.", "continue": False}

    task, new_time = map(str.strip, data.split("||", 1))

    reminders = load_reminders()

    # 🔍 Fuzzy match task
    task_names = list(reminders.keys())
    best_match = difflib.get_close_matches(task, task_names, n=1, cutoff=0.5)

    if not best_match:
        return {"text": "I couldn't find a matching reminder to update.", "continue": False}

    matched_task = best_match[0]

    try:
        updated_time = datetime.fromisoformat(new_time)
    except Exception:
        # updated_time = datetime.now() + timedelta(minutes=30)
        return {"text": "Couldn't understand the new time. Please try again.", "continue": False}

    # 🔁 Update in the reminder JSON
    reminders[matched_task] = updated_time.isoformat()
    save_reminders(reminders)

    # 📆 Re-schedule the reminder with dual notifications
    schedule_reminder(matched_task, (updated_time - timedelta(minutes=10)).isoformat(), early=True)
    schedule_reminder(matched_task, updated_time.isoformat(), early=False)

    return {"text": f"🕒 Reminder for '{matched_task}' updated to {updated_time.strftime('%I:%M %p')}.", "continue": False}
