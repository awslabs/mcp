"""MCP integration tests to cover missing server.py lines 583-605."""

import pytest
from awslabs.healthlake_mcp_server.server import create_healthlake_server
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceRequestParams,
    ReadResourceResult,
    TextContent,
)
from typing import cast
from unittest.mock import AsyncMock, patch


class TestMCPIntegrationCoverage:
    """Test MCP integration to cover missing server.py lines."""

    async def test_mcp_call_tool_validation_error(self):
        """Test MCP call_tool with validation error - covers lines 585-587."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.side_effect = ValueError('Invalid input parameter')
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(name='list_datastores', arguments={}),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "validation_error"' in content_text

    async def test_mcp_call_tool_client_error_not_found(self):
        """Test MCP call_tool with ClientError ResourceNotFoundException - covers lines 588-596."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            error_response = {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Datastore not found'}
            }
            mock_client.get_datastore_details.side_effect = ClientError(
                error_response, 'DescribeFHIRDatastore'
            )
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='get_datastore_details', arguments={'datastore_id': 'a' * 32}
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "not_found"' in content_text

    async def test_mcp_call_tool_client_error_validation_exception(self):
        """Test MCP call_tool with ClientError ValidationException - covers lines 588-596."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            error_response = {
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter value'}
            }
            mock_client.create_resource.side_effect = ClientError(error_response, 'CreateResource')
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(
                    name='create_fhir_resource',
                    arguments={
                        'datastore_id': 'a' * 32,
                        'resource_type': 'Patient',
                        'resource_data': {'resourceType': 'Patient'},
                    },
                ),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "validation_error"' in content_text
            assert 'Invalid parameter value' in content_text

    async def test_mcp_call_tool_client_error_unknown(self):
        """Test MCP call_tool with unknown ClientError - covers lines 588-596."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            error_response = {
                'Error': {'Code': 'UnknownServiceError', 'Message': 'Service unavailable'}
            }
            mock_client.list_datastores.side_effect = ClientError(
                error_response, 'ListFHIRDatastores'
            )
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(name='list_datastores', arguments={}),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "service_error"' in content_text

    async def test_mcp_call_tool_no_credentials_error(self):
        """Test MCP call_tool with NoCredentialsError - covers lines 597-599."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.side_effect = NoCredentialsError()
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(name='list_datastores', arguments={}),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "auth_error"' in content_text
            assert 'AWS credentials not configured' in content_text

    async def test_mcp_call_tool_unexpected_error(self):
        """Test MCP call_tool with unexpected error - covers lines 600-602."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.side_effect = RuntimeError('Unexpected system error')
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            call_tool_handler = server.request_handlers[CallToolRequest]

            request = CallToolRequest(
                method='tools/call',
                params=CallToolRequestParams(name='list_datastores', arguments={}),
            )

            response = await call_tool_handler(request)
            result = cast(CallToolResult, response.root)

            content_text = cast(TextContent, result.content[0]).text
            assert '"error": true' in content_text
            assert '"type": "server_error"' in content_text
            assert 'Internal server error' in content_text

    async def test_mcp_list_tools_handler(self):
        """Test MCP list_tools handler - covers line 233."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient'):
            server = create_healthlake_server()
            list_tools_handler = server.request_handlers[ListToolsRequest]

            request = ListToolsRequest(method='tools/list')
            response = await list_tools_handler(request)
            result = cast(ListToolsResult, response.root)

            assert len(result.tools) == 11
            assert result.tools[0].name == 'list_datastores'

    async def test_mcp_list_resources_handler_success(self):
        """Test MCP list_resources handler success - covers lines 552-565."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.return_value = {
                'DatastorePropertiesList': [
                    {
                        'DatastoreId': 'a' * 32,
                        'DatastoreName': 'test-datastore',
                        'DatastoreStatus': 'ACTIVE',
                        'DatastoreTypeVersion': 'R4',
                        'CreatedAt': datetime(2024, 1, 1),
                        'DatastoreEndpoint': 'https://healthlake.us-east-1.amazonaws.com/datastore/test',
                    }
                ]
            }
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            list_resources_handler = server.request_handlers[ListResourcesRequest]

            request = ListResourcesRequest(method='resources/list')
            response = await list_resources_handler(request)
            result = cast(ListResourcesResult, response.root)

            assert len(result.resources) == 1
            assert 'test-datastore' in result.resources[0].name
            assert 'ACTIVE' in result.resources[0].name

    async def test_mcp_list_resources_handler_error(self):
        """Test MCP list_resources handler error - covers lines 562-565."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.side_effect = RuntimeError('Service error')
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            list_resources_handler = server.request_handlers[ListResourcesRequest]

            request = ListResourcesRequest(method='resources/list')
            response = await list_resources_handler(request)
            result = cast(ListResourcesResult, response.root)

            assert len(result.resources) == 0

    async def test_mcp_read_resource_handler_success(self):
        """Test MCP read_resource handler success - covers lines 570-574."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_datastore_details.return_value = {
                'DatastoreId': 'a' * 32,
                'DatastoreName': 'test-datastore',
            }
            mock_client_class.return_value = mock_client

            server = create_healthlake_server()
            read_resource_handler = server.request_handlers[ReadResourceRequest]

            from pydantic import AnyUrl

            request = ReadResourceRequest(
                method='resources/read',
                params=ReadResourceRequestParams(uri=AnyUrl(f'healthlake://datastore/{"a" * 32}')),
            )

            response = await read_resource_handler(request)
            result = cast(ReadResourceResult, response.root)

            # The response is a string (deprecated format), so we check it directly
            assert 'test-datastore' in str(result.contents[0])

    async def test_mcp_read_resource_handler_invalid_uri(self):
        """Test MCP read_resource handler with invalid URI - covers lines 571-573."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient'):
            server = create_healthlake_server()
            read_resource_handler = server.request_handlers[ReadResourceRequest]

            from pydantic import AnyUrl

            request = ReadResourceRequest(
                method='resources/read',
                params=ReadResourceRequestParams(uri=AnyUrl('invalid://uri/format')),
            )

            with pytest.raises(ValueError, match='Unknown resource URI'):
                await read_resource_handler(request)
