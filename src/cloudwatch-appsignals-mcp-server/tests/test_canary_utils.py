"""Tests for canary_utils functions."""

import gzip
import json
import pytest
from awslabs.cloudwatch_appsignals_mcp_server.canary_utils import (
    _matches_bucket_pattern,
    analyze_canary_logs_with_time_window,
    analyze_har_file,
    analyze_iam_role_and_policies,
    analyze_log_files,
    analyze_screenshots,
    check_iam_exists_for_canary,
    check_lambda_permissions,
    check_resource_arns_correct,
    extract_disk_memory_usage_metrics,
    get_canary_code,
    get_canary_metrics_and_service_insights,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_canary_clients():
    """Mock AWS clients for testing."""
    return {
        'iam_client': MagicMock(),
        's3_client': MagicMock(),
        'synthetics_client': MagicMock(),
        'logs_client': MagicMock(),
        'lambda_client': MagicMock(),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'canary_config,expected_exists',
    [
        ({}, False),
        ({'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}, True),
    ],
)
async def test_check_iam_exists_for_canary(mock_canary_clients, canary_config, expected_exists):
    """Test check iam exists for canary."""
    mock_iam = mock_canary_clients['iam_client']

    if expected_exists:
        mock_iam.get_role.return_value = {'Role': {'RoleName': 'TestRole'}}
    else:
        mock_iam.get_role.side_effect = ClientError({'Error': {'Code': 'NoSuchEntity'}}, 'GetRole')

    result = await check_iam_exists_for_canary(canary_config, mock_iam)

    assert result['exists'] == expected_exists
    if not expected_exists and canary_config:
        assert 'does not exist' in result['error']
    elif not canary_config:
        assert 'No execution role configured' in result['error']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'policies,expected_basic,expected_vpc',
    [
        ([], False, False),
        (
            [{'PolicyArn': 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'}],
            True,
            False,
        ),
        (
            [
                {
                    'PolicyArn': 'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
                }
            ],
            True,
            True,
        ),
    ],
)
async def test_check_lambda_permissions(
    mock_canary_clients, policies, expected_basic, expected_vpc
):
    """Test check lambda permissions."""
    mock_iam = mock_canary_clients['iam_client']
    mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': policies}

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    result = await check_lambda_permissions(canary, mock_iam)

    assert result['has_basic_execution'] == expected_basic
    assert result['has_vpc_permissions'] == expected_vpc


@pytest.mark.asyncio
async def test_analyze_iam_role_and_policies_comprehensive(mock_canary_clients):
    """Test analyze iam role and policies comprehensive."""
    mock_iam = mock_canary_clients['iam_client']

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': True, 'role_name': 'TestRole'}
        mock_lambda_check.return_value = {
            'has_basic_execution': True,
            'has_managed_basic_execution': True,
            'has_vpc_permissions': False,
            'needs_vpc_check': True,
        }

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert '✅ IAM role `TestRole` exists' in result['checks']['iam_exists']
        assert '✅ Has Lambda basic execution permissions' in result['checks']['lambda_execution']


@pytest.mark.parametrize(
    's3_location,expected_correct',
    [
        ('', False),  # No S3 location
        ('s3://cw-syn-results-123456789012-us-east-1/', True),  # Standard bucket
        ('s3://custom-bucket/', True),  # Custom bucket
    ],
)
def test_check_resource_arns_correct(mock_canary_clients, s3_location, expected_correct):
    """Test check resource arns correct."""
    mock_iam = mock_canary_clients['iam_client']
    mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    if s3_location:
        canary['ArtifactS3Location'] = s3_location

    result = check_resource_arns_correct(canary, mock_iam)

    if not s3_location:
        assert result['correct'] is False
        assert 'No S3 artifact location configured' in result['error']
    else:
        assert 'correct' in result


@pytest.mark.parametrize(
    'actual_bucket,pattern,expected',
    [
        ('cw-syn-results-123456789012-us-east-1', 'cw-syn-results-123456789012-us-east-1', True),
        ('cw-syn-results-123456789012-us-east-1', 'cw-syn-results-*-us-east-1', True),
        ('wrong-bucket', 'cw-syn-results-*-us-east-1', False),
    ],
)
def test_matches_bucket_pattern(actual_bucket, pattern, expected):
    """Test matches bucket pattern."""
    assert _matches_bucket_pattern(actual_bucket, pattern) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'har_files,har_content,expected_status',
    [
        ([], None, 'no_har_files'),  # No HAR files
        ([{'Key': 'test.har'}], '{"log":{"entries":[]}}', 'empty_har'),  # Empty HAR
        ([{'Key': 'test.har'}], 'invalid json', 'error'),  # Invalid JSON
        (
            [{'Key': 'test.har'}],
            '{"log":{"entries":[{"request":{"url":"https://example.com"},"response":{"status":200},"timings":{"wait":100}}]}}',
            'analyzed',
        ),  # Valid HAR
    ],
)
async def test_analyze_har_file(mock_canary_clients, har_files, har_content, expected_status):
    """Test analyze har file."""
    mock_s3 = mock_canary_clients['s3_client']

    if har_content:
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: har_content.encode('utf-8'))
        }

    result = await analyze_har_file(mock_s3, 'bucket', har_files, True)
    assert result['status'] == expected_status


@pytest.mark.asyncio
async def test_analyze_har_file_with_failures_and_timing(mock_canary_clients):
    """Test analyze har file with failures and timing."""
    mock_s3 = mock_canary_clients['s3_client']
    har_data = {
        'log': {
            'entries': [
                {
                    'request': {'url': 'https://example.com/api'},
                    'response': {'status': 500, 'statusText': 'Internal Server Error'},
                    'timings': {'blocked': 600, 'wait': 1200, 'receive': 50},
                }
            ]
        }
    }
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(har_data).encode('utf-8'))
    }

    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har'}], True)

    assert result['status'] == 'analyzed'
    assert result['failed_requests'] == 1
    assert 'slowest requests' in ' '.join(result['insights'])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'screenshots,expected_status',
    [
        ([], 'no_screenshots'),  # No screenshots
        ([{'Key': 'step1-error-screenshot.png'}], 'analyzed'),  # Error screenshot
        ([{'Key': 'step1-timeout-screenshot.png'}], 'analyzed'),  # Timeout screenshot
    ],
)
async def test_analyze_screenshots(mock_canary_clients, screenshots, expected_status):
    """Test analyze screenshots."""
    result = await analyze_screenshots(
        mock_canary_clients['s3_client'], 'bucket', screenshots, True
    )
    assert result['status'] == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'logs,log_content,expected_patterns',
    [
        ([], None, 0),  # No logs
        ([{'Key': 'test.log'}], 'INFO: Test completed', 0),  # No errors
        (
            [{'Key': 'test.log'}],
            'ERROR: Navigation timeout\nERROR: Element not found',
            2,
        ),  # Multiple errors
    ],
)
async def test_analyze_log_files(mock_canary_clients, logs, log_content, expected_patterns):
    """Test analyze log files."""
    mock_s3 = mock_canary_clients['s3_client']

    if log_content:
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: log_content.encode('utf-8'))
        }

    result = await analyze_log_files(mock_s3, 'bucket', logs, True)

    if logs:
        assert result['status'] == 'analyzed'
        if expected_patterns > 0:
            assert result['error_patterns_found'] == expected_patterns
    else:
        assert result['status'] == 'no_logs'


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_metrics():
    """Test extract disk memory usage metrics."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs,
    ):
        mock_synthetics.get_canary.return_value = {'Canary': {'Name': 'test-canary'}}
        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result

        mock_synthetics.get_canary.return_value = {
            'Canary': {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        }
        mock_logs.start_query.return_value = {'queryId': 'test-query'}
        mock_logs.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'value': '2024-01-01T12:00:00Z'},
                    {'value': '100.5'},
                    {'value': '25.0'},
                    {'value': '512.0'},
                ]
            ],
        }

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'maxSyntheticsMemoryUsageInMB' in result


@pytest.mark.asyncio
async def test_analyze_canary_logs_with_time_window():
    """Test analyze canary logs with time window."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs:
        canary = {'Name': 'test-canary'}
        failure_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = await analyze_canary_logs_with_time_window(
            'test-canary', failure_time, canary, 5, 'us-east-1'
        )
        assert result['status'] == 'error'

        canary = {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        mock_logs.filter_log_events.return_value = {
            'events': [{'timestamp': 1704110400000, 'message': 'ERROR: Test error message'}]
        }

        result = await analyze_canary_logs_with_time_window(
            'test-canary', failure_time, canary, 5, 'us-east-1'
        )
        assert result['status'] == 'success'
        assert len(result['error_events']) > 0


@pytest.mark.asyncio
async def test_get_canary_code():
    """Test get canary code."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        canary = {'Code': {'SourceLocationArn': 'arn:aws:s3:::test-bucket/code.zip'}}
        result = await get_canary_code(canary, 'us-east-1')
        assert 'error' in result

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {'Handler': 'index.handler'},
        }
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result
        assert result['memory_size'] == 128


@pytest.mark.asyncio
async def test_get_canary_metrics_and_service_insights():
    """Test get canary metrics and service insights."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.audit_utils.execute_audit_api'
    ) as mock_audit:
        mock_audit.return_value = 'Mock audit results'
        result = await get_canary_metrics_and_service_insights('test-canary', 'us-east-1')
        assert isinstance(result, str)

        mock_audit.side_effect = Exception('API unavailable')
        result = await get_canary_metrics_and_service_insights('test-canary', 'us-east-1')
        assert 'ListAuditFindings API unavailable' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_integration():
    """Test analyze canary failures integration."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.aws_clients.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.aws_clients.iam_client'),
        patch('awslabs.cloudwatch_appsignals_mcp_server.aws_clients.s3_client') as mock_s3,
        patch('awslabs.cloudwatch_appsignals_mcp_server.aws_clients.sts_client') as mock_sts,
        patch('subprocess.run') as mock_subprocess,
    ):
        from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures

        mock_synthetics.get_canary_runs.return_value = {
            'CanaryRuns': [
                {
                    'Id': 'run-failed-1',
                    'Status': {'State': 'FAILED', 'StateReason': 'Navigation timeout'},
                    'Timeline': {'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)},
                }
            ]
        }

        mock_synthetics.get_canary.return_value = {
            'Canary': {
                'Name': 'test-canary',
                'ArtifactS3Location': 's3://test-bucket/artifacts/',
                'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
            }
        }

        mock_sts.get_caller_identity.return_value = {'Arn': 'arn:aws:iam::123456789012:user/test'}
        mock_s3.list_objects_v2.return_value = {'Contents': []}
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Analysis complete')

        result = await analyze_canary_failures('test-canary', 'us-east-1')

        assert (
            'Error in comprehensive failure analysis' in result
            or '🔍 Comprehensive Failure Analysis for test-canary' in result
        )


@pytest.mark.asyncio
async def test_check_lambda_permissions_custom_policies():
    """Test check lambda permissions custom policies."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.return_value = {'Policy': {'DefaultVersionId': 'v1'}}
    mock_iam.get_policy_version.return_value = {
        'PolicyVersion': {
            'Document': {
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Action': [
                            'logs:CreateLogGroup',
                            'logs:CreateLogStream',
                            'logs:PutLogEvents',
                        ],
                    }
                ]
            }
        }
    }

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    result = await check_lambda_permissions(canary, mock_iam)

    assert result['has_basic_execution'] is True
    assert 'CustomPolicy' in result['attached_policies'][0]


