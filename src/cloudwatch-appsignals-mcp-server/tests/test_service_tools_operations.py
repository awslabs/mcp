"""Tests for service_tools.py list_service_operations function."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.service_tools import list_service_operations
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_appsignals_client = MagicMock()
    mock_cloudwatch_client = MagicMock()

    patches = [
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_tools.appsignals_client',
            mock_appsignals_client,
        ),
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.service_tools.cloudwatch_client',
            mock_cloudwatch_client,
        ),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'appsignals_client': mock_appsignals_client,
            'cloudwatch_client': mock_cloudwatch_client,
        }
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_list_service_operations_success_with_get_operations(mock_aws_clients):
    """Test successful list_service_operations with GET operations."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'payment-service',
                    'Type': 'AWS::ECS::Service',
                    'Environment': 'production',
                }
            }
        ]
    }

    # Mock operations response with GET operations
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/payments',
                'MetricReferences': [
                    {'MetricType': 'Latency'},
                    {'MetricType': 'Error'},
                ],
            },
            {
                'Name': 'GET /api/orders',
                'MetricReferences': [
                    {'MetricType': 'Latency'},
                    {'MetricType': 'Availability'},
                ],
            },
            {
                'Name': 'POST /api/payments',
                'MetricReferences': [
                    {'MetricType': 'Fault'},
                ],
            },
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='payment-service', hours=12)

    assert 'Operations for Service: payment-service' in result
    assert 'Time Range: Last 12 hour(s)' in result
    assert 'Total Operations: 3' in result
    assert '🔍 GET Operations (2):' in result
    assert 'GET /api/payments' in result
    assert 'GET /api/orders' in result
    assert '📝 POST Operations (1):' in result
    assert 'POST /api/payments' in result
    # Check that both metrics are present (order may vary due to set() usage)
    assert 'Available Metrics:' in result
    assert 'Latency' in result
    assert 'Error' in result
    assert 'Operation Discovery Summary:' in result
    assert 'GET Operations: 2' in result
    assert 'POST Operations: 1' in result
    assert 'Other Operations: 0' in result


@pytest.mark.asyncio
async def test_list_service_operations_success_with_other_operations(mock_aws_clients):
    """Test successful list_service_operations with other operation types."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'api-service',
                    'Type': 'AWS::Lambda::Function',
                }
            }
        ]
    }

    # Mock operations response with various operation types
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'PUT /api/users',
                'MetricReferences': [
                    {'MetricType': 'Latency'},
                ],
            },
            {
                'Name': 'DELETE /api/sessions',
                'MetricReferences': [
                    {'MetricType': 'Error'},
                    {'MetricType': 'Fault'},
                ],
            },
            {
                'Name': 'PATCH /api/profiles',
                'MetricReferences': [],
            },
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='api-service', hours=24)

    assert 'Operations for Service: api-service' in result
    assert 'Total Operations: 3' in result
    assert '🔧 Other Operations (3):' in result
    assert 'PUT /api/users' in result
    assert 'DELETE /api/sessions' in result
    assert 'PATCH /api/profiles' in result
    assert 'Available Metrics: Latency' in result
    # Check that both metrics are present (order may vary due to set() usage)
    assert 'Available Metrics:' in result
    assert 'Error' in result
    assert 'Fault' in result
    assert 'GET Operations: 0' in result
    assert 'POST Operations: 0' in result
    assert 'Other Operations: 3' in result


@pytest.mark.asyncio
async def test_list_service_operations_no_operations_found(mock_aws_clients):
    """Test list_service_operations when no operations are found."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'inactive-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock empty operations response
    mock_operations_response = {'ServiceOperations': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='inactive-service', hours=6)

    assert "No operations found for service 'inactive-service' in the last 6 hours" in result
    assert (
        '⚠️  IMPORTANT: This means NO OPERATION INVOCATIONS occurred in the time window' in result
    )
    assert 'Operations may exist but were not actively called' in result
    assert 'Maximum discovery window is 24 hours for Application Signals' in result
    assert (
        'For comprehensive operation analysis regardless of recent activity, use audit_services()'
        in result
    )
    assert 'Empty results ≠ no operations exist, just no recent invocations' in result


