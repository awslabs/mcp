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

import botocore.config
import sys
from boto3 import Session
from os import environ


class ClientError(Exception):
    """AWS client error."""

    pass


session_config = botocore.config.Config(
    user_agent_extra='aws-iac-mcp-server/1.0.0',
)


def get_aws_client(service_name, region_name=None):
    """Create and return an AWS service client with dynamically detected credentials.

    Args:
        service_name: AWS service name (e.g., 'cloudcontrol', 'logs', 'marketplace-catalog')
        region_name: AWS region name (defaults to environment variable or 'us-east-1')

    Returns:
        Boto3 client for the specified service
    """
    # Default region handling
    if not region_name:
        region_name = environ.get('AWS_REGION', 'us-east-1')

    session = Session(profile_name=environ.get('AWS_PROFILE'))

    # Credential detection and client creation
    try:
        client = session.client(service_name, region_name=region_name, config=session_config)
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
            raise ClientError(f'Error creating AWS client: {str(e)}')
