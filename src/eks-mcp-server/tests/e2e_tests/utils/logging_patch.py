"""Patch for logging_helper to work with mock context."""

import logging
from unittest.mock import patch
from awslabs.eks_mcp_server.logging_helper import LogLevel

logger = logging.getLogger(__name__)

def patched_log_with_request_id(ctx, level, message, **kwargs):
    """Patched version of log_with_request_id that works with mock context.
    
    Args:
        ctx: Mock context object with request_id attribute
        level: Log level
        message: Message to log
        **kwargs: Additional keyword arguments
    """
    # Get request_id from context if available, otherwise use a default
    request_id = getattr(ctx, 'request_id', 'e2e-test')
    
    # Format the log message with request_id
    log_message = f'[request_id={request_id}] {message}'
    
    # Log at the appropriate level
    if level == LogLevel.DEBUG:
        logger.debug(log_message, **kwargs)
    elif level == LogLevel.INFO:
        logger.info(log_message, **kwargs)
    elif level == LogLevel.WARNING:
        logger.warning(log_message, **kwargs)
    elif level == LogLevel.ERROR:
        logger.error(log_message, **kwargs)
    elif level == LogLevel.CRITICAL:
        logger.critical(log_message, **kwargs)

def apply_logging_patch():
    """Apply the patch to log_with_request_id."""
    patch_target = 'awslabs.eks_mcp_server.logging_helper.log_with_request_id'
    patch(patch_target, patched_log_with_request_id).start()
    logger.info("Applied patch to log_with_request_id")
