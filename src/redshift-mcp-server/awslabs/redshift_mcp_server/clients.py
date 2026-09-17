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

"""AWS clients for the Redshift MCP Server, and the error codes their calls answer with."""

import boto3
import os
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
)
from botocore.config import Config
from loguru import logger


# ClientError codes that indicate missing IAM permissions.
ACCESS_DENIED = {'AccessDeniedException', 'UnauthorizedAccess', 'AccessDenied'}

# botocore's name for the batch call, as it appears on ClientError.operation_name. Used to tell
# a denial of the batch action from a denial of the two calls that settle and read it.
BATCH_OPERATION = 'BatchExecuteStatement'
# The IAM action behind that call, as it appears in an AccessDenied message. The call also
# reports denials of the grants the Data API needs on the caller's behalf, so the operation
# alone does not say which action was refused.
BATCH_ACTION = 'redshift-data:BatchExecuteStatement'


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(
        self, config: Config, aws_region: str | None = None, aws_profile: str | None = None
    ):
        """Initialize the client manager."""
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self._redshift_client = None
        self._redshift_serverless_client = None
        self._redshift_data_client = None
        self._config = config

    def redshift_client(self):
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_client = session.client('redshift', config=self._config)
                logger.info(
                    f'Created Redshift client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift client: {str(e)}')
                raise

        return self._redshift_client

    def redshift_serverless_client(self):
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_serverless_client = session.client(
                    'redshift-serverless', config=self._config
                )
                logger.info(
                    f'Created Redshift Serverless client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Serverless client: {str(e)}')
                raise

        return self._redshift_serverless_client

    def redshift_data_client(self):
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_data_client = session.client('redshift-data', config=self._config)
                logger.info(
                    f'Created Redshift Data API client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Data API client: {str(e)}')
                raise

        return self._redshift_data_client


# One per process. Each client is built on first use and then held, so sharing the manager is
# what keeps a second caller from building its own.
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'md/awslabs#mcp#redshift-mcp-server#{__version__}',
    ),
    aws_region=os.environ.get('AWS_REGION'),
    aws_profile=os.environ.get('AWS_PROFILE'),
)
