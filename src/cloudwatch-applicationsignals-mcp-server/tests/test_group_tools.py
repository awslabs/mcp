"""Tests for group_tools.py functions."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.group_tools import (
    audit_group_health,
    get_group_changes,
    get_group_dependencies,
    list_group_services,
    list_grouping_attribute_definitions,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


# =============================================================================
# FIXTURES
# =============================================================================


def _make_service(name, environment='production', service_type='Service', groups=None):
    """Helper to create a mock service dict."""
    svc = {
        'KeyAttributes': {
            'Name': name,
            'Type': service_type,
            'Environment': environment,
        },
        'ServiceGroups': groups or [],
    }
    return svc


def _make_group(group_name, group_value, source='TAG', identifier=None):
    """Helper to create a ServiceGroups entry."""
    return {
        'GroupName': group_name,
        'GroupValue': group_value,
        'GroupSource': source,
        'GroupIdentifier': identifier or f'{group_name}={group_value}',
    }


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_applicationsignals_client = MagicMock()
    mock_cloudwatch_client = MagicMock()

    patches = [
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.applicationsignals_client',
            mock_applicationsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.cloudwatch_client',
            mock_cloudwatch_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'applicationsignals_client': mock_applicationsignals_client,
            'cloudwatch_client': mock_cloudwatch_client,
        }
    finally:
        for p in patches:
            p.stop()


# =============================================================================
# TESTS: list_group_services
# =============================================================================


class TestListGroupServices:
    """Tests for the list_group_services tool."""

    @pytest.mark.asyncio
    async def test_success_exact_match(self, mock_aws_clients):
        """Test successful listing with exact group value match."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('payment-svc', groups=[_make_group('Team', 'Payments')]),
                _make_service('order-svc', groups=[_make_group('Team', 'Payments')]),
                _make_service('auth-svc', groups=[_make_group('Team', 'Auth')]),
            ]
        }

        result = await list_group_services(group_name='Payments')

        assert 'SERVICES IN GROUP: Payments' in result
        assert 'Services in group: 2' in result
        assert 'payment-svc' in result
        assert 'order-svc' in result
        assert 'auth-svc' not in result

    @pytest.mark.asyncio
    async def test_success_wildcard_match(self, mock_aws_clients):
        """Test successful listing with wildcard pattern."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('payment-svc', groups=[_make_group('Team', 'Payments')]),
                _make_service('payment-gateway', groups=[_make_group('Team', 'PaymentGateway')]),
                _make_service('auth-svc', groups=[_make_group('Team', 'Auth')]),
            ]
        }

        result = await list_group_services(group_name='*payment*')

        assert 'Services in group: 2' in result
        assert 'payment-svc' in result
        assert 'payment-gateway' in result
        assert 'auth-svc' not in result

    @pytest.mark.asyncio
    async def test_success_match_by_group_name(self, mock_aws_clients):
        """Test matching by GroupName attribute."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('BusinessUnit', 'Engineering')]),
                _make_service('svc-b', groups=[_make_group('BusinessUnit', 'Marketing')]),
            ]
        }

        result = await list_group_services(group_name='BusinessUnit')

        assert 'Services in group: 2' in result
        assert 'svc-a' in result
        assert 'svc-b' in result

    @pytest.mark.asyncio
    async def test_no_services_found(self, mock_aws_clients):
        """Test when no services match the group."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Auth')]),
            ]
        }

        result = await list_group_services(group_name='NonExistent')

        assert 'No services found' in result
        assert 'Team=Auth' in result

    @pytest.mark.asyncio
    async def test_pagination(self, mock_aws_clients):
        """Test pagination through multiple pages of services."""
        mock_aws_clients['applicationsignals_client'].list_services.side_effect = [
            {
                'ServiceSummaries': [
                    _make_service('svc-1', groups=[_make_group('Team', 'Payments')]),
                ],
                'NextToken': 'page2',
            },
            {
                'ServiceSummaries': [
                    _make_service('svc-2', groups=[_make_group('Team', 'Payments')]),
                ],
            },
        ]

        result = await list_group_services(group_name='Payments')

        assert 'Services in group: 2' in result
        assert 'svc-1' in result
        assert 'svc-2' in result

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, mock_aws_clients):
        """Test that group matching is case-insensitive."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'PAYMENTS')]),
            ]
        }

        result = await list_group_services(group_name='payments')

        assert 'Services in group: 1' in result
        assert 'svc-a' in result

    @pytest.mark.asyncio
    async def test_invalid_time_range(self, mock_aws_clients):
        """Test with end_time before start_time."""
        result = await list_group_services(
            group_name='Payments',
            start_time='2024-01-02 00:00:00',
            end_time='2024-01-01 00:00:00',
        )

        assert 'end_time must be greater than start_time' in result

    @pytest.mark.asyncio
    async def test_displays_group_details(self, mock_aws_clients):
        """Test that group membership details are shown."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments', source='OTEL')]),
            ]
        }

        result = await list_group_services(group_name='Payments')

        assert 'Team=Payments' in result
        assert 'OTEL' in result

    @pytest.mark.asyncio
    async def test_platform_and_environment_distribution(self, mock_aws_clients):
        """Test that platform and environment distribution is shown."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                {
                    'KeyAttributes': {
                        'Name': 'svc-a',
                        'Environment': 'production',
                        'Type': 'Service',
                    },
                    'ServiceGroups': [_make_group('Team', 'Payments')],
                    'AttributeMaps': [{'PlatformType': 'AWS::ECS'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'svc-b',
                        'Environment': 'production',
                        'Type': 'Service',
                    },
                    'ServiceGroups': [_make_group('Team', 'Payments')],
                    'AttributeMaps': [{'PlatformType': 'AWS::Lambda'}],
                },
                {
                    'KeyAttributes': {
                        'Name': 'svc-c',
                        'Environment': 'staging',
                        'Type': 'Service',
                    },
                    'ServiceGroups': [_make_group('Team', 'Payments')],
                    'AttributeMaps': [{'PlatformType': 'AWS::ECS'}],
                },
            ]
        }

        result = await list_group_services(group_name='Payments')

        assert 'Platform Distribution:' in result
        assert 'AWS::ECS: 2 services' in result
        assert 'AWS::Lambda: 1 service' in result
        assert 'Environment Distribution:' in result
        assert 'production: 2 services' in result
        assert 'staging: 1 service' in result

    @pytest.mark.asyncio
    async def test_general_exception(self, mock_aws_clients):
        """Test handling of unexpected exceptions."""
        mock_aws_clients['applicationsignals_client'].list_services.side_effect = Exception(
            'Unexpected error'
        )

        result = await list_group_services(group_name='Payments')

        assert 'Error: Unexpected error' in result


