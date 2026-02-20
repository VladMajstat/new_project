import logging

# === ЛОГИРОВАНИЕ ===
LOG_FILE = "scraper.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def setup_logging():
    """
    Настройка логирования для всего проекта
    """
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
