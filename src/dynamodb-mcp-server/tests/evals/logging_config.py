"""Centralized logging configuration for DynamoDB MCP evaluation system."""

import logging
import sys
from typing import Optional


def setup_evaluation_logging(
    level: str = 'INFO', log_file: Optional[str] = None, console_output: bool = True
) -> logging.Logger:
    """Configure logging for evaluation system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
        console_output: Whether to output to console

    Returns:
        Configured logger instance
    """
    # Create formatter with timestamps and structured format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger for evaluation system
    root_logger = logging.getLogger('dynamodb_evals')
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (preserves emoji-rich user experience)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate messages
    root_logger.propagate = False

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    # Create hierarchical logger name
    if not name.startswith('dynamodb_evals'):
        if name == '__main__':
            logger_name = 'dynamodb_evals.main'
        else:
            # Extract module name from full path
            module_name = name.split('.')[-1] if '.' in name else name
            logger_name = f'dynamodb_evals.{module_name}'
    else:
        logger_name = name

    return logging.getLogger(logger_name)


# Convenience function for quick setup
def init_logging(level: str = 'INFO', log_file: Optional[str] = None) -> None:
    """Initialize logging with default configuration."""
    setup_evaluation_logging(level=level, log_file=log_file)
