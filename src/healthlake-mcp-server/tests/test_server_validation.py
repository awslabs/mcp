"""Tests for server validation logic to increase coverage."""

import pytest
from awslabs.healthlake_mcp_server.server import ToolHandler
from unittest.mock import AsyncMock


class TestServerValidationLogic:
    """Test validation logic in server handlers."""

    @pytest.fixture
    def handler(self):
        """Create ToolHandler instance."""
        mock_client = AsyncMock()
        return ToolHandler(mock_client)

    async def test_search_resources_count_validation_low(self, handler):
        """Test search resources with count too low."""
        handler.client.search_resources.return_value = {'entry': []}

        with pytest.raises(ValueError, match='Count must be between 1 and 100'):
            await handler.handle_tool(
                'search_fhir_resources',
                {
                    'datastore_id': '12345678901234567890123456789012',
                    'resource_type': 'Patient',
                    'count': 0,
                },
            )

    async def test_search_resources_count_validation_high(self, handler):
        """Test search resources with count too high."""
        handler.client.search_resources.return_value = {'entry': []}

        with pytest.raises(ValueError, match='Count must be between 1 and 100'):
            await handler.handle_tool(
                'search_fhir_resources',
                {
                    'datastore_id': '12345678901234567890123456789012',
                    'resource_type': 'Patient',
                    'count': 101,
                },
            )

    async def test_search_resources_count_validation_valid(self, handler):
        """Test search resources with valid count."""
        handler.client.search_resources.return_value = {'entry': []}

        # Test boundary values
        result = await handler.handle_tool(
            'search_fhir_resources',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'count': 1,
            },
        )
        assert len(result) == 1

        result = await handler.handle_tool(
            'search_fhir_resources',
            {
                'datastore_id': '12345678901234567890123456789012',
                'resource_type': 'Patient',
                'count': 100,
            },
        )
        assert len(result) == 1

    async def test_patient_everything_count_validation_low(self, handler):
        """Test patient everything with count too low."""
        handler.client.patient_everything.return_value = {'entry': []}

        with pytest.raises(ValueError, match='Count must be between 1 and 100'):
            await handler.handle_tool(
                'patient_everything',
                {
                    'datastore_id': '12345678901234567890123456789012',
                    'patient_id': 'patient-123',
                    'count': 0,
                },
            )

    async def test_patient_everything_count_validation_high(self, handler):
        """Test patient everything with count too high."""
        handler.client.patient_everything.return_value = {'entry': []}

        with pytest.raises(ValueError, match='Count must be between 1 and 100'):
            await handler.handle_tool(
                'patient_everything',
                {
                    'datastore_id': '12345678901234567890123456789012',
                    'patient_id': 'patient-123',
                    'count': 101,
                },
            )

    async def test_patient_everything_count_validation_valid(self, handler):
        """Test patient everything with valid count."""
        handler.client.patient_everything.return_value = {'entry': []}

        # Test boundary values
        result = await handler.handle_tool(
            'patient_everything',
            {
                'datastore_id': '12345678901234567890123456789012',
                'patient_id': 'patient-123',
                'count': 1,
            },
        )
        assert len(result) == 1

        result = await handler.handle_tool(
            'patient_everything',
            {
                'datastore_id': '12345678901234567890123456789012',
                'patient_id': 'patient-123',
                'count': 100,
            },
        )
        assert len(result) == 1

    async def test_search_resources_default_count(self, handler):
        """Test search resources with default count."""
        handler.client.search_resources.return_value = {'entry': []}

        # Test without count parameter (should use default 100)
        result = await handler.handle_tool(
            'search_fhir_resources',
            {'datastore_id': '12345678901234567890123456789012', 'resource_type': 'Patient'},
        )
        assert len(result) == 1

        # Verify client was called with default count
        handler.client.search_resources.assert_called_with(
            datastore_id='12345678901234567890123456789012',
            resource_type='Patient',
            search_params={},
            include_params=None,
            revinclude_params=None,
            chained_params=None,
            count=100,
            next_token=None,
        )

    async def test_patient_everything_default_count(self, handler):
        """Test patient everything with default count."""
        handler.client.patient_everything.return_value = {'entry': []}

        # Test without count parameter (should use default 100)
        result = await handler.handle_tool(
            'patient_everything',
            {'datastore_id': '12345678901234567890123456789012', 'patient_id': 'patient-123'},
        )
        assert len(result) == 1

        # Verify client was called with default count
        handler.client.patient_everything.assert_called_with(
            datastore_id='12345678901234567890123456789012',
            patient_id='patient-123',
            start=None,
            end=None,
            count=100,
            next_token=None,
        )
