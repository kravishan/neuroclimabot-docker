"""
Clean logging configuration - minimal console output, warnings/errors to file.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

def setup_logging(settings) -> logging.Logger:
    """Setup clean console + file logging."""
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handlers = []
    
    # Console handler - clean format (no timestamp/name)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    handlers.append(console_handler)
    
    # File handler - warnings/errors only
    try:
        file_handler = RotatingFileHandler(
            "logs/neuroclima.log", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        ))
        file_handler.setLevel(logging.WARNING)
        handlers.append(file_handler)
    except Exception:
        pass  # Continue without file logging
    
    # Configure logging
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper()), handlers=handlers, force=True)
    
    # Silence third-party loggers
    for lib in ["urllib3", "requests", "milvus", "httpx", "transformers", "torch"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    return logging.getLogger("neuroclima")

def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)