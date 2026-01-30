# Keep your action classes as is. No major changes are required for the actions themselves.
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from logic_integration import process
from typing import Any, Text, Dict, List

class ActionOpenApp(Action):
    def name(self) -> str:
        return "action_open_app"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        app_name = tracker.get_slot("app_name")
        
        if not app_name:
            app_name = ""

        response = process("OPEN_APP", app_name)
        dispatcher.utter_message(json_message=response)

        return []

class ActionSearchFirefox(Action):
    def name(self) -> str:
        return "action_search_firefox"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        query = tracker.get_slot("query")

        # Collect all query entities into a single query
        entity_queries = [
            entity.get("value") for entity in tracker.latest_message.get("entities", [])
            if entity.get("entity") == "query"
        ]
        
        if entity_queries:
            query = " ".join(entity_queries).strip()
            query = query.strip()
        
        if not query:
            query = ""
        
        response = process("SEARCH_BROWSER", query)
        dispatcher.utter_message(json_message=response)
        
        return []

class ActionTypeWhatISay(Action):
    def name(self) -> Text:
        return "action_type_what_i_say"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text_to_type = next(tracker.get_latest_entity_values("text"), None)

        # Collect all text entities into a single text
        entity_queries = [
            entity.get("value") for entity in tracker.latest_message.get("entities", [])
            if entity.get("entity") == "text"
        ]
        
        if entity_queries:
            text_to_type = " ".join(entity_queries).strip()
            text_to_type = text_to_type.strip()
        
        if not text_to_type:
            text_to_type = ""

        response = process("TYPE_TEXT", text_to_type)
        dispatcher.utter_message(json_message=response)

        return []

class ActionCurrentDateTime(Action):
    def name(self) -> str:
        return "action_current_date_time"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:

        response = process("GET_CURRENT_TIME", "")
        dispatcher.utter_message(json_message=response)

        return []

class ActionMeaningOf(Action):
    def name(self) -> str:
        return "action_meaning_of"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict) -> list:
        word = tracker.get_slot("words")

        if not word:
            word = ""

        response = process("GET_MEANING", word)
        dispatcher.utter_message(json_message=response)

        return []

class ActionOpenBrowser(Action):
    def name(self) -> str:
        return "action_open_browser"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        term = tracker.get_slot("words") # TODO may need to change to last_word

        if not term:
            term = ""

        response = process("OPEN_BROWSER", term)
        dispatcher.utter_message(json_message=response)

        return []

class ActionWeatherUpdate(Action):
    def name(self) -> Text:
        return "action_weather_update"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        # Extract location entity from user input
        location = None
        for entity in tracker.latest_message.get("entities", []):
            if entity.get("entity") == "GPE":
                location = entity.get("value")
                break

        # If location is not provided, get the user's current location
        if not location:
            location = ""

        response = process("GET_WEATHER", location)
        dispatcher.utter_message(json_message=response)

        return []
    
class ActionSetReminder(Action):
    def name(self) -> Text:
        return "action_set_reminder"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        task = tracker.get_slot("task_name") or next(tracker.get_latest_entity_values("task_name"), None)
        time_value = tracker.get_slot("time") or next(tracker.get_latest_entity_values("time"), None)

        if not task or not time_value:
            task = time_value = ""
            response = process("SET_REMINDER", "")
        else:
            response = process("SET_REMINDER", f"{task}||{time_value}")

        dispatcher.utter_message(json_message=response)

        return []

class ActionListReminders(Action):
    def name(self) -> Text:
        return "action_list_reminders"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        response = process("LIST_REMINDERS", "")
        dispatcher.utter_message(json_message=response)

        return []

class ActionRemoveReminder(Action):
    def name(self) -> Text:
        return "action_remove_reminder"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        task = next(tracker.get_latest_entity_values("task_name"), None)

        if not task:
            task = ""
        
        response = process("REMOVE_REMINDER", task)
        dispatcher.utter_message(json_message=response)
        
        return []

class ActionUpdateReminder(Action):
    def name(self) -> Text:
        return "action_update_reminder"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        task = next(tracker.get_latest_entity_values("task_name"), None)
        new_time = tracker.get_slot("time")


        if not task or not new_time:
            task = new_time = ""
            response = process("UPDATE_REMINDER", "")
            dispatcher.utter_message(text="Please specify both the task and the new time.")
            return []
        else: 
            response = process("UPDATE_REMINDER", f"{task}||{new_time}")
            
        dispatcher.utter_message(json_message=response)

        return []