@pytest.mark.asyncio
async def test_check_lambda_permissions_policy_errors():
    """Test check lambda permissions policy errors."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.side_effect = Exception('Policy parsing failed')

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    result = await check_lambda_permissions(canary, mock_iam)

    assert result['has_basic_execution'] is False


@pytest.mark.asyncio
async def test_analyze_har_file_html_complete_json():
    """Test analyze har file html with complete JSON that requires brace counting."""
    mock_s3 = MagicMock()

    # HTML content that will trigger the brace counting logic
    # Key: file must end with .har.html to trigger HTML parsing path
    html_content = 'var harOutput = {"log":{"entries":[]}};'

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=html_content.encode('utf-8')))
    }

    # Use .har.html extension to trigger the HTML parsing path with brace counting
    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har.html'}], True)

    # This covers lines 216-220: brace counting logic where brace_count == 0 and json_end > 0
    assert result['status'] == 'empty_har'  # Empty entries array


@pytest.mark.asyncio
async def test_analyze_har_file_html_incomplete_json():
    """Test analyze har file html incomplete json."""
    mock_s3 = MagicMock()

    html_content = 'var harOutput = {"log":{"entries":[{"request":{"url":"https://example.com"}'
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
    }

    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har.html'}], True)
    assert result['status'] == 'error'
    assert 'Could not find end of HAR JSON data' in result['insights'][0]


@pytest.mark.asyncio
async def test_analyze_har_file_timing_breakdown():
    """Test analyze har file timing breakdown."""
    mock_s3 = MagicMock()
    har_data = {
        'log': {
            'entries': [
                {
                    'request': {'url': 'https://slow-example.com/api'},
                    'response': {'status': 200},
                    'timings': {
                        'blocked': 600,
                        'dns': 50,
                        'connect': 100,
                        'ssl': 200,
                        'send': 10,
                        'wait': 1200,
                        'receive': 40,
                    },
                }
            ]
        }
    }
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: json.dumps(har_data).encode('utf-8'))
    }

    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har'}], True)

    assert result['status'] == 'analyzed'
    insights_text = ' '.join(result['insights'])
    assert 'requests with high blocking time' in insights_text
    assert 'requests with high server wait time' in insights_text


@pytest.mark.asyncio
async def test_check_resource_arns_correct_policy_errors():
    """Test check resource arns correct policy errors."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.side_effect = ClientError({'Error': {'Code': 'NoSuchEntity'}}, 'GetPolicy')

    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        'ArtifactS3Location': 's3://test-bucket/',
    }
    result = check_resource_arns_correct(canary, mock_iam)

    assert result['correct'] is False


