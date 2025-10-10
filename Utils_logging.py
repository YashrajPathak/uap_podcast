"""
logging.py — Centralized logging configuration for the podcast system.

This module:
- Configures a global logger with colorized console output
- Supports structured JSON logs for production if needed
- Provides helper methods for logging at different levels
"""

import logging
import sys
import os
from datetime import datetime

# --------------------------------------------------------------------------
# 🎨 Log formatting (colorful for local dev, clean for production)
# --------------------------------------------------------------------------

class ColorFormatter(logging.Formatter):
    """Custom formatter with ANSI colors for different log levels."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        level_name = f"{color}{record.levelname}{self.RESET}"
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level_name}] {record.name}: {record.getMessage()}"

# --------------------------------------------------------------------------
# 🛠️ Base logger setup
# --------------------------------------------------------------------------

def _create_logger(name: str = "uap_podcast") -> logging.Logger:
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if re-imported
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if os.getenv("DEBUG", "0") == "1" else logging.INFO)

    # Stream handler (console output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColorFormatter())

    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

# Global logger instance
logger = _create_logger()

# --------------------------------------------------------------------------
# ✅ Helper shortcut functions (recommended for imports)
# --------------------------------------------------------------------------

def debug(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

# --------------------------------------------------------------------------
# 📦 Optional: Switch to JSON logging for production (e.g., Kubernetes/ELK)
# --------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return (
            f'{{"timestamp": "{datetime.fromtimestamp(record.created).isoformat()}", '
            f'"level": "{record.levelname}", '
            f'"logger": "{record.name}", '
            f'"message": "{record.getMessage()}"}}'
        )

def enable_json_logging():
    """Switch to JSON logging — useful in containerized production environments."""
    for handler in logger.handlers:
        handler.setFormatter(JSONFormatter())

# --------------------------------------------------------------------------
# ✅ Quick self-test
# --------------------------------------------------------------------------

if __name__ == "__main__":
    debug("Debug message: Podcast system starting up...")
    info("Info message: Configuration loaded.")
    warning("Warning message: Latency above threshold.")
    error("Error message: Audio synthesis failed.")
    critical("Critical message: Unable to contact LLM service.")
