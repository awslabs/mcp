"""Tests for CloudWatch Application Signals MCP Server."""

import json
import pytest
from awslabs.cloudwatch_appsignals_mcp_server.server import _filter_operation_targets, main
from awslabs.cloudwatch_appsignals_mcp_server.service_tools import (
    get_service_detail,
    list_monitored_services,
    query_service_metrics,
)
from awslabs.cloudwatch_appsignals_mcp_server.slo_tools import get_slo
from awslabs.cloudwatch_appsignals_mcp_server.trace_tools import (
    check_transaction_search_enabled,
    get_trace_summaries_paginated,
    list_slis,
    query_sampled_traces,
    search_transaction_spans,
)
from awslabs.cloudwatch_appsignals_mcp_server.utils import remove_null_values
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    # Create mock clients
    mock_logs_client = MagicMock()
    mock_appsignals_client = MagicMock()
    mock_cloudwatch_client = MagicMock()
    mock_xray_client = MagicMock()
    mock_synthetics_client = MagicMock()
    mock_s3_client = MagicMock()

    # Patch the clients in all modules where they're imported
    patches = [
        # Original aws_clients module
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.logs_client', mock_logs_client
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.cloudwatch_client',
            mock_cloudwatch_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.xray_client', mock_xray_client
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.synthetics_client',
            mock_synthetics_client,
        ),
        patch('awslabs.cloudwatch_appsignals_mcp_server.aws_clients.s3_client', mock_s3_client),
        # Service tools module (check what's actually imported)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_tools.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_tools.cloudwatch_client',
            mock_cloudwatch_client,
        ),
        # SLO tools module (check what's actually imported)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.slo_tools.appsignals_client',
            mock_appsignals_client,
        ),
        # Trace tools module (logs_client, xray_client, and appsignals_client are imported)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.logs_client', mock_logs_client
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.xray_client', mock_xray_client
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.appsignals_client',
            mock_appsignals_client,
        ),
        # SLI report client module (appsignals_client and cloudwatch_client are imported)
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.sli_report_client.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.sli_report_client.cloudwatch_client',
            mock_cloudwatch_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.synthetics_client',
            mock_synthetics_client,
        ),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.s3_client', mock_s3_client),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.iam_client', MagicMock()),
    ]

    # Start all patches
    for p in patches:
        p.start()

    try:
        yield {
            'logs_client': mock_logs_client,
            'appsignals_client': mock_appsignals_client,
            'cloudwatch_client': mock_cloudwatch_client,
            'xray_client': mock_xray_client,
            'synthetics_client': mock_synthetics_client,
            's3_client': mock_s3_client,
        }
    finally:
        # Stop all patches
        for p in patches:
            p.stop()


@pytest.fixture
def mock_mcp():
    """Mock the FastMCP instance."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock:
        yield mock


@pytest.mark.asyncio
async def test_list_monitored_services_success(mock_aws_clients):
    """Test successful listing of monitored services."""
    mock_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                    'Environment': 'production',
                }
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_response

    result = await list_monitored_services()

    assert 'Application Signals Services (1 total)' in result
    assert 'test-service' in result
    assert 'AWS::ECS::Service' in result


@pytest.mark.asyncio
async def test_list_monitored_services_empty(mock_aws_clients):
    """Test when no services are found."""
    mock_response = {'ServiceSummaries': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_response

    result = await list_monitored_services()

    assert result == 'No services found in Application Signals.'


@pytest.mark.asyncio
async def test_get_service_detail_success(mock_aws_clients):
    """Test successful retrieval of service details."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'},
            'AttributeMaps': [{'Platform': 'ECS', 'Application': 'test-app'}],
            'MetricReferences': [
                {
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricName': 'Latency',
                    'MetricType': 'GAUGE',
                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                }
            ],
            'LogGroupReferences': [{'Identifier': '/aws/ecs/test-service'}],
        }
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response

    result = await get_service_detail('test-service')

    assert 'Service Details: test-service' in result
    assert 'AWS::ECS::Service' in result
    assert 'Platform: ECS' in result
    assert 'AWS/ApplicationSignals/Latency' in result
    assert '/aws/ecs/test-service' in result


@pytest.mark.asyncio
async def test_get_service_detail_not_found(mock_aws_clients):
    """Test when service is not found."""
    mock_response = {'ServiceSummaries': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_response

    result = await get_service_detail('nonexistent-service')

    assert "Service 'nonexistent-service' not found" in result


@pytest.mark.asyncio
async def test_query_service_metrics_success(mock_aws_clients):
    """Test successful query of service metrics."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'MetricReferences': [
                {
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricName': 'Latency',
                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                }
            ]
        }
    }

    mock_metric_response = {
        'Datapoints': [
            {
                'Timestamp': datetime.now(timezone.utc),
                'Average': 100.5,
                'p99': 150.2,
                'Unit': 'Milliseconds',
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response
    mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = mock_metric_response

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert 'Metrics for test-service - Latency' in result
    assert 'Average Statistics:' in result
    assert 'p99 Statistics:' in result


@pytest.mark.asyncio
async def test_query_service_metrics_list_available(mock_aws_clients):
    """Test listing available metrics when no specific metric is requested."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'MetricReferences': [
                {
                    'MetricName': 'Latency',
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricType': 'GAUGE',
                },
                {
                    'MetricName': 'Error',
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricType': 'COUNT',
                },
            ]
        }
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='',  # Empty to list available metrics
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert "Available metrics for service 'test-service'" in result
    assert 'Latency' in result
    assert 'Error' in result


@pytest.mark.asyncio
async def test_get_slo_success(mock_aws_clients):
    """Test successful retrieval of SLO details."""
    mock_slo_response = {
        'Slo': {
            'Name': 'test-slo',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
            'Description': 'Test SLO for latency',
            'EvaluationType': 'REQUEST_BASED',
            'CreatedTime': '2024-01-01T00:00:00Z',
            'LastUpdatedTime': '2024-01-02T00:00:00Z',
            'Goal': {
                'AttainmentGoal': 99.9,
                'WarningThreshold': 99.0,
                'Interval': {'RollingInterval': {'Duration': 7, 'DurationUnit': 'DAYS'}},
            },
            'RequestBasedSli': {
                'RequestBasedSliMetric': {
                    'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'},
                    'OperationName': 'GET /api/test',
                    'MetricType': 'LATENCY',
                    'MetricDataQueries': [
                        {
                            'Id': 'query1',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApplicationSignals',
                                    'MetricName': 'Latency',
                                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                                },
                                'Period': 60,
                                'Stat': 'Average',
                            },
                        }
                    ],
                },
                'MetricThreshold': 1000,
                'ComparisonOperator': 'GreaterThan',
            },
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo('test-slo-id')

    assert 'Service Level Objective Details' in result
    assert 'test-slo' in result
    assert 'REQUEST_BASED' in result
    assert '99.9%' in result
    assert 'GET /api/test' in result
    assert 'annotation[aws.local.operation]="GET /api/test"' in result


@pytest.mark.asyncio
async def test_get_slo_not_found(mock_aws_clients):
    """Test when SLO is not found."""
    mock_aws_clients['appsignals_client'].get_service_level_objective.return_value = {'Slo': None}

    result = await get_slo('nonexistent-slo')

    assert 'No SLO found with ID: nonexistent-slo' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_success(mock_aws_clients):
    """Test successful transaction search."""
    mock_query_response = {
        'queryId': 'test-query-id',
        'status': 'Complete',
        'statistics': {'recordsMatched': 10},
        'results': [
            [
                {'field': 'spanId', 'value': 'span1'},
                {'field': 'timestamp', 'value': '2024-01-01T00:00:00Z'},
            ]
        ],
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'test-query-id'}
        mock_aws_clients['logs_client'].get_query_results.return_value = mock_query_response

        result = await search_transaction_spans(
            log_group_name='aws/spans',
            start_time='2024-01-01T00:00:00+00:00',  # Fixed ISO format
            end_time='2024-01-01T01:00:00+00:00',
            query_string='fields @timestamp, spanId',
            limit=100,
            max_timeout=30,
        )

        assert result['status'] == 'Complete'
        assert result['queryId'] == 'test-query-id'
        assert len(result['results']) == 1
        assert result['results'][0]['spanId'] == 'span1'


