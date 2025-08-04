# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Logger utilities following AWS Labs patterns."""

import sys
from loguru import logger as _logger


def get_logger(name: str):
    """Get logger instance following AWS Labs patterns.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance with standard AWS Labs configuration
    """
    # Configure loguru logger for AWS Labs standards
    _logger.remove()  # Remove default handler
    _logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Return logger with context
    return _logger.bind(name=name)


def configure_logging(level: str = "INFO"):
    """Configure global logging level.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    _logger.remove()
    _logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level
    )