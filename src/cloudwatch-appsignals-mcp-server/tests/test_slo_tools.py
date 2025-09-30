"""Tests for slo_tools.py functions."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.slo_tools import get_slo, list_slos
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_appsignals_client = MagicMock()

    patches = [
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.slo_tools.appsignals_client',
            mock_appsignals_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'appsignals_client': mock_appsignals_client,
        }
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_get_slo_success_period_based(mock_aws_clients):
    """Test successful get_slo with period-based SLI."""
    mock_slo_response = {
        'Slo': {
            'Name': 'test-slo',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
            'Description': 'Test SLO for latency monitoring',
            'EvaluationType': 'PeriodBased',
            'CreatedTime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'LastUpdatedTime': datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            'Goal': {
                'AttainmentGoal': 99.9,
                'WarningThreshold': 95.0,
                'Interval': {'RollingInterval': {'Duration': 7, 'DurationUnit': 'DAY'}},
            },
            'Sli': {
                'SliMetric': {
                    'KeyAttributes': {
                        'Name': 'payment-service',
                        'Environment': 'eks:production',
                        'Type': 'AWS::ECS::Service',
                    },
                    'OperationName': 'GET /api/payments',
                    'MetricType': 'LATENCY',
                    'MetricDataQueries': [
                        {
                            'Id': 'm1',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApplicationSignals',
                                    'MetricName': 'Latency',
                                    'Dimensions': [
                                        {'Name': 'Service', 'Value': 'payment-service'},
                                        {'Name': 'Operation', 'Value': 'GET /api/payments'},
                                    ],
                                },
                                'Period': 300,
                                'Stat': 'Average',
                                'Unit': 'Milliseconds',
                            },
                            'ReturnData': True,
                        }
                    ],
                    'DependencyConfig': {
                        'DependencyKeyAttributes': {
                            'Name': 'database-service',
                            'Type': 'AWS::RDS::DBCluster',
                        },
                        'DependencyOperationName': 'SELECT',
                    },
                },
                'MetricThreshold': 500.0,
                'ComparisonOperator': 'LessThanThreshold',
            },
            'BurnRateConfigurations': [
                {'LookBackWindowMinutes': 60},
                {'LookBackWindowMinutes': 300},
            ],
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo(slo_id='test-slo')

    assert 'Service Level Objective Details' in result
    assert 'Name: test-slo' in result
    assert 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo' in result
    assert 'Description: Test SLO for latency monitoring' in result
    assert 'Evaluation Type: PeriodBased' in result
    assert 'Attainment Goal: 99.9%' in result
    assert 'Warning Threshold: 95.0%' in result
    assert 'Rolling 7 DAY' in result
    assert 'Period-Based SLI Configuration:' in result
    assert 'Name: payment-service' in result
    assert 'Environment: eks:production' in result
    assert 'Operation Name: GET /api/payments' in result
    assert 'annotation[aws.local.operation]="GET /api/payments"' in result
    assert 'Metric Type: LATENCY' in result
    assert 'Namespace: AWS/ApplicationSignals' in result
    assert 'MetricName: Latency' in result
    assert 'Service: payment-service' in result
    assert 'Operation: GET /api/payments' in result
    assert 'Period: 300 seconds' in result
    assert 'Stat: Average' in result
    assert 'Unit: Milliseconds' in result
    assert 'Dependency Configuration:' in result
    assert 'Name: database-service' in result
    assert 'Type: AWS::RDS::DBCluster' in result
    assert 'Dependency Operation: SELECT' in result
    assert 'annotation[aws.remote.operation]="SELECT"' in result
    assert 'Threshold: 500.0' in result
    assert 'Comparison: LessThanThreshold' in result
    assert 'Burn Rate Configurations:' in result
    assert 'Look-back window: 60 minutes' in result
    assert 'Look-back window: 300 minutes' in result


@pytest.mark.asyncio
async def test_get_slo_success_request_based(mock_aws_clients):
    """Test successful get_slo with request-based SLI."""
    mock_slo_response = {
        'Slo': {
            'Name': 'availability-slo',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/availability-slo',
            'EvaluationType': 'RequestBased',
            'CreatedTime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            'LastUpdatedTime': datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            'Goal': {
                'AttainmentGoal': 99.5,
                'WarningThreshold': 98.0,
                'Interval': {
                    'CalendarInterval': {
                        'Duration': 1,
                        'DurationUnit': 'MONTH',
                        'StartTime': datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    }
                },
            },
            'RequestBasedSli': {
                'RequestBasedSliMetric': {
                    'KeyAttributes': {
                        'Name': 'api-service',
                        'Environment': 'lambda',
                        'Type': 'AWS::Lambda::Function',
                    },
                    'OperationName': 'POST /api/orders',
                    'MetricType': 'AVAILABILITY',
                    'MetricDataQueries': [
                        {
                            'Id': 'availability',
                            'Expression': '(m1 - m2) / m1 * 100',
                            'ReturnData': True,
                        },
                        {
                            'Id': 'm1',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApplicationSignals',
                                    'MetricName': 'RequestCount',
                                    'Dimensions': [
                                        {'Name': 'Service', 'Value': 'api-service'},
                                        {'Name': 'Operation', 'Value': 'POST /api/orders'},
                                    ],
                                },
                                'Period': 60,
                                'Stat': 'Sum',
                            },
                            'ReturnData': False,
                        },
                    ],
                },
                'MetricThreshold': 99.0,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
            },
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo(slo_id='availability-slo')

    assert 'Name: availability-slo' in result
    assert 'Evaluation Type: RequestBased' in result
    assert 'Attainment Goal: 99.5%' in result
    assert 'Calendar 1 MONTH starting' in result
    assert 'Request-Based SLI Configuration:' in result
    assert 'Name: api-service' in result
    assert 'Environment: lambda' in result
    assert 'Operation Name: POST /api/orders' in result
    assert 'annotation[aws.local.operation]="POST /api/orders"' in result
    assert 'Metric Type: AVAILABILITY' in result
    assert 'Query ID: availability' in result
    assert 'Expression: (m1 - m2) / m1 * 100' in result
    assert 'Query ID: m1' in result
    assert 'MetricName: RequestCount' in result
    assert 'Period: 60 seconds' in result
    assert 'Stat: Sum' in result
    assert 'ReturnData: False' in result
    assert 'Threshold: 99.0' in result
    assert 'Comparison: GreaterThanOrEqualToThreshold' in result


@pytest.mark.asyncio
async def test_get_slo_not_found(mock_aws_clients):
    """Test get_slo when SLO is not found."""
    mock_slo_response = {'Slo': {}}

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo(slo_id='nonexistent-slo')

    assert 'No SLO found with ID: nonexistent-slo' in result


@pytest.mark.asyncio
async def test_get_slo_client_error(mock_aws_clients):
    """Test get_slo with AWS ClientError."""
    mock_aws_clients['appsignals_client'].get_service_level_objective.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'SLO not found',
            }
        },
        operation_name='GetServiceLevelObjective',
    )

    result = await get_slo(slo_id='test-slo')

    assert 'AWS Error: SLO not found' in result


@pytest.mark.asyncio
async def test_get_slo_general_exception(mock_aws_clients):
    """Test get_slo with general exception."""
    mock_aws_clients['appsignals_client'].get_service_level_objective.side_effect = Exception(
        'Unexpected error occurred'
    )

    result = await get_slo(slo_id='test-slo')

    assert 'Error: Unexpected error occurred' in result


@pytest.mark.asyncio
async def test_list_slos_success(mock_aws_clients):
    """Test successful list_slos execution."""
    mock_slos_response = {
        'SloSummaries': [
            {
                'Name': 'payment-latency-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-latency-slo',
                'OperationName': 'GET /api/payments',
                'CreatedTime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'KeyAttributes': {
                    'Name': 'payment-service',
                    'Environment': 'eks:production',
                    'Type': 'AWS::ECS::Service',
                },
            },
            {
                'Name': 'order-availability-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/order-availability-slo',
                'OperationName': 'POST /api/orders',
                'CreatedTime': datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                'KeyAttributes': {
                    'Name': 'order-service',
                    'Environment': 'lambda',
                    'Type': 'AWS::Lambda::Function',
                },
            },
        ]
    }

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=50)

    assert 'Service Level Objectives (2 total):' in result
    assert 'SLO: payment-latency-slo' in result
    assert 'arn:aws:application-signals:us-east-1:123456789012:slo/payment-latency-slo' in result
    assert 'Operation: GET /api/payments' in result
    assert 'Name: payment-service' in result
    assert 'Environment: eks:production' in result
    assert 'Type: AWS::ECS::Service' in result
    assert 'SLO: order-availability-slo' in result
    assert 'Operation: POST /api/orders' in result
    assert 'Name: order-service' in result
    assert 'Environment: lambda' in result
    assert 'Type: AWS::Lambda::Function' in result


@pytest.mark.asyncio
async def test_list_slos_with_key_attributes_filter(mock_aws_clients):
    """Test list_slos with key attributes filter."""
    mock_slos_response = {
        'SloSummaries': [
            {
                'Name': 'filtered-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/filtered-slo',
                'OperationName': 'GET /api/test',
                'CreatedTime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'KeyAttributes': {'Name': 'test-service', 'Environment': 'eks:test-cluster'},
            }
        ]
    }

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    key_attributes = '{"Name": "test-service", "Environment": "eks:test-cluster"}'
    result = await list_slos(
        key_attributes=key_attributes, max_results=10, include_linked_accounts=False
    )

    assert 'Service Level Objectives (1 total):' in result
    assert 'SLO: filtered-slo' in result
    assert 'Name: test-service' in result
    assert 'Environment: eks:test-cluster' in result

    # Verify the API was called with correct parameters
    call_args = mock_aws_clients['appsignals_client'].list_service_level_objectives.call_args[1]
    assert call_args['MaxResults'] == 10
    assert not call_args['IncludeLinkedAccounts']
    assert call_args['KeyAttributes'] == {
        'Name': 'test-service',
        'Environment': 'eks:test-cluster',
    }


@pytest.mark.asyncio
async def test_list_slos_no_slos_found(mock_aws_clients):
    """Test list_slos when no SLOs are found."""
    mock_slos_response = {'SloSummaries': []}

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=50)

    assert 'No Service Level Objectives found matching the specified criteria.' in result


@pytest.mark.asyncio
async def test_list_slos_with_pagination(mock_aws_clients):
    """Test list_slos with pagination token."""
    mock_slos_response = {
        'SloSummaries': [
            {
                'Name': 'slo-1',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/slo-1',
                'OperationName': 'GET /api/test1',
                'CreatedTime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'KeyAttributes': {'Name': 'service-1'},
            }
        ],
        'NextToken': 'next-page-token',
    }

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=1)

    assert 'Service Level Objectives (1 total):' in result
    assert 'SLO: slo-1' in result
    assert 'Note: More SLOs may be available. This response shows the first 1 results.' in result


@pytest.mark.asyncio
async def test_list_slos_invalid_json_key_attributes(mock_aws_clients):
    """Test list_slos with invalid JSON in key_attributes."""
    result = await list_slos(key_attributes='invalid-json')

    assert 'Error: Invalid JSON in key_attributes parameter:' in result


@pytest.mark.asyncio
async def test_list_slos_max_results_validation(mock_aws_clients):
    """Test list_slos with max_results validation."""
    mock_slos_response = {'SloSummaries': []}

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    # Test with max_results > 50 (should be clamped to 50)
    await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=100)
    call_args = mock_aws_clients['appsignals_client'].list_service_level_objectives.call_args[1]
    assert call_args['MaxResults'] == 50

    # Test with max_results < 1 (should be clamped to 1)
    await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=0)
    call_args = mock_aws_clients['appsignals_client'].list_service_level_objectives.call_args[1]
    assert call_args['MaxResults'] == 1


@pytest.mark.asyncio
async def test_list_slos_client_error(mock_aws_clients):
    """Test list_slos with AWS ClientError."""
    mock_aws_clients['appsignals_client'].list_service_level_objectives.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this action',
            }
        },
        operation_name='ListServiceLevelObjectives',
    )

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=50)

    assert 'AWS Error: User is not authorized to perform this action' in result


@pytest.mark.asyncio
async def test_list_slos_general_exception(mock_aws_clients):
    """Test list_slos with general exception."""
    mock_aws_clients['appsignals_client'].list_service_level_objectives.side_effect = Exception(
        'Unexpected error occurred'
    )

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=50)

    assert 'Error: Unexpected error occurred' in result


@pytest.mark.asyncio
async def test_list_slos_minimal_slo_data(mock_aws_clients):
    """Test list_slos with minimal SLO data (missing optional fields)."""
    mock_slos_response = {
        'SloSummaries': [
            {
                'Name': 'minimal-slo',
                'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/minimal-slo',
                # Missing OperationName, CreatedTime, KeyAttributes
            }
        ]
    }

    mock_aws_clients[
        'appsignals_client'
    ].list_service_level_objectives.return_value = mock_slos_response

    result = await list_slos(key_attributes='{}', include_linked_accounts=True, max_results=50)

    assert 'Service Level Objectives (1 total):' in result
    assert 'SLO: minimal-slo' in result
    assert 'Operation: N/A' in result
    assert 'Created: Unknown' in result
    # Should not have Service Attributes section since KeyAttributes is missing


@pytest.mark.asyncio
async def test_get_slo_minimal_slo_data(mock_aws_clients):
    """Test get_slo with minimal SLO data (missing optional fields)."""
    mock_slo_response = {
        'Slo': {
            'Name': 'minimal-slo',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/minimal-slo',
            'EvaluationType': 'PeriodBased',
            # Missing Description, CreatedTime, LastUpdatedTime, Goal, Sli, BurnRateConfigurations
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo(slo_id='minimal-slo')

    assert 'Name: minimal-slo' in result
    assert 'Evaluation Type: PeriodBased' in result
    assert 'Created: Unknown' in result
    assert 'Last Updated: Unknown' in result
    # Should not have Goal Configuration, SLI Configuration, or Burn Rate sections


@pytest.mark.asyncio
async def test_get_slo_with_empty_metric_queries(mock_aws_clients):
    """Test get_slo with empty metric data queries."""
    mock_slo_response = {
        'Slo': {
            'Name': 'test-slo',
            'Arn': 'arn:aws:application-signals:us-east-1:123456789012:slo/test-slo',
            'EvaluationType': 'PeriodBased',
            'Sli': {
                'SliMetric': {
                    'KeyAttributes': {'Name': 'test-service'},
                    'MetricType': 'LATENCY',
                    'MetricDataQueries': [],  # Empty queries
                },
                'MetricThreshold': 100.0,
                'ComparisonOperator': 'LessThanThreshold',
            },
        }
    }

    mock_aws_clients[
        'appsignals_client'
    ].get_service_level_objective.return_value = mock_slo_response

    result = await get_slo(slo_id='test-slo')

    assert 'Name: test-slo' in result
    assert 'Period-Based SLI Configuration:' in result
    assert 'Name: test-service' in result
    assert 'Metric Type: LATENCY' in result
    assert 'Threshold: 100.0' in result
    # Should not have Metric Data Queries section since it's empty
