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

"""AWS helper for the EKS MCP Server."""

import boto3
import os
from botocore.config import Config
from typing import Any, Optional


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and profile management and client creation.
    """

    @staticmethod
    def get_aws_region() -> Optional[str]:
        """Get the AWS region from the environment if set."""
        return os.environ.get('AWS_REGION')

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get the AWS profile from the environment if set."""
        return os.environ.get('AWS_PROFILE')

    @classmethod
    def create_boto3_client(cls, service_name: str, region_name: Optional[str] = None) -> Any:
        """Create a boto3 client with the appropriate profile and region.

        The client is configured with a custom user agent suffix 'awslabs/mcp/eks-mcp-server/0.1.0'
        to identify API calls made by the EKS MCP Server.

        Args:
            service_name: The AWS service name (e.g., 'ec2', 's3', 'eks')
            region_name: Optional region name override

        Returns:
            A boto3 client for the specified service
        """
        # Get region from parameter or environment if set
        region: Optional[str] = region_name if region_name is not None else cls.get_aws_region()

        # Get profile from environment if set
        profile = cls.get_aws_profile()

        # Create config with user agent suffix
        config = Config(user_agent_extra='awslabs/mcp/eks-mcp-server/0.1.0')

        # Create session with profile if specified
        if profile:
            session = boto3.Session(profile_name=profile)
            if region is not None:
                return session.client(service_name, region_name=region, config=config)
            else:
                return session.client(service_name, config=config)
        else:
            if region is not None:
                return boto3.client(service_name, region_name=region, config=config)
            else:
                return boto3.client(service_name, config=config)
