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

"""Configuration utilities following AWS Labs patterns."""

import os
from typing import Any


def validate_configuration(config: dict[str, Any]) -> bool:
    """Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    if not isinstance(config, dict):
        return False

    required_fields = ["aws_region"]

    # Check required fields
    for field in required_fields:
        if field not in config:
            return False

    # Validate aws_region format
    aws_region = config.get("aws_region")
    if not aws_region or not isinstance(aws_region, str):
        return False

    # Validate log_level if present
    log_level = config.get("log_level")
    if log_level:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            return False

    return True


def get_aws_region() -> str | None:
    """Get AWS region from environment variables.

    Returns:
        AWS region string or None if not found
    """
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"  # Default fallback
    )


def get_aws_profile() -> str | None:
    """Get AWS profile from environment variables.

    Returns:
        AWS profile string or None if not found
    """
    return os.environ.get("AWS_PROFILE")


def load_configuration() -> dict[str, Any]:
    """Load configuration from environment variables.

    Returns:
        Configuration dictionary
    """
    return {
        "aws_region": get_aws_region(),
        "aws_profile": get_aws_profile(),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    }


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value with fallback.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    config = load_configuration()
    return config.get(key, default)
