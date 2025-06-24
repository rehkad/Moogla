import logging
import os


def configure_logging(level: str | None = None) -> None:
    """Configure root logging level from argument or environment."""
    level_str = level or os.getenv("MOOGLA_LOG_LEVEL", "INFO")
    level_value = getattr(logging, level_str.upper(), logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level_value, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    else:
        logging.getLogger().setLevel(level_value)

