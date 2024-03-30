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
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console",  # -- one of the "formatters"
                }
            },
            "loggers": {
                # socialapi is the top level in this logger hierarchy
                "socialapi": {  # -- name of the top directory
                    "handlers": ["default"],  # -- some of the "handlers"
                    "level": "DEBUG"
                    if isinstance(config, DevConfig)
                    else "INFO",  # -- "DEBUG" level only in dev mode
                    "propagate": False,  # -- socialapi logger doesn't send any logs to its parent(= root)
                }
            },
        }
    )
