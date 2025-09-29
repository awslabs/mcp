"""Additional tests for server.py audit functions to improve coverage."""

import json
import pytest
from awslabs.cloudwatch_appsignals_mcp_server.server import (
    audit_service_operations,
    audit_services,
    audit_slos,
)
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_appsignals_client = MagicMock()

    patches = [
        # Mock the client in server.py
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.appsignals_client',
            mock_appsignals_client,
        ),
        # Mock the client in aws_clients module (where it's actually defined)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
        # Mock the client in audit_utils module (where expand_slo_wildcard_patterns uses it)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.audit_utils.appsignals_client',
            mock_appsignals_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {'appsignals_client': mock_appsignals_client}
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_audit_services_invalid_json(mock_aws_clients):
    """Test audit_services with invalid JSON service_targets."""
    result = await audit_services(
        service_targets='invalid json',
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `service_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_services_invalid_time_range(mock_aws_clients):
    """Test audit_services with end_time before start_time."""
    service_targets = (
        '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service"}}}]'
    )

    result = await audit_services(
        service_targets=service_targets,
        start_time='2024-01-02T00:00:00',
        end_time='2024-01-01T00:00:00',  # Before start_time
        auditors=None,
    )

    assert 'Error: end_time must be greater than start_time.' in result


@pytest.mark.asyncio
async def test_audit_slos_invalid_json(mock_aws_clients):
    """Test audit_slos with invalid JSON slo_targets."""
    result = await audit_slos(
        slo_targets='invalid json',
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `slo_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_slos_not_array(mock_aws_clients):
    """Test audit_slos with non-array slo_targets."""
    result = await audit_slos(
        slo_targets='{"Type":"slo"}',  # Object instead of array
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `slo_targets` must be a JSON array' in result


@pytest.mark.asyncio
async def test_audit_slos_empty_array(mock_aws_clients):
    """Test audit_slos with empty array."""
    result = await audit_slos(
        slo_targets='[]',
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `slo_targets` must contain at least 1 item' in result


@pytest.mark.asyncio
async def test_audit_slos_invalid_time_range(mock_aws_clients):
    """Test audit_slos with invalid time range."""
    slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"test-slo"}}}]'

    result = await audit_slos(
        slo_targets=slo_targets,
        start_time='2024-01-02T00:00:00',
        end_time='2024-01-01T00:00:00',  # Before start_time
        auditors=None,
    )

    assert 'Error: end_time must be greater than start_time.' in result


@pytest.mark.asyncio
async def test_audit_service_operations_invalid_json(mock_aws_clients):
    """Test audit_service_operations with invalid JSON."""
    result = await audit_service_operations(
        operation_targets='invalid json',
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `operation_targets` must be valid JSON (array).' in result


@pytest.mark.asyncio
async def test_audit_service_operations_not_array(mock_aws_clients):
    """Test audit_service_operations with non-array operation_targets."""
    result = await audit_service_operations(
        operation_targets='{"Type":"service_operation"}',  # Object instead of array
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `operation_targets` must be a JSON array' in result


@pytest.mark.asyncio
async def test_audit_service_operations_empty_array(mock_aws_clients):
    """Test audit_service_operations with empty array."""
    result = await audit_service_operations(
        operation_targets='[]',
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: `operation_targets` must contain at least 1 item' in result


def test_main_entry_point():
    """Test the __name__ == '__main__' entry point."""
    # Test that the main function can be called
    from awslabs.cloudwatch_appsignals_mcp_server.server import main

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        # Test normal execution
        main()
        mock_mcp.run.assert_called_once_with(transport='stdio')

        # Reset mock
        mock_mcp.reset_mock()

        # Test KeyboardInterrupt handling
        mock_mcp.run.side_effect = KeyboardInterrupt()
        main()  # Should not raise
        mock_mcp.run.assert_called_once_with(transport='stdio')

        # Reset mock
        mock_mcp.reset_mock()

        # Test general exception handling
        mock_mcp.run.side_effect = Exception('Server error')
        with pytest.raises(Exception, match='Server error'):
            main()
        mock_mcp.run.assert_called_once_with(transport='stdio')


@pytest.mark.asyncio
async def test_audit_slos_wildcard_no_targets_found(mock_aws_clients):
    """Test audit_slos when wildcard expansion results in no targets (covers line 523-524)."""
    slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*nonexistent*"}}}]'

    # Mock the AWS API call that expand_slo_wildcard_patterns makes
    mock_appsignals_client = mock_aws_clients['appsignals_client']
    mock_appsignals_client.list_service_level_objectives.return_value = {
        'SloSummaries': []  # No SLOs found
    }

    result = await audit_slos(
        slo_targets=slo_targets,
        start_time=None,
        end_time=None,
        auditors=None,
    )

    assert 'Error: No SLO targets found after wildcard expansion.' in result


@pytest.mark.asyncio
async def test_audit_slos_successful_execution_with_batching(mock_aws_clients):
    """Test audit_slos successful execution with batching (covers lines 526-558)."""
    # Create enough SLO targets to trigger batching (> BATCH_SIZE_THRESHOLD = 5)
    slo_targets = json.dumps(
        [
            {'Type': 'slo', 'Data': {'Slo': {'SloName': f'test-slo-{i}'}}}
            for i in range(7)  # 7 targets > 5 threshold
        ]
    )

    # Mock the AWS API call that execute_audit_api makes
    mock_appsignals_client = mock_aws_clients['appsignals_client']
    mock_appsignals_client.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'test-finding-1',
                'Severity': 'CRITICAL',
                'Title': 'SLO Breach Detected',
                'Description': 'Test SLO breach finding',
            }
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.expand_slo_wildcard_patterns'
    ) as mock_expand:
        # Mock no wildcard expansion needed
        mock_expand.return_value = json.loads(slo_targets)

        result = await audit_slos(
            slo_targets=slo_targets,
            start_time=None,
            end_time=None,
            auditors='slo,trace',
        )

        # Verify result contains expected content
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result
        assert '📦 Batching: Processing 7 targets in batches of 5' in result
        assert 'test-finding-1' in result

        # Verify the AWS API was called (should be called twice due to batching: 5 + 2)
        assert mock_appsignals_client.list_audit_findings.call_count == 2


@pytest.mark.asyncio
async def test_audit_slos_successful_execution_no_batching(mock_aws_clients):
    """Test audit_slos successful execution without batching (covers lines 526-558)."""
    # Create fewer SLO targets (< BATCH_SIZE_THRESHOLD = 5)
    slo_targets = json.dumps(
        [
            {'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo-1'}}},
            {'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo-2'}}},
        ]
    )

    # Mock the AWS API call that execute_audit_api makes
    mock_appsignals_client = mock_aws_clients['appsignals_client']
    mock_appsignals_client.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'test-finding-2',
                'Severity': 'WARNING',
                'Title': 'SLO Performance Issue',
                'Description': 'Test SLO performance finding',
            }
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.expand_slo_wildcard_patterns'
    ) as mock_expand:
        # Mock no wildcard expansion needed
        mock_expand.return_value = json.loads(slo_targets)

        result = await audit_slos(
            slo_targets=slo_targets,
            start_time=None,
            end_time=None,
            auditors=None,  # Test default auditors
        )

        # Verify result contains expected content
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result
        assert '📦 Batching:' not in result  # No batching for < 5 targets
        assert 'test-finding-2' in result

        # Verify the AWS API was called once (no batching)
        mock_appsignals_client.list_audit_findings.assert_called_once()
