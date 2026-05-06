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

"""Unit tests for Identity token vault tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    ErrorResponse,
    TokenVaultResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.token_vault import (
    TokenVaultTools,
)
from botocore.exceptions import ClientError


class TestIdentityGetTokenVault:
    """Tests for identity_get_token_vault tool."""

    @pytest.mark.asyncio
    async def test_default_vault(self, mock_ctx, client_factory, mock_boto3_client):
        """Gets the default token vault when no ID is provided."""
        mock_boto3_client.get_token_vault.return_value = {
            'tokenVaultId': 'default',
            'kmsConfiguration': {'keyType': 'ServiceManagedKey'},
            'lastModifiedDate': 1700000000,
        }
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_get_token_vault(ctx=mock_ctx)
        assert isinstance(result, TokenVaultResponse)
        assert result.status == 'success'
        assert result.token_vault['tokenVaultId'] == 'default'
        assert result.token_vault['kmsConfiguration']['keyType'] == 'ServiceManagedKey'
        # When token_vault_id is None, no tokenVaultId in API call
        mock_boto3_client.get_token_vault.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_specific_vault(self, mock_ctx, client_factory, mock_boto3_client):
        """Gets a specific token vault by ID."""
        mock_boto3_client.get_token_vault.return_value = {
            'tokenVaultId': 'my-vault',
            'kmsConfiguration': {
                'keyType': 'CustomerManagedKey',
                'kmsKeyArn': 'arn:aws:kms:us-east-1:123:key/abc',
            },
            'lastModifiedDate': 1700000000,
        }
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_get_token_vault(ctx=mock_ctx, token_vault_id='my-vault')
        assert isinstance(result, TokenVaultResponse)
        assert result.token_vault['tokenVaultId'] == 'my-vault'
        assert result.token_vault['kmsConfiguration']['keyType'] == 'CustomerManagedKey'
        mock_boto3_client.get_token_vault.assert_called_once_with(tokenVaultId='my-vault')

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.get_token_vault.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'no vault'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetTokenVault',
        )
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_get_token_vault(ctx=mock_ctx, token_vault_id='missing')
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'


class TestIdentitySetTokenVaultCmk:
    """Tests for identity_set_token_vault_cmk tool."""

    @pytest.mark.asyncio
    async def test_customer_managed_key(self, mock_ctx, client_factory, mock_boto3_client):
        """Sets a customer-managed KMS key on the default vault."""
        kms_config = {
            'keyType': 'CustomerManagedKey',
            'kmsKeyArn': 'arn:aws:kms:us-east-1:123:key/abc',
        }
        mock_boto3_client.set_token_vault_cmk.return_value = {
            'tokenVaultId': 'default',
            'kmsConfiguration': kms_config,
            'lastModifiedDate': 1700000000,
        }
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_set_token_vault_cmk(
            ctx=mock_ctx, kms_configuration=kms_config
        )
        assert isinstance(result, TokenVaultResponse)
        assert result.status == 'success'
        assert result.token_vault['kmsConfiguration']['keyType'] == 'CustomerManagedKey'
        mock_boto3_client.set_token_vault_cmk.assert_called_once_with(kmsConfiguration=kms_config)

    @pytest.mark.asyncio
    async def test_service_managed_key(self, mock_ctx, client_factory, mock_boto3_client):
        """Sets back to a service-managed key on a specific vault."""
        kms_config = {'keyType': 'ServiceManagedKey'}
        mock_boto3_client.set_token_vault_cmk.return_value = {
            'tokenVaultId': 'my-vault',
            'kmsConfiguration': kms_config,
            'lastModifiedDate': 1700000000,
        }
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_set_token_vault_cmk(
            ctx=mock_ctx,
            kms_configuration=kms_config,
            token_vault_id='my-vault',
        )
        assert isinstance(result, TokenVaultResponse)
        mock_boto3_client.set_token_vault_cmk.assert_called_once_with(
            kmsConfiguration=kms_config, tokenVaultId='my-vault'
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError (e.g. KMS key not accessible)."""
        mock_boto3_client.set_token_vault_cmk.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'kms key invalid'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'SetTokenVaultCMK',
        )
        tools = TokenVaultTools(client_factory)
        result = await tools.identity_set_token_vault_cmk(
            ctx=mock_ctx,
            kms_configuration={'keyType': 'CustomerManagedKey', 'kmsKeyArn': 'bad'},
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ValidationException'
