from pathlib import Path
import logging

from django.conf import settings


LOG_FILENAME = "dispolive.log"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_dispolive_logger() -> logging.Logger:
    """Return a configured logger that stores Dispolive API events to file."""
    logger = logging.getLogger("documents.dispolive")
    if logger.handlers:
        return logger

    log_dir = Path(settings.BASE_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_dir / LOG_FILENAME, encoding="utf-8")
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
