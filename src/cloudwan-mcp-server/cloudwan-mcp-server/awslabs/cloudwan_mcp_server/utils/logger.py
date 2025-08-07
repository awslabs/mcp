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

import logging
import sys


def get_logger(name: str):
    """Get logger instance following AWS Labs patterns.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance with standard AWS Labs configuration
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Configure standard logging for AWS Labs standards
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def configure_logging(level: str = "INFO"):
    """Configure global logging level.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        stream=sys.stderr
    )


# Create a default logger instance for backward compatibility
logger = get_logger(__name__)
