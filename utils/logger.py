# utils/logger.py
import logging
import logging.config
from config import DEBUG


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # preserve existing loggers
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if DEBUG else "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG" if DEBUG else "INFO",
            "formatter": "detailed",
            "filename": "logging.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "root": {
        "level": "DEBUG" if DEBUG else "INFO",
        "handlers": ["console", "file"],
    },
    # Optionally, set levels for module-specific loggers
    "loggers": {
        "db": {
            "level": "INFO",  # example: always log INFO for database operations
            "handlers": ["file"],
            "propagate": False,
        },
        "utils": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Apply configuration immediately if desired
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
logger.info("Logging configured; DEBUG mode is %s", DEBUG)
