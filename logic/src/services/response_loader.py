import yaml
import random
import os

# Compute absolute path to responses.yml
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # logic/src/
RESPONSES_PATH = os.path.join(SRC_DIR, "data", "responses.yml")

# Load YAML responses once
with open(RESPONSES_PATH, encoding='utf-8') as file:
    RESPONSES_YML = yaml.safe_load(file)

def get_random_response(action: str, response_type: str, **kwargs) -> dict:
    section = RESPONSES_YML.get(action, {}).get(response_type, {})
    responses = section.get("responses", [])
    continue_chat = section.get("continue", False)

    if not responses:
        return {"text": "Oops! Something went wrong.", "continue": False}

    response = random.choice(responses)
    return {
        "text": response.format(**kwargs),
        "continue": continue_chat
    }