@pytest.mark.asyncio
async def test_search_transaction_spans_not_enabled(mock_aws_clients):
    """Test when transaction search is not enabled."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (False, 'XRay', 'INACTIVE')

        result = await search_transaction_spans(
            log_group_name='',
            start_time='2024-01-01T00:00:00+00:00',
            end_time='2024-01-01T01:00:00+00:00',
            query_string='fields @timestamp',
            limit=None,
            max_timeout=30,
        )

        assert result['status'] == 'Transaction Search Not Available'
        assert not result['transaction_search_status']['enabled']


@pytest.mark.asyncio
async def test_list_slis_success(mock_aws_clients):
    """Test successful listing of SLI status."""
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                    'Environment': 'production',
                }
            }
        ]
    }

    # Mock boto3.client calls in SLIReportClient
    with patch('boto3.client') as mock_boto3_client:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
        ) as mock_check:
            # Configure boto3.client to return our mocked clients
            def boto3_client_side_effect(service_name, **kwargs):
                if service_name == 'application-signals':
                    return mock_aws_clients['appsignals_client']
                elif service_name == 'cloudwatch':
                    return mock_aws_clients['cloudwatch_client']
                else:
                    return MagicMock()

            mock_boto3_client.side_effect = boto3_client_side_effect

            mock_aws_clients[
                'appsignals_client'
            ].list_services.return_value = mock_services_response
            mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')

            # Mock SLO summaries response for SLIReportClient
            mock_slo_response = {
                'SloSummaries': [
                    {
                        'Name': 'test-slo',
                        'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
                        'KeyAttributes': {'Name': 'test-service'},
                        'OperationName': 'GET /api',
                        'CreatedTime': datetime.now(timezone.utc),
                    }
                ]
            }
            mock_aws_clients[
                'appsignals_client'
            ].list_service_level_objectives.return_value = mock_slo_response

            # Mock metric data response showing breach
            mock_metric_response = {
                'MetricDataResults': [
                    {
                        'Id': 'slo0',
                        'Timestamps': [datetime.now(timezone.utc)],
                        'Values': [1.0],  # Breach count > 0 indicates breach
                    }
                ]
            }
            mock_aws_clients[
                'cloudwatch_client'
            ].get_metric_data.return_value = mock_metric_response

            result = await list_slis(hours=24)

            assert 'SLI Status Report - Last 24 hours' in result
            assert 'Transaction Search: ENABLED' in result
            assert 'BREACHED SERVICES:' in result
            assert 'test-service' in result


@pytest.mark.asyncio
async def test_query_sampled_traces_success(mock_aws_clients):
    """Test successful query of sampled traces."""
    mock_traces = [
        {
            'Id': 'trace1',
            'Duration': 0.5,
            'ResponseTime': 500,
            'HasError': False,
            'HasFault': True,
            'HasThrottle': False,
            'Http': {'HttpStatus': 500},
            'FaultRootCauses': [
                {
                    'Services': [
                        {
                            'Name': 'test-service',
                            'Exceptions': [{'Message': 'Internal server error'}],
                        }
                    ]
                }
            ],
        }
    ]

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_get_traces:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
        ) as mock_check:
            mock_get_traces.return_value = mock_traces
            mock_check.return_value = (False, 'XRay', 'INACTIVE')

            result_json = await query_sampled_traces(
                start_time='2024-01-01T00:00:00Z',
                end_time='2024-01-01T01:00:00Z',
                filter_expression='service("test-service"){fault = true}',
            )

            result = json.loads(result_json)
            assert result['TraceCount'] == 1
            assert result['TraceSummaries'][0]['Id'] == 'trace1'
            assert result['TraceSummaries'][0]['HasFault'] is True


@pytest.mark.asyncio
async def test_query_sampled_traces_time_window_too_large(mock_aws_clients):
    """Test when time window is too large."""
    result_json = await query_sampled_traces(
        start_time='2024-01-01T00:00:00Z',
        end_time='2024-01-02T00:00:00Z',  # 24 hours > 6 hours max
        filter_expression='service("test-service")',
    )

    result = json.loads(result_json)
    assert 'error' in result
    assert 'Time window too large' in result['error']


def test_get_trace_summaries_paginated():
    """Test paginated trace retrieval."""
    mock_client = MagicMock()
    mock_responses = [
        {'TraceSummaries': [{'Id': 'trace1'}, {'Id': 'trace2'}], 'NextToken': 'token1'},
        {'TraceSummaries': [{'Id': 'trace3'}]},
    ]
    mock_client.get_trace_summaries.side_effect = mock_responses

    start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    end_time = datetime.now(timezone.utc)

    traces = get_trace_summaries_paginated(
        mock_client, start_time, end_time, 'service("test")', max_traces=10
    )

    assert len(traces) == 3
    assert traces[0]['Id'] == 'trace1'
    assert traces[2]['Id'] == 'trace3'


def test_get_trace_summaries_paginated_with_error():
    """Test paginated trace retrieval with error."""
    mock_client = MagicMock()
    mock_client.get_trace_summaries.side_effect = Exception('API Error')

    start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    end_time = datetime.now(timezone.utc)

    traces = get_trace_summaries_paginated(
        mock_client, start_time, end_time, 'service("test")', max_traces=10
    )

    assert len(traces) == 0  # Should return empty list on error


def test_check_transaction_search_enabled(mock_aws_clients):
    """Test checking transaction search status."""
    mock_aws_clients['xray_client'].get_trace_segment_destination.return_value = {
        'Destination': 'CloudWatchLogs',
        'Status': 'ACTIVE',
    }

    is_enabled, destination, status = check_transaction_search_enabled()

    assert is_enabled is True
    assert destination == 'CloudWatchLogs'
    assert status == 'ACTIVE'


def test_check_transaction_search_enabled_not_active(mock_aws_clients):
    """Test checking transaction search when not active."""
    mock_aws_clients['xray_client'].get_trace_segment_destination.return_value = {
        'Destination': 'XRay',
        'Status': 'INACTIVE',
    }

    is_enabled, destination, status = check_transaction_search_enabled()

    assert is_enabled is False
    assert destination == 'XRay'
    assert status == 'INACTIVE'


def test_check_transaction_search_enabled_error(mock_aws_clients):
    """Test checking transaction search with error."""
    mock_aws_clients['xray_client'].get_trace_segment_destination.side_effect = Exception(
        'API Error'
    )

    is_enabled, destination, status = check_transaction_search_enabled()

    assert is_enabled is False
    assert destination == 'Unknown'
    assert status == 'Error'


def test_remove_null_values():
    """Test remove_null_values function."""
    # Test with mix of None and non-None values
    input_dict = {
        'key1': 'value1',
        'key2': None,
        'key3': 'value3',
        'key4': None,
        'key5': 0,  # Should not be removed
        'key6': '',  # Should not be removed
        'key7': False,  # Should not be removed
    }

    result = remove_null_values(input_dict)

    assert result == {
        'key1': 'value1',
        'key3': 'value3',
        'key5': 0,
        'key6': '',
        'key7': False,
    }
    assert 'key2' not in result
    assert 'key4' not in result


@pytest.mark.asyncio
async def test_list_monitored_services_client_error(mock_aws_clients):
    """Test ClientError handling in list_monitored_services."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this action',
            }
        },
        operation_name='ListServices',
    )

    result = await list_monitored_services()

    assert 'AWS Error: User is not authorized to perform this action' in result


@pytest.mark.asyncio
async def test_list_monitored_services_general_exception(mock_aws_clients):
    """Test general exception handling in list_monitored_services."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = Exception(
        'Unexpected error occurred'
    )

    result = await list_monitored_services()

    assert 'Error: Unexpected error occurred' in result


@pytest.mark.asyncio
async def test_get_service_detail_client_error(mock_aws_clients):
    """Test ClientError handling in get_service_detail."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Service not found in Application Signals',
            }
        },
        operation_name='GetService',
    )

    result = await get_service_detail('test-service')

    assert 'AWS Error: Service not found in Application Signals' in result