@pytest.mark.asyncio
async def test_check_resource_arns_correct_s3_mismatch():
    """Test check resource arns correct s3 mismatch."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.return_value = {'Policy': {'DefaultVersionId': 'v1'}}
    mock_iam.get_policy_version.return_value = {
        'PolicyVersion': {
            'Document': {
                'Statement': [{'Effect': 'Allow', 'Resource': 'arn:aws:s3:::wrong-bucket/*'}]
            }
        }
    }

    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        'ArtifactS3Location': 's3://correct-bucket/',
    }
    result = check_resource_arns_correct(canary, mock_iam)

    assert result['correct'] is False


@pytest.mark.asyncio
async def test_analyze_canary_logs_no_engine_arn():
    """Test analyze canary logs no engine arn."""
    canary = {'Name': 'test-canary'}
    failure_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = await analyze_canary_logs_with_time_window(
        'test-canary', failure_time, canary, 5, 'us-east-1'
    )
    assert result['status'] == 'error'


@pytest.mark.asyncio
async def test_analyze_canary_logs_resource_not_found():
    """Test analyze canary logs resource not found."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs:
        mock_logs.filter_log_events.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}}, 'FilterLogEvents'
        )

        canary = {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        failure_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = await analyze_canary_logs_with_time_window(
            'test-canary', failure_time, canary, 5, 'us-east-1'
        )
        assert result['status'] == 'no_logs'


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_no_engine_configs():
    """Test extract disk memory usage no engine configs."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
    ) as mock_synthetics:
        mock_synthetics.get_canary.return_value = {'Canary': {'Name': 'test-canary'}}

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result
        assert 'No EngineArn or EngineConfigs found' in result['error']


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_with_engine_configs():
    """Test extract disk memory usage with engine configs."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs,
    ):
        mock_synthetics.get_canary.return_value = {
            'Canary': {
                'EngineConfigs': [
                    {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
                ]
            }
        }
        mock_logs.start_query.return_value = {'queryId': 'test-query'}
        mock_logs.get_query_results.return_value = {'status': 'Complete', 'results': []}

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result
        assert 'No telemetry data found' in result['error']


@pytest.mark.asyncio
async def test_get_canary_code_with_engine_configs():
    """Test get canary code with engine configs."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        canary = {
            'EngineConfigs': [
                {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
            ],
            'Code': {'Handler': 'index.handler'},
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result
        assert result['memory_size'] == 128


@pytest.mark.asyncio
async def test_check_iam_exists_access_denied():
    """Test check iam exists access denied."""
    mock_iam = MagicMock()
    mock_iam.get_role.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetRole'
    )

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    result = await check_iam_exists_for_canary(canary, mock_iam)

    assert result['exists'] is False
    assert 'Cannot check role' in result['error']
    assert 'Access denied' in result['error']


@pytest.mark.asyncio
async def test_check_lambda_permissions_no_role():
    """Test check lambda permissions no role."""
    mock_iam = MagicMock()

    canary = {}
    result = await check_lambda_permissions(canary, mock_iam)

    assert result['has_basic_execution'] is False
    assert result['has_vpc_permissions'] is False
    assert result['needs_vpc_check'] is False
    assert 'No execution role configured' in result['error']


@pytest.mark.asyncio
async def test_analyze_log_files_gzipped_content():
    """Test analyze log files gzipped content."""
    mock_s3 = MagicMock()

    log_content = 'ERROR: Navigation timeout\nINFO: Test completed'
    gzipped_content = gzip.compress(log_content.encode('utf-8'))

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: gzipped_content),
        'ContentEncoding': 'gzip',
    }

    result = await analyze_log_files(mock_s3, 'bucket', [{'Key': 'test.log.gz'}], True)

    assert result['status'] == 'analyzed'
    assert result['error_patterns_found'] == 1


@pytest.mark.asyncio
async def test_analyze_har_file_gzipped_content():
    """Test analyze har file gzipped content."""
    mock_s3 = MagicMock()

    har_data = {'log': {'entries': []}}
    gzipped_content = gzip.compress(json.dumps(har_data).encode('utf-8'))

    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: gzipped_content),
        'ContentEncoding': 'gzip',
    }

    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har.gz'}], True)

    assert result['status'] == 'empty_har'


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_query_timeout():
    """Test extract disk memory usage query timeout."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs,
    ):
        mock_synthetics.get_canary.return_value = {
            'Canary': {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        }
        mock_logs.start_query.return_value = {'queryId': 'test-query'}

        mock_logs.get_query_results.return_value = {'status': 'Complete', 'results': []}

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result
        assert 'No telemetry data found in canary logs' in result['error']


@pytest.mark.asyncio
async def test_get_canary_code_with_layers():
    """Test get canary code with layers."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 256,
                'Timeout': 60,
                'EphemeralStorage': {'Size': 1024},
                'Layers': [
                    {'Arn': 'arn:aws:lambda:us-east-1:123456789012:layer:test-layer:1'},
                    {'Arn': 'arn:aws:lambda:us-east-1:123456789012:layer:another-layer:2'},
                ],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {'Handler': 'index.handler'},
        }

        result = await get_canary_code(canary, 'us-east-1')

        assert result['memory_size'] == 256
        assert result['timeout'] == 60
        assert result['layers_count'] == 2
        assert 'function_name' in result


@pytest.mark.asyncio
async def test_analyze_iam_role_missing_execution():
    """Test analyze iam role missing execution."""
    mock_iam = MagicMock()

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': True, 'role_name': 'TestRole'}
        mock_lambda_check.return_value = {
            'has_basic_execution': False,
            'has_managed_basic_execution': False,
            'has_vpc_permissions': False,
            'needs_vpc_check': True,
        }

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert (
            '❌ Missing Lambda basic execution permissions' in result['checks']['lambda_execution']
        )
        assert 'IAM role lacks Lambda execution permissions' in result['issues_found']


@pytest.mark.asyncio
async def test_analyze_iam_role_custom_execution():
    """Test analyze iam role custom execution."""
    mock_iam = MagicMock()

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': True, 'role_name': 'TestRole'}
        mock_lambda_check.return_value = {
            'has_basic_execution': True,
            'has_managed_basic_execution': False,
            'has_vpc_permissions': False,
            'needs_vpc_check': True,
        }

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert (
            '✅ Has custom Lambda execution permissions (sufficient)'
            in result['checks']['lambda_execution']
        )


@pytest.mark.asyncio
async def test_analyze_iam_role_with_error():
    """Test analyze iam role with error."""
    mock_iam = MagicMock()

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': True, 'role_name': 'TestRole'}
        mock_lambda_check.return_value = {'error': 'Permission denied'}

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert (
            '❌ IAM role check failed: Permission denied' in result['checks']['lambda_execution']
        )
        assert 'Cannot verify IAM permissions: Permission denied' in result['issues_found']


@pytest.mark.asyncio
async def test_analyze_har_file_html_no_var():
    """Test analyze har file html no var."""
    mock_s3 = MagicMock()

    html_content = '<html><body>No harOutput variable here</body></html>'
    mock_s3.get_object.return_value = {
        'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
    }

    result = await analyze_har_file(mock_s3, 'bucket', [{'Key': 'test.har.html'}], True)
    assert result['status'] == 'error'
    assert 'Could not find harOutput variable in HTML' in result['insights'][0]


@pytest.mark.asyncio
async def test_analyze_log_files_read_error():
    """Test analyze log files read error."""
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception('S3 read failed')

    result = await analyze_log_files(mock_s3, 'bucket', [{'Key': 'test.log'}], True)

    assert result['status'] == 'analyzed'
    assert any('Could not read log' in insight for insight in result['insights'])


@pytest.mark.asyncio
async def test_check_resource_arns_correct_with_s3_prefix():
    """Test check resource arns correct with s3 prefix."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {'AttachedPolicies': []}

    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        'ArtifactS3Location': 'test-bucket/prefix/',
    }
    result = check_resource_arns_correct(canary, mock_iam)

    assert 'correct' in result
    assert result['actual_bucket'] == 'test-bucket'