# =============================================================================
# TESTS: audit_group_health
# =============================================================================


class TestAuditGroupHealth:
    """Tests for the audit_group_health tool."""

    @pytest.mark.asyncio
    async def test_all_healthy_with_sli(self, mock_aws_clients):
        """Test audit when all services are healthy via SLI."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 2
        mock_sli_report.ok_slo_count = 2
        mock_sli_report.breached_slo_count = 0
        mock_sli_report.breached_slo_names = []
        mock_sli_report.sli_status = 'OK'

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(group_name='Payments')

        assert 'GROUP HEALTH AUDIT: Payments' in result
        assert 'Healthy:  1/1' in result
        assert 'HEALTHY' in result
        assert 'services with SLIs' in result

    @pytest.mark.asyncio
    async def test_critical_slo_breach(self, mock_aws_clients):
        """Test audit when SLOs are breached."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 3
        mock_sli_report.ok_slo_count = 1
        mock_sli_report.breached_slo_count = 2
        mock_sli_report.breached_slo_names = ['latency-slo', 'availability-slo']
        mock_sli_report.sli_status = 'CRITICAL'

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(group_name='Payments')

        assert 'Critical: 1/1' in result
        assert 'CRITICAL' in result
        assert 'latency-slo' in result
        assert 'availability-slo' in result
        assert 'SLO_BREACH' in result or 'SLOs breached' in result

    @pytest.mark.asyncio
    async def test_metrics_fallback_healthy(self, mock_aws_clients):
        """Test audit using metrics fallback when no SLOs configured."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        # SLI has no SLOs
        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Fault',
                        'MetricType': 'Fault',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [{'Average': 0.1}]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(group_name='Payments')

        assert 'Healthy:  1/1' in result
        assert 'using metrics fallback' in result

    @pytest.mark.asyncio
    async def test_metrics_fallback_critical_fault_rate(self, mock_aws_clients):
        """Test audit with critical fault rate via metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Fault',
                        'MetricType': 'Fault',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        # Fault rate above critical threshold (default 5.0%)
        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [{'Average': 10.0}]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(
                group_name='Payments',
                fault_threshold_warning=1.0,
                fault_threshold_critical=5.0,
            )

        assert 'Critical: 1/1' in result
        assert 'CRITICAL' in result
        assert 'Fault rate' in result

    @pytest.mark.asyncio
    async def test_metrics_fallback_error_rate_critical(self, mock_aws_clients):
        """Test audit with critical error rate via metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Error',
                        'MetricType': 'Error',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        # Error rate above critical threshold (default 5.0%)
        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [{'Average': 10.0}]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(
                group_name='Payments',
                error_threshold_warning=1.0,
                error_threshold_critical=5.0,
            )

        assert 'Critical: 1/1' in result
        assert 'CRITICAL' in result
        assert 'Error rate' in result

    @pytest.mark.asyncio
    async def test_metrics_fallback_latency(self, mock_aws_clients):
        """Test audit captures latency p99 via metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Latency',
                        'MetricType': 'Latency',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [
                {'Average': 100.0, 'ExtendedStatistics': {'p99': 500.0}},
                {'Average': 120.0, 'ExtendedStatistics': {'p99': 450.0}},
            ]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(group_name='Payments')

        # Healthy because p99 (500ms) is below default warning threshold (1000ms)
        assert 'Healthy:  1/1' in result

    @pytest.mark.asyncio
    async def test_metrics_fallback_latency_critical(self, mock_aws_clients):
        """Test audit with critical latency via metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Latency',
                        'MetricType': 'Latency',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        # p99 above critical threshold (5000ms)
        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [
                {'Average': 100.0, 'ExtendedStatistics': {'p99': 8000.0}},
            ]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(
                group_name='Payments',
                latency_p99_threshold_warning=1000.0,
                latency_p99_threshold_critical=5000.0,
            )

        assert 'Critical: 1/1' in result
        assert 'CRITICAL' in result
        assert 'Latency P99' in result

    @pytest.mark.asyncio
    async def test_mixed_health_statuses(self, mock_aws_clients):
        """Test audit with a mix of healthy and unhealthy services."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('healthy-svc', groups=[_make_group('Team', 'Payments')]),
                _make_service('critical-svc', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report_ok = MagicMock()
        mock_sli_report_ok.total_slo_count = 1
        mock_sli_report_ok.ok_slo_count = 1
        mock_sli_report_ok.breached_slo_count = 0
        mock_sli_report_ok.breached_slo_names = []
        mock_sli_report_ok.sli_status = 'OK'

        mock_sli_report_critical = MagicMock()
        mock_sli_report_critical.total_slo_count = 1
        mock_sli_report_critical.ok_slo_count = 0
        mock_sli_report_critical.breached_slo_count = 1
        mock_sli_report_critical.breached_slo_names = ['latency-slo']
        mock_sli_report_critical.sli_status = 'CRITICAL'

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.side_effect = [
                mock_sli_report_ok,
                mock_sli_report_critical,
            ]
            result = await audit_group_health(group_name='Payments')

        assert 'Critical: 1/2' in result
        assert 'Healthy:  1/2' in result
        assert 'Overall Status: CRITICAL' in result
        assert 'RECOMMENDATIONS' in result

    @pytest.mark.asyncio
    async def test_no_services_found(self, mock_aws_clients):
        """Test audit when no services match the group."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': []
        }

        result = await audit_group_health(group_name='NonExistent')

        assert 'No services found' in result

    @pytest.mark.asyncio
    async def test_invalid_time_range(self, mock_aws_clients):
        """Test with end_time before start_time."""
        result = await audit_group_health(
            group_name='Payments',
            start_time='2024-01-02 00:00:00',
            end_time='2024-01-01 00:00:00',
        )

        assert 'end_time must be greater than start_time' in result

    @pytest.mark.asyncio
    async def test_custom_thresholds(self, mock_aws_clients):
        """Test with custom fault rate thresholds."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'MetricReferences': [
                    {
                        'MetricName': 'Fault',
                        'MetricType': 'Fault',
                        'Namespace': 'AWS/ApplicationSignals',
                        'Dimensions': [{'Name': 'Service', 'Value': 'svc-a'}],
                    }
                ]
            }
        }

        # Fault rate 8% - above default critical (5%) but below custom critical (10%)
        mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = {
            'Datapoints': [{'Average': 8.0}]
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(
                group_name='Payments',
                fault_threshold_warning=5.0,
                fault_threshold_critical=10.0,
            )

        # Should be WARNING (above 5%) not CRITICAL (below 10%)
        assert 'Warning:  1/1' in result

    @pytest.mark.asyncio
    async def test_sli_exception_falls_back_to_metrics(self, mock_aws_clients):
        """Test that SLI exception triggers metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {'MetricReferences': []}
        }

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.side_effect = Exception(
                'SLI unavailable'
            )
            result = await audit_group_health(group_name='Payments')

        assert 'using metrics fallback' in result
        assert 'Healthy:  1/1' in result

    @pytest.mark.asyncio
    async def test_metrics_get_service_failure(self, mock_aws_clients):
        """Test when get_service fails during metrics fallback."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_sli_report = MagicMock()
        mock_sli_report.total_slo_count = 0

        mock_aws_clients['applicationsignals_client'].get_service.side_effect = Exception(
            'Service not accessible'
        )

        with patch(
            'awslabs.cloudwatch_applicationsignals_mcp_server.group_tools.SLIReportClient'
        ) as mock_sli_class:
            mock_sli_class.return_value.generate_sli_report.return_value = mock_sli_report
            result = await audit_group_health(group_name='Payments')

        assert 'Unknown:  1/1' in result

    @pytest.mark.asyncio
    async def test_general_exception(self, mock_aws_clients):
        """Test handling of unexpected exceptions."""
        mock_aws_clients['applicationsignals_client'].list_services.side_effect = Exception(
            'Unexpected error'
        )

        result = await audit_group_health(group_name='Payments')

        assert 'Error: Unexpected error' in result


# =============================================================================
# TESTS: get_group_dependencies
# =============================================================================


class TestGetGroupDependencies:
    """Tests for the get_group_dependencies tool."""

    @pytest.mark.asyncio
    async def test_intra_group_dependencies(self, mock_aws_clients):
        """Test detection of intra-group dependencies."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('frontend', groups=[_make_group('App', 'Checkout')]),
                _make_service('backend', groups=[_make_group('App', 'Checkout')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': [
                {
                    'DependencyKeyAttributes': {
                        'Name': 'backend',
                        'Type': 'Service',
                        'Environment': 'production',
                    },
                    'OperationName': 'GET /api',
                },
            ]
        }

        result = await get_group_dependencies(group_name='Checkout')

        assert 'GROUP DEPENDENCIES: Checkout' in result
        assert 'INTRA-GROUP DEPENDENCIES' in result
        assert 'frontend' in result
        assert 'backend' in result

    @pytest.mark.asyncio
    async def test_cross_group_dependencies(self, mock_aws_clients):
        """Test detection of cross-group dependencies with group info lookup."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('payment-svc', groups=[_make_group('App', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': [
                {
                    'DependencyKeyAttributes': {
                        'Name': 'user-svc',
                        'Type': 'Service',
                        'Environment': 'production',
                    },
                    'OperationName': 'GET /users',
                },
            ]
        }

        # Mock GetService to return group info for the cross-group dependency
        mock_aws_clients['applicationsignals_client'].get_service.return_value = {
            'Service': {
                'KeyAttributes': {
                    'Name': 'user-svc',
                    'Type': 'Service',
                    'Environment': 'production',
                },
                'ServiceGroups': [
                    {
                        'GroupName': 'App',
                        'GroupValue': 'UserManagement',
                        'GroupSource': 'TAG',
                    }
                ],
                'MetricReferences': [],
            }
        }

        result = await get_group_dependencies(group_name='Payments')

        assert 'CROSS-GROUP DEPENDENCIES' in result
        assert 'user-svc' in result
        assert 'UserManagement' in result
        assert 'Groups:' in result

    @pytest.mark.asyncio
    async def test_external_aws_dependencies(self, mock_aws_clients):
        """Test detection of external AWS service dependencies."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('App', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': [
                {
                    'DependencyKeyAttributes': {
                        'Identifier': 'my-table',
                        'ResourceType': 'AWS::DynamoDB::Table',
                        'Type': 'AWS::Resource',
                    },
                    'OperationName': 'GetItem',
                },
                {
                    'DependencyKeyAttributes': {
                        'Identifier': 'my-bucket',
                        'ResourceType': 'AWS::S3::Bucket',
                        'Type': 'AWS::Resource',
                    },
                    'OperationName': 'PutObject',
                },
            ]
        }

        result = await get_group_dependencies(group_name='Payments')

        assert 'EXTERNAL DEPENDENCIES' in result
        assert 'AWS::DynamoDB::Table:my-table' in result
        assert 'AWS::S3::Bucket:my-bucket' in result

    @pytest.mark.asyncio
    async def test_aws_service_type_external(self, mock_aws_clients):
        """Test that AWS::Service type dependencies are classified as external."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('App', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': [
                {
                    'DependencyKeyAttributes': {
                        'Name': 'AWS.SDK.SQS',
                        'Type': 'AWS::Service',
                    },
                    'OperationName': 'SendMessage',
                },
            ]
        }

        result = await get_group_dependencies(group_name='Payments')

        assert 'EXTERNAL DEPENDENCIES' in result
        assert 'AWS::Service:AWS.SDK.SQS' in result

    @pytest.mark.asyncio
    async def test_cross_group_get_service_failure(self, mock_aws_clients):
        """Test graceful handling when GetService fails for cross-group dependency."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('payment-svc', groups=[_make_group('App', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': [
                {
                    'DependencyKeyAttributes': {
                        'Name': 'unknown-svc',
                        'Type': 'Service',
                        'Environment': 'staging',
                    },
                    'OperationName': 'GET /data',
                },
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependents.return_value = {
            'ServiceDependents': []
        }

        # GetService fails for the cross-group dependency
        mock_aws_clients['applicationsignals_client'].get_service.side_effect = Exception(
            'Service not found'
        )

        result = await get_group_dependencies(group_name='Payments')

        assert 'CROSS-GROUP DEPENDENCIES' in result
        assert 'unknown-svc' in result
        # Should not crash, just no group info shown
        assert 'Groups:' not in result

    @pytest.mark.asyncio
    async def test_no_dependencies(self, mock_aws_clients):
        """Test when a service has no dependencies."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('isolated-svc', groups=[_make_group('App', 'Isolated')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_dependencies.return_value = {
            'ServiceDependencies': []
        }

        result = await get_group_dependencies(group_name='Isolated')

        assert 'No intra-group dependencies found' in result
        assert 'No cross-group dependencies found' in result
        assert 'No external AWS service dependencies found' in result

    @pytest.mark.asyncio
    async def test_no_services_found(self, mock_aws_clients):
        """Test when no services match the group."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': []
        }

        result = await get_group_dependencies(group_name='NonExistent')

        assert 'No services found' in result

    @pytest.mark.asyncio
    async def test_invalid_time_range(self, mock_aws_clients):
        """Test with end_time before start_time."""
        result = await get_group_dependencies(
            group_name='Payments',
            start_time='2024-01-02 00:00:00',
            end_time='2024-01-01 00:00:00',
        )

        assert 'end_time must be greater than start_time' in result

    @pytest.mark.asyncio
    async def test_dependency_api_client_error_skipped(self, mock_aws_clients):
        """Test that ResourceNotFoundException is gracefully skipped."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('App', 'Payments')]),
            ]
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_dependencies.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}
            },
            operation_name='ListServiceDependencies',
        )

        mock_aws_clients['applicationsignals_client'].list_service_dependents.return_value = {
            'ServiceDependents': []
        }

        result = await get_group_dependencies(group_name='Payments')

        # Should not error out, just show no deps
        assert 'GROUP DEPENDENCIES: Payments' in result

    @pytest.mark.asyncio
    async def test_summary_counts(self, mock_aws_clients):
        """Test that the summary section has correct counts."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('App', 'Payments')]),
                _make_service('svc-b', groups=[_make_group('App', 'Payments')]),
            ]
        }

        # svc-a depends on svc-b (intra), plus an external S3
        mock_aws_clients['applicationsignals_client'].list_service_dependencies.side_effect = [
            {
                'ServiceDependencies': [
                    {
                        'DependencyKeyAttributes': {
                            'Name': 'svc-b',
                            'Type': 'Service',
                            'Environment': 'production',
                        },
                        'OperationName': 'GET /api',
                    },
                    {
                        'DependencyKeyAttributes': {
                            'Identifier': 'my-bucket',
                            'ResourceType': 'AWS::S3::Bucket',
                            'Type': 'AWS::Resource',
                        },
                        'OperationName': 'PutObject',
                    },
                ]
            },
            {'ServiceDependencies': []},
        ]

        mock_aws_clients['applicationsignals_client'].list_service_dependents.return_value = {
            'ServiceDependents': []
        }

        result = await get_group_dependencies(group_name='Payments')

        assert 'SUMMARY' in result
        assert 'Intra-group dependencies: 1' in result
        assert 'External AWS dependencies: 1' in result

    @pytest.mark.asyncio
    async def test_general_exception(self, mock_aws_clients):
        """Test handling of unexpected exceptions."""
        mock_aws_clients['applicationsignals_client'].list_services.side_effect = Exception(
            'Unexpected error'
        )

        result = await get_group_dependencies(group_name='Payments')

        assert 'Error: Unexpected error' in result


# =============================================================================
# TESTS: get_group_changes
# =============================================================================


class TestGetGroupChanges:
    """Tests for the get_group_changes tool."""

    @pytest.mark.asyncio
    async def test_deployments_and_config_changes(self, mock_aws_clients):
        """Test detection of both deployment and configuration changes."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.return_value = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'svc-a'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                            'EventName': 'Deploy v2.0',
                            'EventId': 'evt-001',
                            'UserName': 'deploy-bot',
                            'Region': 'us-east-1',
                        },
                        {
                            'Timestamp': datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'CONFIGURATION',
                            'EventName': 'Update env vars',
                            'EventId': 'evt-002',
                            'UserName': 'admin',
                            'Region': 'us-east-1',
                        },
                    ],
                }
            ]
        }

        result = await get_group_changes(group_name='Payments')

        assert 'GROUP CHANGES: Payments' in result
        assert 'Deployments: 1' in result
        assert 'Configuration Changes: 1' in result
        assert 'Total Events: 2' in result
        assert 'Deploy v2.0' in result
        assert 'Update env vars' in result
        assert 'deploy-bot' in result
        assert 'admin' in result

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_aws_clients):
        """Test when no change events are found."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.return_value = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'svc-a'},
                    'LatestChangeEvents': [],
                }
            ]
        }

        result = await get_group_changes(group_name='Payments')

        assert 'Total Events: 0' in result
        assert 'No change events found' in result

    @pytest.mark.asyncio
    async def test_filters_to_group_services_only(self, mock_aws_clients):
        """Test that only changes for services in the group are included."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.return_value = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'svc-a'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                            'EventName': 'Deploy group svc',
                        },
                    ],
                },
                {
                    'Service': {'Name': 'other-svc'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                            'EventName': 'Deploy other',
                        },
                    ],
                },
            ]
        }

        result = await get_group_changes(group_name='Payments')

        assert 'Total Events: 1' in result
        assert 'Deploy group svc' in result
        assert 'Deploy other' not in result

    @pytest.mark.asyncio
    async def test_changes_by_service_section(self, mock_aws_clients):
        """Test the changes-by-service breakdown."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
                _make_service('svc-b', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.return_value = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'svc-a'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                        },
                        {
                            'Timestamp': datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                        },
                    ],
                },
                {
                    'Service': {'Name': 'svc-b'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'CONFIGURATION',
                        },
                    ],
                },
            ]
        }

        result = await get_group_changes(group_name='Payments')

        assert 'CHANGES BY SERVICE' in result
        assert 'svc-a' in result
        assert '2 deployments' in result
        assert 'svc-b' in result
        assert '1 config changes' in result

    @pytest.mark.asyncio
    async def test_pagination(self, mock_aws_clients):
        """Test pagination through service states."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.side_effect = [
            {
                'ServiceStates': [
                    {
                        'Service': {'Name': 'svc-a'},
                        'LatestChangeEvents': [
                            {
                                'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                                'ChangeEventType': 'DEPLOYMENT',
                                'EventName': 'page1-event',
                            },
                        ],
                    }
                ],
                'NextToken': 'page2',
            },
            {
                'ServiceStates': [
                    {
                        'Service': {'Name': 'svc-a'},
                        'LatestChangeEvents': [
                            {
                                'Timestamp': datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
                                'ChangeEventType': 'CONFIGURATION',
                                'EventName': 'page2-event',
                            },
                        ],
                    }
                ],
            },
        ]

        result = await get_group_changes(group_name='Payments')

        assert 'Total Events: 2' in result
        assert 'page1-event' in result
        assert 'page2-event' in result

    @pytest.mark.asyncio
    async def test_service_states_api_error(self, mock_aws_clients):
        """Test graceful handling of service states API error."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients[
            'applicationsignals_client'
        ].list_service_states.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}
            },
            operation_name='ListServiceStates',
        )

        result = await get_group_changes(group_name='Payments')

        assert 'Service state tracking may not be available' in result

    @pytest.mark.asyncio
    async def test_no_services_found(self, mock_aws_clients):
        """Test when no services match the group."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': []
        }

        result = await get_group_changes(group_name='NonExistent')

        assert 'No services found' in result

    @pytest.mark.asyncio
    async def test_invalid_time_range(self, mock_aws_clients):
        """Test with end_time before start_time."""
        result = await get_group_changes(
            group_name='Payments',
            start_time='2024-01-02 00:00:00',
            end_time='2024-01-01 00:00:00',
        )

        assert 'end_time must be greater than start_time' in result

    @pytest.mark.asyncio
    async def test_tips_shown_when_changes_exist(self, mock_aws_clients):
        """Test that tips are shown when there are changes."""
        mock_aws_clients['applicationsignals_client'].list_services.return_value = {
            'ServiceSummaries': [
                _make_service('svc-a', groups=[_make_group('Team', 'Payments')]),
            ]
        }

        mock_aws_clients['applicationsignals_client'].list_service_states.return_value = {
            'ServiceStates': [
                {
                    'Service': {'Name': 'svc-a'},
                    'LatestChangeEvents': [
                        {
                            'Timestamp': datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                            'ChangeEventType': 'DEPLOYMENT',
                        },
                    ],
                }
            ]
        }

        result = await get_group_changes(group_name='Payments')

        assert 'TIPS' in result
        assert 'audit_group_health()' in result

    @pytest.mark.asyncio
    async def test_general_exception(self, mock_aws_clients):
        """Test handling of unexpected exceptions."""
        mock_aws_clients['applicationsignals_client'].list_services.side_effect = Exception(
            'Unexpected error'
        )

        result = await get_group_changes(group_name='Payments')

        assert 'Error: Unexpected error' in result


