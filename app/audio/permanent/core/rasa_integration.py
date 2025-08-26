import requests

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

def process_command(command, sender="user1"):
    """
    Sends the command to Rasa and gets the response.

    :param command: User's voice command.
    :param sender: Unique sender ID to identify the conversation.
    :return: List of response texts and a flag indicating whether to continue the conversation.
    """
    payload = {"sender": sender, "message": command}

    try:
        response = requests.post(RASA_URL, json=payload)
        response_data = response.json()
        messages = []
        continue_conversation = False

        if response_data:
            print("======================= response data =======================")
            print(response_data)

            for message in response_data:
                # Case 1: Response has a direct "text" key
                if "text" in message:
                    messages.append(message["text"])

                # Case 2: Response is inside "custom"
                elif "custom" in message:
                    custom_data = message["custom"]
                    if "text" in custom_data:
                        messages.append(custom_data["text"])
                    if custom_data.get("continue"):  # Check "continue" flag
                        continue_conversation = True

            print("======================= response =======================")
            for msg in messages:
                print(msg)
            print(f"Continue conversation: {continue_conversation}")

            return messages, continue_conversation
        else:
            return ["Sorry, I didn't understand that."], False

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to Rasa: {e}")
        return ["I'm having trouble connecting to the server."], False
