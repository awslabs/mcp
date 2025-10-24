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

"""AWS helper for the AWS IoT SiteWise MCP Server."""

import boto3
import os


class AwsHelper:
    """Helper class for AWS operations.

    This class provides utility methods for interacting with AWS services,
    including region and partition management.
    """

    # Class variables to cache AWS information
    _aws_partition = None

    @staticmethod
    def get_aws_region() -> str:
        """Get the AWS region from the environment if set."""
        aws_region = os.environ.get(
            'AWS_REGION',
        )
        if not aws_region:
            return 'us-east-1'
        return aws_region

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
