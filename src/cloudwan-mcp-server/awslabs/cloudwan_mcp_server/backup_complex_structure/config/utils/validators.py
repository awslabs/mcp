"""
Validators for CloudWAN MCP configuration.
"""

import re


class ResolutionValidator:
    """Validator for screen resolution values."""

    @staticmethod
    def validate(value: str) -> bool:
        """
        Validate a resolution string.

        Args:
            value: Resolution string in format "WIDTHxHEIGHT"

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(value, str):
            return False

        pattern = r"^\d+x\d+$"
        if not re.match(pattern, value):
            return False

        width, height = map(int, value.lower().split("x"))
        return width >= 320 and height >= 240


def validate_aws_region(region: str) -> bool:
    """
    Validate AWS region format.

    Args:
        region: AWS region string

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(region, str) or not region:
        return False

    # Basic format check: region-name-number
    parts = region.split("-")
    if len(parts) < 3:
        return False

    # Check that last part is numeric
    try:
        int(parts[-1])
        return True
    except ValueError:
        return False


class TimeoutValidator:
    """Validator for timeout values."""

    @staticmethod
    def validate(value: int, min_value: int = 1, max_value: int = 3600) -> bool:
        """
        Validate a timeout value.

        Args:
            value: Timeout value in seconds
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(value, int):
            return False

        return min_value <= value <= max_value


__all__ = [
    "ResolutionValidator",
    "validate_aws_region",
    "TimeoutValidator",
]
