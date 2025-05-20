"""Logging utilities for AWS Lambda MCP Server."""

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Default log directory in system's temporary directory
DEFAULT_LOG_DIR = os.path.join(tempfile.gettempdir(), 'aws-lambda-mcp-server-logs')
# Create the default log directory if it doesn't exist
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)

# Current log directory (can be overridden)
LOG_DIR = DEFAULT_LOG_DIR

def set_log_directory(directory: str) -> str:
    """
    Set a custom log directory.
    
    Args:
        directory: Path to the log directory
    
    Returns:
        str: Path to the log directory
    """
    global LOG_DIR
    directory_path = Path(directory)
    
    # Create the directory if it doesn't exist
    os.makedirs(directory_path, exist_ok=True)
    
    LOG_DIR = str(directory_path)
    
    # Reconfigure the root logger with the new log file
    _configure_root_logger()
    
    return LOG_DIR

def get_log_directory() -> str:
    """
    Get the current log directory.
    
    Returns:
        str: Path to the log directory
    """
    return LOG_DIR

def _configure_root_logger():
    """Configure the root logger with both console and file handlers."""
    # Create a log file path
    log_file = os.path.join(LOG_DIR, 'aws-lambda-mcp-server.log')
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file)
        ]
    )

# Initialize the root logger
_configure_root_logger()

class Logger:
    """Logger class for AWS Lambda MCP Server."""
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize a logger with the given name.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name or __name__)
    
    def debug(self, message: str, *args, **kwargs):
        """Log a debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log an info message."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log an error message."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log a critical message."""
        self.logger.critical(message, *args, **kwargs)

# Create a default logger instance
logger = Logger("aws-lambda-mcp-server")
