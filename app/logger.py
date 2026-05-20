import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - " "%(filename)s:%(lineno)d - %(message)s"
)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

# Create logger
logger = logging.getLogger("app")

# File handler
file_handler = RotatingFileHandler(
    f"{LOG_DIR}/app.log", maxBytes=5 * 1024 * 1024, backupCount=5
)

file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(file_handler)

logger.setLevel(logging.INFO)
