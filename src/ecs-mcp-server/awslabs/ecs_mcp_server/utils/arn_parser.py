"""
ARN parser utility for AWS resources.

This module provides functions to parse and validate AWS ARNs (Amazon Resource Names).
"""

import re
from typing import NamedTuple, Optional


class ParsedArn(NamedTuple):
    """Structured representation of an AWS ARN."""

    partition: str
    service: str
    region: str
    account: str
    resource_type: Optional[str]
    resource_id: str

    @property
    def resource_name(self) -> str:
        """Extract resource name from resource_id."""
        # Handle different resource ID formats
        if "/" in self.resource_id:
            return self.resource_id.split("/")[-1]
        if ":" in self.resource_id:
            return self.resource_id.split(":")[-1]
        return self.resource_id


def parse_arn(arn: str) -> Optional[ParsedArn]:
    """
    Parse an AWS ARN string into structured components.

    Examples:
        - Task Definition: arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1
        - Cluster: arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster
        - Service: arn:aws:ecs:us-west-2:123456789012:service/test-app-service

    Returns:
        ParsedArn object or None if the ARN is invalid
    """
    if not arn or not isinstance(arn, str):
        return None

    # Basic format: arn:partition:service:region:account-id:resource-id
    # or: arn:partition:service:region:account-id:resource-type/resource-id
    arn_pattern = r"^arn:([^:]*):([^:]*):([^:]*):([^:]*):(.*)$"
    match = re.match(arn_pattern, arn)

    if not match:
        return None

    partition, service, region, account, resource_path = match.groups()

    # Handle resource path which can be either resource-id or resource-type/resource-id
    resource_parts = resource_path.split("/", 1)
    if len(resource_parts) == 2:
        resource_type, resource_id = resource_parts
    else:
        # Handle cases like S3 where format is arn:aws:s3:::bucket-name
        resource_type_parts = resource_parts[0].split(":", 1)
        if len(resource_type_parts) == 2:
            resource_type, resource_id = resource_type_parts
        else:
            resource_type = None
            resource_id = resource_parts[0]

    return ParsedArn(
        partition=partition,
        service=service,
        region=region,
        account=account,
        resource_type=resource_type,
        resource_id=resource_id,
    )


def is_ecs_task_definition(arn: str) -> bool:
    """Check if ARN is for an ECS task definition."""
    parsed = parse_arn(arn)
    return bool(parsed and parsed.service == "ecs" and parsed.resource_type == "task-definition")


def is_ecs_cluster(arn: str) -> bool:
    """Check if ARN is for an ECS cluster."""
    parsed = parse_arn(arn)
    return bool(parsed and parsed.service == "ecs" and parsed.resource_type == "cluster")


def get_task_definition_name(arn: str) -> Optional[str]:
    """
    Extract the task definition name from an ECS task definition ARN.
    Returns None if the ARN is not a valid ECS task definition ARN.
    """
    parsed = parse_arn(arn)
    if not parsed or parsed.service != "ecs" or parsed.resource_type != "task-definition":
        return None
    return parsed.resource_name


def get_resource_name(arn: str) -> Optional[str]:
    """
    Extract the resource name from an ARN, regardless of service or type.
    Returns None if the ARN is invalid.
    """
    parsed = parse_arn(arn)
    if not parsed:
        return None
    return parsed.resource_name