# =============================================================================
# TESTS: list_grouping_attribute_definitions
# =============================================================================


class TestListGroupingAttributeDefinitions:
    """Tests for the list_grouping_attribute_definitions tool."""

    @pytest.mark.asyncio
    async def test_success_with_definitions(self, mock_aws_clients):
        """Test successful listing with grouping attribute definitions."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.return_value = {
            'GroupingAttributeDefinitions': [
                {
                    'GroupingName': 'BusinessUnit',
                    'GroupingSourceKeys': ['aws:tag:BusinessUnit', 'otel.resource.business_unit'],
                    'DefaultGroupingValue': 'Unassigned',
                },
                {
                    'GroupingName': 'Team',
                    'GroupingSourceKeys': ['aws:tag:Team'],
                    'DefaultGroupingValue': 'DefaultTeam',
                },
            ],
            'UpdatedAt': datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
        }

        result = await list_grouping_attribute_definitions()

        assert 'GROUPING ATTRIBUTE DEFINITIONS' in result
        assert 'Found **2 grouping attribute definition(s)**' in result
        assert 'BusinessUnit' in result
        assert 'aws:tag:BusinessUnit' in result
        assert 'otel.resource.business_unit' in result
        assert 'Unassigned' in result
        assert 'Team' in result
        assert 'aws:tag:Team' in result
        assert 'DefaultTeam' in result
        assert '2024-06-15 14:30:00' in result

    @pytest.mark.asyncio
    async def test_success_no_definitions(self, mock_aws_clients):
        """Test when no grouping attribute definitions are configured."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.return_value = {
            'GroupingAttributeDefinitions': [],
            'UpdatedAt': datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
        }

        result = await list_grouping_attribute_definitions()

        assert 'No custom grouping attribute definitions found' in result
        assert 'Tips' in result

    @pytest.mark.asyncio
    async def test_pagination(self, mock_aws_clients):
        """Test pagination through multiple pages of definitions."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.side_effect = [
            {
                'GroupingAttributeDefinitions': [
                    {
                        'GroupingName': 'BusinessUnit',
                        'GroupingSourceKeys': ['aws:tag:BusinessUnit'],
                        'DefaultGroupingValue': 'Unassigned',
                    },
                ],
                'UpdatedAt': datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                'NextToken': 'page2',
            },
            {
                'GroupingAttributeDefinitions': [
                    {
                        'GroupingName': 'Team',
                        'GroupingSourceKeys': ['aws:tag:Team'],
                        'DefaultGroupingValue': '',
                    },
                ],
            },
        ]

        result = await list_grouping_attribute_definitions()

        assert 'Found **2 grouping attribute definition(s)**' in result
        assert 'BusinessUnit' in result
        assert 'Team' in result

    @pytest.mark.asyncio
    async def test_definition_without_optional_fields(self, mock_aws_clients):
        """Test definitions with missing optional fields."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.return_value = {
            'GroupingAttributeDefinitions': [
                {
                    'GroupingName': 'Region',
                    # No GroupingSourceKeys
                    # No DefaultGroupingValue
                },
            ],
        }

        result = await list_grouping_attribute_definitions()

        assert 'Found **1 grouping attribute definition(s)**' in result
        assert 'Region' in result
        # Should not contain "Source Keys:" or "Default Value:" for this entry
        assert 'Source Keys' not in result
        assert 'Default Value' not in result

    @pytest.mark.asyncio
    async def test_tips_with_results(self, mock_aws_clients):
        """Test that actionable tips are shown when definitions exist."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.return_value = {
            'GroupingAttributeDefinitions': [
                {
                    'GroupingName': 'Team',
                    'GroupingSourceKeys': ['aws:tag:Team'],
                },
            ],
        }

        result = await list_grouping_attribute_definitions()

        assert 'list_group_services' in result
        assert 'audit_group_health' in result

    @pytest.mark.asyncio
    async def test_client_error_access_denied(self, mock_aws_clients):
        """Test handling of AccessDeniedException."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized',
                }
            },
            operation_name='ListGroupingAttributeDefinitions',
        )

        result = await list_grouping_attribute_definitions()

        assert 'Error: AccessDeniedException - User is not authorized' in result

    @pytest.mark.asyncio
    async def test_client_error_validation(self, mock_aws_clients):
        """Test handling of ValidationException."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'Invalid parameter',
                }
            },
            operation_name='ListGroupingAttributeDefinitions',
        )

        result = await list_grouping_attribute_definitions()

        assert 'Error: ValidationException - Invalid parameter' in result

    @pytest.mark.asyncio
    async def test_general_exception(self, mock_aws_clients):
        """Test handling of unexpected exceptions."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.side_effect = Exception('Unexpected error occurred')

        result = await list_grouping_attribute_definitions()

        assert 'Error: Unexpected error occurred' in result

    @pytest.mark.asyncio
    async def test_multiple_source_keys_formatting(self, mock_aws_clients):
        """Test that multiple source keys are formatted correctly."""
        mock_aws_clients[
            'applicationsignals_client'
        ].list_grouping_attribute_definitions.return_value = {
            'GroupingAttributeDefinitions': [
                {
                    'GroupingName': 'CostCenter',
                    'GroupingSourceKeys': [
                        'aws:tag:CostCenter',
                        'otel.resource.cost_center',
                        'custom.attribute.cc',
                    ],
                },
            ],
        }

        result = await list_grouping_attribute_definitions()

        assert 'aws:tag:CostCenter, otel.resource.cost_center, custom.attribute.cc' in result
