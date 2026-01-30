# scheduler_core.py
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# Get absolute path to reminder_jobs.sqlite inside data/
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # logic/src/
DB_PATH = os.path.join(SRC_DIR, "data", "reminders", "reminder_jobs.sqlite").replace("\\", "/")

scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{DB_PATH}")},
    executors={"default": ThreadPoolExecutor(10)},
    timezone="Asia/Kolkata"
)
scheduler.start()
