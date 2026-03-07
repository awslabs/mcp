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

"""AWS client helpers for the GuardDuty MCP server."""

from __future__ import annotations

import boto3
from awslabs.aws_guardduty_mcp_server.consts import USER_AGENT
from botocore.config import Config
from loguru import logger
from typing import Any, Optional


def get_guardduty_client(region: Optional[str] = None) -> Any:
    """Create a GuardDuty client with a server-specific user agent."""
    try:
        config = Config(user_agent_extra=USER_AGENT)
        if region:
            logger.debug(f'Creating GuardDuty client for region: {region}')
            return boto3.client('guardduty', region_name=region, config=config)
        logger.debug('Creating GuardDuty client with default region')
        return boto3.client('guardduty', config=config)
    except Exception as e:
        logger.error(f'Failed to create GuardDuty client: {e}')
        raise Exception(f'Failed to create GuardDuty client: {str(e)}')