@pytest.mark.asyncio
async def test_get_canary_code_source_location_arn():
    """Test get canary code source location arn."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
        ) as mock_lambda,
        patch('requests.get') as mock_requests,
        patch('tempfile.NamedTemporaryFile') as mock_temp,
        patch('zipfile.ZipFile') as mock_zip,
        patch('os.unlink'),
    ):
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        mock_lambda.get_layer_version_by_arn.return_value = {
            'Content': {'Location': 'https://s3.amazonaws.com/layer.zip'}
        }

        mock_zip_instance = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_zip_instance
        mock_zip_instance.namelist.return_value = ['nodejs/node_modules/index.js']
        mock_zip_instance.open.return_value.__enter__.return_value.read.return_value = (
            b'console.log("test");'
        )

        mock_temp.return_value.__enter__.return_value.name = '/tmp/test.zip'
        mock_requests.return_value.content = b'zip content'

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {
                'SourceLocationArn': 'arn:aws:lambda:us-east-1:123456789012:layer:test:1',
                'Handler': 'index.handler',
            },
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result


@pytest.mark.asyncio
async def test_get_canary_code_custom_layers():
    """Test get canary code custom layers."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
        ) as mock_lambda,
        patch('requests.get') as mock_requests,
        patch('tempfile.NamedTemporaryFile') as mock_temp,
        patch('zipfile.ZipFile') as mock_zip,
        patch('os.unlink'),
    ):
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [{'Arn': 'arn:aws:lambda:us-east-1:123456789012:layer:custom:1'}],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        mock_lambda.get_layer_version_by_arn.return_value = {
            'Content': {'Location': 'https://s3.amazonaws.com/layer.zip'}
        }

        mock_zip_instance = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_zip_instance
        mock_zip_instance.namelist.return_value = ['index.js']
        mock_zip_instance.open.return_value.__enter__.return_value.read.return_value = (
            b'console.log("custom layer");'
        )

        mock_temp.return_value.__enter__.return_value.name = '/tmp/test.zip'
        mock_requests.return_value.content = b'zip content'

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {'Handler': 'index.handler'},
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result
        assert 'code_content' in result