@pytest.mark.asyncio
async def test_get_service_detail_general_exception(mock_aws_clients):
    """Test general exception handling in get_service_detail."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.side_effect = Exception(
        'Unexpected error in get_service'
    )

    result = await get_service_detail('test-service')

    assert 'Error: Unexpected error in get_service' in result


@pytest.mark.asyncio
async def test_query_service_metrics_no_datapoints(mock_aws_clients):
    """Test query service metrics when no datapoints are returned."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'MetricReferences': [
                {
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricName': 'Latency',
                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                }
            ]
        }
    }

    mock_metric_response = {'Datapoints': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response
    mock_aws_clients['cloudwatch_client'].get_metric_statistics.return_value = mock_metric_response

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert 'No data points found' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_timeout(mock_aws_clients):
    """Test search transaction spans with timeout."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.trace_tools.timer') as mock_timer:
            # Mock asyncio.sleep to prevent actual waiting
            with patch('asyncio.sleep', new_callable=AsyncMock):
                mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
                mock_aws_clients['logs_client'].start_query.return_value = {
                    'queryId': 'test-query-id'
                }
                mock_aws_clients['logs_client'].get_query_results.return_value = {
                    'status': 'Running'
                }

                # Simulate timeout by making timer exceed max_timeout
                mock_timer.side_effect = [
                    0,
                    0,
                    0,
                    31,
                    31,
                ]  # start_time_perf, poll_start, poll check 1, poll check 2

                result = await search_transaction_spans(
                    log_group_name='',
                    start_time='2024-01-01T00:00:00+00:00',
                    end_time='2024-01-01T01:00:00+00:00',
                    query_string='fields @timestamp',
                    limit=None,
                    max_timeout=30,
                )

                assert result['status'] == 'Polling Timeout'
                assert 'did not complete within 30 seconds' in result['message']


def test_main_normal_execution(mock_mcp):
    """Test normal execution of main function."""
    main()
    mock_mcp.run.assert_called_once_with(transport='stdio')


def test_main_keyboard_interrupt(mock_mcp):
    """Test KeyboardInterrupt handling in main function."""
    mock_mcp.run.side_effect = KeyboardInterrupt()
    # Should not raise an exception
    main()
    mock_mcp.run.assert_called_once_with(transport='stdio')


def test_main_general_exception(mock_mcp):
    """Test general exception handling in main function."""
    mock_mcp.run.side_effect = Exception('Server error')
    with pytest.raises(Exception, match='Server error'):
        main()
    mock_mcp.run.assert_called_once_with(transport='stdio')


@pytest.mark.asyncio
async def test_get_slo_period_based(mock_aws_clients):
    """Test get_slo with period-based SLI configuration."""
    mock_slo_response = {
        'Slo': {
            'Name': 'test-slo-period',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
            'EvaluationType': 'PERIOD_BASED',
            'Sli': {
                'SliMetric': {
                    'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::Lambda::Function'},
                    'OperationName': 'ProcessOrder',
                    'MetricType': 'AVAILABILITY',
                    'DependencyConfig': {
                        'DependencyKeyAttributes': {'Name': 'payment-service'},
                        'DependencyOperationName': 'ProcessPayment',
                    },
                },
                'MetricThreshold': 0.99,
                'ComparisonOperator': 'LessThan',
            },
            'BurnRateConfigurations': [
                {'LookBackWindowMinutes': 5},
                {'LookBackWindowMinutes': 60},
            ],
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo('test-slo-period')

    assert 'PERIOD_BASED' in result
    assert 'ProcessOrder' in result
    assert 'annotation[aws.remote.operation]="ProcessPayment"' in result
    assert 'Burn Rate Configurations' in result


@pytest.mark.asyncio
async def test_list_slis_with_error_in_sli_client(mock_aws_clients):
    """Test list_slis when SLIReportClient throws error for some services."""
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service-1',
                    'Type': 'AWS::ECS::Service',
                    'Environment': 'production',
                }
            },
            {
                'KeyAttributes': {
                    'Name': 'test-service-2',
                    'Type': 'AWS::Lambda::Function',
                    'Environment': 'staging',
                }
            },
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.SLIReportClient'
    ) as mock_sli_client:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
        ) as mock_check:
            mock_aws_clients[
                'appsignals_client'
            ].list_services.return_value = mock_services_response
            mock_check.return_value = (False, 'XRay', 'INACTIVE')

            # First service succeeds, second fails
            mock_report = MagicMock()
            mock_report.breached_slo_count = 0
            mock_report.ok_slo_count = 3
            mock_report.total_slo_count = 3
            mock_report.sli_status = 'OK'
            mock_report.start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            mock_report.end_time = datetime.now(timezone.utc)

            mock_sli_client.return_value.generate_sli_report.side_effect = [
                mock_report,
                Exception('Failed to get SLI report'),
            ]

            result = await list_slis(hours=24)

            assert 'Transaction Search: NOT ENABLED' in result
            assert 'HEALTHY SERVICES:' in result
            assert 'INSUFFICIENT DATA:' in result
            assert 'test-service-1' in result
            assert 'test-service-2' in result


@pytest.mark.asyncio
async def test_query_service_metrics_service_not_found(mock_aws_clients):
    """Test query service metrics when service is not found."""
    mock_list_response = {'ServiceSummaries': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response

    result = await query_service_metrics(
        service_name='nonexistent-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert "Service 'nonexistent-service' not found" in result


@pytest.mark.asyncio
async def test_query_service_metrics_no_metrics(mock_aws_clients):
    """Test query service metrics when service has no metrics."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {'Service': {'MetricReferences': []}}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert "No metrics found for service 'test-service'" in result


@pytest.mark.asyncio
async def test_query_service_metrics_metric_not_found(mock_aws_clients):
    """Test query service metrics when specific metric is not found."""
    mock_list_response = {
        'ServiceSummaries': [
            {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
        ]
    }

    mock_get_response = {
        'Service': {
            'MetricReferences': [
                {
                    'Namespace': 'AWS/ApplicationSignals',
                    'MetricName': 'Error',
                    'Dimensions': [{'Name': 'Service', 'Value': 'test-service'}],
                }
            ]
        }
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
    mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',  # Looking for Latency but only Error exists
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert "Metric 'Latency' not found" in result
    assert 'Available: Error' in result


@pytest.mark.asyncio
async def test_query_service_metrics_client_error(mock_aws_clients):
    """Test query service metrics with client error."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized',
            }
        },
        operation_name='ListServices',
    )

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert 'AWS Error: User is not authorized' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_failed_query(mock_aws_clients):
    """Test search transaction spans when query fails."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'test-query-id'}
        mock_aws_clients['logs_client'].get_query_results.return_value = {
            'queryId': 'test-query-id',
            'status': 'Failed',
            'statistics': {'error': 'Query syntax error'},
        }

        result = await search_transaction_spans(
            log_group_name='',
            start_time='2024-01-01T00:00:00+00:00',
            end_time='2024-01-01T01:00:00+00:00',
            query_string='invalid query',
            limit=None,
            max_timeout=30,
        )

        assert result['status'] == 'Failed'


@pytest.mark.asyncio
async def test_get_slo_client_error(mock_aws_clients):
    """Test get_slo with client error."""
    mock_aws_clients['appsignals_client'].get_service_level_objective.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'SLO not found',
            }
        },
        operation_name='GetServiceLevelObjective',
    )

    result = await get_slo('test-slo-id')

    assert 'AWS Error: SLO not found' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_empty_log_group(mock_aws_clients):
    """Test search transaction spans with empty log group defaults to aws/spans."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'test-query-id'}
        mock_aws_clients['logs_client'].get_query_results.return_value = {
            'queryId': 'test-query-id',
            'status': 'Complete',
            'results': [],
        }

        await search_transaction_spans(
            log_group_name='',  # Empty string should default to 'aws/spans'
            start_time='2024-01-01T00:00:00+00:00',
            end_time='2024-01-01T01:00:00+00:00',
            query_string='fields @timestamp',
            limit=None,
            max_timeout=30,
        )

        # Verify start_query was called with default 'aws/spans'
        mock_aws_clients['logs_client'].start_query.assert_called()
        call_args = mock_aws_clients['logs_client'].start_query.call_args[1]
        assert 'aws/spans' in call_args['logGroupNames']


@pytest.mark.asyncio
async def test_list_slis_no_services(mock_aws_clients):
    """Test list_slis when no services exist."""
    mock_aws_clients['appsignals_client'].list_services.return_value = {'ServiceSummaries': []}

    result = await list_slis(hours=24)

    assert 'No services found in Application Signals.' in result


@pytest.mark.asyncio
async def test_get_slo_with_calendar_interval(mock_aws_clients):
    """Test get_slo with calendar interval in goal."""
    mock_slo_response = {
        'Slo': {
            'Name': 'test-slo-calendar',
            'Goal': {
                'AttainmentGoal': 99.5,
                'Interval': {
                    'CalendarInterval': {
                        'Duration': 1,
                        'DurationUnit': 'MONTH',
                        'StartTime': '2024-01-01T00:00:00Z',
                    }
                },
            },
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo('test-slo-calendar')

    assert 'Calendar 1 MONTH starting 2024-01-01T00:00:00Z' in result


@pytest.mark.asyncio
async def test_query_service_metrics_different_periods(mock_aws_clients):
    """Test query service metrics with different time periods."""
    # Test data for different hour ranges
    test_cases = [
        (2, 60),  # 2 hours -> 1 minute period
        (12, 300),  # 12 hours -> 5 minute period
        (48, 3600),  # 48 hours -> 1 hour period
    ]

    for hours, expected_period in test_cases:
        mock_list_response = {
            'ServiceSummaries': [
                {'KeyAttributes': {'Name': 'test-service', 'Type': 'AWS::ECS::Service'}}
            ]
        }

        mock_get_response = {
            'Service': {
                'MetricReferences': [
                    {
                        'Namespace': 'AWS/ApplicationSignals',
                        'MetricName': 'Latency',
                        'Dimensions': [],
                    }
                ]
            }
        }

        mock_metric_response = {
            'Datapoints': [{'Timestamp': datetime.now(timezone.utc), 'Average': 100.0}]
        }

        mock_aws_clients['appsignals_client'].list_services.return_value = mock_list_response
        mock_aws_clients['appsignals_client'].get_service.return_value = mock_get_response
        mock_aws_clients[
            'cloudwatch_client'
        ].get_metric_statistics.return_value = mock_metric_response

        await query_service_metrics(
            service_name='test-service',
            metric_name='Latency',
            statistic='Average',
            extended_statistic='p99',
            hours=hours,
        )

        # Verify the period was set correctly
        call_args = mock_aws_clients['cloudwatch_client'].get_metric_statistics.call_args[1]
        assert call_args['Period'] == expected_period


@pytest.mark.asyncio
async def test_query_service_metrics_general_exception(mock_aws_clients):
    """Test query service metrics with unexpected exception."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = Exception('Unexpected error')

    result = await query_service_metrics(
        service_name='test-service',
        metric_name='Latency',
        statistic='Average',
        extended_statistic='p99',
        hours=1,
    )

    assert 'Error: Unexpected error' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_general_exception(mock_aws_clients):
    """Test search transaction spans with general exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.side_effect = Exception('Query failed')

        with pytest.raises(Exception) as exc_info:
            await search_transaction_spans(
                log_group_name='aws/spans',
                start_time='2024-01-01T00:00:00+00:00',
                end_time='2024-01-01T01:00:00+00:00',
                query_string='fields @timestamp',
                limit=100,
                max_timeout=30,
            )

        assert 'Query failed' in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_monitored_services_with_attributes_branch(mock_aws_clients):
    """Test list_monitored_services with key attributes that trigger the branch."""
    mock_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {}  # Empty attributes to test the branch
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_response

    result = await list_monitored_services()

    assert 'Application Signals Services (1 total)' in result
    assert 'Key Attributes:' not in result  # Should not show when empty


@pytest.mark.asyncio
async def test_get_trace_summaries_paginated_with_limit(mock_aws_clients):
    """Test get_trace_summaries_paginated when it hits the max_traces limit."""
    # Mock responses with more traces than the limit
    mock_response_1 = {
        'TraceSummaries': [{'Id': f'trace-{i}', 'Duration': 100} for i in range(10)],
        'NextToken': 'token1',
    }
    mock_response_2 = {
        'TraceSummaries': [{'Id': f'trace-{i}', 'Duration': 100} for i in range(10, 15)]
    }

    mock_aws_clients['xray_client'].get_trace_summaries.side_effect = [
        mock_response_1,
        mock_response_2,
    ]

    # Test with max_traces=12
    traces = get_trace_summaries_paginated(
        mock_aws_clients['xray_client'],
        datetime.now(timezone.utc),
        datetime.now(timezone.utc),
        'service("test")',
        max_traces=12,
    )

    # The function continues until it gets all traces from the current page
    # before checking the limit, so we might get more than max_traces
    assert len(traces) >= 12  # Should have at least the limit


@pytest.mark.asyncio
async def test_get_slo_with_period_based_sli_full_details(mock_aws_clients):
    """Test get_slo with comprehensive period-based SLI configuration."""
    mock_response = {
        'Slo': {
            'Name': 'test-slo',
            'Arn': 'arn:aws:slo:test',
            'Description': 'Test SLO',
            'EvaluationType': 'PERIOD_BASED',
            'CreatedTime': datetime.now(timezone.utc),
            'LastUpdatedTime': datetime.now(timezone.utc),
            'Goal': {
                'AttainmentGoal': 99.9,
                'WarningThreshold': 95,
                'Interval': {
                    'CalendarInterval': {
                        'Duration': 1,
                        'DurationUnit': 'MONTH',
                        'StartTime': datetime.now(timezone.utc),
                    }
                },
            },
            'Sli': {
                'SliMetric': {
                    'KeyAttributes': {'Service': 'test-service', 'Environment': 'prod'},
                    'OperationName': 'GetItem',
                    'MetricType': 'LATENCY',
                    'MetricDataQueries': [
                        {
                            'Id': 'query1',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApplicationSignals',
                                    'MetricName': 'Latency',
                                    'Dimensions': [
                                        {'Name': 'Service', 'Value': 'test-service'},
                                        {'Name': 'Operation', 'Value': 'GetItem'},
                                    ],
                                },
                                'Period': 300,
                                'Stat': 'p99',
                                'Unit': 'Milliseconds',
                            },
                            'ReturnData': True,
                        },
                        {'Id': 'query2', 'Expression': 'query1 * 2', 'ReturnData': False},
                    ],
                    'DependencyConfig': {
                        'DependencyKeyAttributes': {
                            'RemoteService': 'downstream-service',
                            'RemoteEnvironment': 'prod',
                        },
                        'DependencyOperationName': 'ProcessRequest',
                    },
                },
                'MetricThreshold': 1000,
                'ComparisonOperator': 'LessThan',
            },
            'BurnRateConfigurations': [
                {'LookBackWindowMinutes': 5},
                {'LookBackWindowMinutes': 60},
            ],
        }
    }

    mock_aws_clients['appsignals_client'].get_service_level_objective.return_value = mock_response

    result = await get_slo('test-slo-id')

    # Verify all sections are present
    assert 'Service Level Objective Details' in result
    assert 'Goal Configuration' in result
    assert 'Calendar 1 MONTH' in result
    assert 'Period-Based SLI Configuration' in result
    assert 'Key Attributes:' in result
    assert 'Service: test-service' in result
    assert 'Operation Name: GetItem' in result
    assert 'Metric Data Queries:' in result
    assert 'Query ID: query1' in result
    assert 'Namespace: AWS/ApplicationSignals' in result
    assert 'Dimensions:' in result
    assert 'Expression: query1 * 2' in result
    assert 'ReturnData: False' in result
    assert 'Dependency Configuration:' in result
    assert 'RemoteService: downstream-service' in result
    assert 'Dependency Operation: ProcessRequest' in result
    assert 'Burn Rate Configurations:' in result


@pytest.mark.asyncio
async def test_get_slo_with_request_based_sli_full_details(mock_aws_clients):
    """Test get_slo with comprehensive request-based SLI configuration."""
    mock_response = {
        'Slo': {
            'Name': 'test-slo-rbs',
            'Arn': 'arn:aws:slo:test-rbs',
            'Goal': {
                'AttainmentGoal': 99.5,
                'Interval': {'RollingInterval': {'Duration': 7, 'DurationUnit': 'DAY'}},
            },
            'RequestBasedSli': {
                'RequestBasedSliMetric': {
                    'KeyAttributes': {'Service': 'api-service', 'Type': 'AWS::Lambda::Function'},
                    'OperationName': 'ProcessOrder',
                    'MetricType': 'AVAILABILITY',
                    'MetricDataQueries': [
                        {
                            'Id': 'success',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Success',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': 'process-order'}
                                    ],
                                },
                                'Period': 60,
                                'Stat': 'Sum',
                            },
                        },
                        {
                            'Id': 'errors',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Errors',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': 'process-order'}
                                    ],
                                },
                                'Period': 60,
                                'Stat': 'Sum',
                                'Unit': 'Count',
                            },
                        },
                        {'Id': 'availability', 'Expression': 'success / (success + errors) * 100'},
                    ],
                    'DependencyConfig': {
                        'DependencyKeyAttributes': {'Database': 'orders-db'},
                        'DependencyOperationName': 'Query',
                    },
                },
                'MetricThreshold': 99.0,
                'ComparisonOperator': 'GreaterThan',
            },
        }
    }

    mock_aws_clients['appsignals_client'].get_service_level_objective.return_value = mock_response

    result = await get_slo('test-slo-rbs-id')

    # Verify request-based sections
    assert 'Request-Based SLI Configuration:' in result
    assert 'api-service' in result
    assert 'ProcessOrder' in result
    assert 'AVAILABILITY' in result
    assert 'Expression: success / (success + errors) * 100' in result
    assert 'Dependency Configuration:' in result
    assert 'Database: orders-db' in result
    assert 'Unit: Count' in result


@pytest.mark.asyncio
async def test_get_slo_general_exception(mock_aws_clients):
    """Test get_slo with general exception."""
    mock_aws_clients['appsignals_client'].get_service_level_objective.side_effect = Exception(
        'Unexpected error'
    )

    result = await get_slo('test-slo-id')

    assert 'Error: Unexpected error' in result


@pytest.mark.asyncio
async def test_search_transaction_spans_with_none_log_group(mock_aws_clients):
    """Test search_transaction_spans when log_group_name is None."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'test-query-id'}
        mock_aws_clients['logs_client'].get_query_results.return_value = {
            'queryId': 'test-query-id',
            'status': 'Complete',
            'results': [],
        }

        # Pass None for log_group_name to test the default handling
        await search_transaction_spans(
            log_group_name=None,  # type: ignore
            start_time='2024-01-01T00:00:00+00:00',
            end_time='2024-01-01T01:00:00+00:00',
            query_string='fields @timestamp',
            limit=100,
            max_timeout=30,
        )

        # Verify it used the default log group
        call_args = mock_aws_clients['logs_client'].start_query.call_args[1]
        assert 'aws/spans' in call_args['logGroupNames']


