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

"""AWS helper for the DataProcessing MCP Server."""

import boto3
import os
from .consts import (
    CUSTOM_TAGS_ENV_VAR,
    DEFAULT_RESOURCE_TAGS,
    EMR_CLUSTER_RESOURCE_TYPE,
    MCP_CREATION_TIME_TAG_KEY,
    MCP_MANAGED_TAG_KEY,
    MCP_MANAGED_TAG_VALUE,
    MCP_RESOURCE_TYPE_TAG_KEY,
)
from awslabs.aws_dataprocessing_mcp_server import __version__
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Any, Dict, List, Optional


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and profile management and client creation.
    """

    @staticmethod
    def get_aws_region() -> str:
        """Get the AWS region from the environment if set."""
        aws_region = os.environ.get(
            'AWS_REGION',
        )
        if not aws_region:
            return 'us-east-1'
        return aws_region

    @staticmethod
    def get_aws_profile() -> Optional[str]:
        """Get the AWS profile from the environment if set."""
        return os.environ.get('AWS_PROFILE')

    @staticmethod
    def is_custom_tags_enabled() -> bool:
        """Check if custom tags are enabled.

        When CUSTOM_TAGS environment variable is set to 'True', the system will
        ignore adding new tags or verifying ManagedBy tags for resources.

        Returns:
            True if custom tags are enabled, False otherwise
        """
        custom_tags = os.environ.get(CUSTOM_TAGS_ENV_VAR, '').lower()
        return custom_tags == 'true'

    # Class variables to cache AWS information
    _aws_account_id = None
    _aws_partition = None

    @classmethod
    def get_aws_account_id(cls) -> str:
        """Get the AWS account ID for the current session.

        The account ID is cached after the first call to avoid repeated STS calls.

        Returns:
            The AWS account ID as a string
        """
        # Return cached account ID if available
        if cls._aws_account_id is not None:
            return cls._aws_account_id

        try:
            sts_client = boto3.client('sts')
            cls._aws_account_id = sts_client.get_caller_identity()['Account']
            return cls._aws_account_id
        except Exception:
            # If we can't get the account ID, return a placeholder
            # This is better than nothing for ARN construction
            return 'current-account'

    @classmethod
    def get_aws_partition(cls) -> str:
        """Get the AWS partition for the current session.

        The partition is cached after the first call to avoid repeated STS calls.
        Common partitions include 'aws' (standard), 'aws-cn' (China), 'aws-us-gov' (GovCloud).

        Returns:
            The AWS partition as a string
        """
        # Return cached partition if available
        if cls._aws_partition is not None:
            return cls._aws_partition

        try:
            sts_client = boto3.client('sts')
            # Extract partition from the ARN in the response
            arn = sts_client.get_caller_identity()['Arn']
            # ARN format: arn:partition:service:region:account-id:resource
            cls._aws_partition = arn.split(':')[1]
            return cls._aws_partition
        except Exception:
            # If we can't get the partition, return the standard partition
            # This is better than nothing for ARN construction
            return 'aws'

    @classmethod
    def create_boto3_client(cls, service_name: str, region_name: Optional[str] = None) -> Any:
        """Create a boto3 client with the appropriate profile and region.

        The client is configured with a custom user agent suffix 'awslabs/mcp/aws-dataprocessing-mcp-server/0.1.0'
        to identify API calls made by the Dataprocessing MCP Server.

        Args:
            service_name: The AWS service name (e.g., 'ec2', 's3', 'glue', 'emr-ec2')
            region_name: Optional region name override

        Returns:
            A boto3 client for the specified service
        """
        # Get region from parameter or environment if set
        region: Optional[str] = region_name if region_name is not None else cls.get_aws_region()

        # Get profile from environment if set
        profile = cls.get_aws_profile()

        # Create config with user agent suffix
        config = Config(
            user_agent_extra=f'awslabs/mcp/aws-dataprocessing-mcp-server/{__version__}'
        )

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

    @staticmethod
    def prepare_resource_tags(
        resource_type: str, additional_tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Prepare standard tags for a resource.

        Args:
            resource_type: The type of resource being created (e.g., 'EMRCluster', 'GlueJob', 'Crawler')
            additional_tags: Optional additional tags to include

        Returns:
            Dictionary of tags to apply to the resource
        """
        # If custom tags are enabled, only use additional tags if provided
        if AwsHelper.is_custom_tags_enabled():
            return additional_tags or {}

        # Otherwise, apply default MCP tags
        tags = DEFAULT_RESOURCE_TAGS.copy()
        tags[MCP_RESOURCE_TYPE_TAG_KEY] = resource_type
        tags[MCP_CREATION_TIME_TAG_KEY] = datetime.utcnow().isoformat()

        if additional_tags:
            tags.update(additional_tags)

        return tags

    @staticmethod
    def convert_tags_to_aws_format(
        tags: Dict[str, str], format_type: str = 'key_value'
    ) -> List[Dict[str, str]]:
        """Convert tags dictionary to AWS API format.

        Args:
            tags: Dictionary of tag key-value pairs
            format_type: Format type - 'key_value' for [{'Key': 'k', 'Value': 'v'}] or 'tag_key_value' for [{'TagKey': 'k', 'TagValue': 'v'}]

        Returns:
            List of tag dictionaries in AWS API format
        """
        if format_type == 'tag_key_value':
            return [{'TagKey': key, 'TagValue': value} for key, value in tags.items()]
        else:
            return [{'Key': key, 'Value': value} for key, value in tags.items()]

    @staticmethod
    def get_resource_tags_athena_workgroup(
        athena_client: Any, workgroup_name: str
    ) -> List[Dict[str, str]]:
        """Get tags for an Athena workgroup.

        Args:
            athena_client: Athena boto3 client
            workgroup_name: Athena workgroup name

        Returns:
            List of tag dictionaries
        """
        try:
            response = athena_client.list_tags_for_resource(
                ResourceARN=f'arn:aws:athena:{AwsHelper.get_aws_region()}:{AwsHelper.get_aws_account_id()}:workgroup/{workgroup_name}'
            )
            return response.get('Tags', [])
        except ClientError:
            return []

    @staticmethod
    def verify_resource_managed_by_mcp(
        tags: List[Dict[str, str]], tag_format: str = 'key_value'
    ) -> bool:
        """Verify if a resource is managed by the MCP server based on its tags.

        Args:
            tags: List of tag dictionaries from AWS API
            tag_format: Format of the tags - 'key_value' or 'tag_key_value'

        Returns:
            True if the resource is managed by MCP server, False otherwise
        """
        # If custom tags are enabled, skip verification
        if AwsHelper.is_custom_tags_enabled():
            return True

        if not tags:
            return False

        # Convert tags to dictionary for easier lookup
        tag_dict = {}
        if tag_format == 'tag_key_value':
            tag_dict = {tag.get('TagKey', ''): tag.get('TagValue', '') for tag in tags}
        else:
            tag_dict = {tag.get('Key', ''): tag.get('Value', '') for tag in tags}

        return tag_dict.get(MCP_MANAGED_TAG_KEY) == MCP_MANAGED_TAG_VALUE

    @staticmethod
    def get_resource_tags_glue_job(glue_client: Any, job_name: str) -> Dict[str, str]:
        """Get tags for a Glue job.

        Args:
            glue_client: Glue boto3 client
            job_name: Glue job name

        Returns:
            Dictionary of tags
        """
        try:
            response = glue_client.get_tags(ResourceArn=f'arn:aws:glue:*:*:job/{job_name}')
            return response.get('Tags', {})
        except ClientError:
            return {}

    @staticmethod
    def is_resource_mcp_managed(
        glue_client: Any, resource_arn: str, parameters: Optional[Dict[str, str]] = None
    ) -> bool:
        """Check if a resource is managed by MCP by looking at Tags and Parameters.

        This method first checks if the resource has the MCP managed tag.
        If the tag check fails, it falls back to checking Parameters (if provided).

        Args:
            glue_client: Glue boto3 client
            resource_arn: ARN of the resource to check
            parameters: Optional parameters dictionary to check if tag check fails

        Returns:
            True if the resource is managed by MCP, False otherwise
        """
        # If custom tags are enabled, skip verification
        if AwsHelper.is_custom_tags_enabled():
            return True

        # First try to check tags
        try:
            tags_response = glue_client.get_tags(ResourceArn=resource_arn)
            tags = tags_response.get('Tags', {})

            # Check if the resource is managed by MCP using tags
            if tags.get(MCP_MANAGED_TAG_KEY) == MCP_MANAGED_TAG_VALUE:
                return True
        except ClientError:
            # If we can't get tags, fall back to checking parameters
            pass

        # If tag check failed or no tags found, check parameters if provided
        if parameters:
            return parameters.get(MCP_MANAGED_TAG_KEY) == MCP_MANAGED_TAG_VALUE

        return False

    @staticmethod
    def verify_emr_cluster_managed_by_mcp(
        emr_client: Any, cluster_id: str, expected_resource_type: str = EMR_CLUSTER_RESOURCE_TYPE
    ) -> Dict[str, Any]:
        """Verify if an EMR cluster is managed by the MCP server and has the expected resource type.

        This method checks if the EMR cluster has the MCP managed tag and the correct resource type tag.

        Args:
            emr_client: EMR boto3 client
            cluster_id: ID of the EMR cluster to verify
            expected_resource_type: The expected resource type value (default: EMR_CLUSTER_RESOURCE_TYPE)

        Returns:
            Dictionary with verification result:
                - is_valid: True if verification passed, False otherwise
                - error_message: Error message if verification failed, None otherwise
        """
        # If custom tags are enabled, skip verification
        if AwsHelper.is_custom_tags_enabled():
            return {'is_valid': True, 'error_message': None}

        result = {'is_valid': False, 'error_message': None}

        try:
            response = emr_client.describe_cluster(ClusterId=cluster_id)
            tags_list = response.get('Cluster', {}).get('Tags', [])

            # Check if the resource is managed by MCP
            if not AwsHelper.verify_resource_managed_by_mcp(tags_list):
                result['error_message'] = (
                    f'Cluster {cluster_id} is not managed by MCP (missing required tags)'
                )
                return result

            # Convert tags to dictionary for easier lookup
            tag_dict = {tag.get('Key', ''): tag.get('Value', '') for tag in tags_list}

            # Check if the resource has the expected resource type
            actual_type = tag_dict.get(MCP_RESOURCE_TYPE_TAG_KEY, 'unknown')
            if actual_type != expected_resource_type and actual_type != EMR_CLUSTER_RESOURCE_TYPE:
                result['error_message'] = (
                    f'Cluster {cluster_id} has incorrect type (expected {expected_resource_type}, got {actual_type})'
                )
                return result

            # All checks passed
            result['is_valid'] = True
            return result

        except ClientError as e:
            # If we can't get the cluster information, return error
            result['error_message'] = f'Error retrieving cluster {cluster_id}: {str(e)}'
            return result

    @classmethod
    def verify_athena_data_catalog_managed_by_mcp(
        cls, athena_client: Any, name: str, work_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify if an Athena data catalog is managed by the MCP server.

        This method checks if the Athena data catalog exists and has the MCP managed tag.

        Args:
            athena_client: Athena boto3 client
            name: Name of the data catalog
            work_group: Optional workgroup name

        Returns:
            Dictionary with verification result:
                - is_valid: True if verification passed, False otherwise
                - error_message: Error message if verification failed, None otherwise
        """
        # If custom tags are enabled, skip verification
        if cls.is_custom_tags_enabled():
            return {'is_valid': True, 'error_message': None}

        result = {'is_valid': False, 'error_message': None}

        try:
            # Get data catalog to confirm it exists
            get_params = {'Name': name}
            if work_group is not None:
                get_params['WorkGroup'] = work_group

            athena_client.get_data_catalog(**get_params)

            # Construct the ARN for the data catalog
            account_id = cls.get_aws_account_id()
            region = cls.get_aws_region()
            data_catalog_arn = (
                f'arn:{cls.get_aws_partition()}:athena:{region}:{account_id}:datacatalog/{name}'
            )

            # Get tags for the data catalog
            try:
                tags_response = athena_client.list_tags_for_resource(ResourceARN=data_catalog_arn)
                tags = tags_response.get('Tags', [])

                # Check if the data catalog is managed by MCP
                if not cls.verify_resource_managed_by_mcp(tags):
                    result['error_message'] = (
                        f'Data catalog {name} is not managed by MCP (missing required tags)'
                    )
                    return result

                # All checks passed
                result['is_valid'] = True
                return result

            except Exception as e:
                result['error_message'] = f'Error checking data catalog tags: {str(e)}'
                return result

        except Exception as e:
            result['error_message'] = f'Error getting data catalog: {str(e)}'
            return result
