"""Logging configuration."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with consistent formatting across all modules."""
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("garmin_to_notion")
    root.setLevel(level)
    root.addHandler(handler)
