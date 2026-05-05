"""Mock-based integration tests for HealthLake MCP Server."""

from awslabs.healthlake_mcp_server.server import ToolHandler
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestPhase1ComponentIntegration:
    """Phase 1: Component integration with mocks."""

    async def test_server_to_client_integration(self):
        """Test server → client integration with realistic mocks."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_created_at = datetime(2024, 1, 1)

            # Mock realistic client responses
            mock_client.list_datastores.return_value = {
                'DatastorePropertiesList': [
                    {
                        'DatastoreId': 'a' * 32,
                        'DatastoreName': 'integration-test',
                        'DatastoreStatus': 'ACTIVE',
                        'DatastoreTypeVersion': 'R4',
                        'CreatedAt': mock_created_at,
                        'DatastoreEndpoint': 'https://healthlake.us-east-1.amazonaws.com/datastore/test',
                    }
                ]
            }
            mock_client_class.return_value = mock_client

            # Test server uses client correctly
            tool_handler = ToolHandler(mock_client)
            result = await tool_handler.handle_tool('list_datastores', {})

            assert len(result) == 1
            assert 'integration-test' in result[0].text
            assert 'ACTIVE' in result[0].text


class TestPhase2EndToEndFlow:
    """Phase 2: End-to-end flow testing with mocks."""

    async def test_complete_tool_call_flow(self):
        """Test complete MCP tool call flow."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_datastores.return_value = {'DatastorePropertiesList': []}
            mock_client_class.return_value = mock_client

            tool_handler = ToolHandler(mock_client)

            # Test complete flow: tool call → handler → client → response
            result = await tool_handler.handle_tool('list_datastores', {})

            assert len(result) == 1
            assert 'DatastorePropertiesList' in result[0].text


class TestPhase3RealisticScenarios:
    """Phase 3: Realistic user scenarios with comprehensive mocks."""

    async def test_user_creates_then_updates_patient_scenario(self):
        """Test realistic scenario: user creates then updates a patient."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()

            # Mock patient creation
            mock_client.create_resource.return_value = {
                'resourceType': 'Patient',
                'id': 'new-patient-123',
                'name': [{'family': 'Doe', 'given': ['John']}],
            }

            # Mock patient update
            mock_client.update_resource.return_value = {
                'resourceType': 'Patient',
                'id': 'new-patient-123',
                'name': [{'family': 'Smith', 'given': ['John']}],
            }

            mock_client_class.return_value = mock_client
            tool_handler = ToolHandler(mock_client)

            # Step 1: Create patient
            create_result = await tool_handler.handle_tool(
                'create_fhir_resource',
                {
                    'datastore_id': 'a' * 32,
                    'resource_type': 'Patient',
                    'resource_data': {
                        'resourceType': 'Patient',
                        'name': [{'family': 'Doe', 'given': ['John']}],
                    },
                },
            )
            assert 'new-patient-123' in create_result[0].text

            # Step 2: Update patient
            update_result = await tool_handler.handle_tool(
                'update_fhir_resource',
                {
                    'datastore_id': 'a' * 32,
                    'resource_type': 'Patient',
                    'resource_id': 'new-patient-123',
                    'resource_data': {
                        'resourceType': 'Patient',
                        'name': [{'family': 'Smith', 'given': ['John']}],
                    },
                },
            )
            assert 'Smith' in update_result[0].text

    async def test_multi_step_workflow_integration(self):
        """Test multi-step workflow integration."""
        with patch('awslabs.healthlake_mcp_server.server.HealthLakeClient') as mock_client_class:
            mock_client = AsyncMock()

            # Mock datastore details
            mock_client.get_datastore_details.return_value = {
                'DatastoreId': 'a' * 32,
                'DatastoreName': 'test-datastore',
                'DatastoreStatus': 'ACTIVE',
            }

            # Mock search results
            mock_client.search_resources.return_value = {
                'resourceType': 'Bundle',
                'total': 1,
                'entry': [{'resource': {'resourceType': 'Patient', 'id': 'patient-123'}}],
            }

            mock_client_class.return_value = mock_client
            tool_handler = ToolHandler(mock_client)

            # Step 1: Get datastore details
            details_result = await tool_handler.handle_tool(
                'get_datastore_details', {'datastore_id': 'a' * 32}
            )
            assert 'test-datastore' in details_result[0].text

            # Step 2: Search for patients
            search_result = await tool_handler.handle_tool(
                'search_fhir_resources', {'datastore_id': 'a' * 32, 'resource_type': 'Patient'}
            )
            assert 'patient-123' in search_result[0].text