@pytest.mark.asyncio
async def test_get_canary_code_function_code_fallback():
    """Test get canary code function code fallback."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
        ) as mock_lambda,
        patch('requests.get') as mock_requests,
        patch('tempfile.NamedTemporaryFile') as mock_temp,
        patch('zipfile.ZipFile') as mock_zip,
        patch('os.unlink'),
    ):
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        mock_zip_instance = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_zip_instance
        mock_zip_instance.namelist.return_value = ['index.js']
        mock_zip_instance.open.return_value.__enter__.return_value.read.return_value = (
            b'exports.handler = async () => {};'
        )

        mock_temp.return_value.__enter__.return_value.name = '/tmp/test.zip'
        mock_requests.return_value.content = b'zip content'

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {'Handler': 'index.handler'},
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result
        assert 'code_content' in result


@pytest.mark.asyncio
async def test_get_canary_code_extraction_error():
    """Test get canary code extraction error."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        with patch('requests.get', side_effect=Exception('Download failed')):
            canary = {
                'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
                'Code': {'Handler': 'index.handler'},
            }

            result = await get_canary_code(canary, 'us-east-1')
            assert 'function_name' in result
            assert 'Could not extract function code' in result['code_content']


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_invalid_results():
    """Test extract disk memory usage invalid results."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs,
    ):
        mock_synthetics.get_canary.return_value = {
            'Canary': {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        }
        mock_logs.start_query.return_value = {'queryId': 'test-query'}

        mock_logs.get_query_results.return_value = {
            'status': 'Complete',
            'results': [[{'value': '2024-01-01T12:00:00Z'}]],
        }

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result
        assert 'No valid telemetry metrics found' in result['error']


@pytest.mark.asyncio
async def test_coverage_check_lambda_permissions_string_actions():
    """Test coverage check lambda permissions string actions."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.return_value = {'Policy': {'DefaultVersionId': 'v1'}}
    mock_iam.get_policy_version.return_value = {
        'PolicyVersion': {
            'Document': {'Statement': [{'Effect': 'Allow', 'Action': 'logs:CreateLogGroup'}]}
        }
    }

    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
    result = await check_lambda_permissions(canary, mock_iam)

    assert result['has_basic_execution'] is True


