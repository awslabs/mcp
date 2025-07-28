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

"""AWS client utilities for Amazon SageMaker MCP Server."""

import os
from typing import Optional
import boto3
from botocore.config import Config


def get_aws_config() -> Config:
    """Get AWS configuration with retry settings."""
    return Config(
        retries={
            'max_attempts': 3,
            'mode': 'adaptive'
        },
        max_pool_connections=50,
        user_agent_extra='MCP/SagemakerServer' # Custom User agent to identify requests from LLM/MCP
    )


def get_session() -> boto3.Session:
    """Get AWS session with proper configuration."""
    # Use explicit credentials if provided
    if all(os.getenv(var) for var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']):
        return boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
    
    # Use profile if specified
    profile_name = os.getenv('AWS_PROFILE')
    if profile_name:
        return boto3.Session(
            profile_name=profile_name,
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
    
    # Use default session
    return boto3.Session(region_name=os.getenv('AWS_REGION', 'us-east-1'))


def get_sagemaker_client():
    """Get SageMaker client."""
    session = get_session()
    return session.client('sagemaker', config=get_aws_config())


def get_sagemaker_runtime_client():
    """Get SageMaker Runtime client."""
    session = get_session()
    return session.client('sagemaker-runtime', config=get_aws_config())

def validate_aws_credentials() -> bool:
    """Validate AWS credentials by making a simple API call."""
    try:
        session = get_session()
        sts_client = session.client('sts', config=get_aws_config())
        sts_client.get_caller_identity()
        return True
    except Exception:
        return False


def get_current_region() -> str:
    """Get the current AWS region."""
    return get_session().region_name or 'us-east-1'


def get_account_id() -> Optional[str]:
    """Get the current AWS account ID."""
    try:
        session = get_session()
        sts_client = session.client('sts', config=get_aws_config())
        response = sts_client.get_caller_identity()
        return response.get('Account')
    except Exception:
        return None
