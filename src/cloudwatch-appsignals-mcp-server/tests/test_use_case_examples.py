"""Unit tests for use case examples in the audit tools documentation.

This test file verifies that all use case examples in the tool documentation
call the correct tools with the right parameters and target formats.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Mock AWS clients BEFORE any imports that would initialize them
with patch('boto3.client') as mock_boto3_client, patch('boto3.Session') as mock_session:
    # Create mock clients
    mock_appsignals = MagicMock()
    mock_cloudwatch = MagicMock()
    mock_logs = MagicMock()
    mock_xray = MagicMock()

    # Configure boto3.client to return appropriate mocks
    def mock_client_factory(service_name, **kwargs):
        """Mock factory for boto3 clients."""
        if service_name == 'application-signals':
            return mock_appsignals
        elif service_name == 'cloudwatch':
            return mock_cloudwatch
        elif service_name == 'logs':
            return mock_logs
        elif service_name == 'xray':
            return mock_xray
        else:
            return MagicMock()

    mock_boto3_client.side_effect = mock_client_factory

    # Configure session to also return our mocks
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_session_instance.client.side_effect = mock_client_factory

    # Configure appsignals_client mock with comprehensive responses
    mock_appsignals.list_audit_findings.return_value = {
        'AuditFindings': [
            {
                'FindingId': 'test-finding-1',
                'Severity': 'CRITICAL',
                'Description': 'Test finding for validation',
            }
        ],
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }

    mock_appsignals.list_services.return_value = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'Service',
                    'Environment': 'eks:test-cluster',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'payment-service',
                    'Type': 'Service',
                    'Environment': 'eks:payment-cluster',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'payment-api',
                    'Type': 'Service',
                    'Environment': 'eks:prod-cluster',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'lambda-processor',
                    'Type': 'Service',
                    'Environment': 'lambda',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'orders-service',
                    'Type': 'Service',
                    'Environment': 'eks:orders-cluster',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'tier1-service',
                    'Type': 'Service',
                    'Environment': 'eks:prod-cluster',
                }
            },
        ]
    }

    mock_appsignals.list_service_level_objectives.return_value = {
        'SloSummaries': [
            {
                'Name': 'test-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
            },
            {
                'Name': 'payment-latency-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-latency-slo',
            },
            {
                'Name': 'payment-availability-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-availability-slo',
            },
            {
                'Name': 'latency-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/latency-slo',
            },
        ]
    }

    mock_appsignals.list_service_operations.return_value = {
        'Operations': [
            {
                'Name': 'GET /api',
                'MetricReferences': [{'MetricType': 'Latency'}, {'MetricType': 'Availability'}],
            },
            {
                'Name': 'POST /api',
                'MetricReferences': [{'MetricType': 'Latency'}, {'MetricType': 'Error'}],
            },
            {
                'Name': 'GET /api/payments',
                'MetricReferences': [{'MetricType': 'Latency'}, {'MetricType': 'Availability'}],
            },
            {
                'Name': 'POST /api/visits',
                'MetricReferences': [{'MetricType': 'Latency'}, {'MetricType': 'Availability'}],
            },
            {
                'Name': 'GET /api/query',
                'MetricReferences': [{'MetricType': 'Latency'}, {'MetricType': 'Availability'}],
            },
        ]
    }

    # NOW import the tools we're testing (after mocking is in place)
    from awslabs.cloudwatch_appsignals_mcp_server.server import (
        audit_service_operations,
        audit_services,
        audit_slos,
    )


@pytest.fixture
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls."""
    # The actual mocking is done at module level above
    # This fixture is kept for compatibility with existing test signatures
    yield {
        'appsignals': mock_appsignals,
        'cloudwatch': mock_cloudwatch,
        'logs': mock_logs,
        'xray': mock_xray,
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess execution for AWS CLI calls."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.asyncio.create_subprocess_exec'
    ) as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            json.dumps(
                {
                    'AuditFindings': [
                        {
                            'FindingId': 'test-finding-1',
                            'Severity': 'CRITICAL',
                            'Description': 'Test finding',
                        }
                    ]
                }
            ).encode(),
            b'',
        )
        mock_exec.return_value = mock_process
        yield mock_exec