@pytest.mark.asyncio
async def test_search_transaction_spans_complete_with_statistics(mock_aws_clients):
    """Test search_transaction_spans when query completes with detailed statistics."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.check_transaction_search_enabled'
    ) as mock_check:
        mock_check.return_value = (True, 'CloudWatchLogs', 'ACTIVE')
        mock_aws_clients['logs_client'].start_query.return_value = {'queryId': 'test-query-id'}

        # First return Running, then Complete
        mock_aws_clients['logs_client'].get_query_results.side_effect = [
            {'queryId': 'test-query-id', 'status': 'Running'},
            {
                'queryId': 'test-query-id',
                'status': 'Complete',
                'statistics': {
                    'recordsMatched': 100,
                    'recordsScanned': 1000,
                    'bytesScanned': 50000,
                },
                'results': [
                    [
                        {'field': 'spanId', 'value': 'span1'},
                        {'field': '@timestamp', 'value': '2024-01-01 00:00:00'},
                    ]
                ],
            },
        ]

        result = await search_transaction_spans(
            log_group_name='aws/spans',
            start_time='2024-01-01T00:00:00+00:00',
            end_time='2024-01-01T01:00:00+00:00',
            query_string='fields @timestamp, spanId',
            limit=100,
            max_timeout=30,
        )

        assert result['status'] == 'Complete'
        assert result['statistics']['recordsMatched'] == 100
        assert len(result['results']) == 1


@pytest.mark.asyncio
async def test_list_slis_general_exception(mock_aws_clients):
    """Test list_slis with general exception."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = Exception(
        'Service unavailable'
    )

    result = await list_slis(hours=24)

    assert 'Error getting SLI status: Service unavailable' in result


