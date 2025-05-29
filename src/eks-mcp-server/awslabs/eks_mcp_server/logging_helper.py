# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Logging helper for the EKS MCP Server."""

from enum import Enum
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any


class LogLevel(Enum):
    """Enum for log levels."""

    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


def log_with_request_id(ctx: Context, level: LogLevel, message: str, **kwargs: Any) -> None:
    """Log a message with the request ID from the context.

    Args:
        ctx: The MCP context containing the request ID
        level: The log level (from LogLevel enum)
        message: The message to log
        **kwargs: Additional fields to include in the log message
    """
    # Format the log message with request_id
    log_message = f'[request_id={ctx.request_id}] {message}'

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
