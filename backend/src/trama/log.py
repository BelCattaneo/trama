import logging

import structlog


def configure_logging(level: str) -> None:
    level_name = level.upper()
    logging.basicConfig(format="%(message)s", level=level_name)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level_name]
        ),
        cache_logger_on_first_use=True,
    )