@pytest.mark.asyncio
async def test_query_sampled_traces_with_defaults(mock_aws_clients):
    """Test query_sampled_traces with default start_time and end_time."""
    mock_trace_response = {
        'TraceSummaries': [
            {
                'Id': 'trace1',
                'Duration': 100,
                'HasError': True,
                'ErrorRootCauses': [
                    {
                        'Services': [
                            {
                                'Name': 'test-service',
                                'Names': ['test-service'],
                                'Type': 'AWS::ECS::Service',
                                'AccountId': '123456789012',
                                'EntityPath': [
                                    {'Name': 'test-service', 'Coverage': 1.0, 'Remote': False}
                                ],
                                'Inferred': False,
                            }
                        ],
                        'ClientImpacting': True,
                    }
                ],
            }
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.return_value = mock_trace_response['TraceSummaries']

        # Call without start_time and end_time to test defaults
        result_json = await query_sampled_traces(
            filter_expression='service("test-service")',
            start_time=None,
            end_time=None,
            region='us-east-1',
        )

        result = json.loads(result_json)
        assert result['TraceCount'] == 1
        assert result['TraceSummaries'][0]['HasError'] is True

        # Verify the time window was set to 3 hours
        call_args = mock_paginated.call_args[0]
        time_diff = call_args[2] - call_args[1]  # end_time - start_time
        assert 2.9 < time_diff.total_seconds() / 3600 < 3.1  # Approximately 3 hours


@pytest.mark.asyncio
async def test_query_sampled_traces_with_annotations(mock_aws_clients):
    """Test query_sampled_traces with annotations filtering."""
    mock_trace = {
        'Id': 'trace1',
        'Duration': 100,
        'Annotations': {
            'aws.local.operation': 'GetItem',
            'aws.remote.operation': 'Query',
            'custom.field': 'should-be-filtered',
            'another.field': 'also-filtered',
        },
        'Users': [
            {'UserName': 'user1', 'ServiceIds': []},
            {'UserName': 'user2', 'ServiceIds': []},
            {'UserName': 'user3', 'ServiceIds': []},  # Should be limited to 2
        ],
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.return_value = [mock_trace]

        result_json = await query_sampled_traces(
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-01T01:00:00Z',
            filter_expression='service("test")',
        )

        result = json.loads(result_json)
        trace_summary = result['TraceSummaries'][0]

        # Check annotations were filtered
        assert 'Annotations' in trace_summary
        assert 'aws.local.operation' in trace_summary['Annotations']
        assert 'aws.remote.operation' in trace_summary['Annotations']
        assert 'custom.field' not in trace_summary['Annotations']

        # Check users were limited
        assert len(trace_summary['Users']) == 2


@pytest.mark.asyncio
async def test_query_sampled_traces_with_fault_causes(mock_aws_clients):
    """Test query_sampled_traces with fault root causes."""
    mock_trace = {
        'Id': 'trace1',
        'Duration': 100,
        'HasFault': True,
        'FaultRootCauses': [
            {'Services': [{'Name': 'service1', 'Exceptions': [{'Message': 'Test fault error'}]}]},
            {'Services': [{'Name': 'service2'}]},
            {'Services': [{'Name': 'service3'}]},
            {'Services': [{'Name': 'service4'}]},  # Should be limited to 3
        ],
        'ResponseTimeRootCauses': [{'Services': [{'Name': 'slow-service'}]}],
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.return_value = [mock_trace]

        result_json = await query_sampled_traces(
            start_time='2024-01-01T00:00:00Z', end_time='2024-01-01T01:00:00Z'
        )

        result = json.loads(result_json)
        trace_summary = result['TraceSummaries'][0]

        # Check root causes were limited to 3
        assert len(trace_summary['FaultRootCauses']) == 3
        assert 'ResponseTimeRootCauses' in trace_summary


@pytest.mark.asyncio
async def test_query_sampled_traces_general_exception(mock_aws_clients):
    """Test query_sampled_traces with general exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.side_effect = Exception('Trace query failed')

        result_json = await query_sampled_traces(
            start_time='2024-01-01T00:00:00Z', end_time='2024-01-01T01:00:00Z'
        )

        result = json.loads(result_json)
        assert 'error' in result
        assert 'Trace query failed' in result['error']


@pytest.mark.asyncio
async def test_query_sampled_traces_datetime_conversion(mock_aws_clients):
    """Test query_sampled_traces with datetime objects that need conversion."""
    # The convert_datetime function in server.py only processes top-level fields,
    # not nested datetime objects. Let's test with a datetime at the top level.
    mock_trace = {
        'Id': 'trace1',
        'Duration': 100,
        'Http': {'HttpStatus': 200, 'HttpMethod': 'GET'},
        'StartTime': datetime.now(timezone.utc),  # This will be processed by convert_datetime
        'EndTime': datetime.now(timezone.utc) + timedelta(minutes=1),
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.return_value = [mock_trace]

        result_json = await query_sampled_traces(
            start_time='2024-01-01T00:00:00Z', end_time='2024-01-01T01:00:00Z'
        )

        # Should not raise JSON serialization error
        result = json.loads(result_json)
        assert result['TraceCount'] == 1
        # The datetime fields should have been converted during processing
        trace_summary = result['TraceSummaries'][0]
        assert (
            'StartTime' not in trace_summary
        )  # These fields are not included in the simplified output
        assert 'EndTime' not in trace_summary


@pytest.mark.asyncio
async def test_query_sampled_traces_deduplication(mock_aws_clients):
    """Test query_sampled_traces deduplicates traces with same fault message.

    Note: Only FaultRootCauses are deduplicated, not ErrorRootCauses.
    This is because the primary use case is investigating server faults (5xx errors),
    not client errors (4xx).
    """
    # Create 5 traces with the same fault message
    mock_traces = [
        {
            'Id': f'trace{i}',
            'Duration': 100 + i * 10,
            'ResponseTime': 95 + i * 10,
            'HasFault': True,
            'FaultRootCauses': [
                {
                    'Services': [
                        {
                            'Name': 'test-service',
                            'Exceptions': [{'Message': 'Database connection timeout'}],
                        }
                    ]
                }
            ],
        }
        for i in range(1, 6)
    ]

    # Add 2 traces with ErrorRootCauses (these should NOT be deduplicated)
    mock_traces.extend(
        [
            {
                'Id': 'trace6',
                'Duration': 200,
                'HasError': True,
                'ErrorRootCauses': [
                    {
                        'Services': [
                            {
                                'Name': 'api-service',
                                'Exceptions': [{'Message': 'Invalid API key'}],
                            }
                        ]
                    }
                ],
            },
            {
                'Id': 'trace7',
                'Duration': 210,
                'HasError': True,
                'ErrorRootCauses': [
                    {
                        'Services': [
                            {
                                'Name': 'api-service',
                                'Exceptions': [{'Message': 'Invalid API key'}],
                            }
                        ]
                    }
                ],
            },
        ]
    )

    # Add 2 healthy traces
    mock_traces.extend(
        [
            {
                'Id': 'trace8',
                'Duration': 50,
                'ResponseTime': 45,
                'HasError': False,
                'HasFault': False,
            },
            {
                'Id': 'trace9',
                'Duration': 55,
                'ResponseTime': 50,
                'HasError': False,
                'HasFault': False,
            },
        ]
    )

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.trace_tools.get_trace_summaries_paginated'
    ) as mock_paginated:
        mock_paginated.return_value = mock_traces

        result_json = await query_sampled_traces(
            start_time='2024-01-01T00:00:00Z', end_time='2024-01-01T01:00:00Z'
        )

        result = json.loads(result_json)

        # Verify deduplication worked - should only have 5 traces
        # 1 for database timeout fault (deduplicated from 5)
        # 2 for API key errors (NOT deduplicated - only faults are deduped)
        # 2 healthy traces (not deduplicated)
        assert result['TraceCount'] == 5
        assert len(result['TraceSummaries']) == 5

        # Verify deduplication stats
        assert 'DeduplicationStats' in result
        assert result['DeduplicationStats']['OriginalTraceCount'] == 9
        assert result['DeduplicationStats']['DuplicatesRemoved'] == 4  # 9 - 5 = 4
        assert (
            result['DeduplicationStats']['UniqueFaultMessages'] == 1
        )  # Only counting FaultRootCauses

        # Find the trace with fault
        db_trace = next(
            (
                t
                for t in result['TraceSummaries']
                if t.get('FaultRootCauses')
                and any(
                    'Database connection timeout' in str(s.get('Exceptions', []))
                    for cause in t['FaultRootCauses']
                    for s in cause.get('Services', [])
                )
            ),
            None,
        )
        assert db_trace is not None
        assert db_trace['HasFault'] is True

        # Verify both error traces are present (not deduplicated)
        error_traces = [
            t
            for t in result['TraceSummaries']
            if t.get('ErrorRootCauses')
            and any(
                'Invalid API key' in str(s.get('Exceptions', []))
                for cause in t['ErrorRootCauses']
                for s in cause.get('Services', [])
            )
        ]
        assert len(error_traces) == 2  # Both error traces should be kept
        assert all(t['HasError'] is True for t in error_traces)

        # Verify healthy traces are included
        healthy_count = sum(
            1
            for t in result['TraceSummaries']
            if not t.get('HasError') and not t.get('HasFault') and not t.get('HasThrottle')
        )
        assert healthy_count == 2


def test_main_success(mock_aws_clients):
    """Test main function normal execution."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        main()
        mock_mcp.run.assert_called_once_with(transport='stdio')


def test_main_exception(mock_aws_clients):
    """Test main function with general exception."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        mock_mcp.run.side_effect = Exception('Server error')

        with pytest.raises(Exception) as exc_info:
            main()

        assert 'Server error' in str(exc_info.value)


def test_main_entry_point(mock_aws_clients):
    """Test the if __name__ == '__main__' entry point."""
    # The __main__ block is simple and just calls main()
    # We can't easily test it without executing the module
    # So we'll just ensure the main() function works
    # The actual line 1346 will be covered when the module is imported
    # during normal test execution

    # Instead, let's just verify the main function exists and is callable
    from awslabs.cloudwatch_appsignals_mcp_server.server import main

    assert callable(main)

    # And verify that running main with mocked mcp doesn't raise
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.mcp') as mock_mcp:
        mock_mcp.run.side_effect = KeyboardInterrupt()
        # Should handle KeyboardInterrupt gracefully
        main()


@pytest.mark.asyncio
async def test_analyze_canary_failures_no_runs(mock_aws_clients):
    """Test analyze_canary_failures when no runs are found."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': []}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {
        'Canary': {'Name': 'test-canary'}
    }

    result = await analyze_canary_failures('test-canary', 'us-east-1')

    assert 'No run history found for test-canary' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_healthy_canary(mock_aws_clients):
    """Test analyze_canary_failures with healthy canary."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'run1',
            'Status': {'State': 'PASSED'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {
        'Canary': {'Name': 'test-canary'}
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        mock_insights.return_value = 'Telemetry insights available'

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert 'Canary is healthy - no failures since last success' in result
        assert '🔍 Comprehensive Failure Analysis for test-canary' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_telemetry_unavailable(mock_aws_clients):
    """Test analyze_canary_failures when telemetry is unavailable."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'run1',
            'Status': {'State': 'PASSED'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {
        'Canary': {'Name': 'test-canary'}
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        mock_insights.side_effect = Exception('Telemetry API error')

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert 'Telemetry API unavailable: Telemetry API error' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_with_failures(mock_aws_clients):
    """Test analyze_canary_failures with actual failures."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run-1',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timeout'},
            'Timeline': {'Started': '2024-01-01T01:00:00Z'},
        },
        {
            'Id': 'failed-run-2',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timeout'},
            'Timeline': {'Started': '2024-01-01T00:30:00Z'},
        },
        {
            'Id': 'success-run',
            'Status': {'State': 'PASSED'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        },
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 artifacts
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/screenshot.png'},
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/logs.txt'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            with patch(
                'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_screenshots'
            ) as mock_screenshots:
                with patch(
                    'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_log_files'
                ) as mock_logs:
                    mock_insights.return_value = 'Telemetry insights'
                    mock_har.return_value = {
                        'failed_requests': 2,
                        'total_requests': 10,
                        'request_details': [
                            {'url': 'https://example.com', 'status': 500, 'time': 1000}
                        ],
                    }
                    mock_screenshots.return_value = {'insights': ['Screenshot analysis']}
                    mock_logs.return_value = {'insights': ['Log analysis']}

                    result = await analyze_canary_failures('test-canary', 'us-east-1')

                    assert 'Found 2 consecutive failures since last success' in result
                    assert 'All failures have same cause: Navigation timeout' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_iam_analysis(mock_aws_clients):
    """Test analyze_canary_failures with IAM-related failures."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Access denied'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies'
        ) as mock_iam:
            with patch(
                'awslabs.cloudwatch_appsignals_mcp_server.server.check_resource_arns_correct'
            ) as mock_arn:
                mock_insights.return_value = 'Telemetry insights'
                mock_iam.return_value = {
                    'status': 'issues_found',
                    'checks': {'role_exists': 'PASS', 'policies_attached': 'FAIL'},
                    'issues_found': ['Missing S3 permissions'],
                    'recommendations': ['Add S3 read permissions'],
                }
                mock_arn.return_value = {
                    'correct': False,
                    'error': 'Invalid bucket ARN',
                    'issues': ['Bucket name mismatch'],
                }

                result = await analyze_canary_failures('test-canary', 'us-east-1')

                assert 'RUNNING COMPREHENSIVE IAM ANALYSIS' in result
                assert 'IAM Role Analysis Status: issues_found' in result
                assert 'ALL IAM ISSUES FOUND (2 total):' in result
                assert 'IAM Policy: Missing S3 permissions' in result
                assert 'Resource ARN: Bucket name mismatch' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_enospc_error(mock_aws_clients):
    """Test analyze_canary_failures with ENOSPC error."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'ENOSPC: no space left on device'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics'
        ) as mock_metrics:
            mock_insights.return_value = 'Telemetry insights'
            mock_metrics.return_value = {
                'maxEphemeralStorageUsageInMb': 512.5,
                'maxEphemeralStorageUsagePercent': 95.2,
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert 'DISK USAGE ROOT CAUSE ANALYSIS:' in result
            assert 'Storage: 512.5 MB peak' in result
            assert 'Usage: 95.2% peak' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_protocol_error(mock_aws_clients):
    """Test analyze_canary_failures with protocol error."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {
                'State': 'FAILED',
                'StateReason': 'Protocol error (Target.activateTarget): Session closed',
            },
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics'
        ) as mock_metrics:
            mock_insights.return_value = 'Telemetry insights'
            mock_metrics.return_value = {'maxSyntheticsMemoryUsageInMB': 256.8}

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert 'MEMORY USAGE ROOT CAUSE ANALYSIS:' in result
            assert 'Memory: 256.8 MB peak' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_navigation_timeout_with_har(mock_aws_clients):
    """Test analyze_canary_failures with navigation timeout and HAR analysis."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timed out after 30000ms'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return HAR files
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            mock_har.return_value = {
                'failed_requests': 5,
                'total_requests': 10,
                'request_details': [
                    {'url': 'https://example.com/slow', 'status': 200, 'time': 5000}
                ],
                'insights': [
                    'Slow DNS resolution detected',
                    'High server response time',
                    'Network connectivity issues',
                    'Resource loading delays',
                    'JavaScript execution timeout',
                ],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert '🔍 Comprehensive Failure Analysis for test-canary' in result
            assert 'Slow DNS resolution detected' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_s3_exception(mock_aws_clients):
    """Test analyze_canary_failures when S3 operations fail."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    mock_aws_clients['s3_client'].list_objects_v2.side_effect = Exception('S3 access denied')

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_canary_logs_with_time_window'
        ) as mock_logs:
            mock_insights.return_value = 'Telemetry insights'
            mock_logs.return_value = {
                'status': 'success',
                'time_window': '2024-01-01 00:00:00 - 2024-01-01 00:05:00',
                'total_events': 5,
                'error_events': [
                    {'timestamp': datetime.now(timezone.utc), 'message': 'Test error message'}
                ],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            # Should fall back to CloudWatch Logs analysis when S3 fails
            assert '⚠️ Artifacts not available - Checking CloudWatch Logs for root cause' in result
            assert 'CLOUDWATCH LOGS ANALYSIS' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_visual_variation(mock_aws_clients):
    """Test analyze_canary_failures with visual variation error."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Visual variation detected'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_code') as mock_code:
            mock_insights.return_value = 'Telemetry insights'
            mock_code.return_value = {'code_content': 'const synthetics = require("Synthetics");'}

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert 'VISUAL MONITORING ISSUE DETECTED' in result
            assert 'Website UI changed - not a technical failure' in result
            assert 'canary code:' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_get_canary_code_exception(mock_aws_clients):
    """Test analyze_canary_failures when get_canary_code fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_code') as mock_code:
            mock_insights.return_value = 'Telemetry insights'
            # Make get_canary_code raise an exception
            mock_code.side_effect = Exception('Code retrieval failed')

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert 'Note: Could not retrieve canary code: Code retrieval failed' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_iam_analysis_exception(mock_aws_clients):
    """Test analyze_canary_failures when IAM analysis fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Access denied'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies'
        ) as mock_iam:
            mock_insights.return_value = 'Telemetry insights'
            # Make IAM analysis raise an exception
            mock_iam.side_effect = Exception('IAM analysis failed')

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert '⚠️ IAM analysis failed: IAM analysis failed' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_disk_usage_exception(mock_aws_clients):
    """Test analyze_canary_failures when disk usage analysis fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'ENOSPC: no space left on device'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics'
        ) as mock_metrics:
            mock_insights.return_value = 'Telemetry insights'
            # Make disk usage analysis raise an exception
            mock_metrics.side_effect = Exception('Disk usage analysis failed')

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert (
                '⚠️ Could not generate disk usage debugging code: Disk usage analysis failed'
                in result
            )


@pytest.mark.asyncio
async def test_analyze_canary_failures_memory_usage_exception(mock_aws_clients):
    """Test analyze_canary_failures when memory usage analysis fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {
                'State': 'FAILED',
                'StateReason': 'Protocol error (Target.activateTarget): Session closed',
            },
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics'
        ) as mock_metrics:
            mock_insights.return_value = 'Telemetry insights'
            # Make memory usage analysis raise an exception
            mock_metrics.side_effect = Exception('Memory usage analysis failed')

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert (
                '⚠️ Could not collect memory usage metrics: Memory usage analysis failed' in result
            )


@pytest.mark.asyncio
async def test_analyze_canary_failures_har_timeout_exception(mock_aws_clients):
    """Test analyze_canary_failures when HAR timeout analysis fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timed out after 30000ms'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return HAR files
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            # Make HAR analysis raise an exception
            mock_har.side_effect = Exception('HAR analysis failed')

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert '⚠️ HAR analysis failed: HAR analysis failed' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_success_artifacts_exception(mock_aws_clients):
    """Test analyze_canary_failures when success artifacts retrieval fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        },
        {
            'Id': 'success-run',
            'Status': {'State': 'PASSED'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        },
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return failure artifacts but fail on success artifacts
    def s3_side_effect(*args, **kwargs):
        prefix = kwargs.get('Prefix', '')
        if 'success' in prefix or len(prefix.split('/')) > 5:  # Simulate success path failure
            raise Exception('Success artifacts access failed')
        return {
            'Contents': [
                {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
            ]
        }

    mock_aws_clients['s3_client'].list_objects_v2.side_effect = s3_side_effect

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            mock_har.return_value = {
                'failed_requests': 2,
                'total_requests': 10,
                'request_details': [],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            # Should still process failure artifacts even if success artifacts fail
            assert '🔍 Comprehensive Failure Analysis for test-canary' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_no_failure_timestamp(mock_aws_clients):
    """Test analyze_canary_failures when failure has no timestamp."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {},  # No Started timestamp
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        mock_insights.return_value = 'Telemetry insights'

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert '📋 No failure timestamp available for targeted log analysis' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_log_analysis_failure(mock_aws_clients):
    """Test analyze_canary_failures when log analysis fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch(
            'awslabs.cloudwatch_appsignals_mcp_server.server.analyze_canary_logs_with_time_window'
        ) as mock_logs:
            mock_insights.return_value = 'Telemetry insights'
            mock_logs.return_value = {
                'status': 'failed',
                'insights': ['Log analysis failed due to missing log group'],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            assert '📋 Log analysis failed due to missing log group' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_main_exception(mock_aws_clients):
    """Test analyze_canary_failures when main function fails."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    # Make get_canary_runs raise an exception
    mock_aws_clients['synthetics_client'].get_canary_runs.side_effect = Exception('API error')

    result = await analyze_canary_failures('test-canary', 'us-east-1')

    assert '❌ Error in comprehensive failure analysis: API error' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_no_har_files_navigation_timeout(mock_aws_clients):
    """Test analyze_canary_failures navigation timeout without HAR files."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timed out after 30000ms'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        mock_insights.return_value = 'Telemetry insights'

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert 'NAVIGATION TIMEOUT DETECTED:' in result
        assert 'No HAR files available for detailed analysis' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_artifact_location_without_s3_prefix(mock_aws_clients):
    """Test analyze_canary_failures with artifact location without s3:// prefix."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 'test-bucket/canary/us-east-1/test-canary',  # No s3:// prefix
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return artifacts
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            mock_har.return_value = {
                'failed_requests': 1,
                'total_requests': 5,
                'request_details': [],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            # Should still process artifacts even without s3:// prefix
            assert 'FAILURE ANALYSIS' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_empty_base_path(mock_aws_clients):
    """Test analyze_canary_failures with empty base path."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket',  # Only bucket, no path
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return artifacts
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            mock_har.return_value = {
                'failed_requests': 1,
                'total_requests': 5,
                'request_details': [],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            # Should construct default canary path when base_path is empty
            assert 'FAILURE ANALYSIS' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_multiple_failure_causes(mock_aws_clients):
    """Test analyze_canary_failures with multiple different failure causes."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run-1',
            'Status': {'State': 'FAILED', 'StateReason': 'Navigation timeout'},
            'Timeline': {'Started': '2024-01-01T00:00:00Z'},
        },
        {
            'Id': 'failed-run-2',
            'Status': {'State': 'FAILED', 'StateReason': 'Access denied'},
            'Timeline': {'Started': '2024-01-01T00:01:00Z'},
        },
        {
            'Id': 'success-run',
            'Status': {'State': 'PASSED'},
            'Timeline': {'Started': '2023-12-31T23:59:00Z'},
        },
    ]

    mock_canary = {'Name': 'test-canary', 'ArtifactS3Location': ''}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        mock_insights.return_value = 'Telemetry insights'

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert 'Multiple failure causes (2 different issues):' in result
        assert '1. **Navigation timeout** (1 occurrences)' in result
        assert '2. **Access denied** (1 occurrences)' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_no_failure_time_fallback(mock_aws_clients):
    """Test analyze_canary_failures fallback when no failure time."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

    mock_runs = [
        {
            'Id': 'failed-run',
            'Status': {'State': 'FAILED', 'StateReason': 'Test failure'},
            'Timeline': {},  # No Started time
        }
    ]

    mock_canary = {
        'Name': 'test-canary',
        'ArtifactS3Location': 's3://test-bucket/canary/us-east-1/test-canary',
    }

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = {'CanaryRuns': mock_runs}
    mock_aws_clients['synthetics_client'].get_canary.return_value = {'Canary': mock_canary}

    # Mock S3 to return artifacts
    mock_aws_clients['s3_client'].list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'canary/us-east-1/test-canary/2024/01/01/test.har'},
        ]
    }

    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_metrics_and_service_insights'
    ) as mock_insights:
        with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har:
            mock_insights.return_value = 'Telemetry insights'
            mock_har.return_value = {
                'failed_requests': 1,
                'total_requests': 5,
                'request_details': [],
            }

            result = await analyze_canary_failures('test-canary', 'us-east-1')

            # Should use current time when no failure time available
            assert 'FAILURE ANALYSIS' in result


def test_filter_operation_targets_fault_to_availability():
    """Test _filter_operation_targets converts Fault to Availability."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    'MetricType': 'Fault',
                }
            },
        }
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify the MetricType was changed from Fault to Availability
    assert len(operation_targets) == 1
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
    assert has_wildcards is False


