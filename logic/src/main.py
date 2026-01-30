from fastapi import FastAPI
from pydantic import BaseModel
from routes.logic import process  # Import our logic router
import logging
import sys


# Configure root logger with stream handler explicitly
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create the FastAPI app instance
app = FastAPI(title="Logic Service")

# Define the structure of the incoming request body
class Request(BaseModel):
    action: str
    data: str
    # conversation_id: str = "default" # Optional ID to track conversations

# This is a special event handler that runs when the server starts up.
# It's the perfect place to load our heavy NLP model once.
@app.on_event("startup")
def startup_event():
    # logic.initialize_nlp()
    pass

# Define our main API endpoint
@app.post("/process")
def parse_text(request: Request):
    """
    recieves data from rasa/actions/actions.py and processes it using logic.py
    """
    # Call the main processing function from our logic module
    response = process(request.action, request.data)
    logger.debug("request data processed successfully")
    logger.debug(f"response: {response}")
    return response

# A simple root endpoint to check if the server is running
@app.get("/")
def read_root():
    return {"status": "Logic Service is running."}