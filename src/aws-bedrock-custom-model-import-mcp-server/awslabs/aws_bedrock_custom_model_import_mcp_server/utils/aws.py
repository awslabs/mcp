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

"""AWS helper functions."""

import boto3
from awslabs.aws_bedrock_custom_model_import_mcp_server import __version__
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.consts import (
    AWS_REGION,
    ENV_ROLE_ARN,
)
from botocore.config import Config
from loguru import logger
from typing import Any


def get_aws_client(
    service_name: str, region_name: str = AWS_REGION, profile_name: str | None = None
) -> Any:
    """Get an AWS service client.

    Args:
        service_name (str): Name of the AWS service
        region_name (str): AWS region
        profile_name (str): AWS profile
    Returns:
        Any: AWS service client
    """
    try:
        config = Config(
            retries={'max_attempts': 3, 'mode': 'standard'},
            user_agent_extra=f'awslabs/mcp/aws-bedrock-custom-model-import-mcp-server/{__version__}',
        )
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        return session.client(service_name, config=config)
    except Exception as e:
        logger.error(f'Error creating {service_name} client: {str(e)}')
        if 'ExpiredToken' in str(e):
            raise RuntimeError('Your AWS credentials have expired. Please refresh them.')
        elif 'NoCredentialProviders' in str(e):
            raise RuntimeError(
                'No AWS credentials found. Please configure credentials using environment variables or AWS configuration.'
            )
        else:
            raise RuntimeError('Got an error when loading your client.')


def get_iam_role_arn_from_sts() -> str:
    """Infer the IAM role ARN from the current STS credentials.

    This function assumes the caller is using an assumed role. It extracts
    the account ID and role name from the STS ARN to construct the IAM role ARN.

    Returns:
        str: The inferred IAM role ARN.

    Raises:
        ValueError: If the STS ARN does not match the expected format for an assumed role.
    """
    sts_client = get_aws_client('sts')

    try:
        caller_identity = sts_client.get_caller_identity()
        sts_arn = caller_identity['Arn']

        # Expecting: arn:aws:sts::ACCOUNT_ID:assumed-role/ROLE_NAME/SESSION_NAME
        parts = sts_arn.split(':')
        if len(parts) != 6 or 'assumed-role' not in parts[5]:
            raise ValueError(f'Failed to parse assumed credentials: {sts_arn}')

        account_id = parts[4]
        role_name = parts[5].split('/')[1]

        return f'arn:aws:iam::{account_id}:role/{role_name}'
    except Exception as e:
        raise ValueError(
            'Failed to parse assumed credentials.'
            f'Make sure you have enough permissions or specify the {ENV_ROLE_ARN} in the environment'
        ) from e
