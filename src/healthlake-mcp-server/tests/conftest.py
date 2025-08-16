"""Test fixtures for HealthLake MCP Server tests."""

import pytest


@pytest.fixture
def sample_datastore_id():
    """Valid 32-character datastore ID for testing."""
    return '12345678901234567890123456789012'


@pytest.fixture
def sample_args():
    """Sample arguments for tool handlers."""
    return {
        'datastore_id': '12345678901234567890123456789012',
        'resource_type': 'Patient',
        'resource_id': 'test-patient-123',
    }
