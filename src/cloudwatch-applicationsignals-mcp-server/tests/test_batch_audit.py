"""Tests for pagination functionality in CloudWatch Application Signals MCP Server.

This module contains comprehensive tests for the batch audit functionality,
organized by the audit functions they test: audit_services, audit_slos, and audit_service_operations.
"""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.server import (
    audit_service_operations,
    audit_services,
    audit_slos,
)
from unittest.mock import MagicMock, patch


# =============================================================================
# FIXTURES AND SETUP
# =============================================================================


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests.

    This fixture automatically mocks all AWS service clients used by the
    CloudWatch Application Signals MCP server to ensure tests run in isolation
    without making actual AWS API calls.

    Returns:
        dict: Dictionary containing all mocked AWS clients
    """
    # Create mock clients
    mock_logs_client = MagicMock()
    mock_applicationsignals_client = MagicMock()
    mock_cloudwatch_client = MagicMock()
    mock_xray_client = MagicMock()
    mock_synthetics_client = MagicMock()
    mock_s3_client = MagicMock()
    mock_iam_client = MagicMock()

    # Patch the clients in all modules where they're imported
    patches = [
        # Original aws_clients module
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
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.synthetics_client',
            mock_synthetics_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.s3_client',
            mock_s3_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.aws_clients.iam_client',
            mock_iam_client,
        ),
        # Server module
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.applicationsignals_client',
            mock_applicationsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.synthetics_client',
            mock_synthetics_client,
        ),
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.s3_client', mock_s3_client),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.iam_client', mock_iam_client
        ),
    ]

    # Start all patches
    for p in patches:
        p.start()

    try:
        yield {
            'logs_client': mock_logs_client,
            'applicationsignals_client': mock_applicationsignals_client,
            'cloudwatch_client': mock_cloudwatch_client,
            'xray_client': mock_xray_client,
            'synthetics_client': mock_synthetics_client,
            's3_client': mock_s3_client,
            'iam_client': mock_iam_client,
        }
    finally:
        # Stop all patches
        for p in patches:
            p.stop()


# =============================================================================
# AUDIT_SERVICES TESTS
# =============================================================================


class TestAuditServices:
    """Test cases for the audit_services function.

    This class contains all tests related to the audit_services function,
    including pagination, wildcard expansion, parameter validation, and successful execution.
    """

    @pytest.mark.asyncio
    async def test_next_token_rejected_without_wildcards(self, mock_aws_clients):
        """Test that next_token is rejected when no wildcards are used."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service"}}}]'
        )

        result = await audit_services(
            service_targets=service_targets,
            next_token='some_token',
        )

        assert (
            'Error: next_token parameter is only supported when using wildcard patterns in service names.'
            in result
        )

    @pytest.mark.asyncio
    async def test_pagination_with_wildcards(self, mock_aws_clients):
        """Test pagination functionality with wildcard patterns."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
        )

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock expansion to return paginated results
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service',
                        'Data': {'Service': {'Type': 'Service', 'Name': 'payment-service-1'}},
                    }
                ],
                'next_token_123',
                ['payment-service-1', 'payment-service-2'],
            )
            mock_normalize.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'payment-service-1'}},
                }
            ]
            mock_validate.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'payment-service-1'}},
                }
            ]
            mock_execute.return_value = 'Audit results here'

            result = await audit_services(
                service_targets=service_targets,
                max_services=2,
            )

            # Verify pagination info is included
            assert '📊 Processed 2 services in this batch:' in result
            assert '   • payment-service-1' in result
            assert '   • payment-service-2' in result
            assert '🔄 PAGINATION: More services available!' in result
            assert 'next_token="next_token_123"' in result

            # Verify expand function was called with pagination parameters
            mock_expand.assert_called_once()
            call_args = mock_expand.call_args[0]
            # Handle Pydantic FieldInfo objects - check if it's None or has default None
            next_token_arg = call_args[3]
            if hasattr(next_token_arg, 'default'):
                assert next_token_arg.default is None  # Pydantic FieldInfo with None default
            else:
                assert next_token_arg is None  # Direct None value
            assert call_args[4] == 2  # max_services

    @pytest.mark.asyncio
    async def test_pagination_last_batch(self, mock_aws_clients):
        """Test pagination behavior on the last batch (no next_token)."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock expansion to return final batch (no next_token)
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service',
                        'Data': {'Service': {'Type': 'Service', 'Name': 'final-service'}},
                    }
                ],
                None,  # No next_token
                ['final-service'],
            )
            mock_normalize.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'final-service'}},
                }
            ]
            mock_validate.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'final-service'}},
                }
            ]
            mock_execute.return_value = 'Final audit results'

            result = await audit_services(
                service_targets=service_targets,
                next_token='previous_token',
                max_services=5,
            )

            # Verify final batch pagination info
            assert '✅ PAGINATION: Complete! This was the last batch of services.' in result
            assert '📊 Processed 1 services in final batch:' in result
            assert '   • final-service' in result

    @pytest.mark.asyncio
    async def test_no_services_found_with_wildcard(self, mock_aws_clients):
        """Test behavior when wildcard expansion finds no services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*nonexistent*"}}}]'
        )

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
        ) as mock_expand:
            # Mock expansion to return empty results
            mock_expand.return_value = ([], None, [])

            result = await audit_services(service_targets=service_targets)

            assert (
                'Error: No services found matching the wildcard pattern. Use list_monitored_services() to see available services.'
                in result
            )

    @pytest.mark.asyncio
    async def test_zero_max_services(self, mock_aws_clients):
        """Test audit_services with max_services set to 0."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            mock_expand.return_value = ([], None, [])
            mock_normalize.return_value = []
            mock_validate.return_value = []
            mock_execute.return_value = 'Results'

            # Test with max_services=0 (should still work)
            await audit_services(
                service_targets=service_targets,
                max_services=0,
            )

            # Verify max_services was passed correctly
            call_args = mock_expand.call_args[0]
            assert call_args[4] == 0  # max_services parameter

    @pytest.mark.asyncio
    async def test_negative_max_services(self, mock_aws_clients):
        """Test audit_services with negative max_services."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            mock_expand.return_value = ([], None, [])
            mock_normalize.return_value = []
            mock_validate.return_value = []
            mock_execute.return_value = 'Results'

            # Test with negative max_services (should still work, passed through)
            await audit_services(
                service_targets=service_targets,
                max_services=-1,
            )

            # Verify negative value was passed correctly
            call_args = mock_expand.call_args[0]
            assert call_args[4] == -1  # max_services parameter

    @pytest.mark.asyncio
    async def test_custom_max_services_parameter(self, mock_aws_clients):
        """Test parameter validation for custom max_services values."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            mock_expand.return_value = ([], None, [])
            mock_normalize.return_value = []
            mock_validate.return_value = []
            mock_execute.return_value = 'Results'

            # Test with custom max_services
            await audit_services(
                service_targets=service_targets,
                max_services=10,
            )

            # Verify max_services was passed correctly
            call_args = mock_expand.call_args[0]
            assert call_args[4] == 10  # max_services parameter

    @pytest.mark.asyncio
    async def test_complete_pagination_workflow(self, mock_aws_clients):
        """Test complete pagination workflow for services."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # First call - returns next_token
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service',
                        'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                    }
                ],
                'token_batch_1',
                ['service-1', 'service-2'],
            )
            mock_normalize.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                }
            ]
            mock_validate.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                }
            ]
            mock_execute.return_value = 'Batch 1 results'

            result1 = await audit_services(
                service_targets=service_targets,
                start_time='1640995200',
                end_time='1641081600',
                max_services=2,
            )

            # Verify first batch
            assert 'next_token="token_batch_1"' in result1
            assert 'start_time="1640995200"' in result1
            assert 'end_time="1641081600"' in result1

            # Second call - final batch
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service',
                        'Data': {'Service': {'Type': 'Service', 'Name': 'service-3'}},
                    }
                ],
                None,  # No more batches
                ['service-3'],
            )
            mock_normalize.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-3'}},
                }
            ]
            mock_validate.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-3'}},
                }
            ]
            mock_execute.return_value = 'Final batch results'

            result2 = await audit_services(
                service_targets=service_targets,
                start_time='1640995200',
                end_time='1641081600',
                next_token='token_batch_1',
                max_services=2,
            )

            # Verify final batch
            assert '✅ PAGINATION: Complete!' in result2
            assert 'next_token=' not in result2  # No continuation

    @pytest.mark.asyncio
    async def test_time_parameter_preservation(self, mock_aws_clients):
        """Test that pagination preserves time parameters correctly."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.normalize_service_targets'
            ) as mock_normalize,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.validate_and_enrich_service_targets'
            ) as mock_validate,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service',
                        'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                    }
                ],
                'time_token',
                ['service-1'],
            )
            mock_normalize.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                }
            ]
            mock_validate.return_value = [
                {
                    'Type': 'service',
                    'Data': {'Service': {'Type': 'Service', 'Name': 'service-1'}},
                }
            ]
            mock_execute.return_value = 'Time test results'

            result = await audit_services(
                service_targets=service_targets,
                start_time='2024-01-01 00:00:00',
                end_time='2024-01-01 23:59:59',
            )

            # Verify time parameters are preserved in pagination info
            # The function converts datetime strings to unix timestamps
            assert 'start_time=' in result
            assert 'end_time=' in result
            assert 'next_token="time_token"' in result


