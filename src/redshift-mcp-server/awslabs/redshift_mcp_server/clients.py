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
import botocore.session
import os
import threading
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
    CREDENTIAL_REFRESH_TTL,
)
from botocore.config import Config
from botocore.credentials import (
    CredentialProvider,
    RefreshableCredentials,
    SharedCredentialProvider,
)
from botocore.exceptions import CredentialRetrievalError
from datetime import datetime, timedelta, timezone
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


class RefreshingSharedCredentialProvider(CredentialProvider):
    """Keys from the shared credentials file, read again each time they are a TTL old.

    Botocore reads these keys once, as credentials that never expire, so a client signs with them
    for the life of the process. Keys rewritten in place - by `aws configure`, say - went unseen
    until a restart, and every call meanwhile failed with ExpiredToken, which botocore does not
    retry. Here the same keys carry an expiry of their own, so the signer has botocore read the
    file again, under its own refresh lock, on the first call after it passes. The client is never
    rebuilt, and nothing that holds it can tell.

    Only this source needs it. SSO, assume-role, web identity and container credentials already
    refresh inside a client, and keys in the environment cannot be read again in-process.
    """

    # The method of the credentials it stands in for, so what a client reports is unchanged.
    METHOD = SharedCredentialProvider.METHOD

    def __init__(self, provider: SharedCredentialProvider, ttl: float):
        """Wrap the session's own provider, so file, profile and parsing stay botocore's.

        Args:
            provider: The provider botocore built for this session's profile and file.
            ttl: How long, in seconds, one read of the file is used before the next.
        """
        super().__init__()
        self._provider = provider
        self._ttl = ttl

    def load(self):  # pyright: ignore[reportIncompatibleMethodOverride] - botocore is untyped
        """Read the profile's keys, or None to leave the chain to the providers after this one."""
        metadata = self._read()
        if metadata is None:
            return None
        return RefreshableCredentials.create_from_metadata(
            metadata=metadata,
            refresh_using=self._refresh,
            method=self.METHOD,
            # Botocore's defaults refresh up to 15 minutes ahead of the expiry, which for a TTL
            # this short is every call. At 0 the file is read once the expiry has passed, and a
            # failed read raises instead of being swallowed, as an early one would be.
            advisory_timeout=0,
            mandatory_timeout=0,
        )

    def _read(self) -> dict | None:
        credentials = self._provider.load()
        if credentials is None:
            return None
        frozen = credentials.get_frozen_credentials()
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self._ttl)
        return {
            'access_key': frozen.access_key,
            'secret_key': frozen.secret_key,
            'token': frozen.token,
            'account_id': frozen.account_id,
            'expiry_time': expiry.isoformat(),
        }

    def _refresh(self) -> dict:
        metadata = self._read()
        if metadata is None:
            # Raised to the call being signed, rather than signing it with keys the file no
            # longer holds. The next call reads the file again.
            raise CredentialRetrievalError(
                provider=self.METHOD,
                error_msg="the profile's keys are no longer in the shared credentials file",
            )
        return metadata


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

        Keys from the shared credentials file are read again every CREDENTIAL_REFRESH_TTL
        seconds; see `RefreshingSharedCredentialProvider`.

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
            botocore_session = botocore.session.Session()
            session = boto3.Session(
                botocore_session=botocore_session,
                profile_name=os.environ.get('AWS_PROFILE'),
                region_name=os.environ.get('AWS_REGION'),
            )
            # Only once the session has its profile: this builds the resolver the client would
            # otherwise build, and the resolver fixes then which profile it reads and whether
            # keys in the environment are passed over for it.
            resolver = botocore_session.get_component('credential_provider')
            resolver.insert_before(
                SharedCredentialProvider.METHOD,
                RefreshingSharedCredentialProvider(
                    resolver.get_provider(SharedCredentialProvider.METHOD),
                    ttl=CREDENTIAL_REFRESH_TTL,
                ),
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