def test_filter_operation_targets_non_fault_unchanged():
    """Test _filter_operation_targets leaves non-Fault MetricTypes unchanged."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    'MetricType': 'Latency',
                }
            },
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service-2'},
                    'Operation': 'POST /api',
                    'MetricType': 'Error',
                }
            },
        },
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify non-Fault MetricTypes are unchanged
    assert len(operation_targets) == 2
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Latency'
    assert operation_targets[1]['Data']['ServiceOperation']['MetricType'] == 'Error'
    assert has_wildcards is False


def test_filter_operation_targets_multiple_fault_conversions():
    """Test _filter_operation_targets converts multiple Fault entries to Availability."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'service-1'},
                    'Operation': 'GET /api',
                    'MetricType': 'Fault',
                }
            },
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'service-2'},
                    'Operation': 'POST /api',
                    'MetricType': 'Latency',
                }
            },
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'service-3'},
                    'Operation': 'PUT /api',
                    'MetricType': 'Fault',
                }
            },
        },
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify multiple Fault entries are converted
    assert len(operation_targets) == 3
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
    assert operation_targets[1]['Data']['ServiceOperation']['MetricType'] == 'Latency'
    assert operation_targets[2]['Data']['ServiceOperation']['MetricType'] == 'Availability'
    assert has_wildcards is False


