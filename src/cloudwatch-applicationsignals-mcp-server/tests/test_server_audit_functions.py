"""Additional tests for server.py audit functions to improve coverage."""

import json
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
    mock_applicationsignals_client = MagicMock()

    patches = [
        # Mock the client in server.py
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ),
        # Mock the client in aws_clients module (where it's actually defined)
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.applicationsignals_client',
            mock_applicationsignals_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {'applicationsignals_client': mock_applicationsignals_client}
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
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import main

    with patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.mcp') as mock_mcp:
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
    mock_applicationsignals_client = mock_aws_clients['applicationsignals_client']
    mock_applicationsignals_client.list_audit_findings.return_value = {
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
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
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
        assert mock_applicationsignals_client.list_audit_findings.call_count == 2


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
    mock_applicationsignals_client = mock_aws_clients['applicationsignals_client']
    mock_applicationsignals_client.list_audit_findings.return_value = {
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
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
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
        mock_applicationsignals_client.list_audit_findings.assert_called_once()


@pytest.mark.asyncio
async def test_audit_services_wildcard_expansion_error(mock_aws_clients):
    """Test audit_services when wildcard expansion fails."""
    service_targets = (
        '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
    )

    # Mock the expand_service_wildcard_patterns to raise an exception
    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
    ) as mock_expand:
        mock_expand.side_effect = ValueError('Failed to expand service wildcard patterns')

        result = await audit_services(
            service_targets=service_targets,
            start_time=None,
            end_time=None,
            auditors=None,
        )

        assert 'Error: Failed to expand service wildcard patterns' in result


@pytest.mark.asyncio
async def test_audit_service_operations_successful_execution_with_batching(mock_aws_clients):
    """Test audit_service_operations successful execution with batching (covers batching logic)."""
    # Create enough operation targets to trigger batching (> BATCH_SIZE_THRESHOLD = 5)
    operation_targets = json.dumps(
        [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Type': 'Service', 'Name': f'test-service-{i}'},
                        'Operation': 'GET /api',
                        'MetricType': 'Latency',
                    }
                },
            }
            for i in range(7)  # 7 targets > 5 threshold
        ]
    )

    # Mock the AWS API call that execute_audit_api makes
    mock_applicationsignals_client = mock_aws_clients['applicationsignals_client']
    mock_applicationsignals_client.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'test-finding-op-batch',
                'Severity': 'WARNING',
                'Title': 'Operation Latency Issue',
                'Description': 'Test operation batching finding',
            }
        ]
    }

    # Mock the expand_service_operation_wildcard_patterns
    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
    ) as mock_expand:
        mock_expand.return_value = json.loads(operation_targets)

        result = await audit_service_operations(
            operation_targets=operation_targets,
            start_time=None,
            end_time=None,
            auditors='operation_metric,trace',
        )

        # Verify result contains expected content including batching message
        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result
        assert '📦 Batching: Processing 7 targets in batches of 5' in result
        assert 'test-finding-op-batch' in result

        # Verify the AWS API was called (should be called twice due to batching: 5 + 2)
        assert mock_applicationsignals_client.list_audit_findings.call_count == 2


def test_filter_operation_targets():
    """Test the _filter_operation_targets helper function directly."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import _filter_operation_targets

    # Create mixed targets with different types and wildcard patterns
    provided = [
        # Valid service_operation target without wildcards
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'payment-service'},
                    'Operation': 'GET /api/payments',
                    'MetricType': 'Latency',
                }
            },
        },
        # Valid service_operation target with wildcard in service name
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': '*payment*'},
                    'Operation': 'POST /api/process',
                    'MetricType': 'Error',
                }
            },
        },
        # Valid service_operation target with wildcard in operation name
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'order-service'},
                    'Operation': '*GET*',
                    'MetricType': 'Availability',
                }
            },
        },
        # Invalid target type (should be ignored with warning)
        {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'ignored-service'}},
        },
        # Another invalid target type (should be ignored with warning)
        {
            'Type': 'slo',
            'Data': {'Slo': {'SloName': 'ignored-slo'}},
        },
    ]

    # Test the helper function directly
    with patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.logger') as mock_logger:
        operation_only_targets, has_wildcards = _filter_operation_targets(provided)

        # Verify that only service_operation targets are returned
        assert len(operation_only_targets) == 3
        for target in operation_only_targets:
            assert target.get('Type') == 'service_operation'

        # Verify wildcards were detected
        assert has_wildcards is True

        # Verify warnings were logged for ignored target types
        warning_calls = list(mock_logger.warning.call_args_list)
        assert len(warning_calls) == 2  # Two invalid targets should generate warnings

        # Check that warnings mention the ignored target types
        warning_messages = [str(call[0][0]) for call in warning_calls]
        assert any("Ignoring target of type 'service'" in msg for msg in warning_messages)
        assert any("Ignoring target of type 'slo'" in msg for msg in warning_messages)


def test_filter_operation_targets_no_wildcards():
    """Test the _filter_operation_targets helper function with no wildcards."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import _filter_operation_targets

    # Create targets without wildcards
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'payment-service'},
                    'Operation': 'GET /api/payments',
                    'MetricType': 'Latency',
                }
            },
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'order-service'},
                    'Operation': 'POST /api/orders',
                    'MetricType': 'Error',
                }
            },
        },
    ]

    # Test the helper function directly
    operation_only_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify that all targets are returned
    assert len(operation_only_targets) == 2
    for target in operation_only_targets:
        assert target.get('Type') == 'service_operation'

    # Verify no wildcards were detected
    assert has_wildcards is False


# Note: The integration test for audit_service_operations with target filtering
# is covered by the unit tests above (test_filter_operation_targets and
# test_filter_operation_targets_no_wildcards) which directly test the
# _filter_operation_targets helper function that was extracted from the main function.
# This provides better test coverage with simpler, more reliable tests.


@pytest.mark.asyncio
async def test_audit_service_operations_no_wildcards_no_expansion(mock_aws_clients):
    """Test audit_service_operations when no wildcards are present (no expansion needed)."""
    # Create operation targets without any wildcard patterns
    operation_targets = json.dumps(
        [
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Type': 'Service', 'Name': 'payment-service'},
                        'Operation': 'GET /api/payments',
                        'MetricType': 'Latency',
                    }
                },
            },
            {
                'Type': 'service_operation',
                'Data': {
                    'ServiceOperation': {
                        'Service': {'Type': 'Service', 'Name': 'order-service'},
                        'Operation': 'POST /api/orders',
                        'MetricType': 'Error',
                    }
                },
            },
        ]
    )

    # Mock the AWS API call that execute_audit_api makes
    mock_applicationsignals_client = mock_aws_clients['applicationsignals_client']
    mock_applicationsignals_client.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'test-finding-no-wildcards',
                'Severity': 'INFO',
                'Title': 'No Wildcards Test',
                'Description': 'Test without wildcard patterns',
            }
        ]
    }

    with patch(
        'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
    ) as mock_expand:
        result = await audit_service_operations(
            operation_targets=operation_targets,
            start_time=None,
            end_time=None,
            auditors='operation_metric',
        )

        # Verify result contains expected content
        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result
        assert 'test-finding-no-wildcards' in result

        # Verify wildcard expansion was NOT called because no wildcards were detected
        mock_expand.assert_not_called()

        # Verify the AWS API was called once
        mock_applicationsignals_client.list_audit_findings.assert_called_once()
