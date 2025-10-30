import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration for the application."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    daily_filename = f"tf2avm_{datetime.now():%Y%m%d}.log"
    file_path = log_dir / daily_filename
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)