def test_filter_operation_targets_with_wildcards():
    """Test _filter_operation_targets detects wildcards and converts Fault to Availability."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': '*payment*'},
                    'Operation': '*GET*',
                    'MetricType': 'Fault',
                }
            },
        }
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify wildcard detection and Fault conversion
    assert len(operation_targets) == 1
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
    assert has_wildcards is True


def test_filter_operation_targets_ignores_non_service_operation():
    """Test _filter_operation_targets ignores non-service_operation targets."""
    provided = [
        {
            'Type': 'service',
            'Data': {'Service': {'Type': 'Service', 'Name': 'test-service'}},
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    'MetricType': 'Fault',
                }
            },
        },
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify only service_operation targets are included
    assert len(operation_targets) == 1
    assert operation_targets[0]['Type'] == 'service_operation'
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'Availability'
    assert has_wildcards is False


def test_filter_operation_targets_empty_metric_type():
    """Test _filter_operation_targets handles empty MetricType gracefully."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    'MetricType': '',
                }
            },
        }
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify empty MetricType is unchanged
    assert len(operation_targets) == 1
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == ''
    assert has_wildcards is False


def test_filter_operation_targets_missing_metric_type():
    """Test _filter_operation_targets handles missing MetricType gracefully."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    # MetricType is missing
                }
            },
        }
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify missing MetricType doesn't cause errors
    assert len(operation_targets) == 1
    # MetricType should remain missing (empty string from .get())
    assert operation_targets[0]['Data']['ServiceOperation'].get('MetricType', '') == ''
    assert has_wildcards is False


def test_filter_operation_targets_case_sensitive():
    """Test _filter_operation_targets is case-sensitive for Fault conversion."""
    provided = [
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service'},
                    'Operation': 'GET /api',
                    'MetricType': 'fault',  # lowercase
                }
            },
        },
        {
            'Type': 'service_operation',
            'Data': {
                'ServiceOperation': {
                    'Service': {'Type': 'Service', 'Name': 'test-service-2'},
                    'Operation': 'POST /api',
                    'MetricType': 'FAULT',  # uppercase
                }
            },
        },
    ]

    operation_targets, has_wildcards = _filter_operation_targets(provided)

    # Verify only exact case "Fault" is converted
    assert len(operation_targets) == 2
    assert operation_targets[0]['Data']['ServiceOperation']['MetricType'] == 'fault'  # unchanged
    assert operation_targets[1]['Data']['ServiceOperation']['MetricType'] == 'FAULT'  # unchanged
    assert has_wildcards is False
