import logging
import os
from config import LOG_FILE

# Create logs folder if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logger = logging.getLogger("SLMS")

if not logger.hasHandlers():
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)