@pytest.mark.asyncio
async def test_coverage_check_resource_arns_policy_exception():
    """Test coverage check resource arns policy exception."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.side_effect = Exception('General error')

    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        'ArtifactS3Location': 's3://test-bucket/',
    }
    result = check_resource_arns_correct(canary, mock_iam)

    assert 'correct' in result


@pytest.mark.asyncio
async def test_coverage_check_resource_arns_string_resources():
    """Test coverage check resource arns string resources."""
    mock_iam = MagicMock()
    mock_iam.list_attached_role_policies.return_value = {
        'AttachedPolicies': [{'PolicyArn': 'arn:aws:iam::123456789012:policy/CustomPolicy'}]
    }

    mock_iam.get_policy.return_value = {'Policy': {'DefaultVersionId': 'v1'}}
    mock_iam.get_policy_version.return_value = {
        'PolicyVersion': {
            'Document': {
                'Statement': [{'Effect': 'Allow', 'Resource': 'arn:aws:s3:::test-bucket/*'}]
            }
        }
    }

    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole',
        'ArtifactS3Location': 's3://test-bucket/',
    }
    result = check_resource_arns_correct(canary, mock_iam)

    assert result['correct'] is True


@pytest.mark.asyncio
async def test_coverage_analyze_canary_logs_string_failure_time():
    """Test coverage analyze canary logs string failure time."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs:
        mock_logs.filter_log_events.return_value = {'events': []}

        canary = {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        failure_time = '2024-01-01T12:00:00Z'

        result = await analyze_canary_logs_with_time_window(
            'test-canary', failure_time, canary, 5, 'us-east-1'
        )
        assert result['status'] == 'success'


@pytest.mark.asyncio
async def test_coverage_analyze_canary_logs_other_client_error():
    """Test coverage analyze canary logs other client error."""
    with patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs:
        mock_logs.filter_log_events.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'FilterLogEvents'
        )

        canary = {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        failure_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = await analyze_canary_logs_with_time_window(
            'test-canary', failure_time, canary, 5, 'us-east-1'
        )
        assert result['status'] == 'error'
        assert 'CloudWatch logs access error' in result['insights'][0]


@pytest.mark.asyncio
async def test_coverage_extract_disk_memory_usage_query_running():
    """Test coverage extract disk memory usage query running."""
    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
        ) as mock_synthetics,
        patch('awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client') as mock_logs,
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        mock_synthetics.get_canary.return_value = {
            'Canary': {'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test'}
        }
        mock_logs.start_query.return_value = {'queryId': 'test-query'}

        mock_logs.get_query_results.return_value = {'status': 'Running'}

        result = await extract_disk_memory_usage_metrics('test-canary', 'us-east-1')
        assert 'error' in result