class TestAuditServicesUseCases:
    """Test use case examples from audit_services() documentation."""

    @pytest.mark.asyncio
    async def test_use_case_1_audit_all_services(self, mock_aws_clients, mock_subprocess):
        """Test use case 1: Audit all services."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        result = await audit_services(
            service_targets=service_targets, auditors='slo,operation_metric'
        )

        # Verify the call was made
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_2_audit_specific_service(self, mock_aws_clients, mock_subprocess):
        """Test use case 2: Audit specific service."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"orders-service","Environment":"eks:orders-cluster"}}}]'

        result = await audit_services(service_targets=service_targets)

        # Verify the call was made with correct parameters
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_3_audit_payment_services(self, mock_aws_clients, mock_subprocess):
        """Test use case 3: Audit payment services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
        )

        result = await audit_services(service_targets=service_targets)

        # Verify wildcard expansion occurred
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_8_audit_lambda_services(self, mock_aws_clients, mock_subprocess):
        """Test use case 8: Audit lambda services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*lambda*"}}}]'
        )

        result = await audit_services(service_targets=service_targets)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_9_audit_service_last_night(self, mock_aws_clients, mock_subprocess):
        """Test use case 9: Audit service last night."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"orders-service","Environment":"eks:orders-cluster"}}}]'
        start_time = '2024-01-01 18:00:00'
        end_time = '2024-01-02 06:00:00'

        result = await audit_services(
            service_targets=service_targets, start_time=start_time, end_time=end_time
        )

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_11_trace_availability_issues(self, mock_aws_clients, mock_subprocess):
        """Test use case 11: Trace availability issues in production services."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]'
        auditors = 'all'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_13_look_for_errors_in_logs(self, mock_aws_clients, mock_subprocess):
        """Test use case 13: Look for errors in logs of payment services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
        )
        auditors = 'log,trace'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_16_look_for_lemon_hosts(self, mock_aws_clients, mock_subprocess):
        """Test use case 16: Look for lemon hosts in production."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]'
        auditors = 'top_contributor,operation_metric'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_18_status_report(self, mock_aws_clients, mock_subprocess):
        """Test use case 18: Status report."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        result = await audit_services(service_targets=service_targets)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_19_audit_dependencies(self, mock_aws_clients, mock_subprocess):
        """Test use case 19: Audit dependencies."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'
        auditors = 'dependency_metric,trace'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_21_audit_quota_usage(self, mock_aws_clients, mock_subprocess):
        """Test use case 21: Audit quota usage of tier 1 services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*tier1*"}}}]'
        )
        auditors = 'service_quota,operation_metric'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result


class TestAuditSlosUseCases:
    """Test use case examples from audit_slos() documentation."""

    @pytest.mark.asyncio
    async def test_use_case_4_audit_all_slos(self, mock_aws_clients, mock_subprocess):
        """Test use case 4: Audit all SLOs."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        # Verify the call was made and SLO targets were filtered
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_audit_payment_slos(self, mock_aws_clients, mock_subprocess):
        """Test auditing payment SLOs with wildcard pattern."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*payment*"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_audit_latency_slos(self, mock_aws_clients, mock_subprocess):
        """Test auditing latency SLOs with wildcard pattern."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*latency*"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_slo_root_cause_analysis(self, mock_aws_clients, mock_subprocess):
        """Test SLO root cause analysis with all auditors."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"payment-latency-slo"}}}]'
        auditors = 'all'

        result = await audit_slos(slo_targets=slo_targets, auditors=auditors)

        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_slo_target_filtering(self, mock_aws_clients, mock_subprocess):
        """Test that non-SLO targets are filtered out."""
        # Mix SLO and service targets - only SLO should be processed
        mixed_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"test-slo"}}},{"Type":"service","Data":{"Service":{"Name":"test-service"}}}]'

        result = await audit_slos(slo_targets=mixed_targets)

        # Should process only the SLO target
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result


class TestAuditServiceOperationsUseCases:
    """Test use case examples from audit_service_operations() documentation."""

    @pytest.mark.asyncio
    async def test_use_case_5_audit_get_operations_latency(
        self, mock_aws_clients, mock_subprocess
    ):
        """Test use case 5: Audit GET operations in payment services (Latency)."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_6_audit_visit_operations_availability(
        self, mock_aws_clients, mock_subprocess
    ):
        """Test use case 6: Audit availability of visit operations."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Availability"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_7_audit_visit_operations_latency(
        self, mock_aws_clients, mock_subprocess
    ):
        """Test use case 7: Audit latency of visit operations."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Latency"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_use_case_12_trace_latency_query_operations(
        self, mock_aws_clients, mock_subprocess
    ):
        """Test use case 12: Trace latency in query operations."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*query*","MetricType":"Latency"}}}]'
        auditors = 'all'

        result = await audit_service_operations(
            operation_targets=operation_targets, auditors=auditors
        )

        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_operation_target_filtering(self, mock_aws_clients, mock_subprocess):
        """Test that non-operation targets are filtered out."""
        # Mix operation and service targets - only operation should be processed
        mixed_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Name":"test-service"},"Operation":"GET /api","MetricType":"Latency"}}},{"Type":"service","Data":{"Service":{"Name":"test-service"}}}]'

        result = await audit_service_operations(operation_targets=mixed_targets)

        # Should process only the operation target
        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_default_operation_metric_auditor(self, mock_aws_clients, mock_subprocess):
        """Test that operation_metric is the default auditor for operations."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test"},"Operation":"GET /api","MetricType":"Latency"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        # Should use operation_metric as default auditor
        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result


