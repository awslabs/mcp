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

"""Unit tests for CodeConnections tools."""

import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.codeconnections import (
    create_codeconnection,
    generate_console_url,
    get_codeconnection,
    get_status_guidance,
    list_codeconnections,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestGenerateConsoleUrl:
    """Tests for the generate_console_url function."""

    def test_generate_console_url_us_east_1(self):
        """Test console URL generation for us-east-1 region."""
        result = generate_console_url('us-east-1')
        expected = 'https://us-east-1.console.aws.amazon.com/codesuite/settings/connections?region=us-east-1'
        assert result == expected

    def test_generate_console_url_eu_west_1(self):
        """Test console URL generation for eu-west-1 region."""
        result = generate_console_url('eu-west-1')
        expected = 'https://eu-west-1.console.aws.amazon.com/codesuite/settings/connections?region=eu-west-1'
        assert result == expected

    def test_generate_console_url_ap_southeast_1(self):
        """Test console URL generation for ap-southeast-1 region."""
        result = generate_console_url('ap-southeast-1')
        expected = 'https://ap-southeast-1.console.aws.amazon.com/codesuite/settings/connections?region=ap-southeast-1'
        assert result == expected

    def test_generate_console_url_contains_region_in_subdomain(self):
        """Test that the generated URL contains the region in the subdomain."""
        region = 'us-west-2'
        result = generate_console_url(region)
        assert result.startswith(f'https://{region}.')

    def test_generate_console_url_contains_region_in_query_param(self):
        """Test that the generated URL contains the region in the query parameter."""
        region = 'eu-central-1'
        result = generate_console_url(region)
        assert f'region={region}' in result

    def test_generate_console_url_points_to_codeconnections_page(self):
        """Test that the generated URL points to the CodeConnections settings page."""
        result = generate_console_url('us-east-1')
        assert 'codesuite/settings/connections' in result

    def test_generate_console_url_is_valid_https_url(self):
        """Test that the generated URL is a valid HTTPS URL."""
        result = generate_console_url('us-east-1')
        assert result.startswith('https://')
        assert '.console.aws.amazon.com/' in result


class TestGetStatusGuidance:
    """Tests for the get_status_guidance function."""

    def test_pending_status_mentions_oauth(self):
        """Test that PENDING status guidance mentions OAuth authorization."""
        result = get_status_guidance('PENDING')
        assert 'OAuth' in result

    def test_pending_status_mentions_console(self):
        """Test that PENDING status guidance mentions the AWS Console."""
        result = get_status_guidance('PENDING')
        assert 'Console' in result or 'console' in result

    def test_pending_status_mentions_authorization(self):
        """Test that PENDING status guidance mentions authorization process."""
        result = get_status_guidance('PENDING')
        assert 'authorization' in result.lower()

    def test_available_status_indicates_ready_for_workflows(self):
        """Test that AVAILABLE status indicates readiness for HealthOmics workflows."""
        result = get_status_guidance('AVAILABLE')
        assert 'ready' in result.lower()
        assert 'HealthOmics' in result or 'workflows' in result.lower()

    def test_available_status_mentions_connection_arn_usage(self):
        """Test that AVAILABLE status mentions how to use the connection ARN."""
        result = get_status_guidance('AVAILABLE')
        assert 'connection_arn' in result or 'ARN' in result

    def test_available_status_mentions_definition_repository(self):
        """Test that AVAILABLE status mentions the definition_repository parameter."""
        result = get_status_guidance('AVAILABLE')
        assert 'definition_repository' in result

    def test_error_status_includes_troubleshooting_guidance(self):
        """Test that ERROR status includes troubleshooting guidance."""
        result = get_status_guidance('ERROR')
        assert 'error' in result.lower()

    def test_error_status_mentions_console_for_details(self):
        """Test that ERROR status mentions checking the AWS Console for details."""
        result = get_status_guidance('ERROR')
        assert 'Console' in result or 'console' in result

    def test_error_status_suggests_creating_new_connection(self):
        """Test that ERROR status suggests creating a new connection."""
        result = get_status_guidance('ERROR')
        assert 'new connection' in result.lower() or 'creating' in result.lower()

    def test_unknown_status_returns_unknown_message(self):
        """Test that unknown status returns an appropriate message."""
        result = get_status_guidance('UNKNOWN_STATUS')
        assert 'Unknown status' in result
        assert 'UNKNOWN_STATUS' in result

    def test_empty_status_returns_unknown_message(self):
        """Test that empty status returns an unknown message."""
        result = get_status_guidance('')
        assert 'Unknown status' in result

    def test_case_sensitive_status_pending(self):
        """Test that status matching is case-sensitive for PENDING."""
        result = get_status_guidance('pending')
        assert 'Unknown status' in result

    def test_case_sensitive_status_available(self):
        """Test that status matching is case-sensitive for AVAILABLE."""
        result = get_status_guidance('available')
        assert 'Unknown status' in result

    def test_case_sensitive_status_error(self):
        """Test that status matching is case-sensitive for ERROR."""
        result = get_status_guidance('error')
        assert 'Unknown status' in result

    def test_pending_guidance_full_content(self):
        """Test the full content of PENDING status guidance."""
        result = get_status_guidance('PENDING')
        expected = (
            'This connection requires OAuth authorization. '
            'Please visit the AWS Console URL provided to complete the authorization process. '
            'Once authorized, the connection status will change to AVAILABLE.'
        )
        assert result == expected

    def test_available_guidance_full_content(self):
        """Test the full content of AVAILABLE status guidance."""
        result = get_status_guidance('AVAILABLE')
        expected = (
            'This connection is ready to use with HealthOmics workflows. '
            'You can use the connection ARN with the definition_repository.connection_arn parameter '
            'when creating workflows from Git repositories.'
        )
        assert result == expected

    def test_error_guidance_full_content(self):
        """Test the full content of ERROR status guidance."""
        result = get_status_guidance('ERROR')
        expected = (
            'This connection has encountered an error. '
            'Please check the AWS Console for more details or try creating a new connection.'
        )
        assert result == expected


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def mock_client():
    """Create a mock CodeConnections client."""
    return MagicMock()


class TestListCodeconnections:
    """Tests for the list_codeconnections function."""

    @pytest.mark.asyncio
    async def test_list_codeconnections_success(self, mock_ctx, mock_client):
        """Test successful listing of CodeConnections."""
        mock_client.list_connections.return_value = {
            'Connections': [
                {
                    'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                    'ConnectionName': 'my-github-connection',
                    'ConnectionStatus': 'AVAILABLE',
                    'ProviderType': 'GitHub',
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert 'connections' in result
        assert len(result['connections']) == 1
        assert result['connections'][0]['connection_name'] == 'my-github-connection'
        assert result['connections'][0]['ready_for_workflows'] is True

    @pytest.mark.asyncio
    async def test_list_codeconnections_with_pagination(self, mock_ctx, mock_client):
        """Test listing with pagination token."""
        mock_client.list_connections.return_value = {
            'Connections': [
                {
                    'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                    'ConnectionName': 'connection-1',
                    'ConnectionStatus': 'AVAILABLE',
                    'ProviderType': 'GitHub',
                }
            ],
            'NextToken': 'next-page-token',
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert 'nextToken' in result
        assert result['nextToken'] == 'next-page-token'

    @pytest.mark.asyncio
    async def test_list_codeconnections_with_provider_filter(self, mock_ctx, mock_client):
        """Test listing with provider type filter."""
        mock_client.list_connections.return_value = {'Connections': []}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            await list_codeconnections(ctx=mock_ctx, provider_type_filter='GitHub')

        mock_client.list_connections.assert_called_once()
        call_args = mock_client.list_connections.call_args
        assert call_args[1]['ProviderTypeFilter'] == 'GitHub'

    @pytest.mark.asyncio
    async def test_list_codeconnections_pending_status(self, mock_ctx, mock_client):
        """Test that PENDING connections are marked as not ready for workflows."""
        mock_client.list_connections.return_value = {
            'Connections': [
                {
                    'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                    'ConnectionName': 'pending-connection',
                    'ConnectionStatus': 'PENDING',
                    'ProviderType': 'GitHub',
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert result['connections'][0]['ready_for_workflows'] is False

    @pytest.mark.asyncio
    async def test_list_codeconnections_client_error(self, mock_ctx, mock_client):
        """Test handling of AWS ClientError."""
        mock_client.list_connections.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'ListConnections',
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert 'error' in result
        assert 'Error listing CodeConnections' in result['error']

    @pytest.mark.asyncio
    async def test_list_codeconnections_botocore_error(self, mock_ctx, mock_client):
        """Test handling of BotoCoreError."""
        mock_client.list_connections.side_effect = botocore.exceptions.BotoCoreError()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert 'error' in result
        assert 'Error listing CodeConnections' in result['error']

    @pytest.mark.asyncio
    async def test_list_codeconnections_unexpected_error(self, mock_ctx, mock_client):
        """Test handling of unexpected errors."""
        mock_client.list_connections.side_effect = RuntimeError('Unexpected error')

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert 'error' in result
        assert 'Error listing CodeConnections' in result['error']

    @pytest.mark.asyncio
    async def test_list_codeconnections_with_next_token(self, mock_ctx, mock_client):
        """Test listing with next_token parameter."""
        mock_client.list_connections.return_value = {'Connections': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            await list_codeconnections(ctx=mock_ctx, next_token='some-token')

        call_args = mock_client.list_connections.call_args
        assert call_args[1]['NextToken'] == 'some-token'

    @pytest.mark.asyncio
    async def test_list_codeconnections_empty_result(self, mock_ctx, mock_client):
        """Test listing when no connections exist."""
        mock_client.list_connections.return_value = {'Connections': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            result = await list_codeconnections(ctx=mock_ctx)

        assert result['connections'] == []
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_list_codeconnections_max_results(self, mock_ctx, mock_client):
        """Test listing with custom max_results."""
        mock_client.list_connections.return_value = {'Connections': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
            return_value=mock_client,
        ):
            await list_codeconnections(ctx=mock_ctx, max_results=50)

        call_args = mock_client.list_connections.call_args
        assert call_args[1]['MaxResults'] == 50


class TestCreateCodeconnection:
    """Tests for the create_codeconnection function."""

    @pytest.mark.asyncio
    async def test_create_codeconnection_success(self, mock_ctx, mock_client):
        """Test successful creation of a CodeConnection."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123'
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'connection_arn' in result
        assert 'console_url' in result
        assert 'guidance' in result
        assert (
            result['connection_arn']
            == 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123'
        )

    @pytest.mark.asyncio
    async def test_create_codeconnection_with_tags(self, mock_ctx, mock_client):
        """Test creation with tags."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123'
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            await create_codeconnection(
                ctx=mock_ctx,
                connection_name='my-connection',
                provider_type='GitHub',
                tags={'Environment': 'Production', 'Team': 'Genomics'},
            )

        call_args = mock_client.create_connection.call_args
        assert 'Tags' in call_args[1]
        tags = call_args[1]['Tags']
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_create_codeconnection_console_url_region(self, mock_ctx, mock_client):
        """Test that console URL contains correct region."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections:eu-west-1:123456789012:connection/abc123'
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'eu-west-1' in result['console_url']

    @pytest.mark.asyncio
    async def test_create_codeconnection_guidance_is_pending(self, mock_ctx, mock_client):
        """Test that guidance is for PENDING status."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123'
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'OAuth' in result['guidance']

    @pytest.mark.asyncio
    async def test_create_codeconnection_client_error(self, mock_ctx, mock_client):
        """Test handling of AWS ClientError."""
        mock_client.create_connection.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Limit exceeded'}},
            'CreateConnection',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'error' in result
        assert 'Error creating CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_create_codeconnection_botocore_error(self, mock_ctx, mock_client):
        """Test handling of BotoCoreError."""
        mock_client.create_connection.side_effect = botocore.exceptions.BotoCoreError()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'error' in result
        assert 'Error creating CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_create_codeconnection_unexpected_error(self, mock_ctx, mock_client):
        """Test handling of unexpected errors."""
        mock_client.create_connection.side_effect = RuntimeError('Unexpected error')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        assert 'error' in result
        assert 'Error creating CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_create_codeconnection_short_arn(self, mock_ctx, mock_client):
        """Test handling of short/malformed ARN (fallback to us-east-1)."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections'  # Malformed ARN
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            result = await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        # Should fallback to us-east-1
        assert 'us-east-1' in result['console_url']

    @pytest.mark.asyncio
    async def test_create_codeconnection_no_tags(self, mock_ctx, mock_client):
        """Test creation without tags."""
        mock_client.create_connection.return_value = {
            'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123'
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_provider_type',
                new_callable=AsyncMock,
                return_value='GitHub',
            ),
        ):
            await create_codeconnection(
                ctx=mock_ctx, connection_name='my-connection', provider_type='GitHub'
            )

        call_args = mock_client.create_connection.call_args
        assert 'Tags' not in call_args[1]


class TestGetCodeconnection:
    """Tests for the get_codeconnection function."""

    @pytest.mark.asyncio
    async def test_get_codeconnection_success(self, mock_ctx, mock_client):
        """Test successful retrieval of a CodeConnection."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'my-connection',
                'ConnectionStatus': 'AVAILABLE',
                'ProviderType': 'GitHub',
                'OwnerAccountId': '123456789012',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert result['connection_name'] == 'my-connection'
        assert result['connection_status'] == 'AVAILABLE'
        assert 'guidance' in result

    @pytest.mark.asyncio
    async def test_get_codeconnection_with_host_arn(self, mock_ctx, mock_client):
        """Test retrieval of a connection with host_arn (self-managed provider)."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'my-gitlab-connection',
                'ConnectionStatus': 'AVAILABLE',
                'ProviderType': 'GitLabSelfManaged',
                'OwnerAccountId': '123456789012',
                'HostArn': 'arn:aws:codeconnections:us-east-1:123456789012:host/xyz789',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert 'host_arn' in result
        assert result['host_arn'] == 'arn:aws:codeconnections:us-east-1:123456789012:host/xyz789'

    @pytest.mark.asyncio
    async def test_get_codeconnection_pending_status(self, mock_ctx, mock_client):
        """Test retrieval of a PENDING connection."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'pending-connection',
                'ConnectionStatus': 'PENDING',
                'ProviderType': 'GitHub',
                'OwnerAccountId': '123456789012',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert result['connection_status'] == 'PENDING'
        assert 'OAuth' in result['guidance']

    @pytest.mark.asyncio
    async def test_get_codeconnection_not_found(self, mock_ctx, mock_client):
        """Test handling of ResourceNotFoundException."""
        mock_client.get_connection.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Connection not found'}},
            'GetConnection',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/nonexistent',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/nonexistent',
            )

        assert 'error' in result
        assert 'Error getting CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_get_codeconnection_client_error(self, mock_ctx, mock_client):
        """Test handling of other AWS ClientErrors."""
        mock_client.get_connection.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'GetConnection',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert 'error' in result
        assert 'Error getting CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_get_codeconnection_botocore_error(self, mock_ctx, mock_client):
        """Test handling of BotoCoreError."""
        mock_client.get_connection.side_effect = botocore.exceptions.BotoCoreError()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert 'error' in result
        assert 'Error getting CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_get_codeconnection_unexpected_error(self, mock_ctx, mock_client):
        """Test handling of unexpected errors."""
        mock_client.get_connection.side_effect = RuntimeError('Unexpected error')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert 'error' in result
        assert 'Error getting CodeConnection' in result['error']

    @pytest.mark.asyncio
    async def test_get_codeconnection_error_status(self, mock_ctx, mock_client):
        """Test retrieval of an ERROR status connection."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'error-connection',
                'ConnectionStatus': 'ERROR',
                'ProviderType': 'GitHub',
                'OwnerAccountId': '123456789012',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert result['connection_status'] == 'ERROR'
        assert 'error' in result['guidance'].lower()

    @pytest.mark.asyncio
    async def test_get_codeconnection_codestar_arn(self, mock_ctx, mock_client):
        """Test retrieval with codestar-connections ARN format."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codestar-connections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'my-connection',
                'ConnectionStatus': 'AVAILABLE',
                'ProviderType': 'GitHub',
                'OwnerAccountId': '123456789012',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codestar-connections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codestar-connections:us-east-1:123456789012:connection/abc123',
            )

        assert result['connection_status'] == 'AVAILABLE'

    @pytest.mark.asyncio
    async def test_get_codeconnection_no_host_arn(self, mock_ctx, mock_client):
        """Test retrieval of a connection without host_arn."""
        mock_client.get_connection.return_value = {
            'Connection': {
                'ConnectionArn': 'arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
                'ConnectionName': 'my-connection',
                'ConnectionStatus': 'AVAILABLE',
                'ProviderType': 'GitHub',
                'OwnerAccountId': '123456789012',
            }
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.get_codeconnections_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.codeconnections.validate_connection_arn',
                new_callable=AsyncMock,
                return_value='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            ),
        ):
            result = await get_codeconnection(
                ctx=mock_ctx,
                connection_arn='arn:aws:codeconnections:us-east-1:123456789012:connection/abc123',
            )

        assert 'host_arn' not in result
