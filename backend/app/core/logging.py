"""Safe structured application logging."""

from __future__ import annotations

import logging
import sys
from typing import Any


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        stream=sys.stdout,
        format=LOG_FORMAT,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, **metadata: Any) -> None:
    safe_metadata = {key: value for key, value in metadata.items() if value is not None}
    logger.info("%s %s", event, safe_metadata) if safe_metadata else logger.info(event)
