"""Tests for validation functions."""

import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import (
    MAX_SEARCH_COUNT,
    HealthImagingSearchError,
    validate_datastore_id,
)
from awslabs.healthimaging_mcp_server.server import InputValidationError, validate_count


def test_max_search_count_constant():
    """Test that MAX_SEARCH_COUNT is properly defined."""
    assert MAX_SEARCH_COUNT == 100


def test_validate_datastore_id_valid():
    """Test validation of valid datastore ID."""
    valid_id = '12345678901234567890123456789012'
    result = validate_datastore_id(valid_id)
    assert result == valid_id


def test_validate_datastore_id_invalid_length():
    """Test validation fails for invalid length."""
    with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
        validate_datastore_id('short')


def test_validate_datastore_id_empty():
    """Test validation fails for empty string."""
    with pytest.raises(ValueError, match='Datastore ID must be 32 characters'):
        validate_datastore_id('')


def test_validate_count_valid():
    """Test validation of valid count."""
    assert validate_count(50) == 50
    assert validate_count(1) == 1
    assert validate_count(100) == 100


def test_validate_count_invalid_low():
    """Test validation fails for count too low."""
    with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
        validate_count(0)


def test_validate_count_invalid_high():
    """Test validation fails for count too high."""
    with pytest.raises(InputValidationError, match='Count must be between 1 and 100'):
        validate_count(101)


def test_healthimaging_search_error():
    """Test HealthImagingSearchError exception."""
    error = HealthImagingSearchError('Test error', ['param1', 'param2'])
    assert str(error) == 'Test error'
    assert error.invalid_params == ['param1', 'param2']


def test_healthimaging_search_error_no_params():
    """Test HealthImagingSearchError without invalid params."""
    error = HealthImagingSearchError('Test error')
    assert str(error) == 'Test error'
    assert error.invalid_params == []
