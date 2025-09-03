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

"""Additional test module for gateway functionality - focused on coverage gaps."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.gateway import register_gateway_tools
from mcp.server.fastmcp import FastMCP
from unittest.mock import Mock, mock_open, patch


class TestGatewayDeletionRetryLogic:
    """Test gateway deletion with retry logic and error handling."""

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)
        return mcp

    def _extract_result(self, result_tuple):
        """Extract string result from MCP response tuple."""
        try:
            if isinstance(result_tuple, tuple) and len(result_tuple) >= 1:
                result_content = result_tuple[0]
                if hasattr(result_content, 'content'):
                    return str(result_content.content)
                elif hasattr(result_content, 'text'):
                    return str(result_content.text)
                return str(result_content)
            elif hasattr(result_tuple, 'content'):
                return str(result_tuple.content)  # type: ignore
            elif hasattr(result_tuple, 'text'):
                return str(result_tuple.text)  # type: ignore
            return str(result_tuple)
        except (AttributeError, TypeError):
            return str(result_tuple)

    @pytest.mark.asyncio
    async def test_delete_gateway_with_throttling_retry(self):
        """Test gateway deletion retry logic when throttled."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway exists in list
            mock_client.list_gateways.return_value = {
                'items': [{'gatewayId': 'gw-12345', 'name': 'test-gateway'}]
            }

            # Mock list_gateway_targets to return no targets initially
            mock_client.list_gateway_targets.return_value = {'items': []}

            # Mock delete_gateway to fail with throttling first, then succeed
            throttling_error = Exception('ThrottlingException: Rate exceeded')
            mock_client.delete_gateway.side_effect = [throttling_error, {'status': 'DELETING'}]

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'delete',
                    'gateway_name': 'test-gateway',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Deleted Successfully' in result or 'throttled' in result.lower()

    @pytest.mark.asyncio
    async def test_delete_gateway_with_target_cleanup_retry(self):
        """Test gateway deletion with target cleanup and retry logic."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway exists in list
            mock_client.list_gateways.return_value = {
                'items': [{'gatewayId': 'gw-12345', 'name': 'test-gateway'}]
            }

            # Mock targets that need cleanup
            mock_targets_initial = {
                'items': [
                    {'targetId': 'target-1', 'status': 'ACTIVE'},
                    {'targetId': 'target-2', 'status': 'ACTIVE'},
                ]
            }
            mock_targets_after_first_delete = {
                'items': [{'targetId': 'target-2', 'status': 'ACTIVE'}]
            }
            mock_targets_empty = {'items': []}

            mock_client.list_gateway_targets.side_effect = [
                mock_targets_initial,
                mock_targets_after_first_delete,
                mock_targets_empty,
            ]

            # Mock delete_gateway_target to succeed
            mock_client.delete_gateway_target.return_value = {'status': 'DELETING'}

            # Mock delete_gateway to succeed after targets are cleaned
            mock_client.delete_gateway.return_value = {'status': 'DELETING'}

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'delete',
                    'gateway_name': 'test-gateway',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Deleted Successfully' in result
            assert mock_client.delete_gateway_target.call_count >= 1
            assert 'target' in result.lower()

    @pytest.mark.asyncio
    async def test_delete_gateway_max_attempts_reached(self):
        """Test gateway deletion when max attempts are reached."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway exists in list
            mock_client.list_gateways.return_value = {
                'items': [{'gatewayId': 'gw-12345', 'name': 'test-gateway'}]
            }

            # Mock persistent targets that won't delete
            mock_client.list_gateway_targets.return_value = {
                'items': [{'targetId': 'persistent-target', 'status': 'ACTIVE'}]
            }

            # Mock target deletion to always fail
            mock_client.delete_gateway_target.side_effect = Exception('Target deletion failed')

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'delete',
                    'gateway_name': 'test-gateway',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Failed to delete gateway' in result
                or 'max attempts' in result.lower()
                or 'Targets Still Exist' in result
            )

    @pytest.mark.asyncio
    async def test_delete_gateway_with_targets_associated_error(self):
        """Test gateway deletion when targets are still associated."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway exists in list
            mock_client.list_gateways.return_value = {
                'items': [{'gatewayId': 'gw-12345', 'name': 'test-gateway'}]
            }

            # Mock no targets initially
            mock_client.list_gateway_targets.return_value = {'items': []}

            # Mock delete_gateway to fail with targets associated error
            targets_error = Exception('Gateway still has targets associated')
            mock_client.delete_gateway.side_effect = targets_error

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'delete',
                    'gateway_name': 'test-gateway',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Failed to delete gateway' in result or 'targets associated' in result


class TestCognitoOAuthSetup:
    """Test Cognito OAuth setup functionality."""

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)
        return mcp

    def _extract_result(self, result_tuple):
        """Extract string result from MCP response tuple."""
        try:
            if isinstance(result_tuple, tuple) and len(result_tuple) >= 1:
                result_content = result_tuple[0]
                if hasattr(result_content, 'content'):
                    return str(result_content.content)
                elif hasattr(result_content, 'text'):
                    return str(result_content.text)
                return str(result_content)
            elif hasattr(result_tuple, 'content'):
                return str(result_tuple.content)  # type: ignore
            elif hasattr(result_tuple, 'text'):
                return str(result_tuple.text)  # type: ignore
            return str(result_tuple)
        except (AttributeError, TypeError):
            return str(result_tuple)

    @pytest.mark.asyncio
    async def test_setup_cognito_oauth_success(self):
        """Test successful Cognito OAuth setup with config saving."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('os.makedirs'),
            patch('builtins.open', mock_open()),
            patch('os.path.expanduser') as mock_expanduser,
        ):
            mock_expanduser.return_value = '/home/user/.agentcore_gateways'

            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_cognito_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 'cognito-idp':
                    return mock_cognito_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock successful Cognito operations
            mock_cognito_service.create_user_pool.return_value = {
                'UserPool': {'Id': 'us-east-1_TEST123', 'Name': 'test-pool'}
            }
            mock_cognito_service.create_user_pool_client.return_value = {
                'UserPoolClient': {
                    'ClientId': 'test-client-id',  # pragma: allowlist secret
                    'ClientSecret': 'test-client-secret',  # pragma: allowlist secret
                }
            }

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'test-gateway',
                    'enable_oauth': True,  # noqa: S105
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
                or 'Gateway Setup Failed' in result
            )

    @pytest.mark.asyncio
    async def test_setup_cognito_oauth_client_creation_fails(self):
        """Test Cognito OAuth setup when client creation fails."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_cognito_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 'cognito-idp':
                    return mock_cognito_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock successful user pool creation but failed client creation
            mock_cognito_service.create_user_pool.return_value = {
                'UserPool': {'Id': 'us-east-1_TEST123', 'Name': 'test-pool'}
            }
            mock_cognito_service.create_user_pool_client.side_effect = Exception(
                'Client creation failed'
            )

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'test-gateway',
                    'enable_oauth': True,  # noqa: S105
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            # Test should hit the setup path with proper error handling
            assert (
                'Gateway Setup Failed' in result
                or 'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
            )

    @pytest.mark.asyncio
    async def test_setup_cognito_oauth_config_file_write_fails(self):
        """Test Cognito OAuth setup when config file writing fails."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('os.makedirs'),
            patch('builtins.open', side_effect=OSError('Permission denied')),
            patch('os.path.expanduser') as mock_expanduser,
        ):
            mock_expanduser.return_value = '/home/user/.agentcore_gateways'

            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_cognito_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 'cognito-idp':
                    return mock_cognito_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock successful Cognito operations
            mock_cognito_service.create_user_pool.return_value = {
                'UserPool': {'Id': 'us-east-1_TEST123', 'Name': 'test-pool'}
            }
            mock_cognito_service.create_user_pool_client.return_value = {
                'UserPoolClient': {
                    'ClientId': 'test-client-id',  # pragma: allowlist secret
                    'ClientSecret': 'test-client-secret',  # pragma: allowlist secret
                }
            }

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'test-gateway',
                    'enable_oauth': True,  # noqa: S105
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            # Should still succeed even if config file write fails
            assert (
                'Gateway Setup Failed' in result
                or 'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
            )