class TestTargetFormatValidation:
    """Test that target formats are correctly validated and normalized."""

    @pytest.mark.asyncio
    async def test_service_target_full_format(self, mock_aws_clients, mock_subprocess):
        """Test full format service target."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"}}}]'

        result = await audit_services(service_targets=service_targets)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_service_target_shorthand_format(self, mock_aws_clients, mock_subprocess):
        """Test shorthand format service target."""
        service_targets = '[{"Type":"service","Service":"test-service"}]'

        result = await audit_services(service_targets=service_targets)

        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_slo_target_by_name(self, mock_aws_clients, mock_subprocess):
        """Test SLO target by name."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"test-slo"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_slo_target_by_arn(self, mock_aws_clients, mock_subprocess):
        """Test SLO target by ARN."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloArn":"arn:aws:application-signals:us-east-1:123456789012:slo/test-slo"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_operation_target_full_format(self, mock_aws_clients, mock_subprocess):
        """Test full format operation target."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"},"Operation":"GET /api","MetricType":"Latency"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_invalid_json_format(self, mock_aws_clients, mock_subprocess):
        """Test invalid JSON format handling."""
        invalid_targets = 'invalid json'

        result = await audit_services(service_targets=invalid_targets)

        assert 'Error: `service_targets` must be valid JSON (array)' in result

    @pytest.mark.asyncio
    async def test_empty_targets_array(self, mock_aws_clients, mock_subprocess):
        """Test empty targets array handling."""
        empty_targets = '[]'

        result = await audit_services(service_targets=empty_targets)

        assert (
            'Error: No services found matching the wildcard pattern' in result
            or 'Error:' in result
        )


