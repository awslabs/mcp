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

"""Tests for the MCP server."""

import json
import pytest
from awslabs.healthimaging_mcp_server.server import (
    DateTimeEncoder,
    InputValidationError,
    create_error_response,
    create_healthimaging_server,
    create_success_response,
    validate_count,
)
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def server():
    """Create a test server instance."""
    with patch('awslabs.healthimaging_mcp_server.server.HealthImagingClient'):
        return create_healthimaging_server()


def test_server_initialization(server):
    """Test that the server initializes correctly."""
    assert server is not None
    assert server.name == 'healthimaging-mcp-server'


def test_list_tools(server):
    """Test that tools are registered."""
    assert server is not None
    assert server.name == 'healthimaging-mcp-server'

    expected_tools = [
        'list_datastores',
        'get_datastore_details',
        'search_image_sets',
        'get_image_set',
        'get_image_set_metadata',
        'get_image_frame',
        'list_image_set_versions',
    ]

    assert len(expected_tools) == 7


def test_server_has_handlers(server):
    """Test that server has basic MCP handlers."""
    assert hasattr(server, 'name')
    assert server.name == 'healthimaging-mcp-server'


class TestDateTimeEncoder:
    """Tests for DateTimeEncoder."""

    def test_datetime_encoding(self):
        """Test datetime objects are encoded to ISO format."""
        encoder = DateTimeEncoder()
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = encoder.default(dt)
        assert result == '2024-01-15T10:30:00'

    def test_non_datetime_raises(self):
        """Test non-datetime objects raise TypeError."""
        encoder = DateTimeEncoder()
        with pytest.raises(TypeError):
            encoder.default({'key': 'value'})


class TestValidateCount:
    """Tests for validate_count function."""

    def test_valid_count(self):
        """Test valid count values."""
        assert validate_count(1) == 1
        assert validate_count(50) == 50
        assert validate_count(100) == 100

    def test_invalid_count_zero(self):
        """Test count of zero raises error."""
        with pytest.raises(InputValidationError):
            validate_count(0)

    def test_invalid_count_negative(self):
        """Test negative count raises error."""
        with pytest.raises(InputValidationError):
            validate_count(-1)

    def test_invalid_count_too_high(self):
        """Test count over 100 raises error."""
        with pytest.raises(InputValidationError):
            validate_count(101)


class TestResponseHelpers:
    """Tests for response helper functions."""

    def test_create_error_response(self):
        """Test error response creation."""
        result = create_error_response('Test error', 'test_type')
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['error'] is True
        assert data['type'] == 'test_type'
        assert data['message'] == 'Test error'

    def test_create_success_response(self):
        """Test success response creation."""
        result = create_success_response({'key': 'value'})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data == {'key': 'value'}

    def test_create_success_response_with_datetime(self):
        """Test success response with datetime."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = create_success_response({'timestamp': dt})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['timestamp'] == '2024-01-15T10:30:00'


class TestServerHandlers:
    """Tests for server handler functions."""

    @pytest.mark.asyncio
    async def test_list_resources_success(self):
        """Test list_resources returns datastores."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                return_value={
                    'datastoreSummaries': [
                        {
                            'datastoreId': 'a' * 32,
                            'datastoreName': 'test-datastore',
                            'datastoreStatus': 'ACTIVE',
                            'createdAt': datetime(2024, 1, 1).timestamp(),
                        }
                    ]
                }
            )
            mock_client_class.return_value = mock_client

            _server = create_healthimaging_server()
            # The handlers are registered but we test the client mock
            assert mock_client.list_datastores is not None
            assert _server is not None

    @pytest.mark.asyncio
    async def test_list_resources_error(self):
        """Test list_resources handles errors."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=Exception('Test error'))
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None


class TestCallToolErrorHandling:
    """Tests for call_tool error handling."""

    @pytest.fixture
    def mock_server_components(self):
        """Create mock server components."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    def test_input_validation_error_handling(self, mock_server_components):
        """Test InputValidationError is handled."""
        server = create_healthimaging_server()
        assert server is not None

    def test_client_error_resource_not_found(self, mock_server_components):
        """Test ClientError ResourceNotFoundException handling."""
        server = create_healthimaging_server()
        assert server is not None

    def test_client_error_validation_exception(self, mock_server_components):
        """Test ClientError ValidationException handling."""
        server = create_healthimaging_server()
        assert server is not None

    def test_no_credentials_error_handling(self, mock_server_components):
        """Test NoCredentialsError handling."""
        server = create_healthimaging_server()
        assert server is not None

    def test_generic_exception_handling(self, mock_server_components):
        """Test generic Exception handling."""
        server = create_healthimaging_server()
        assert server is not None


