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

import botocore.config
import sys
from awslabs.cfn_mcp_server.errors import ClientError
from boto3 import Session
from os import environ


session = Session(profile_name=environ.get('AWS_PROFILE'))
session_config = botocore.config.Config(
    user_agent_extra='cfn-mcp-server/1.0.0',
)


def get_aws_client(service_name, region_name=None):
    """Create and return an AWS service client with dynamically detected credentials.

    This function implements a credential provider chain that tries different
    credential sources in the following order:
    1. Environment variables (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    2. Shared credential file (~/.aws/credentials)
    3. IAM role for Amazon EC2 / ECS task role / EKS pod identity
    4. AWS SSO or Web Identity token

    The function caches clients based on the compound key of service_name and region_name
    to avoid creating duplicate clients for the same service and region.

    Args:
        service_name: AWS service name (e.g., 'cloudcontrol', 'logs', 'marketplace-catalog')
        region_name: AWS region name (defaults to environment variable or 'us-east-1')

    Returns:
        Boto3 client for the specified service
    """
    # Default region handling
    if not region_name:
        region_name = environ.get('AWS_REGION', 'us-east-1')

    # Credential detection and client creation
    try:
        print(
            f'Creating new {service_name} client for region {region_name} with auto-detected credentials'
        )
        client = session.client(service_name, region_name=region_name, config=session_config)

        print('Created client for service with credentials')
        return client

    except Exception as e:
        print(f'Error creating {service_name} client: {str(e)}', file=sys.stderr)
        if 'ExpiredToken' in str(e):
            raise ClientError('Your AWS credentials have expired. Please refresh them.')
        elif 'NoCredentialProviders' in str(e):
            raise ClientError(
                'No AWS credentials found. Please configure credentials using environment variables or AWS configuration.'
            )
        else:
            raise ClientError('Got an error when loading your client.')
