"""
Configuration validation utilities.

Provides validators and constraints for configuration values.
"""

import logging

logger = logging.getLogger(__name__)


class ResolutionValidator:
    """Validators for display resolution configurations."""

    COMMON_WIDTHS = [800, 1024, 1280, 1600, 1920, 2560, 3200, 3840]
    COMMON_HEIGHTS = [600, 768, 800, 900, 1080, 1440, 1600, 2160]

    @staticmethod
    def validate_width(v: int) -> int:
        """Validate and warn about non-standard widths."""
        if v not in ResolutionValidator.COMMON_WIDTHS:
            logger.warning(
                f"Non-standard width {v}px. Consider using standard widths: "
                f"{ResolutionValidator.COMMON_WIDTHS}"
            )
        return v

    @staticmethod
    def validate_height(v: int) -> int:
        """Validate and warn about non-standard heights."""
        if v not in ResolutionValidator.COMMON_HEIGHTS:
            logger.warning(
                f"Non-standard height {v}px. Consider using standard heights: "
                f"{ResolutionValidator.COMMON_HEIGHTS}"
            )
        return v

    @staticmethod
    def validate_aspect_ratio(width: int, height: int) -> tuple[int, int]:
        """Validate aspect ratio is reasonable."""
        ratio = width / height
        common_ratios = {"4:3": 1.33, "16:9": 1.78, "16:10": 1.6, "21:9": 2.33}

        # Find closest common ratio
        closest_ratio = min(common_ratios.items(), key=lambda x: abs(x[1] - ratio))

        if abs(ratio - closest_ratio[1]) > 0.1:
            logger.warning(
                f"Unusual aspect ratio {ratio:.2f} ({width}x{height}). "
                f"Closest common ratio is {closest_ratio[0]} ({closest_ratio[1]:.2f})"
            )

        return width, height


class NetworkValidator:
    """Validators for network-related configurations."""

    @staticmethod
    def validate_cidr(cidr: str) -> str:
        """Validate CIDR notation."""
        import ipaddress

        try:
            ipaddress.ip_network(cidr, strict=True)
            return cidr
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation '{cidr}': {e}")

    @staticmethod
    def validate_port(port: int) -> int:
        """Validate network port."""
        if not 1 <= port <= 65535:
            raise ValueError(f"Port {port} must be between 1 and 65535")

        # Warn about well-known ports
        if port < 1024:
            logger.warning(f"Port {port} is in the well-known range (< 1024)")

        return port


class TimeoutValidator:
    """Validators for timeout configurations."""

    @staticmethod
    def validate_timeout(timeout: int, context: str = "operation") -> int:
        """Validate timeout values with context-aware limits."""
        min_timeout = 1
        max_timeout = 300  # 5 minutes

        if not min_timeout <= timeout <= max_timeout:
            raise ValueError(
                f"Timeout for {context} must be between {min_timeout} "
                f"and {max_timeout} seconds, got {timeout}"
            )

        # Context-specific warnings
        if context == "api_call" and timeout > 30:
            logger.warning(
                f"API call timeout of {timeout}s is high. "
                "Consider 10-30s for most AWS API calls."
            )
        elif context == "batch_operation" and timeout < 60:
            logger.warning(
                f"Batch operation timeout of {timeout}s might be too low. "
                "Consider 60-300s for batch operations."
            )

        return timeout


class ResourceLimitValidator:
    """Validators for resource limits and quotas."""

    AWS_SERVICE_LIMITS = {
        "ec2_describe_instances": 1000,
        "vpc_describe_vpcs": 100,
        "networkmanager_describe_global_networks": 100,
        "concurrent_api_calls": 10,
        "tags_per_resource": 50,
    }

    @staticmethod
    def validate_batch_size(size: int, operation: str) -> int:
        """Validate batch size against AWS limits."""
        limit = ResourceLimitValidator.AWS_SERVICE_LIMITS.get(operation, 100)  # Default limit

        if size > limit:
            raise ValueError(
                f"Batch size {size} exceeds AWS limit of {limit} " f"for operation '{operation}'"
            )

        # Warn about efficiency
        if size < limit * 0.1:  # Less than 10% of limit
            logger.warning(
                f"Batch size {size} is small for '{operation}' "
                f"(limit: {limit}). Consider larger batches for efficiency."
            )

        return size

    @staticmethod
    def validate_concurrency(concurrency: int, context: str = "general") -> int:
        """Validate concurrency limits."""
        max_concurrency = {
            "regions": 10,
            "api_calls": 20,
            "file_operations": 5,
            "general": 50,
        }.get(context, 50)

        if concurrency > max_concurrency:
            raise ValueError(
                f"Concurrency {concurrency} exceeds recommended limit "
                f"of {max_concurrency} for {context}"
            )

        return concurrency


def validate_aws_region(region: str) -> str:
    """Validate AWS region name."""
    # Current AWS regions (as of 2024)
    valid_regions = {
        # US
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        # EU
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-central-1",
        "eu-north-1",
        "eu-south-1",
        "eu-central-2",
        # Asia Pacific
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-southeast-3",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-south-1",
        "ap-south-2",
        "ap-east-1",
        # Other
        "ca-central-1",
        "sa-east-1",
        "me-south-1",
        "me-central-1",
        "af-south-1",
        "il-central-1",
    }

    if region not in valid_regions:
        # Check if it's a valid format at least
        import re

        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", region):
            raise ValueError(
                f"Invalid AWS region format: '{region}'. "
                f"Expected format: 'xx-xxxx-#' (e.g., 'us-east-1')"
            )
        else:
            logger.warning(
                f"Region '{region}' is not in the known regions list. "
                "It may be a new region or GovCloud/China region."
            )

    return region


def validate_resource_tag(key: str, value: str) -> tuple[str, str]:
    """Validate AWS resource tags."""
    # AWS tag restrictions
    if len(key) > 128:
        raise ValueError(f"Tag key length {len(key)} exceeds AWS limit of 128")
    if len(value) > 256:
        raise ValueError(f"Tag value length {len(value)} exceeds AWS limit of 256")

    # Check for aws: prefix (reserved)
    if key.lower().startswith("aws:"):
        raise ValueError(f"Tag key '{key}' uses reserved 'aws:' prefix")

    # Check for valid characters
    import re

    valid_pattern = r"^[\w\s\+\-=\._:/@]*$"
    if not re.match(valid_pattern, key):
        raise ValueError(f"Tag key '{key}' contains invalid characters")
    if not re.match(valid_pattern, value):
        raise ValueError(f"Tag value '{value}' contains invalid characters")

    return key, value