# =============================================================================
# AUDIT_SLOS TESTS
# =============================================================================


class TestAuditSlos:
    """Test cases for the audit_slos function.

    This class contains all tests related to the audit_slos function,
    including pagination, wildcard expansion, error handling, and successful execution.
    """

    @pytest.mark.asyncio
    async def test_next_token_rejected_without_wildcards(self, mock_aws_clients):
        """Test that next_token is rejected when no wildcards are used."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"test-slo"}}}]'

        result = await audit_slos(
            slo_targets=slo_targets,
            next_token='some_token',
        )

        assert (
            'Error: next_token parameter is only supported when using wildcard patterns in SLO names.'
            in result
        )

    @pytest.mark.asyncio
    async def test_pagination_with_wildcards(self, mock_aws_clients):
        """Test pagination functionality with wildcard patterns."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*payment*"}}}]'

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock expansion to return paginated results
            mock_expand.return_value = (
                [{'Type': 'slo', 'Data': {'Slo': {'SloName': 'payment-slo-1'}}}],
                'slo_token_456',
                ['payment-slo-1', 'payment-slo-2', 'payment-slo-3'],
            )
            mock_execute.return_value = 'SLO audit results'

            result = await audit_slos(
                slo_targets=slo_targets,
                max_slos=3,
            )

            # Verify SLO pagination info is included
            assert '📊 Processed 3 SLOs in this batch:' in result
            assert '   • payment-slo-1' in result
            assert '   • payment-slo-2' in result
            assert '   • payment-slo-3' in result
            assert '🔄 PAGINATION: More SLOs available!' in result
            assert 'audit_slos(' in result
            assert 'next_token="slo_token_456"' in result
            assert 'max_slos=3' in result

            # Verify expand function was called with pagination parameters
            mock_expand.assert_called_once()
            call_args = mock_expand.call_args[0]
            # Handle Pydantic FieldInfo objects - check if it's None or has default None
            next_token_arg = call_args[1]
            if hasattr(next_token_arg, 'default'):
                assert next_token_arg.default is None  # Pydantic FieldInfo with None default
            else:
                assert next_token_arg is None  # Direct None value
            assert call_args[2] == 3  # max_slos

    @pytest.mark.asyncio
    async def test_expansion_failure(self, mock_aws_clients):
        """Test behavior when SLO wildcard expansion fails."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*invalid*"}}}]'

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
        ) as mock_expand:
            # Mock expansion to raise an exception
            mock_expand.side_effect = Exception('SLO expansion failed')

            result = await audit_slos(slo_targets=slo_targets)

            assert 'Error: Failed to expand SLO wildcard patterns. SLO expansion failed' in result

    @pytest.mark.asyncio
    async def test_successful_execution_with_batching(self, mock_aws_clients):
        """Test audit_slos successful execution with batching."""
        # Create SLO targets with wildcard patterns to avoid next_token validation error
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]'

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

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock wildcard expansion to return concrete targets
            concrete_targets = [
                {'Type': 'slo', 'Data': {'Slo': {'SloName': f'test-slo-{i}'}}} for i in range(7)
            ]
            mock_expand.return_value = (
                concrete_targets,
                None,
                [f'test-slo-{i}' for i in range(7)],
            )
            mock_execute.return_value = (
                '[MCP-SLO] Application Signals SLO Compliance Audit\n'
                '📦 Batching: Processing 7 targets in batches of 5\n'
                'test-finding-1'
            )

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

            # Verify the execute_audit_api was called
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_execution_without_batching(self, mock_aws_clients):
        """Test audit_slos successful execution without batching."""
        # Create fewer SLO targets with wildcard patterns to avoid next_token validation error
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]'

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

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_slo_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock wildcard expansion to return concrete targets
            concrete_targets = [
                {'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo-1'}}},
                {'Type': 'slo', 'Data': {'Slo': {'SloName': 'test-slo-2'}}},
            ]
            mock_expand.return_value = (concrete_targets, None, ['test-slo-1', 'test-slo-2'])
            mock_execute.return_value = (
                '[MCP-SLO] Application Signals SLO Compliance Audit\ntest-finding-2'
            )

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

            # Verify the execute_audit_api was called once (no batching)
            mock_execute.assert_called_once()


# =============================================================================
# AUDIT_SERVICE_OPERATIONS TESTS
# =============================================================================


class TestAuditServiceOperations:
    """Test cases for the audit_service_operations function.

    This class contains all tests related to the audit_service_operations function,
    including pagination, wildcard expansion, operation discovery, and successful execution.
    """

    @pytest.mark.asyncio
    async def test_next_token_rejected_without_wildcards(self, mock_aws_clients):
        """Test that next_token is rejected when no wildcards are used."""
        operation_targets = (
            '[{"Type":"service_operation","Data":{"ServiceOperation":'
            '{"Service":{"Type":"Service","Name":"test-service"},'
            '"Operation":"GET /api","MetricType":"Latency"}}}]'
        )

        result = await audit_service_operations(
            operation_targets=operation_targets,
            next_token='some_token',
        )

        assert (
            'Error: next_token parameter is only supported when using wildcard patterns in service names.'
            in result
        )

    @pytest.mark.asyncio
    async def test_pagination_with_wildcards(self, mock_aws_clients):
        """Test pagination functionality with wildcard patterns."""
        operation_targets = (
            '[{"Type":"service_operation","Data":{"ServiceOperation":'
            '{"Service":{"Type":"Service","Name":"*payment*"},'
            '"Operation":"*GET*","MetricType":"Latency"}}}]'
        )

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock expansion to return paginated results
            mock_expand.return_value = (
                [
                    {
                        'Type': 'service_operation',
                        'Data': {
                            'ServiceOperation': {
                                'Service': {'Type': 'Service', 'Name': 'payment-service'},
                                'Operation': 'GET /api',
                                'MetricType': 'Latency',
                            }
                        },
                    }
                ],
                'op_token_789',
                ['payment-service', 'order-service'],
            )
            mock_execute.return_value = 'Operation audit results'

            result = await audit_service_operations(
                operation_targets=operation_targets,
                max_services=2,
            )

            # Verify operation pagination info is included
            assert '📊 Processed 2 services in this batch:' in result
            assert '   • payment-service' in result
            assert '   • order-service' in result
            assert '🔄 PAGINATION: More services available!' in result
            assert 'audit_service_operations(' in result
            assert 'next_token="op_token_789"' in result
            assert 'max_services=2' in result

            # Verify expand function was called with pagination parameters
            mock_expand.assert_called_once()
            call_args = mock_expand.call_args[0]
            # Handle Pydantic FieldInfo objects - check if it's None or has default None
            next_token_arg = call_args[3]
            if hasattr(next_token_arg, 'default'):
                assert next_token_arg.default is None  # Pydantic FieldInfo with None default
            else:
                assert next_token_arg is None  # Direct None value
            assert call_args[4] == 2  # max_services

    @pytest.mark.asyncio
    async def test_no_targets_after_expansion(self, mock_aws_clients):
        """Test behavior when wildcard expansion finds no operations."""
        operation_targets = (
            '[{"Type":"service_operation","Data":{"ServiceOperation":'
            '{"Service":{"Type":"Service","Name":"*nonexistent*"},'
            '"Operation":"GET /api","MetricType":"Latency"}}}]'
        )

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
        ) as mock_expand:
            # Mock expansion to return empty results
            mock_expand.return_value = ([], None, [])

            result = await audit_service_operations(operation_targets=operation_targets)

            assert (
                'Error: No service_operation targets found after wildcard expansion. '
                'Use list_monitored_services() to see available services.' in result
            )

    @pytest.mark.asyncio
    async def test_successful_execution_with_batching(self, mock_aws_clients):
        """Test audit_service_operations successful execution with batching."""
        # Create enough operation targets with wildcard patterns to trigger batching (> BATCH_SIZE_THRESHOLD = 5)
        operation_targets = (
            '[{"Type":"service_operation","Data":{"ServiceOperation":'
            '{"Service":{"Type":"Service","Name":"*"},'
            '"Operation":"*","MetricType":"Latency"}}}]'
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

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock wildcard expansion to return concrete targets
            concrete_targets = [
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
                for i in range(7)
            ]
            mock_expand.return_value = (
                concrete_targets,
                None,
                [f'test-service-{i}' for i in range(7)],
            )
            mock_execute.return_value = (
                '[MCP-OPERATION] Application Signals Operation Performance Audit\n'
                '📦 Batching: Processing 7 targets in batches of 5\n'
                'test-finding-op-batch'
            )

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

            # Verify the execute_audit_api was called
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_execution_without_wildcards(self, mock_aws_clients):
        """Test audit_service_operations when no wildcards are present (no expansion needed)."""
        # Create operation targets with wildcard patterns that will be expanded to concrete targets
        operation_targets = json.dumps(
            [
                {
                    'Type': 'service_operation',
                    'Data': {
                        'ServiceOperation': {
                            'Service': {'Type': 'Service', 'Name': 'payment-service'},
                            'Operation': '*GET*',
                            'MetricType': 'Latency',
                        }
                    },
                },
                {
                    'Type': 'service_operation',
                    'Data': {
                        'ServiceOperation': {
                            'Service': {'Type': 'Service', 'Name': 'order-service'},
                            'Operation': '*POST*',
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

        with (
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.expand_service_operation_wildcard_patterns'
            ) as mock_expand,
            patch(
                'awslabs.cloudwatch_applicationsignals_mcp_server.server.execute_audit_api'
            ) as mock_execute,
        ):
            # Mock wildcard expansion to return concrete targets
            mock_expand.return_value = (
                operation_targets,
                None,
                ['payment-service', 'order-service'],
            )
            mock_execute.return_value = (
                '[MCP-OPERATION] Application Signals Operation Performance Audit\n'
                'test-finding-no-wildcards'
            )

            result = await audit_service_operations(
                operation_targets=operation_targets,
                start_time=None,
                end_time=None,
                auditors='operation_metric',
            )

            # Verify result contains expected content
            assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result
            assert 'test-finding-no-wildcards' in result

            # Verify wildcard expansion was called because wildcards were detected
            mock_expand.assert_called_once()

            # Verify the execute_audit_api was called once
            mock_execute.assert_called_once()
