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

"""
AWS utilities for the EC2 MCP Server.
"""

import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class AWSClientManager:
    """Manages AWS client instances with proper error handling."""

    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        """
        Initialize the AWS client manager.

        Args:
            region: AWS region to use
            profile: AWS profile to use (optional)
        """
        self.region = region
        self.profile = profile
        self._session = None
        self._clients = {}

    def _get_session(self) -> boto3.Session:
        """Get or create a boto3 session."""
        if self._session is None:
            try:
                if self.profile:
                    self._session = boto3.Session(profile_name=self.profile)
                else:
                    self._session = boto3.Session()
            except Exception as e:
                logger.error(f"Failed to create AWS session: {e}")
                raise

        return self._session

    def get_client(self, service: str) -> Any:
        """
        Get or create an AWS client for the specified service.

        Args:
            service: AWS service name (e.g., 'ec2', 'iam', 'cloudformation')

        Returns:
            AWS client instance

        Raises:
            NoCredentialsError: If AWS credentials are not configured
            ClientError: If there's an error creating the client
        """
        if service not in self._clients:
            try:
                session = self._get_session()
                self._clients[service] = session.client(service, region_name=self.region)
                logger.debug(f"Created {service} client for region {self.region}")
            except NoCredentialsError:
                logger.error("AWS credentials not found. Please configure your credentials.")
                raise
            except Exception as e:
                logger.error(f"Failed to create {service} client: {e}")
                raise

        return self._clients[service]

    def test_credentials(self) -> Dict[str, Any]:
        """
        Test AWS credentials by making a simple API call.

        Returns:
            Dict containing test results
        """
        try:
            sts_client = self.get_client("sts")
            identity = sts_client.get_caller_identity()
            return {
                "status": "success",
                "message": "AWS credentials are valid",
                "account_id": identity.get("Account"),
                "user_id": identity.get("UserId"),
                "arn": identity.get("Arn"),
            }
        except NoCredentialsError:
            return {
                "status": "error",
                "message": "AWS credentials not found. Please configure your credentials.",
            }
        except ClientError as e:
            return {
                "status": "error",
                "message": f"AWS credentials test failed: {e.response['Error']['Message']}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error testing AWS credentials: {str(e)}",
            }


def handle_aws_error(error: Exception) -> Dict[str, Any]:
    """
    Handle AWS-specific errors and return formatted error response.

    Args:
        error: The exception to handle

    Returns:
        Dict containing error information
    """
    if isinstance(error, NoCredentialsError):
        return {
            "status": "error",
            "error": "AWS credentials not found",
            "message": "Please configure your AWS credentials using AWS CLI, environment variables, or IAM roles.",
        }
    elif isinstance(error, ClientError):
        error_code = error.response["Error"]["Code"]
        error_message = error.response["Error"]["Message"]
        return {
            "status": "error",
            "error": error_code,
            "message": error_message,
        }
    else:
        return {
            "status": "error",
            "error": "Unknown error",
            "message": str(error),
        }


def get_availability_zones(client: Any) -> list:
    """
    Get list of availability zones for the current region.

    Args:
        client: EC2 client instance

    Returns:
        List of availability zone names
    """
    try:
        response = client.describe_availability_zones()
        return [az["ZoneName"] for az in response["AvailabilityZones"]]
    except Exception as e:
        logger.error(f"Failed to get availability zones: {e}")
        return []


def get_default_vpc(client: Any) -> Optional[str]:
    """
    Get the default VPC ID for the current region.

    Args:
        client: EC2 client instance

    Returns:
        Default VPC ID or None if not found
    """
    try:
        response = client.describe_vpcs(
            Filters=[{"Name": "isDefault", "Values": ["true"]}]
        )
        vpcs = response.get("Vpcs", [])
        if vpcs:
            return vpcs[0]["VpcId"]
        return None
    except Exception as e:
        logger.error(f"Failed to get default VPC: {e}")
        return None


def get_default_subnet(client: Any, vpc_id: str) -> Optional[str]:
    """
    Get a default subnet ID for the specified VPC.

    Args:
        client: EC2 client instance
        vpc_id: VPC ID to search for subnets

    Returns:
        Default subnet ID or None if not found
    """
    try:
        response = client.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )
        subnets = response.get("Subnets", [])
        if subnets:
            return subnets[0]["SubnetId"]
        return None
    except Exception as e:
        logger.error(f"Failed to get default subnet: {e}")
        return None


def parse_tags(tags: Optional[list]) -> Dict[str, str]:
    """
    Parse AWS tags list into a dictionary.

    Args:
        tags: List of AWS tag dictionaries

    Returns:
        Dictionary of tag key-value pairs
    """
    if not tags:
        return {}
    
    return {tag["Key"]: tag["Value"] for tag in tags}


def format_tags(tags: Dict[str, str]) -> list:
    """
    Format tag dictionary into AWS tags list format.

    Args:
        tags: Dictionary of tag key-value pairs

    Returns:
        List of AWS tag dictionaries
    """
    return [{"Key": key, "Value": value} for key, value in tags.items()]


def format_s3_tags(tags: Dict[str, str]) -> str:
    """
    Format tag dictionary into S3 object tags string format.
    
    S3 object tags require URL encoding and are formatted as key=value&key2=value2.

    Args:
        tags: Dictionary of tag key-value pairs

    Returns:
        URL-encoded tag string for S3
    """
    if not tags or not isinstance(tags, dict):
        return ""
    
    from urllib.parse import quote
    tag_pairs = []
    for k, v in tags.items():
        if k is not None and v is not None:
            # URL encode tag keys and values
            encoded_key = quote(str(k))
            encoded_value = quote(str(v))
            tag_pairs.append(f"{encoded_key}={encoded_value}")
    
    return "&".join(tag_pairs)