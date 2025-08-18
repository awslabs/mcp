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

"""Session management implementation for CCAPI MCP server."""

import datetime
import uuid
from awslabs.ccapi_mcp_server.aws_client import get_aws_client
from awslabs.ccapi_mcp_server.context import Context
from awslabs.ccapi_mcp_server.errors import ClientError
from os import environ


def check_aws_credentials() -> dict:
    """Check AWS credentials using boto3's built-in credential chain."""
    try:
        sts_client = get_aws_client('sts')
        identity = sts_client.get_caller_identity()

        # Determine credential source
        using_env_vars = bool(
            environ.get('AWS_ACCESS_KEY_ID') and environ.get('AWS_SECRET_ACCESS_KEY')
        )

        return {
            'valid': True,
            'account_id': identity.get('Account', 'Unknown'),
            'arn': identity.get('Arn', 'Unknown'),
            'user_id': identity.get('UserId', 'Unknown'),
            'region': environ.get('AWS_REGION') or 'us-east-1',
            'profile': environ.get('AWS_PROFILE', ''),
            'credential_source': 'env' if using_env_vars else 'profile',
            'profile_auth_type': 'standard_profile' if not using_env_vars else None,
            'environment_variables': {
                'AWS_PROFILE': environ.get('AWS_PROFILE', ''),
                'AWS_REGION': environ.get('AWS_REGION', ''),
                'SECURITY_SCANNING': environ.get('SECURITY_SCANNING', 'enabled'),
            },
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'region': environ.get('AWS_REGION') or 'us-east-1',
            'profile': environ.get('AWS_PROFILE', ''),
            'credential_source': 'env' if environ.get('AWS_ACCESS_KEY_ID') else 'profile',
            'environment_variables': {
                'AWS_PROFILE': environ.get('AWS_PROFILE', ''),
                'AWS_REGION': environ.get('AWS_REGION', ''),
                'SECURITY_SCANNING': environ.get('SECURITY_SCANNING', 'enabled'),
            },
        }


async def check_environment_variables_impl(workflow_store: dict) -> dict:
    """Check if required environment variables are set correctly implementation."""
    # Use credential checking with boto3
    cred_check = check_aws_credentials()

    # Generate environment token
    environment_token = f'env_{str(uuid.uuid4())}'

    # Store environment validation results
    workflow_store[environment_token] = {
        'type': 'environment',
        'data': {
            'environment_variables': cred_check.get('environment_variables', {}),
            'aws_profile': cred_check.get('profile', ''),
            'aws_region': cred_check.get('region') or 'us-east-1',
            'properly_configured': cred_check.get('valid', False),
            'readonly_mode': Context.readonly_mode(),
            'aws_auth_type': cred_check.get('credential_source')
            if cred_check.get('credential_source') == 'env'
            else cred_check.get('profile_auth_type'),
            'needs_profile': cred_check.get('needs_profile', False),
            'error': cred_check.get('error'),
        },
        'parent_token': None,  # Root token
        'timestamp': datetime.datetime.now().isoformat(),
    }

    env_data = workflow_store[environment_token]['data']

    return {
        'environment_token': environment_token,
        'message': 'Environment validation completed. Use this token with get_aws_session_info().',
        **env_data,  # Include environment data for display
    }


