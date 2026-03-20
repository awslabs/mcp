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

"""AWS client utilities for cross-account access via STS AssumeRole."""

import time
from awslabs.cross_account_cloudwatch_mcp_server import MCP_SERVER_VERSION
from boto3 import Session
from botocore.config import Config
from loguru import logger


_session_cache: dict[str, dict] = {}

_user_agent_config = Config(
    user_agent_extra=f'awslabs/mcp/cross-account-cloudwatch-mcp-server/{MCP_SERVER_VERSION}'
)


def get_cross_account_client(
    service_name: str,
    account_id: str,
    role_name: str,
    region: str,
):
    """Get a boto3 client by assuming a role in the target account.

    Caches assumed-role sessions keyed by account_id:role_name:region.
    Sessions are refreshed when credentials expire.

    Args:
        service_name: AWS service name (e.g., 'logs')
        account_id: 12-digit AWS account ID
        role_name: IAM role name to assume in the target account
        region: AWS region

    Returns:
        boto3 client for the specified service in the target account
    """
    cache_key = f'{account_id}:{role_name}:{region}'

    cached = _session_cache.get(cache_key)
    if cached:
        expiration = cached['expiration']
        # Refresh 5 minutes before expiry
        if expiration.timestamp() - time.time() > 300:
            return cached['session'].client(
                service_name, region_name=region, config=_user_agent_config
            )
        logger.info(f'Session for {cache_key} expiring soon, refreshing')

    sts = Session().client('sts', config=_user_agent_config)
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'

    logger.info(f'Assuming role {role_arn} in {region}')
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=f'mcp-xacct-cw-{int(time.time())}',
    )

    creds = response['Credentials']
    session = Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken'],
        region_name=region,
    )

    _session_cache[cache_key] = {
        'session': session,
        'expiration': creds['Expiration'],
    }

    return session.client(service_name, region_name=region, config=_user_agent_config)


def clear_session_cache():
    """Clear the assumed-role session cache."""
    _session_cache.clear()