@pytest.mark.asyncio
async def test_coverage_get_canary_code_layer_exception():
    """Test coverage get canary code layer exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [{'Arn': 'arn:aws:lambda:us-east-1:123456789012:layer:custom:1'}],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        mock_lambda.get_layer_version_by_arn.side_effect = Exception('Layer processing failed')

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {'Handler': 'index.handler'},
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result


@pytest.mark.asyncio
async def test_coverage_get_canary_code_source_location_exception():
    """Test coverage get canary code source location exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.lambda_client'
    ) as mock_lambda:
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'MemorySize': 128,
                'Timeout': 30,
                'EphemeralStorage': {'Size': 512},
                'Layers': [],
            },
            'Code': {'Location': 'https://s3.amazonaws.com/bucket/code.zip'},
        }

        mock_lambda.get_layer_version_by_arn.side_effect = Exception('Source location failed')

        canary = {
            'EngineArn': 'arn:aws:lambda:us-east-1:123456789012:function:test',
            'Code': {
                'SourceLocationArn': 'arn:aws:lambda:us-east-1:123456789012:layer:test:1',
                'Handler': 'index.handler',
            },
        }

        result = await get_canary_code(canary, 'us-east-1')
        assert 'function_name' in result


@pytest.mark.asyncio
async def test_coverage_analyze_iam_role_no_exists():
    """Test coverage analyze iam role no exists."""
    mock_iam = MagicMock()

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': False, 'error': 'Role does not exist'}
        mock_lambda_check.return_value = {
            'has_basic_execution': True,
            'has_managed_basic_execution': True,
            'has_vpc_permissions': True,
            'needs_vpc_check': False,
        }

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert '❌ IAM role does not exist' in result['checks']['iam_exists']
        assert 'Role does not exist' in result['issues_found']


@pytest.mark.asyncio
async def test_coverage_analyze_iam_role_with_vpc():
    """Test coverage analyze iam role with vpc."""
    mock_iam = MagicMock()

    with (
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_iam_exists_for_canary'
        ) as mock_iam_check,
        patch(
            'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.check_lambda_permissions'
        ) as mock_lambda_check,
    ):
        mock_iam_check.return_value = {'exists': True, 'role_name': 'TestRole'}
        mock_lambda_check.return_value = {
            'has_basic_execution': True,
            'has_managed_basic_execution': True,
            'has_vpc_permissions': True,
            'needs_vpc_check': False,
        }

        canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/TestRole'}
        result = await analyze_iam_role_and_policies(canary, mock_iam, 'us-east-1')

        assert result['status'] == 'completed'
        assert '✅ Has Lambda VPC permissions' in result['checks']['lambda_vpc']