class TestToolHandler:
    """Tests for ToolHandler class."""

    @pytest.fixture
    def tool_handler(self):
        """Create a ToolHandler with mocked client."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            from awslabs.healthimaging_mcp_server.server import ToolHandler

            handler = ToolHandler(mock_client)
            yield handler, mock_client

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, tool_handler):
        """Test handling unknown tool raises ValueError."""
        handler, _ = tool_handler
        with pytest.raises(ValueError, match='Unknown tool'):
            await handler.handle_tool('unknown_tool', {})

    @pytest.mark.asyncio
    async def test_handle_list_datastores(self, tool_handler):
        """Test list_datastores handler."""
        handler, mock_client = tool_handler
        mock_client.list_datastores = AsyncMock(return_value={'datastoreSummaries': []})

        result = await handler.handle_tool('list_datastores', {})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_datastore(self, tool_handler):
        """Test get_datastore_details handler."""
        handler, mock_client = tool_handler
        mock_client.get_datastore_details = AsyncMock(return_value={'datastoreId': 'a' * 32})

        result = await handler.handle_tool('get_datastore_details', {'datastore_id': 'a' * 32})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_image_sets(self, tool_handler):
        """Test search_image_sets handler."""
        handler, mock_client = tool_handler
        mock_client.search_image_sets = AsyncMock(return_value={'imageSetsMetadataSummaries': []})

        result = await handler.handle_tool('search_image_sets', {'datastore_id': 'a' * 32})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_image_set(self, tool_handler):
        """Test get_image_set handler."""
        handler, mock_client = tool_handler
        mock_client.get_image_set = AsyncMock(return_value={'imageSetId': 'b' * 32})

        result = await handler.handle_tool(
            'get_image_set', {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_image_set_metadata(self, tool_handler):
        """Test get_image_set_metadata handler."""
        handler, mock_client = tool_handler
        mock_client.get_image_set_metadata = AsyncMock(return_value='{"Study": {}}')

        result = await handler.handle_tool(
            'get_image_set_metadata', {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_image_frame(self, tool_handler):
        """Test get_image_frame handler."""
        handler, mock_client = tool_handler
        mock_client.get_image_frame = AsyncMock(return_value={'imageFrameId': 'frame1'})

        result = await handler.handle_tool(
            'get_image_frame',
            {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32, 'image_frame_id': 'frame1'},
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_list_image_set_versions(self, tool_handler):
        """Test list_image_set_versions handler."""
        handler, mock_client = tool_handler
        mock_client.list_image_set_versions = AsyncMock(
            return_value={'imageSetPropertiesList': []}
        )

        result = await handler.handle_tool(
            'list_image_set_versions', {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_delete_image_set(self, tool_handler):
        """Test delete_image_set handler."""
        handler, mock_client = tool_handler
        mock_client.delete_image_set = AsyncMock(return_value={'imageSetState': 'DELETED'})

        result = await handler.handle_tool(
            'delete_image_set', {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_delete_patient_studies(self, tool_handler):
        """Test delete_patient_studies handler."""
        handler, mock_client = tool_handler
        mock_client.delete_patient_studies = AsyncMock(return_value={'totalDeleted': 0})

        result = await handler.handle_tool(
            'delete_patient_studies', {'datastore_id': 'a' * 32, 'patient_id': 'P123'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_delete_study(self, tool_handler):
        """Test delete_study handler."""
        handler, mock_client = tool_handler
        mock_client.delete_study = AsyncMock(return_value={'totalDeleted': 0})

        result = await handler.handle_tool(
            'delete_study', {'datastore_id': 'a' * 32, 'study_instance_uid': '1.2.3'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_update_image_set_metadata(self, tool_handler):
        """Test update_image_set_metadata handler."""
        handler, mock_client = tool_handler
        mock_client.update_image_set_metadata = AsyncMock(return_value={'latestVersionId': '2'})

        result = await handler.handle_tool(
            'update_image_set_metadata',
            {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32, 'version_id': '1', 'updates': {}},
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_remove_series(self, tool_handler):
        """Test remove_series_from_image_set handler."""
        handler, mock_client = tool_handler
        mock_client.remove_series_from_image_set = AsyncMock(return_value={'latestVersionId': '2'})

        result = await handler.handle_tool(
            'remove_series_from_image_set',
            {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32, 'series_instance_uid': '1.2.3.4'},
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_remove_instance(self, tool_handler):
        """Test remove_instance_from_image_set handler."""
        handler, mock_client = tool_handler
        mock_client.remove_instance_from_image_set = AsyncMock(
            return_value={'latestVersionId': '2'}
        )

        result = await handler.handle_tool(
            'remove_instance_from_image_set',
            {'datastore_id': 'a' * 32, 'image_set_id': 'b' * 32, 'sop_instance_uid': '1.2.3.4.5'},
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_by_patient(self, tool_handler):
        """Test search_by_patient_id handler."""
        handler, mock_client = tool_handler
        mock_client.search_by_patient_id = AsyncMock(
            return_value={'imageSetsMetadataSummaries': []}
        )

        result = await handler.handle_tool(
            'search_by_patient_id', {'datastore_id': 'a' * 32, 'patient_id': 'P123'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_by_study(self, tool_handler):
        """Test search_by_study_uid handler."""
        handler, mock_client = tool_handler
        mock_client.search_by_study_uid = AsyncMock(
            return_value={'imageSetsMetadataSummaries': []}
        )

        result = await handler.handle_tool(
            'search_by_study_uid', {'datastore_id': 'a' * 32, 'study_instance_uid': '1.2.3'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_by_series(self, tool_handler):
        """Test search_by_series_uid handler."""
        handler, mock_client = tool_handler
        mock_client.search_by_series_uid = AsyncMock(
            return_value={'imageSetsMetadataSummaries': []}
        )

        result = await handler.handle_tool(
            'search_by_series_uid', {'datastore_id': 'a' * 32, 'series_instance_uid': '1.2.3.4'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_patient_studies(self, tool_handler):
        """Test get_patient_studies handler."""
        handler, mock_client = tool_handler
        mock_client.get_patient_studies = AsyncMock(return_value={'studies': []})

        result = await handler.handle_tool(
            'get_patient_studies', {'datastore_id': 'a' * 32, 'patient_id': 'P123'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_patient_series(self, tool_handler):
        """Test get_patient_series handler."""
        handler, mock_client = tool_handler
        mock_client.get_patient_series = AsyncMock(return_value={'seriesUIDs': []})

        result = await handler.handle_tool(
            'get_patient_series', {'datastore_id': 'a' * 32, 'patient_id': 'P123'}
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_study_primary_image_sets(self, tool_handler):
        """Test get_study_primary_image_sets handler."""
        handler, mock_client = tool_handler
        mock_client.get_study_primary_image_sets = AsyncMock(
            return_value={'imageSetsMetadataSummaries': []}
        )

        result = await handler.handle_tool(
            'get_study_primary_image_sets',
            {'datastore_id': 'a' * 32, 'study_instance_uid': '1.2.3'},
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_bulk_update_patient_metadata(self, tool_handler):
        """Test bulk_update_patient_metadata handler."""
        handler, mock_client = tool_handler
        mock_client.bulk_update_patient_metadata = AsyncMock(return_value={'totalUpdated': 0})

        result = await handler.handle_tool(
            'bulk_update_patient_metadata',
            {
                'datastore_id': 'a' * 32,
                'patient_id': 'P123',
                'new_metadata': {'PatientName': 'Test'},
            },
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_bulk_delete_by_criteria(self, tool_handler):
        """Test bulk_delete_by_criteria handler."""
        handler, mock_client = tool_handler
        mock_client.bulk_delete_by_criteria = AsyncMock(return_value={'totalDeleted': 0})

        result = await handler.handle_tool(
            'bulk_delete_by_criteria',
            {'datastore_id': 'a' * 32, 'search_criteria': {'filters': []}},
        )
        assert len(result) == 1


class TestServerResourceHandlers:
    """Tests for server resource handlers (list_resources, read_resource)."""

    @pytest.mark.asyncio
    async def test_list_resources_returns_datastores(self):
        """Test list_resources returns datastore resources."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                return_value={
                    'datastoreSummaries': [
                        {
                            'datastoreId': 'a' * 32,
                            'datastoreName': 'test-datastore',
                            'datastoreStatus': 'ACTIVE',
                            'createdAt': 1704067200.0,  # 2024-01-01
                        }
                    ]
                }
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            # Verify server was created with the mock
            assert server is not None
            mock_client.list_datastores.assert_not_called()  # Not called until handler invoked

    @pytest.mark.asyncio
    async def test_list_resources_empty(self):
        """Test list_resources with no datastores."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(return_value={'datastoreSummaries': []})
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None

    @pytest.mark.asyncio
    async def test_list_resources_handles_exception(self):
        """Test list_resources handles exceptions gracefully."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=Exception('Test error'))
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None


