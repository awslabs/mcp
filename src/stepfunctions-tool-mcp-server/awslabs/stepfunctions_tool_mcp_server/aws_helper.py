"""AWS Helper for Step Functions Tool MCP Server."""

import boto3
import botocore.config
import os
from typing import Any, Optional


class AwsHelper:
    """Helper class for AWS operations."""

    @staticmethod
    def get_aws_region() -> Optional[str]:
        """Get AWS region from environment variable.

        Returns:
            str: AWS region if set in environment, None otherwise
        """
        return os.environ.get('AWS_REGION', 'us-east-1')

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get AWS profile from environment variable.

        Returns:
            str: AWS profile if set in environment, None otherwise
        """
        return os.environ.get('AWS_PROFILE')

    @staticmethod
    def create_boto3_client(service_name: str, region_name: Optional[str] = None) -> Any:
        """Create a boto3 client with the appropriate configuration.

        Args:
            service_name: AWS service name (e.g., 'stepfunctions', 'schemas')
            region_name: Optional region override

        Returns:
            boto3.client: Configured boto3 client
        """
        from awslabs.stepfunctions_tool_mcp_server.server import __version__

        # Create config with user agent
        config = botocore.config.Config(
            user_agent_extra=f'awslabs/mcp/aws-stepfunctions-tool-mcp-server/{__version__}'
        )

        # Get profile and region
        profile = AwsHelper.get_aws_profile()
        region = region_name or AwsHelper.get_aws_region()

        # Create client with or without profile
        if profile:
            session = boto3.Session(profile_name=profile)
            return session.client(service_name, region_name=region, config=config)
        else:
            return boto3.client(service_name, region_name=region, config=config)
