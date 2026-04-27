import logging
import requests

logger = logging.getLogger(__name__)

LOGIC_URL = "http://localhost:8021/process"

def process(action, data=""):
    """
    Sends the command to LOGIC layer and gets the response.

    :param action: User's voice command.
    :param data: data associated with the command.
    :return: response from LOGIC layer.
    """
    payload = {"action": action, "data": data}

    try:
        response = requests.post(LOGIC_URL, json=payload)
        response_data = response.json()

        if response_data:
            logger.debug("Logic layer response: %s", response_data)

            text = [response_data.get("text", "")]
            continue_conversation = response_data.get("continue", False)

            return {"text": text, "continue": continue_conversation}
        else:
            return {"text": "No response from logic layer.", "continue": False}

    except requests.exceptions.RequestException as e:
        logger.error("Error sending request to logic layer: %s", e)
        return {"text": "I'm having trouble connecting to the LOGIC layer.", "continue": False}