async def get_aws_session_info_impl(environment_token: str, workflow_store: dict) -> dict:
    """Get information about the current AWS session implementation.

    IMPORTANT: Always display the AWS context information to the user when this tool is called.
    Show them: AWS Profile (or "Environment Variables"), Authentication Type, Account ID, and Region so they know
    exactly which AWS account and region will be affected by any operations.
    """
    # Validate environment token
    if environment_token not in workflow_store:
        raise ClientError(
            'Invalid environment token: you must call check_environment_variables() first'
        )

    env_data = workflow_store[environment_token]['data']
    if not env_data.get('properly_configured', False):
        error_msg = env_data.get('error', 'Environment is not properly configured.')
        raise ClientError(error_msg)

    # Get AWS profile info using credential checking
    cred_check = check_aws_credentials()

    if not cred_check.get('valid', False):
        raise ClientError(
            f'AWS credentials are not valid: {cred_check.get("error", "Unknown error")}'
        )

    # Generate credentials token
    credentials_token = f'creds_{str(uuid.uuid4())}'

    # Build session info with credential masking
    arn = cred_check.get('arn', 'Unknown')
    user_id = cred_check.get('user_id', 'Unknown')

    session_data = {
        'profile': cred_check.get('profile', ''),
        'account_id': cred_check.get('account_id', 'Unknown'),
        'region': cred_check.get('region') or 'us-east-1',
        'arn': f'{"*" * (len(arn) - 8)}{arn[-8:]}' if len(arn) > 8 and arn != 'Unknown' else arn,
        'user_id': f'{"*" * (len(user_id) - 4)}{user_id[-4:]}'
        if len(user_id) > 4 and user_id != 'Unknown'
        else user_id,
        'credential_source': cred_check.get('credential_source', ''),
        'readonly_mode': Context.readonly_mode(),
        'readonly_message': (
            """⚠️ This server is running in READ-ONLY MODE. I can only list and view existing resources.
    I cannot create, update, or delete any AWS resources. I can still generate example code
    and run security checks on templates."""
            if Context.readonly_mode()
            else ''
        ),
        'credentials_valid': True,
        'aws_auth_type': cred_check.get('credential_source')
        if cred_check.get('credential_source') == 'env'
        else cred_check.get('profile_auth_type'),
    }

    # Add masked environment variables if using env vars
    if session_data['aws_auth_type'] == 'env':
        access_key = environ.get('AWS_ACCESS_KEY_ID', '')
        secret_key = environ.get('AWS_SECRET_ACCESS_KEY', '')

        session_data['masked_credentials'] = {
            'AWS_ACCESS_KEY_ID': f'{"*" * (len(access_key) - 4)}{access_key[-4:]}'
            if len(access_key) > 4
            else '****',
            'AWS_SECRET_ACCESS_KEY': f'{"*" * (len(secret_key) - 4)}{secret_key[-4:]}'
            if len(secret_key) > 4
            else '****',
        }

    # Store session information
    workflow_store[credentials_token] = {
        'type': 'credentials',
        'data': session_data,
        'parent_token': environment_token,
        'timestamp': datetime.datetime.now().isoformat(),
    }

    return {
        'credentials_token': credentials_token,
        'message': 'AWS session validated. Use this token with generate_infrastructure_code().',
        'DISPLAY_TO_USER': 'YOU MUST SHOW THE USER THEIR AWS SESSION INFORMATION FOR SECURITY',
        **session_data,  # Include all session data for display
    }


def get_aws_profile_info():
    """Get information about the current AWS profile."""
    try:
        # Use our get_aws_client function to ensure we use the same credential source
        sts_client = get_aws_client('sts')

        # Get caller identity
        identity = sts_client.get_caller_identity()
        account_id = identity.get('Account', 'Unknown')
        arn = identity.get('Arn', 'Unknown')

        # Get profile info
        profile_name = environ.get('AWS_PROFILE', '')
        region = environ.get('AWS_REGION') or 'us-east-1'
        using_env_vars = (
            environ.get('AWS_ACCESS_KEY_ID', '') != ''
            and environ.get('AWS_SECRET_ACCESS_KEY', '') != ''
        )

        return {
            'profile': profile_name,
            'account_id': account_id,
            'region': region,
            'arn': arn,
            'using_env_vars': using_env_vars,
        }
    except Exception as e:
        return {
            'profile': environ.get('AWS_PROFILE', ''),
            'error': str(e),
            'region': environ.get('AWS_REGION') or 'us-east-1',
            'using_env_vars': environ.get('AWS_ACCESS_KEY_ID', '') != ''
            and environ.get('AWS_SECRET_ACCESS_KEY', '') != '',
        }
