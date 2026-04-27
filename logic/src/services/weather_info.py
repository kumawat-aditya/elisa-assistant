import logging
import requests

logger = logging.getLogger(__name__)

def fetch_weather(location: str) :
    """Fetches weather data from OpenWeatherMap API"""
    api_key = "b80e877092745687574e38e26b612a42"  # Replace with your OpenWeatherMap API key
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": api_key, "units": "metric"}

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def get_user_location() :
    """Gets the user's current location based on IP address"""
    try:
        response = requests.get("https://ipinfo.io/json")
        if response.status_code == 200:
            data = response.json()
            return data.get("city", "Unknown")
    except Exception as e:
        logger.error("Error fetching user location: %s", e)
    return None