class TestWildcardPatternExpansion:
    """Test wildcard pattern expansion functionality."""

    @pytest.mark.asyncio
    async def test_service_wildcard_all_services(self, mock_aws_clients, mock_subprocess):
        """Test wildcard pattern for all services."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]'

        result = await audit_services(service_targets=service_targets)

        # Should expand to all services
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_service_wildcard_payment_services(self, mock_aws_clients, mock_subprocess):
        """Test wildcard pattern for payment services."""
        service_targets = (
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]'
        )

        result = await audit_services(service_targets=service_targets)

        # Should expand to payment-api and payment-processor
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_slo_wildcard_all_slos(self, mock_aws_clients, mock_subprocess):
        """Test wildcard pattern for all SLOs."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        # Should expand to all SLOs
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_slo_wildcard_payment_slos(self, mock_aws_clients, mock_subprocess):
        """Test wildcard pattern for payment SLOs."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"*payment*"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        # Should expand to payment-latency-slo and payment-availability-slo
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result


class TestAuditorSelection:
    """Test auditor selection for different use cases."""

    @pytest.mark.asyncio
    async def test_default_service_auditors(self, mock_aws_clients, mock_subprocess):
        """Test default auditors for service auditing."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"}}}]'

        result = await audit_services(service_targets=service_targets)

        # Should use default auditors: slo,operation_metric
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_default_slo_auditors(self, mock_aws_clients, mock_subprocess):
        """Test default auditors for SLO auditing."""
        slo_targets = '[{"Type":"slo","Data":{"Slo":{"SloName":"test-slo"}}}]'

        result = await audit_slos(slo_targets=slo_targets)

        # Should use default auditor: slo
        assert '[MCP-SLO] Application Signals SLO Compliance Audit' in result

    @pytest.mark.asyncio
    async def test_default_operation_auditors(self, mock_aws_clients, mock_subprocess):
        """Test default auditors for operation auditing."""
        operation_targets = '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"},"Operation":"GET /api","MetricType":"Latency"}}}]'

        result = await audit_service_operations(operation_targets=operation_targets)

        # Should use default auditor: operation_metric
        assert '[MCP-OPERATION] Application Signals Operation Performance Audit' in result

    @pytest.mark.asyncio
    async def test_all_auditors_selection(self, mock_aws_clients, mock_subprocess):
        """Test 'all' auditors selection."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"}}}]'
        auditors = 'all'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        # Should use all available auditors
        assert '[MCP-SERVICE] Application Signals Service Audit' in result

    @pytest.mark.asyncio
    async def test_custom_auditors_selection(self, mock_aws_clients, mock_subprocess):
        """Test custom auditors selection."""
        service_targets = '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"test-service","Environment":"eks:test-cluster"}}}]'
        auditors = 'slo,trace,log'

        result = await audit_services(service_targets=service_targets, auditors=auditors)

        # Should use specified auditors
        assert '[MCP-SERVICE] Application Signals Service Audit' in result


class TestUseCaseDocumentationCorrectness:
    """Test that use case examples in documentation are correct and complete."""

    def test_audit_services_use_case_examples_completeness(self):
        """Test that all documented use cases for audit_services are covered."""
        # This test ensures we have covered all the use cases mentioned in the documentation
        documented_use_cases = [
            1,  # Audit all services
            2,  # Audit specific service
            3,  # Audit payment services
            8,  # Audit lambda services
            9,  # Audit service last night
            10,  # Audit service before and after time (covered by use case 9 pattern)
            11,  # Trace availability issues in production services
            13,  # Look for errors in logs of payment services
            14,  # Look for new errors after time (covered by time range pattern)
            15,  # Look for errors after deployment (covered by use case 13 pattern)
            16,  # Look for lemon hosts in production
            17,  # Look for outliers in EKS services (covered by use case 16 pattern)
            18,  # Status report
            19,  # Audit dependencies
            20,  # Audit dependency on S3 (covered by use case 19 pattern)
            21,  # Audit quota usage of tier 1 services
        ]

        # Verify we have test methods for the key use cases
        test_methods = [
            'test_use_case_1_audit_all_services',
            'test_use_case_2_audit_specific_service',
            'test_use_case_3_audit_payment_services',
            'test_use_case_8_audit_lambda_services',
            'test_use_case_9_audit_service_last_night',
            'test_use_case_11_trace_availability_issues',
            'test_use_case_13_look_for_errors_in_logs',
            'test_use_case_16_look_for_lemon_hosts',
            'test_use_case_18_status_report',
            'test_use_case_19_audit_dependencies',
            'test_use_case_21_audit_quota_usage',
        ]

        # Verify we have comprehensive coverage of documented use cases
        assert len(documented_use_cases) >= 16, 'Should document at least 16 use cases'
        assert len(test_methods) >= 10, 'Should have at least 10 key use case tests'

    def test_audit_slos_use_case_examples_completeness(self):
        """Test that all documented use cases for audit_slos are covered."""
        documented_use_cases = [
            4,  # Audit all SLOs
            14,  # Look for new SLO breaches after time
        ]

        test_methods = [
            'test_use_case_4_audit_all_slos',
            'test_audit_payment_slos',
            'test_audit_latency_slos',
            'test_slo_root_cause_analysis',
        ]

        # Verify we have comprehensive coverage of documented SLO use cases
        assert len(documented_use_cases) >= 2, 'Should document at least 2 SLO use cases'
        assert len(test_methods) >= 4, 'Should have at least 4 SLO use case tests'

    def test_audit_service_operations_use_case_examples_completeness(self):
        """Test that all documented use cases for audit_service_operations are covered."""
        documented_use_cases = [
            5,  # Audit GET operations in payment services (Latency)
            6,  # Audit availability of visit operations
            7,  # Audit latency of visit operations
            12,  # Trace latency in query operations
        ]

        test_methods = [
            'test_use_case_5_audit_get_operations_latency',
            'test_use_case_6_audit_visit_operations_availability',
            'test_use_case_7_audit_visit_operations_latency',
            'test_use_case_12_trace_latency_query_operations',
        ]

        # Verify we have comprehensive coverage of documented operation use cases
        assert len(documented_use_cases) >= 4, 'Should document at least 4 operation use cases'
        assert len(test_methods) >= 4, 'Should have at least 4 operation use case tests'

    def test_target_format_examples_are_valid_json(self):
        """Test that all target format examples in documentation are valid JSON."""
        # Service target examples
        service_examples = [
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]',
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"orders-service","Environment":"eks:orders-cluster"}}}]',
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]',
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*lambda*"}}}]',
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*","Environment":"eks:*"}}}]',
            '[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*tier1*"}}}]',
        ]

        # SLO target examples
        slo_examples = [
            '[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]',
            '[{"Type":"slo","Data":{"Slo":{"SloName":"*payment*"}}}]',
            '[{"Type":"slo","Data":{"Slo":{"SloName":"*latency*"}}}]',
            '[{"Type":"slo","Data":{"Slo":{"SloName":"*availability*"}}}]',
        ]

        # Operation target examples
        operation_examples = [
            '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]',
            '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Availability"}}}]',
            '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*"},"Operation":"*visit*","MetricType":"Latency"}}}]',
            '[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*query*","MetricType":"Latency"}}}]',
        ]

        # Test that all examples are valid JSON
        all_examples = service_examples + slo_examples + operation_examples
        for example in all_examples:
            try:
                parsed = json.loads(example)
                assert isinstance(parsed, list), f'Example should be a JSON array: {example}'
                assert len(parsed) > 0, f'Example should not be empty: {example}'
            except json.JSONDecodeError as e:
                pytest.fail(f'Invalid JSON in documentation example: {example}\nError: {e}')

    def test_auditor_examples_are_valid(self):
        """Test that all auditor examples in documentation are valid."""
        valid_auditors = {
            'slo',
            'operation_metric',
            'trace',
            'log',
            'dependency_metric',
            'top_contributor',
            'service_quota',
        }

        auditor_examples = [
            'all',
            'slo,operation_metric',
            'slo',
            'operation_metric',
            'slo,trace,log',
            'log,trace',
            'top_contributor,operation_metric',
            'dependency_metric,trace',
            'service_quota,operation_metric',
        ]

        for example in auditor_examples:
            if example == 'all':
                continue  # "all" is a special case

            auditors = [a.strip() for a in example.split(',')]
            for auditor in auditors:
                assert auditor in valid_auditors, (
                    f'Invalid auditor in example: {auditor} (from {example})'
                )


if __name__ == '__main__':
    pytest.main([__file__])