@pytest.mark.asyncio
async def test_list_service_operations_service_not_found(mock_aws_clients):
    """Test list_service_operations when service is not found."""
    # Mock empty services response
    mock_services_response = {'ServiceSummaries': []}

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response

    result = await list_service_operations(service_name='nonexistent-service', hours=24)

    assert "Service 'nonexistent-service' not found in Application Signals" in result
    assert 'Use list_monitored_services() to see available services' in result


@pytest.mark.asyncio
async def test_list_service_operations_hours_limit_enforcement(mock_aws_clients):
    """Test that hours parameter is limited to 24 hours maximum."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/test',
                'MetricReferences': [{'MetricType': 'Latency'}],
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    # Request 48 hours but should be limited to 24
    result = await list_service_operations(service_name='test-service', hours=48)

    assert 'Time Range: Last 24 hour(s)' in result  # Should be limited to 24

    # Verify the API was called with 24 hours max
    call_args = mock_aws_clients['appsignals_client'].list_service_operations.call_args[1]
    start_time = call_args['StartTime']
    end_time = call_args['EndTime']
    time_diff = end_time - start_time
    assert time_diff.total_seconds() <= 24 * 3600  # Should be <= 24 hours


@pytest.mark.asyncio
async def test_list_service_operations_mixed_operation_types(mock_aws_clients):
    """Test list_service_operations with mixed GET, POST, and other operations."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'mixed-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response with mixed types
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/users',
                'MetricReferences': [{'MetricType': 'Latency'}],
            },
            {
                'Name': 'get /api/profiles',  # lowercase get
                'MetricReferences': [{'MetricType': 'Error'}],
            },
            {
                'Name': 'POST /api/users',
                'MetricReferences': [{'MetricType': 'Fault'}],
            },
            {
                'Name': 'post /api/sessions',  # lowercase post
                'MetricReferences': [{'MetricType': 'Availability'}],
            },
            {
                'Name': 'PUT /api/settings',
                'MetricReferences': [{'MetricType': 'Latency'}],
            },
            {
                'Name': 'Unknown Operation',  # No GET/POST in name
                'MetricReferences': [{'MetricType': 'Error'}],
            },
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='mixed-service', hours=24)

    assert 'Total Operations: 6' in result
    assert '🔍 GET Operations (2):' in result
    assert 'GET /api/users' in result
    assert 'get /api/profiles' in result
    assert '📝 POST Operations (2):' in result
    assert 'POST /api/users' in result
    assert 'post /api/sessions' in result
    assert '🔧 Other Operations (2):' in result
    assert 'PUT /api/settings' in result
    assert 'Unknown Operation' in result
    assert 'GET Operations: 2' in result
    assert 'POST Operations: 2' in result
    assert 'Other Operations: 2' in result


@pytest.mark.asyncio
async def test_list_service_operations_operations_without_metrics(mock_aws_clients):
    """Test list_service_operations with operations that have no metric references."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response with operations without metrics
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/health',
                'MetricReferences': [],  # No metrics
            },
            {
                'Name': 'POST /api/webhook',
                # Missing MetricReferences key entirely
            },
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'Total Operations: 2' in result
    assert 'GET /api/health' in result
    assert 'POST /api/webhook' in result
    # Should not show "Available Metrics:" for operations without metrics
    lines = result.split('\n')
    health_line_idx = next(i for i, line in enumerate(lines) if 'GET /api/health' in line)
    webhook_line_idx = next(i for i, line in enumerate(lines) if 'POST /api/webhook' in line)

    # Check that the next line after each operation doesn't contain "Available Metrics"
    if health_line_idx + 1 < len(lines):
        assert 'Available Metrics:' not in lines[health_line_idx + 1]
    if webhook_line_idx + 1 < len(lines):
        assert 'Available Metrics:' not in lines[webhook_line_idx + 1]


@pytest.mark.asyncio
async def test_list_service_operations_client_error(mock_aws_clients):
    """Test list_service_operations with AWS ClientError."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this action',
            }
        },
        operation_name='ListServices',
    )

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'AWS Error: User is not authorized to perform this action' in result


