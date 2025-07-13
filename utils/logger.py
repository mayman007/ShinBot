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
        "library": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if DEBUG else "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "console_library": {
            "class": "logging.StreamHandler",
            "level": "WARNING",  # Show warnings and errors from libraries
            "formatter": "library",
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
        "level": "WARNING",  # Set to WARNING to catch library errors
        "handlers": ["console_library", "file"],
    },
    # Module-specific loggers
    "loggers": {
        "db": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "utils": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        # Your bot's main modules
        "handlers": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "__main__": {
            "level": "DEBUG" if DEBUG else "INFO", 
            "handlers": ["console", "file"],
            "propagate": False,
        },
        # Third-party library loggers - show their errors/warnings
        "pyrogram": {
            "level": "WARNING",
            "handlers": ["console_library", "file"],
            "propagate": False,
        },
        "httpx": {
            "level": "WARNING", 
            "handlers": ["console_library", "file"],
            "propagate": False,
        },
        "yt_dlp": {
            "level": "WARNING",
            "handlers": ["console_library", "file"], 
            "propagate": False,
        },
        "aiosqlite": {
            "level": "WARNING",
            "handlers": ["console_library", "file"],
            "propagate": False,
        },
        "asyncio": {
            "level": "WARNING",
            "handlers": ["console_library", "file"],
            "propagate": False,
        },
        "telegram": {
            "level": "WARNING",
            "handlers": ["console_library", "file"],
            "propagate": False,
        },
    },
}

# Apply configuration immediately if desired
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
logger.info("Logging configured; DEBUG mode is %s", DEBUG)
