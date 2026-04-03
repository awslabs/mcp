"""Tests for CloudWatch Application Signals MCP Server audit tools."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.server import (
    audit_service_operations,
    audit_services,
    audit_slos,
)
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_logs_client = MagicMock()
    mock_applicationsignals_client = MagicMock()
    mock_cloudwatch_client = MagicMock()
    mock_xray_client = MagicMock()

    # Mock the list_audit_findings method to return a proper response
    mock_applicationsignals_client.list_audit_findings.return_value = {
        'AuditFindings': [],
        'NextToken': None,
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }

    # Mock list_services to prevent real AWS calls in wildcard expansion
    mock_applicationsignals_client.list_services.return_value = {
        'ServiceSummaries': [],
        'NextToken': None,
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }

    # Mock list_service_level_objectives to prevent real AWS calls in SLO wildcard expansion
    mock_applicationsignals_client.list_service_level_objectives.return_value = {
        'SloSummaries': [],
        'NextToken': None,
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }

    # Mock list_service_operations to prevent real AWS calls in operation wildcard expansion
    mock_applicationsignals_client.list_service_operations.return_value = {
        'Operations': [],
        'NextToken': None,
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }

    patches = [
        # Only patch the aws_clients module - this is where all clients are defined
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.logs_client',
            mock_logs_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.applicationsignals_client',
            mock_applicationsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.cloudwatch_client',
            mock_cloudwatch_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.xray_client',
            mock_xray_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'logs_client': mock_logs_client,
            'applicationsignals_client': mock_applicationsignals_client,
            'cloudwatch_client': mock_cloudwatch_client,
            'xray_client': mock_xray_client,
        }
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_audit_services_invalid_json(mock_aws_clients):
    """Test audit_services with invalid JSON."""
    result = await audit_services(service_targets='invalid json')

    assert 'Error: `service_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_services_invalid_time_range(mock_aws_clients):
    """Test audit_services with invalid time range."""
    service_targets = (
        '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service"}}}]'
    )

    result = await audit_services(
        service_targets=service_targets,
        start_time='2024-01-01 01:00:00',
        end_time='2024-01-01 00:00:00',  # End before start
    )

    assert 'Error: end_time must be greater than start_time.' in result


@pytest.mark.asyncio
async def test_audit_slos_wildcard_expansion_error(mock_aws_clients):
    """Test audit_slos when wildcard expansion fails."""
    slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*invalid*"}}}]'

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
    ) as mock_expand:
        mock_expand.side_effect = Exception('Failed to expand patterns')

        result = await audit_slos(slo_targets=slo_targets)

        assert 'Error: Failed to expand SLO wildcard patterns' in result


@pytest.mark.asyncio
async def test_audit_slos_invalid_json(mock_aws_clients):
    """Test audit_slos with invalid JSON."""
    result = await audit_slos(slo_targets='invalid json')

    assert 'Error: `slo_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_slos_not_array(mock_aws_clients):
    """Test audit_slos with non-array JSON."""
    result = await audit_slos(slo_targets='{"Type":"slo"}')

    assert 'Error: `slo_targets` must be a JSON array' in result


@pytest.mark.asyncio
async def test_audit_slos_empty_array(mock_aws_clients):
    """Test audit_slos with empty array."""
    result = await audit_slos(slo_targets='[]')

    assert 'Error: `slo_targets` must contain at least 1 item' in result


@pytest.mark.asyncio
async def test_audit_service_operations_invalid_json(mock_aws_clients):
    """Test audit_service_operations with invalid JSON."""
    result = await audit_service_operations(operation_targets='invalid json')

    assert 'Error: `operation_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_service_operations_not_array(mock_aws_clients):
    """Test audit_service_operations with non-array JSON."""
    result = await audit_service_operations(operation_targets='{"Type":"service_operation"}')

    assert 'Error: `operation_targets` must be a JSON array' in result


@pytest.mark.asyncio
async def test_audit_service_operations_empty_array(mock_aws_clients):
    """Test audit_service_operations with empty array."""
    result = await audit_service_operations(operation_targets='[]')

    assert 'Error: `operation_targets` must contain at least 1 item' in result