@pytest.mark.asyncio
async def test_list_service_operations_general_exception(mock_aws_clients):
    """Test list_service_operations with general exception."""
    mock_aws_clients['appsignals_client'].list_services.side_effect = Exception(
        'Unexpected error occurred'
    )

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'Error: Unexpected error occurred' in result


@pytest.mark.asyncio
async def test_list_service_operations_operations_api_client_error(mock_aws_clients):
    """Test list_service_operations when list_service_operations API fails."""
    # Mock successful service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response

    # Mock failure in list_service_operations API
    mock_aws_clients['appsignals_client'].list_service_operations.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded',
            }
        },
        operation_name='ListServiceOperations',
    )

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'AWS Error: Rate exceeded' in result


@pytest.mark.asyncio
async def test_list_service_operations_duplicate_metric_types(mock_aws_clients):
    """Test list_service_operations with duplicate metric types (should be deduplicated)."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response with duplicate metric types
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/test',
                'MetricReferences': [
                    {'MetricType': 'Latency'},
                    {'MetricType': 'Error'},
                    {'MetricType': 'Latency'},  # Duplicate
                    {'MetricType': 'Error'},  # Duplicate
                    {'MetricType': 'Fault'},
                ],
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'GET /api/test' in result
    # Should deduplicate metric types using set()
    assert 'Available Metrics:' in result
    # The exact order may vary due to set() behavior, but should contain all unique types
    metrics_line = next(line for line in result.split('\n') if 'Available Metrics:' in line)
    assert 'Latency' in metrics_line
    assert 'Error' in metrics_line
    assert 'Fault' in metrics_line
    # Count occurrences - each should appear only once in the metrics line
    assert metrics_line.count('Latency') == 1
    assert metrics_line.count('Error') == 1
    assert metrics_line.count('Fault') == 1


@pytest.mark.asyncio
async def test_list_service_operations_unknown_operation_name(mock_aws_clients):
    """Test list_service_operations with operations that have missing or unknown names."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response with missing/unknown operation names
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/test',
                'MetricReferences': [{'MetricType': 'Latency'}],
            },
            {
                # Missing 'Name' key
                'MetricReferences': [{'MetricType': 'Error'}],
            },
            {
                'Name': '',  # Empty name
                'MetricReferences': [{'MetricType': 'Fault'}],
            },
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'Total Operations: 3' in result
    assert 'GET /api/test' in result
    assert 'Unknown' in result  # Should show "Unknown" for missing names
    # Should handle empty names gracefully
    assert '🔍 GET Operations (1):' in result  # Only the valid GET operation
    assert '🔧 Other Operations (2):' in result  # The unknown operations


@pytest.mark.asyncio
async def test_list_service_operations_unknown_metric_types(mock_aws_clients):
    """Test list_service_operations with operations that have unknown metric types."""
    # Mock service discovery
    mock_services_response = {
        'ServiceSummaries': [
            {
                'KeyAttributes': {
                    'Name': 'test-service',
                    'Type': 'AWS::ECS::Service',
                }
            }
        ]
    }

    # Mock operations response with unknown metric types
    mock_operations_response = {
        'ServiceOperations': [
            {
                'Name': 'GET /api/test',
                'MetricReferences': [
                    {'MetricType': 'Latency'},
                    {},  # Missing MetricType key
                    {'MetricType': ''},  # Empty MetricType
                ],
            }
        ]
    }

    mock_aws_clients['appsignals_client'].list_services.return_value = mock_services_response
    mock_aws_clients[
        'appsignals_client'
    ].list_service_operations.return_value = mock_operations_response

    result = await list_service_operations(service_name='test-service', hours=24)

    assert 'GET /api/test' in result
    assert 'Available Metrics:' in result
    # Should handle unknown metric types gracefully
    metrics_line = next(line for line in result.split('\n') if 'Available Metrics:' in line)
    assert 'Latency' in metrics_line
    assert 'Unknown' in metrics_line  # Should show "Unknown" for missing/empty metric types
