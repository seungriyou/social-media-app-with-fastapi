import logging
from logging.config import dictConfig

from socialapi.config import DevConfig, config


# custom filter for hiding emails
def obfuscated(email: str, obfuscated_length: int) -> str:
    characters = email[:obfuscated_length]
    first, last = email.split("@")
    return characters + ("*" * (len(first) - obfuscated_length)) + "@" + last


class EmailObfuscationFilter(logging.Filter):
    """
    for not logging some personal data(ex. emails) which are included in extra argument
    extra argument:
        ```
        logger.debug(query, extra={"email": "bob@example.net"})
        ```
        -> to log extra information that isn't included in formatting message
    """

    def __init__(self, name: str = "", obfuscated_length: int = 2) -> None:
        super().__init(name)
        self.obfuscated_length = obfuscated_length

    def filter(self, record: logging.LogRecord) -> bool:
        """
        If return true, the log record will be displayed.
        Otherwise, the log record will be filtered out.

        If you want to add new variables like "correlation_id", just set an attribute of record.
        ```
        record.your_variable = "123"
        ```
        This variable can be used in formatters.
        """
        if "email" in record.__dict__:
            record.email = obfuscated(record.email, self.obfuscated_length)
        return True


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {
                    # NOTE: same as `filter = asgi_correlation_id.CorrelationIdFilter(**kwargs)`
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 8 if isinstance(config, DevConfig) else 32,
                    "default_value": "-",
                },
                # add custom filter
                "email_obfuscation": {
                    "()": EmailObfuscationFilter,  # class -> use class // str -> import
                    "obfuscated_length": 2 if isinstance(config, DevConfig) else 0,
                },
            },
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    "format": "(%(correlation_id)s) %(name)s:%(lineno)d - %(message)s",
                },
                # file logs
                "file": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    # standard datetime format for file logs (ISO format standard) -> for analyzing
                    # when using json logger, just list variables (don't care the format)
                    "format": "%(asctime)s %(msecs)03d %(levelname)-8s %(correlation_id)s %(name)s %(lineno)d %(message)s",
                },
            },
            "handlers": {
                # NOTE: DO NOT limit any handler. DO limit with logger.
                "default": {
                    "class": "rich.logging.RichHandler",  # -- change to rich handler
                    "level": "DEBUG",
                    "formatter": "console",  # -- one of the "formatters"
                    "filters": ["correlation_id", "email_obfuscation"],
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
                    "filters": ["correlation_id", "email_obfuscation"],
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