def test_check_resource_arns_correct_no_execution_role():
    """Test check_resource_arns_correct with no execution role."""
    canary = {}
    iam_client = MagicMock()

    result = check_resource_arns_correct(canary, iam_client)

    assert result['correct'] is False
    assert 'No execution role configured' in result['error']


def test_check_resource_arns_correct_iam_exception():
    """Test check_resource_arns_correct with IAM client exception."""
    canary = {
        'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/test-role',
        'ArtifactS3Location': 's3://test-bucket/path/',
    }
    iam_client = MagicMock()
    iam_client.list_attached_role_policies.side_effect = Exception('IAM error')

    result = check_resource_arns_correct(canary, iam_client)

    assert result['correct'] is False
    assert 'IAM error' in result['error']


@pytest.mark.asyncio
async def test_analyze_canary_logs_with_time_window_exception():
    """Test analyze_canary_logs_with_time_window with exception during processing."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client'
    ) as mock_logs_client:
        mock_logs_client.describe_log_groups.side_effect = Exception('Logs error')

        result = await analyze_canary_logs_with_time_window(
            'test-canary', '2024-01-01T00:00:00Z', {}, 3
        )

        assert result['status'] == 'error'
        assert 'Log analysis failed:' in result['insights'][0]


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_metrics_exception():
    """Test extract_disk_memory_usage_metrics with exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.synthetics_client'
    ) as mock_synthetics_client:
        mock_synthetics_client.get_canary.side_effect = Exception('CloudWatch error')

        result = await extract_disk_memory_usage_metrics('test-canary')

        assert 'error' in result
        assert 'Resource analysis failed: CloudWatch error' in result['error']


@pytest.mark.asyncio
async def test_extract_disk_memory_usage_metrics_telemetry_exception():
    """Test extract_disk_memory_usage_metrics with telemetry processing exception."""
    with patch(
        'awslabs.cloudwatch_appsignals_mcp_server.canary_utils.logs_client'
    ) as mock_logs_client:
        # Mock successful log group check but fail during telemetry processing
        mock_logs_client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': '/aws/synthetics/canary/test-canary'}]
        }
        mock_logs_client.start_query.return_value = {'queryId': 'test-query-id'}
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-01T00:00:00Z'},
                    {'field': '@message', 'value': 'invalid json'},
                ]
            ],
        }

        result = await extract_disk_memory_usage_metrics('test-canary')

        # Should handle JSON parsing errors gracefully
        assert 'error' in result
        assert 'Resource analysis failed:' in result['error']


@pytest.mark.asyncio
async def test_check_iam_exists_for_canary_no_such_entity():
    """Test check_iam_exists_for_canary with NoSuchEntity error."""
    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/nonexistent-role'}
    iam_client = MagicMock()

    error_response = {'Error': {'Code': 'NoSuchEntity', 'Message': 'Role does not exist'}}
    iam_client.get_role.side_effect = ClientError(error_response, 'GetRole')  # type: ignore

    result = await check_iam_exists_for_canary(canary, iam_client)

    assert result['exists'] is False
    assert "Role 'nonexistent-role' does not exist" in result['error']


@pytest.mark.asyncio
async def test_check_iam_exists_for_canary_other_client_error():
    """Test check_iam_exists_for_canary with other ClientError."""
    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/test-role'}
    iam_client = MagicMock()

    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
    iam_client.get_role.side_effect = ClientError(error_response, 'GetRole')  # type: ignore

    result = await check_iam_exists_for_canary(canary, iam_client)

    assert result['exists'] is False
    assert 'Cannot check role: Access denied' in result['error']


@pytest.mark.asyncio
async def test_check_lambda_permissions_exception():
    """Test check_lambda_permissions with exception."""
    canary = {'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/test-role'}
    iam_client = MagicMock()
    iam_client.list_attached_role_policies.side_effect = Exception('IAM error')

    result = await check_lambda_permissions(canary, iam_client)

    assert result['has_basic_execution'] is False
    assert result['has_vpc_permissions'] is False
    assert result['needs_vpc_check'] is False
    assert 'IAM error' in result['error']


@pytest.mark.asyncio
async def test_get_canary_code_exception():
    """Test get_canary_code with general exception."""
    canary = {}  # Invalid canary to trigger exception

    result = await get_canary_code(canary)

    assert 'error' in result
    assert 'No EngineArn or EngineConfigs found for canary' in result['error']
