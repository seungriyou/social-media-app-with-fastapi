from logging.config import dictConfig

from socialapi.config import DevConfig, config


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    "format": "%(name)s:%(lineno)d - %(message)s",
                },
                # file logs
                "file": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    # standard datetime format for file logs (ISO format standard) -> for analyzing
                    "format": "%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
                },
            },
            "handlers": {
                # NOTE: DO NOT limit any handler. DO limit with logger.
                "default": {
                    "class": "rich.logging.RichHandler",  # -- change to rich handler
                    "level": "DEBUG",
                    "formatter": "console",  # -- one of the "formatters"
                },
                # when file size reaches certain size...
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "file",  # -- one of the "formatters"
                    "filename": "socialapi.log",
                    # should calculate the disk size to decide maxBytes & backupCount
                    "maxBytes": 1024 * 1024,  # 1MB per file
                    "backupCount": 5,  # 5 files
                    "encoding": "utf8",
                },
            },
            "loggers": {
                # socialapi is the top level in this logger hierarchy
                "socialapi": {  # -- name of the top directory
                    "handlers": [
                        "default",
                        "rotating_file",
                    ],  # -- some of the "handlers"
                    "level": "DEBUG"
                    if isinstance(config, DevConfig)
                    else "INFO",  # -- "DEBUG" level only in dev mode
                    "propagate": False,  # -- socialapi logger doesn't send any logs to its parent(= root)
                },
                # for packages (for better readability & easily saving to files)
                "uvicorn": {"handlers": ["default", "rotating_file"], "level": "INFO"},
                "databases": {"handlers": ["default"], "level": "WARNING"},
                "aiosqlite": {"handlers": ["default"], "level": "WARNING"},
            },
        }
    )