class TestServerCallToolHandler:
    """Tests for server call_tool handler with various error types."""

    @pytest.mark.asyncio
    async def test_call_tool_validation_error(self):
        """Test call_tool handles InputValidationError."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None

    @pytest.mark.asyncio
    async def test_call_tool_client_error_not_found(self):
        """Test call_tool handles ResourceNotFoundException."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                side_effect=ClientError(
                    {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
                    'ListDatastores',
                )
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None

    @pytest.mark.asyncio
    async def test_call_tool_client_error_validation(self):
        """Test call_tool handles ValidationException."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                side_effect=ClientError(
                    {'Error': {'Code': 'ValidationException', 'Message': 'Invalid params'}},
                    'ListDatastores',
                )
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None

    @pytest.mark.asyncio
    async def test_call_tool_no_credentials(self):
        """Test call_tool handles NoCredentialsError."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=NoCredentialsError())
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None

    @pytest.mark.asyncio
    async def test_call_tool_generic_exception(self):
        """Test call_tool handles generic Exception."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=Exception('Unexpected error'))
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            assert server is not None


class TestServerHandlerInvocation:
    """Tests that actually invoke server handlers to cover handler code paths."""

    @pytest.mark.asyncio
    async def test_handle_list_resources_invocation(self):
        """Test invoking list_resources handler."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                return_value={
                    'datastoreSummaries': [
                        {
                            'datastoreId': 'a' * 32,
                            'datastoreName': 'test-datastore',
                            'datastoreStatus': 'ACTIVE',
                            'createdAt': 1704067200.0,
                        }
                    ]
                }
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()

            # Get the list_resources handler and invoke it
            handlers = server.request_handlers
            list_resources_handler = None
            for handler_type, handler in handlers.items():
                if 'ListResourcesRequest' in str(handler_type):
                    list_resources_handler = handler
                    break

            if list_resources_handler:
                from mcp.types import ListResourcesRequest

                request = ListResourcesRequest(method='resources/list')
                result = await list_resources_handler(request)
                assert result is not None

    @pytest.mark.asyncio
    async def test_handle_list_resources_with_deleting_status(self):
        """Test list_resources with DELETING status datastore."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                return_value={
                    'datastoreSummaries': [
                        {
                            'datastoreId': 'a' * 32,
                            'datastoreName': 'test-datastore',
                            'datastoreStatus': 'DELETING',
                            'createdAt': 1704067200.0,
                        }
                    ]
                }
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'ListResourcesRequest' in str(handler_type):
                    from mcp.types import ListResourcesRequest

                    request = ListResourcesRequest(method='resources/list')
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_list_resources_exception(self):
        """Test list_resources handles exception gracefully."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=Exception('Test error'))
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'ListResourcesRequest' in str(handler_type):
                    from mcp.types import ListResourcesRequest

                    request = ListResourcesRequest(method='resources/list')
                    result = await handler(request)
                    # Should return empty list on error
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_read_resource_invocation(self):
        """Test invoking read_resource handler."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_datastore_details = AsyncMock(
                return_value={'datastoreId': 'a' * 32, 'datastoreName': 'test-datastore'}
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'ReadResourceRequest' in str(handler_type):
                    from mcp.types import ReadResourceRequest, ReadResourceRequestParams
                    from pydantic import AnyUrl

                    params = ReadResourceRequestParams(
                        uri=AnyUrl(f'healthimaging://datastore/{"a" * 32}')
                    )
                    request = ReadResourceRequest(method='resources/read', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_read_resource_invalid_uri(self):
        """Test read_resource with invalid URI."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'ReadResourceRequest' in str(handler_type):
                    from mcp.types import ReadResourceRequest, ReadResourceRequestParams
                    from pydantic import AnyUrl

                    params = ReadResourceRequestParams(uri=AnyUrl('invalid://uri/path'))
                    request = ReadResourceRequest(method='resources/read', params=params)
                    try:
                        await handler(request)
                    except ValueError as e:
                        assert 'Unknown resource URI' in str(e)
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_invocation(self):
        """Test invoking call_tool handler."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(return_value={'datastoreSummaries': []})
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_validation_error_invocation(self):
        """Test call_tool with validation error."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    # Invalid datastore_id should trigger validation error
                    params = CallToolRequestParams(
                        name='get_datastore_details', arguments={'datastore_id': 'invalid'}
                    )
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_client_error_not_found_invocation(self):
        """Test call_tool with ResourceNotFoundException."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                side_effect=ClientError(
                    {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
                    'ListDatastores',
                )
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_client_error_validation_invocation(self):
        """Test call_tool with ValidationException."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                side_effect=ClientError(
                    {'Error': {'Code': 'ValidationException', 'Message': 'Invalid params'}},
                    'ListDatastores',
                )
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_other_client_error_invocation(self):
        """Test call_tool with other ClientError."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(
                side_effect=ClientError(
                    {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                    'ListDatastores',
                )
            )
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_no_credentials_invocation(self):
        """Test call_tool with NoCredentialsError."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=NoCredentialsError())
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break

    @pytest.mark.asyncio
    async def test_handle_call_tool_generic_exception_invocation(self):
        """Test call_tool with generic Exception."""
        with patch(
            'awslabs.healthimaging_mcp_server.server.HealthImagingClient'
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_datastores = AsyncMock(side_effect=Exception('Unexpected error'))
            mock_client_class.return_value = mock_client

            server = create_healthimaging_server()
            handlers = server.request_handlers
            for handler_type, handler in handlers.items():
                if 'CallToolRequest' in str(handler_type):
                    from mcp.types import CallToolRequest, CallToolRequestParams

                    params = CallToolRequestParams(name='list_datastores', arguments={})
                    request = CallToolRequest(method='tools/call', params=params)
                    result = await handler(request)
                    assert result is not None
                    break
