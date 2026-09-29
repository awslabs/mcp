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
import threading
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

# Held while the environment is scrubbed of empty AWS_* variables. The discovery clients are built
# on worker threads and the Data API client on the event loop, and two scrubs at once raised
# KeyError from the second one's delete.
_ENVIRONMENT_LOCK = threading.Lock()


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(self, config: Config):
        """Initialize the client manager.

        Args:
            config: The botocore configuration every client is built with.
        """
        self._redshift_client = None
        self._redshift_serverless_client = None
        self._redshift_data_client = None
        self._config = config

    def redshift_client(self):
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            self._redshift_client = self._client('redshift')
        return self._redshift_client

    def redshift_serverless_client(self):
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            self._redshift_serverless_client = self._client('redshift-serverless')
        return self._redshift_serverless_client

    def redshift_data_client(self):
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            self._redshift_data_client = self._client('redshift-data')
        return self._redshift_data_client

    def _client(self, service: str):
        """Build one client, reading the environment as it stands.

        An empty AWS_* variable is removed first. Botocore reads most of these itself and takes an
        empty one as a value, so each fails every client and with it every tool: AWS_PROFILE or
        AWS_DEFAULT_PROFILE (`The config profile () could not be found`), AWS_DEFAULT_REGION
        (`Invalid endpoint: https://redshift..amazonaws.com`), AWS_CA_BUNDLE. Passing None instead
        would not help, since botocore would still read the empty value. An empty value is what
        an MCP config template leaves behind, and unset is what it means - so an empty variable
        naming a file, such as AWS_CONFIG_FILE, selects the default file.

        AWS_PROFILE and AWS_REGION are passed in rather than left to botocore. A profile botocore
        finds for itself ranks below AWS_DEFAULT_PROFILE, keys in the environment and web
        identity; passed in, it ranks above them, which is what naming a profile means. Botocore
        reads only AWS_DEFAULT_REGION, where the README gives AWS_REGION precedence.

        Args:
            service: The botocore service name.

        Returns:
            The client.
        """
        with _ENVIRONMENT_LOCK:
            empty = [name for name, value in os.environ.items() if not value]
            for name in empty:
                if name.startswith('AWS_'):
                    del os.environ[name]

        try:
            session = boto3.Session(
                profile_name=os.environ.get('AWS_PROFILE'),
                region_name=os.environ.get('AWS_REGION'),
            )
            client = session.client(service, config=self._config)
        except Exception as e:
            logger.error(f'Error creating {service} client: {e}')
            raise

        logger.info(
            f'Created {service} client with profile: {session.profile_name}, '
            f'region: {client.meta.region_name}'
        )
        return client


# One per process. Each client is built on first use and then held, so sharing the manager is
# what keeps a second caller from building its own. Each reads its region and profile from the
# environment when it is built, after the scrub in `_client`.
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'md/awslabs#mcp#redshift-mcp-server#{__version__}',
    ),
)
