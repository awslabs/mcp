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

"""Token vault tools for AgentCore Identity.

The token vault is the encrypted store that holds API keys and OAuth2
tokens for credential providers. Each account has a default token vault
that can be configured with a customer-managed KMS key (CMK) for
encryption at rest.
"""

from .error_handler import handle_identity_error, strip_response_metadata
from .models import ErrorResponse, TokenVaultResponse
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class TokenVaultTools:
    """Tools for managing the AgentCore Identity token vault."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register token vault tools with the MCP server."""
        mcp.tool(name='identity_get_token_vault')(self.identity_get_token_vault)
        mcp.tool(name='identity_set_token_vault_cmk')(self.identity_set_token_vault_cmk)

    async def identity_get_token_vault(
        self,
        ctx: Context,
        token_vault_id: Annotated[
            str | None,
            Field(
                description=(
                    'Token vault ID (1-64 chars). Omit to get the default '
                    'token vault for the account.'
                )
            ),
        ] = None,
    ) -> TokenVaultResponse | ErrorResponse:
        """Get details of an AgentCore Identity token vault.

        Returns the token vault ID, KMS configuration (key type and key
        ARN), and last-modified timestamp. This is a read-only operation
        with no cost implications.
        """
        logger.info(f'Getting token vault (id={token_vault_id or "default"})')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if token_vault_id is not None:
                kwargs['tokenVaultId'] = token_vault_id

            response = client.get_token_vault(**kwargs)
            vault = strip_response_metadata(response)

            return TokenVaultResponse(
                status='success',
                message=(f'Token vault "{vault.get("tokenVaultId", "default")}" retrieved.'),
                token_vault=vault,
            )
        except Exception as e:
            return handle_identity_error('GetTokenVault', e)

    async def identity_set_token_vault_cmk(
        self,
        ctx: Context,
        kms_configuration: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'KMS configuration. An object with keys: "keyType" '
                    '(either "CustomerManagedKey" or "ServiceManagedKey") and '
                    '"kmsKeyArn" (required when keyType is CustomerManagedKey; '
                    'an ARN like arn:aws:kms:region:account:key/key-id).'
                )
            ),
        ],
        token_vault_id: Annotated[
            str | None,
            Field(
                description=(
                    'Token vault ID (1-64 chars). Omit to update the default token vault.'
                )
            ),
        ] = None,
    ) -> TokenVaultResponse | ErrorResponse:
        """Set the customer master key (CMK) for an AgentCore Identity token vault.

        COST WARNING: Switching to a CustomerManagedKey incurs AWS KMS
        charges for every encryption and decryption request against
        secrets in the vault (each stored credential). Switching back
        to ServiceManagedKey stops these KMS charges.

        SECURITY NOTE: This operation changes how credentials stored in
        the vault are encrypted. Ensure the KMS key policy grants the
        AgentCore service principal the necessary permissions
        (kms:Decrypt, kms:Encrypt, kms:GenerateDataKey, kms:DescribeKey)
        before switching to a CustomerManagedKey, or stored credentials
        will become inaccessible.
        """
        logger.info(f'Setting token vault CMK (id={token_vault_id or "default"})')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'kmsConfiguration': kms_configuration}
            if token_vault_id is not None:
                kwargs['tokenVaultId'] = token_vault_id

            response = client.set_token_vault_cmk(**kwargs)
            vault = strip_response_metadata(response)

            return TokenVaultResponse(
                status='success',
                message=(
                    f'Token vault "{vault.get("tokenVaultId", "default")}" '
                    f'KMS configuration updated.'
                ),
                token_vault=vault,
            )
        except Exception as e:
            return handle_identity_error('SetTokenVaultCMK', e)
