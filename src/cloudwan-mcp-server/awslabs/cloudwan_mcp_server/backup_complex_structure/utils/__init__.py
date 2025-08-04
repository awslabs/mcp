"""
Utility modules for CloudWAN MCP Server.

This package contains reusable utilities for AWS operations,
validation, and common patterns.
"""

from .aws_operations import (
    handle_aws_errors,
    search_across_regions,
    aws_client_context,
    retry_aws_operation,
    batch_aws_operations,
    format_aws_tags,
    parse_arn,
    AWSOperationError,
    MultiRegionOperationError,
)

from .validators import (
    ResolutionValidator,
    NetworkValidator,
    TimeoutValidator,
    ResourceLimitValidator,
    validate_aws_region,
    validate_resource_tag,
)

__all__ = [
    # AWS operations
    "handle_aws_errors",
    "search_across_regions",
    "aws_client_context",
    "retry_aws_operation",
    "batch_aws_operations",
    "format_aws_tags",
    "parse_arn",
    "AWSOperationError",
    "MultiRegionOperationError",
    # Validators
    "ResolutionValidator",
    "NetworkValidator",
    "TimeoutValidator",
    "ResourceLimitValidator",
    "validate_aws_region",
    "validate_resource_tag",
]