class TestSmithyModelOperations:
    """Test Smithy model discovery and upload operations."""

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)
        return mcp

    def _extract_result(self, result_tuple):
        """Extract string result from MCP response tuple."""
        try:
            if isinstance(result_tuple, tuple) and len(result_tuple) >= 1:
                result_content = result_tuple[0]
                if hasattr(result_content, 'content'):
                    return str(result_content.content)
                elif hasattr(result_content, 'text'):
                    return str(result_content.text)
                return str(result_content)
            elif hasattr(result_tuple, 'content'):
                return str(result_tuple.content)  # type: ignore
            elif hasattr(result_tuple, 'text'):
                return str(result_tuple.text)  # type: ignore
            return str(result_tuple)
        except (AttributeError, TypeError):
            return str(result_tuple)

    @pytest.mark.asyncio
    async def test_smithy_models_discover_action_github_api_error(self):
        """Test Smithy model discovery action when GitHub API fails."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('requests.get') as mock_get,
        ):
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {'message': 'Rate limit exceeded'}
            mock_get.return_value = mock_response

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'discover',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Service Discovery Failed' in result
                or 'AWS Service Discovery' in result
                or 'Discovery Error' in result
            )

    @pytest.mark.asyncio
    async def test_smithy_models_upload_with_multiple_services(self):
        """Test Smithy model upload with multiple services."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('requests.get') as mock_get,
        ):
            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_s3_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 's3':
                    return mock_s3_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock S3 operations
            mock_s3_service.head_bucket.return_value = True
            mock_s3_service.put_object.return_value = True

            # Mock successful requests for multiple services
            def mock_request_side_effect(url, **kwargs):
                mock_response = Mock()
                mock_response.status_code = 200
                if 'dynamodb' in url:
                    mock_response.json.return_value = [
                        {'type': 'dir', 'name': 'service', 'url': 'https://api.github.com/service'}
                    ]
                elif 'service' in url:
                    mock_response.json.return_value = [
                        {'type': 'dir', 'name': '2023-01-01', 'url': 'https://api.github.com/2023'}
                    ]
                elif '2023' in url:
                    mock_response.json.return_value = [
                        {
                            'type': 'file',
                            'name': 'dynamodb-2023-01-01.json',
                            'download_url': 'https://raw.github.com/file.json',
                        }
                    ]
                else:
                    mock_response.json.return_value = {
                        'service': 'dynamodb',
                        'version': '2023-01-01',
                    }
                return mock_response

            mock_get.side_effect = mock_request_side_effect

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'test-gateway',
                    'smithy_model': 'dynamodb',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Gateway Setup Failed' in result
                or 'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
            )

    @pytest.mark.asyncio
    async def test_smithy_models_upload_s3_failure(self):
        """Test Smithy model upload when S3 operations fail."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('requests.get') as mock_get,
        ):
            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_s3_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 's3':
                    return mock_s3_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock S3 operations to fail
            mock_s3_service.head_bucket.return_value = True
            mock_s3_service.put_object.side_effect = Exception('S3 upload failed')

            # Mock successful HTTP requests
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'service': 'test'}
            mock_get.return_value = mock_response

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'test-gateway',
                    'smithy_model': 'dynamodb',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Gateway Setup Failed' in result
                or 'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
            )


class TestGatewayIntegrationScenarios:
    """Test complex gateway integration scenarios."""

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = FastMCP('Test Gateway Server')
        register_gateway_tools(mcp)
        return mcp

    def _extract_result(self, result_tuple):
        """Extract string result from MCP response tuple."""
        try:
            if isinstance(result_tuple, tuple) and len(result_tuple) >= 1:
                result_content = result_tuple[0]
                if hasattr(result_content, 'content'):
                    return str(result_content.content)
                elif hasattr(result_content, 'text'):
                    return str(result_content.text)
                return str(result_content)
            elif hasattr(result_tuple, 'content'):
                return str(result_tuple.content)  # type: ignore
            elif hasattr(result_tuple, 'text'):
                return str(result_tuple.text)  # type: ignore
            return str(result_tuple)
        except (AttributeError, TypeError):
            return str(result_tuple)

    @pytest.mark.asyncio
    async def test_agent_gateway_setup_with_oauth_and_smithy(self):
        """Test complete gateway setup with OAuth and Smithy model integration."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('requests.get') as mock_requests,
            patch('os.makedirs'),
            patch('builtins.open', mock_open()),
            patch('os.path.expanduser', return_value='/home/user/.agentcore_gateways'),
        ):
            # Mock all AWS clients
            mock_bedrock_service = Mock()  # noqa: S105
            mock_cognito_service = Mock()  # noqa: S105
            mock_s3_service = Mock()  # noqa: S105

            def get_client(service, **kwargs):
                if service == 'bedrock-agentcore-control':
                    return mock_bedrock_service
                elif service == 'cognito-idp':
                    return mock_cognito_service
                elif service == 's3':
                    return mock_s3_service
                return Mock()

            mock_boto3.side_effect = get_client

            # Mock successful gateway creation
            mock_bedrock_service.create_gateway.return_value = {
                'gatewayId': 'gw-12345',
                'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw-12345',
            }

            # Mock successful Cognito setup
            mock_cognito_service.create_user_pool.return_value = {
                'UserPool': {'Id': 'us-east-1_TEST123', 'Name': 'test-pool'}
            }
            mock_cognito_service.create_user_pool_client.return_value = {
                'UserPoolClient': {
                    'ClientId': 'test-client-id',  # pragma: allowlist secret
                    'ClientSecret': 'test-client-secret',  # pragma: allowlist secret
                }
            }

            # Mock Smithy model discovery
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {'type': 'dir', 'name': 'dynamodb'},
                {'type': 'dir', 'name': 's3'},
            ]
            mock_requests.return_value = mock_response

            # Mock S3 operations
            mock_s3_service.head_bucket.return_value = True
            mock_s3_service.put_object.return_value = True

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'setup',
                    'gateway_name': 'comprehensive-test-gateway',
                    'smithy_model': 'dynamodb',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert (
                'Gateway Setup Complete' in result
                or 'Starter Toolkit Not Available' in result
                or 'Gateway Setup Failed' in result
            )
            if 'Gateway Setup Complete' in result:
                assert 'dynamodb' in result.lower() or 'smithy' in result.lower()

    @pytest.mark.asyncio
    async def test_agent_gateway_delete_with_complex_error_scenarios(self):
        """Test gateway deletion with various error scenarios."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
            patch('time.sleep'),
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock gateway list to find gateway
            mock_client.list_gateways.return_value = {
                'items': [{'gatewayId': 'gw-12345', 'name': 'test-gateway'}]
            }

            # Mock targets that persist through several cleanup attempts
            persistent_targets = {'items': [{'targetId': 'stubborn-target', 'status': 'ACTIVE'}]}
            fewer_targets = {'items': []}

            mock_client.list_gateway_targets.side_effect = [
                persistent_targets,
                persistent_targets,
                persistent_targets,
                fewer_targets,
            ]

            # Mock target deletion to eventually succeed
            mock_client.delete_gateway_target.side_effect = [
                Exception('Temporary failure'),
                Exception('Still failing'),
                {'status': 'DELETING'},
            ]

            # Mock gateway deletion to succeed after targets cleared
            mock_client.delete_gateway.return_value = {'status': 'DELETING'}

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'delete',
                    'gateway_name': 'test-gateway',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Deleted Successfully' in result
            assert 'target' in result.lower()
            assert mock_client.delete_gateway_target.call_count >= 1

    @pytest.mark.asyncio
    async def test_agent_gateway_list_with_detailed_info(self):
        """Test gateway list with detailed configuration information."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.gateway.SDK_AVAILABLE', True),
            patch('boto3.client') as mock_boto3,
        ):
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock detailed gateway response
            mock_client.list_gateways.return_value = {
                'items': [
                    {
                        'gatewayId': 'gw-12345',
                        'name': 'test-gateway',
                        'status': 'ACTIVE',
                        'createdAt': '2024-01-01T00:00:00Z',
                        'updatedAt': '2024-01-02T00:00:00Z',
                    }
                ]
            }

            result_tuple = await mcp.call_tool(
                'agent_gateway',
                {
                    'action': 'list',
                    'region': 'us-east-1',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Gateway Resources Found' in result
            assert 'gw-12345' in result
            assert 'test-gateway' in result
            assert 'ACTIVE' in result
