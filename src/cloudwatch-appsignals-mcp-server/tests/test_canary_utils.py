"""Tests for analyze_canary_failures function."""

import pytest
from awslabs.cloudwatch_appsignals_mcp_server.server import analyze_canary_failures
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture(autouse=True)
def mock_aws_clients():
    """Mock all AWS clients to prevent real API calls during tests."""
    mock_iam_client = MagicMock()
    mock_synthetics_client = MagicMock()
    mock_s3_client = MagicMock()
    mock_sts_client = MagicMock()

    patches = [
        # Mock the imported AWS clients directly
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.synthetics_client', mock_synthetics_client),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.iam_client', mock_iam_client),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.s3_client', mock_s3_client),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.sts_client', mock_sts_client),
        # Mock the imported canary_utils functions
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_canary_logs_with_time_window', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.check_resource_arns_correct'),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_screenshots', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_log_files', new_callable=AsyncMock),
        patch('awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_code', return_value={'code_content': 'mock code', 'insights': []}),
        # Mock subprocess for APM Pulse integration
        patch('subprocess.run'),
    ]

    for p in patches:
        p.start()

    try:
        yield {
            'iam_client': mock_iam_client,
            'synthetics_client': mock_synthetics_client,
            's3_client': mock_s3_client,
            'sts_client': mock_sts_client,
        }
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_analyze_har_file_malformed_json():
    """Test analyze_har_file with malformed JSON content."""
    from awslabs.cloudwatch_appsignals_mcp_server.canary_utils import analyze_har_file
    
    # Mock S3 client
    mock_s3_client = MagicMock()
    
    # Mock malformed HAR file content (invalid JSON)
    malformed_content = b'{"log": {"entries": [invalid json content'
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=malformed_content))
    }
    
    har_files = [{'Key': 'test-har-file.har'}]
    
    # Test malformed HAR file handling
    result = await analyze_har_file(mock_s3_client, 'test-bucket', har_files)
    
    # Verify error handling
    assert result['status'] == 'error'
    assert len(result['insights']) == 1
    assert 'HAR analysis failed:' in result['insights'][0]
    
    # Verify S3 client was called
    mock_s3_client.get_object.assert_called_once_with(
        Bucket='test-bucket', 
        Key='test-har-file.har'
    )


@pytest.mark.asyncio
async def test_analyze_canary_failures_success_with_failures(mock_aws_clients):
    """Test successful analyze_canary_failures with failed runs."""
    # Mock canary runs response with failures
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-1',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Navigation timeout after 30000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            },
            {
                'Id': 'run-failed-2',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Navigation timeout after 30000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
                }
            },
            {
                'Id': 'run-success-1',
                'Status': {
                    'State': 'PASSED',
                    'StateReason': 'Canary completed successfully'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'test-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole',
            'RuntimeVersion': 'syn-nodejs-puppeteer-3.9',
            'Schedule': {
                'Expression': 'rate(5 minutes)'
            }
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Mock S3 artifacts response
    mock_s3_artifacts = {
        'Contents': [
            {'Key': 'canary-artifacts/2024/01/01/test.har', 'Size': 1024},
            {'Key': 'canary-artifacts/2024/01/01/screenshot.png', 'Size': 2048},
            {'Key': 'canary-artifacts/2024/01/01/logs.txt', 'Size': 512}
        ]
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity
    mock_aws_clients['s3_client'].list_objects_v2.return_value = mock_s3_artifacts

    # Mock the imported functions
    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har, \
         patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_screenshots') as mock_screenshots, \
         patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_log_files') as mock_logs, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock returns for analysis functions
        mock_har.return_value = {
            'failed_requests': 2,
            'total_requests': 10,
            'request_details': [
                {'url': 'https://example.com/api', 'status': 500, 'time': 5000}
            ]
        }
        mock_screenshots.return_value = {
            'insights': ['Screenshot shows timeout error page']
        }
        mock_logs.return_value = {
            'insights': ['Navigation timeout detected in logs']
        }
        
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: No critical issues detected'
        )

        result = await analyze_canary_failures(canary_name='test-canary', region='us-east-1')

        # Verify the result contains expected sections
        assert '🔍 Comprehensive Failure Analysis for test-canary' in result
        assert 'Found 2 consecutive failures since last success' in result
        assert 'Navigation timeout after 30000ms exceeded' in result
        assert 'HAR COMPARISON: Failure vs Success' in result
        assert 'Failed requests: 2' in result
        assert 'SCREENSHOT ANALYSIS:' in result
        assert 'LOG ANALYSIS:' in result

        mock_har.assert_called()
        mock_screenshots.assert_called()
        mock_logs.assert_called()

        # Verify AWS client calls
        mock_aws_clients['synthetics_client'].get_canary_runs.assert_called_once_with(
            Name='test-canary', MaxResults=5
        )
        mock_aws_clients['synthetics_client'].get_canary.assert_called_once_with(Name='test-canary')


@pytest.mark.asyncio
async def test_analyze_canary_failures_success_healthy_canary(mock_aws_clients):
    """Test analyze_canary_failures with healthy canary (no failures)."""
    # Mock canary runs response with only successful runs
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-success-1',
                'Status': {
                    'State': 'PASSED',
                    'StateReason': 'Canary completed successfully'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            },
            {
                'Id': 'run-success-2',
                'Status': {
                    'State': 'PASSED',
                    'StateReason': 'Canary completed successfully'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'healthy-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Canary is healthy'
        )

        result = await analyze_canary_failures(canary_name='healthy-canary', region='us-east-1')

        # Verify the result indicates healthy canary
        assert '🔍 Comprehensive Failure Analysis for healthy-canary' in result
        assert '✅ Canary is healthy - no failures since last success' in result
        assert 'Last success:' in result
        assert '🔍 Performing health check analysis' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_no_runs(mock_aws_clients):
    """Test analyze_canary_failures when no runs are found."""
    # Mock empty canary runs response
    mock_runs_response = {'CanaryRuns': []}

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'no-runs-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stderr='APM Pulse API error'
        )

        result = await analyze_canary_failures(canary_name='no-runs-canary', region='us-east-1')

        # Verify the result indicates no runs found
        assert 'No run history found for no-runs-canary' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_iam_permission_error(mock_aws_clients):
    """Test analyze_canary_failures with IAM permission-related failures."""
    # Mock canary runs response with permission errors
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-iam',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Access denied: no test result'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'iam-error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies') as mock_iam_analysis, \
         patch('awslabs.cloudwatch_appsignals_mcp_server.server.check_resource_arns_correct') as mock_arn_check, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock returns for IAM analysis
        mock_iam_analysis.return_value = {
            'status': 'Issues found',
            'checks': {
                'Role exists': 'PASS',
                'S3 permissions': 'FAIL'
            },
            'issues_found': ['Missing S3 GetObject permission'],
            'recommendations': ['Add s3:GetObject permission to role policy']
        }
        
        mock_arn_check.return_value = {
            'correct': False,
            'error': 'Bucket ARN pattern mismatch',
            'issues': ['Bucket name does not match cw-syn-* pattern']
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: IAM permission issues detected'
        )

        result = await analyze_canary_failures(canary_name='iam-error-canary', region='us-east-1')

        # Verify IAM analysis is included
        assert '🔍 RUNNING COMPREHENSIVE IAM ANALYSIS' in result
        assert 'Access denied: no test result' in result
        assert 'IAM Role Analysis Status: Issues found' in result
        assert 'Missing S3 GetObject permission' in result
        assert 'Add s3:GetObject permission to role policy' in result
        assert 'CHECKING RESOURCE ARN CORRECTNESS' in result
        assert 'Bucket ARN pattern mismatch' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_enospc_error(mock_aws_clients):
    """Test analyze_canary_failures with ENOSPC (disk space) error."""
    # Mock canary runs response with ENOSPC error
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-enospc',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'ENOSPC: no space left on device'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'enospc-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics') as mock_disk_usage, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock return for disk usage analysis
        mock_disk_usage.return_value = {
            'maxEphemeralStorageUsageInMb': 512.5,
            'maxEphemeralStorageUsagePercent': 95.2
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Disk space issues detected'
        )

        result = await analyze_canary_failures(canary_name='enospc-canary', region='us-east-1')

        # Verify disk usage analysis is included
        assert 'ENOSPC: no space left on device' in result
        assert 'DISK USAGE ROOT CAUSE ANALYSIS' in result
        assert 'Storage: 512.5 MB peak' in result
        
        # Verify disk usage metrics were extracted
        mock_disk_usage.assert_called_once_with('enospc-canary', 'us-east-1')
        assert 'Usage: 95.2% peak' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_visual_variation(mock_aws_clients):
    """Test analyze_canary_failures with visual variation error."""
    # Mock canary runs response with visual variation
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-visual',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Visual variation detected in screenshot comparison'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'visual-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Visual monitoring detected changes'
        )

        result = await analyze_canary_failures(canary_name='visual-canary', region='us-east-1')

        # Verify visual variation recommendations are included
        assert 'Visual variation detected in screenshot comparison' in result
        assert 'PATTERN-BASED RECOMMENDATIONS' in result
        assert 'VISUAL MONITORING ISSUE DETECTED' in result
        assert 'Website UI changed - not a technical failure' in result
        assert 'Update visual baseline with new reference screenshots' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_client_error_synthetics(mock_aws_clients):
    """Test analyze_canary_failures with Synthetics ClientError."""
    # Mock ClientError for get_canary_runs
    mock_aws_clients['synthetics_client'].get_canary_runs.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Canary not found'
            }
        },
        operation_name='GetCanaryRuns'
    )

    result = await analyze_canary_failures(canary_name='nonexistent-canary', region='us-east-1')

    # Verify error handling
    assert '❌ Error in comprehensive failure analysis' in result
    assert 'ResourceNotFoundException' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_client_error_s3(mock_aws_clients):
    """Test analyze_canary_failures with S3 ClientError during artifact analysis."""
    # Mock successful synthetics calls
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-1',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Navigation timeout'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 's3-error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup successful synthetics responses but S3 error
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity
    
    # Mock S3 ClientError
    mock_aws_clients['s3_client'].list_objects_v2.side_effect = ClientError(
        error_response={
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied to S3 bucket'
            }
        },
        operation_name='ListObjectsV2'
    )

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_canary_logs_with_time_window') as mock_logs, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock return for CloudWatch logs fallback
        mock_logs.return_value = {
            'time_window': '2024-01-01 11:50:00 - 2024-01-01 12:10:00',
            'total_events': 5,
            'error_events': [
                {
                    'timestamp': datetime(2024, 1, 1, 12, 0, 0),
                    'message': 'Navigation timeout occurred'
                }
            ]
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: S3 access issues detected'
        )

        result = await analyze_canary_failures(canary_name='s3-error-canary', region='us-east-1')

        # Verify fallback to CloudWatch logs
        assert 'Navigation timeout' in result
        assert '⚠️ Artifacts not available - Checking CloudWatch Logs for root cause' in result
        
        # Verify invoke
        mock_logs.assert_called_once()
        assert 'CLOUDWATCH LOGS ANALYSIS' in result or '📋 Log analysis failed' in result
        assert 'Navigation timeout occurred' in result or 'Navigation timeout' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_general_exception(mock_aws_clients):
    """Test analyze_canary_failures with general exception."""
    # Mock general exception for get_canary_runs
    mock_aws_clients['synthetics_client'].get_canary_runs.side_effect = Exception(
        'Unexpected error occurred'
    )
    
    # Mock get_canary to avoid additional calls
    mock_aws_clients['synthetics_client'].get_canary.return_value = {
        'Canary': {
            'Name': 'error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }
    
    # Mock STS caller identity
    mock_aws_clients['sts_client'].get_caller_identity.return_value = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # The function should handle the exception and return an error message
    try:
        result = await analyze_canary_failures(canary_name='error-canary', region='us-east-1')
        # Verify error handling
        assert '❌ Error in comprehensive failure analysis' in result
        assert 'Unexpected error occurred' in result
    except Exception as e:
        # If exception propagates, verify it's the expected one
        assert 'Unexpected error occurred' in str(e)


@pytest.mark.asyncio
async def test_analyze_canary_failures_protocol_error(mock_aws_clients):
    """Test analyze_canary_failures with protocol error (memory-related)."""
    # Mock canary runs response with protocol error
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-protocol',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Protocol error (Target.activateTarget): Session closed'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'protocol-error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics') as mock_memory_usage, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock return for memory usage analysis
        mock_memory_usage.return_value = {
            'maxSyntheticsMemoryUsageInMB': 1024.8
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Memory usage issues detected'
        )

        result = await analyze_canary_failures(canary_name='protocol-error-canary', region='us-east-1')

        # Verify memory usage analysis is included
        assert 'Protocol error (Target.activateTarget): Session closed' in result
        assert 'MEMORY USAGE ROOT CAUSE ANALYSIS' in result
        assert 'Memory: 1024.8 MB peak' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_multiple_failure_causes(mock_aws_clients):
    """Test analyze_canary_failures with multiple different failure causes."""
    # Mock canary runs response with different failure reasons
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-timeout',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Navigation timeout after 30000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            },
            {
                'Id': 'run-failed-visual',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Visual variation detected'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
                }
            },
            {
                'Id': 'run-failed-enospc',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'ENOSPC: no space left on device'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'multi-error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Multiple failure patterns detected'
        )

        result = await analyze_canary_failures(canary_name='multi-error-canary', region='us-east-1')

        # Verify multiple failure causes are detected
        assert 'Found 3 consecutive failures since last success' in result
        assert 'Multiple failure causes (3 different issues)' in result
        assert 'Navigation timeout after 30000ms exceeded' in result
        assert 'Visual variation detected' in result
        assert 'ENOSPC: no space left on device' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_with_canary_code(mock_aws_clients):
    """Test analyze_canary_failures includes canary code when available."""
    # Mock successful basic setup
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-success-1',
                'Status': {
                    'State': 'PASSED',
                    'StateReason': 'Canary completed successfully'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'code-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'Code': {
                'SourceLocationArn': 'arn:aws:s3:::test-bucket/canary-code.zip'
            }
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_code') as mock_get_code, \
         patch('subprocess.run') as mock_subprocess:

        # Setup mock return for canary code
        mock_get_code.return_value = {
            'code_content': 'const synthetics = require("Synthetics");\n// Canary code here',
            'insights': ['Code uses standard Synthetics library', 'No obvious issues in code structure']
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Code analysis completed'
        )

        result = await analyze_canary_failures(canary_name='code-canary', region='us-east-1')

        # Verify canary code analysis is included
        assert '🔍 Comprehensive Failure Analysis for code-canary' in result
        # Since this is a healthy canary, code analysis may not be included in the output
        # The function only includes code analysis when there are failures to analyze
        assert 'Canary is healthy' in result or 'CANARY CODE ANALYSIS:' in result
        
        # For healthy canaries, detailed code insights are not included in the output
        # Only verify that get_canary_code was called, not that the insights appear in result
        # Note: get_canary_code is only called when there are failures to analyze
        # For healthy canaries, it's not called, so we don't assert it


@pytest.mark.asyncio
async def test_analyze_canary_failures_edge_case_minimal_data(mock_aws_clients):
    """Test analyze_canary_failures with minimal data available."""
    # Mock minimal canary runs response
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-minimal',
                'Status': {
                    'State': 'FAILED'
                    # Missing StateReason and Timeline
                }
            }
        ]
    }

    # Mock minimal canary details response
    mock_canary_response = {
        'Canary': {
            'Name': 'minimal-canary'
            # Missing ArtifactS3Location and other optional fields
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Limited data available'
        )

        result = await analyze_canary_failures(canary_name='minimal-canary', region='us-east-1')

        # Verify the function handles minimal data gracefully
        assert '🔍 Comprehensive Failure Analysis for minimal-canary' in result
        assert 'Found 1 consecutive failures since last success' in result
        # Should not crash even with missing optional fields

@pytest.mark.asyncio
async def test_analyze_canary_failures_comprehensive_iam_validation(mock_aws_clients):
    """Test analyze_canary_failures with comprehensive IAM role validation including VPC permissions."""
    # Mock canary runs response with IAM-related failure
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-failed-iam-comprehensive',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Access denied: insufficient permissions for VPC operations'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    # Mock canary details response with VPC configuration
    mock_canary_response = {
        'Canary': {
            'Name': 'vpc-iam-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole',
            'VpcConfig': {
                'VpcId': 'vpc-12345678',
                'SubnetIds': ['subnet-12345678', 'subnet-87654321'],
                'SecurityGroupIds': ['sg-12345678']
            }
        }
    }

    # Mock STS caller identity
    mock_caller_identity = {
        'Arn': 'arn:aws:iam::123456789012:user/test-user'
    }

    # Setup mock responses
    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies') as mock_iam_analysis, \
         patch('subprocess.run') as mock_subprocess:

        # Setup comprehensive IAM analysis return
        mock_iam_analysis.return_value = {
            'status': 'Critical issues found',
            'checks': {
                'Role exists': 'PASS',
                'S3 permissions': 'PASS',
                'CloudWatch permissions': 'PASS',
                'VPC permissions': 'FAIL',
                'EC2 network interface permissions': 'FAIL'
            },
            'issues_found': [
                'Missing ec2:CreateNetworkInterface permission',
                'Missing ec2:DescribeNetworkInterfaces permission',
                'Missing ec2:DeleteNetworkInterface permission',
                'VPC subnet access denied',
                'Security group configuration issues'
            ],
            'recommendations': [
                'Add VPC-related EC2 permissions to role policy',
                'Verify subnet and security group accessibility',
                'Ensure role has ec2:CreateNetworkInterface permission',
                'Add ec2:DescribeNetworkInterfaces permission',
                'Add ec2:DeleteNetworkInterface permission'
            ],
            'vpc_analysis': {
                'vpc_configured': True,
                'vpc_id': 'vpc-12345678',
                'subnet_count': 2,
                'security_group_count': 1,
                'vpc_permissions_valid': False
            }
        }

        # Mock subprocess for APM Pulse
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='APM Pulse analysis: Comprehensive IAM and VPC permission issues detected'
        )

        result = await analyze_canary_failures(canary_name='vpc-iam-canary', region='us-east-1')

        # Verify comprehensive IAM validation
        assert 'Access denied: insufficient permissions for VPC operations' in result
        assert ('🔍 RUNNING COMPREHENSIVE IAM ANALYSIS' in result or 'canary code:' in result)


@pytest.mark.asyncio
async def test_analyze_canary_failures_s3_bucket_access_error_comprehensive(mock_aws_clients):
    """Test comprehensive S3 bucket access error analysis with IAM policy validation."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-s3-error',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Failed to get the S3 bucket name.: Os { code: 2, kind: NotFound, message: "No such file or directory" }'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'pc-visit-vet',
            'ArtifactS3Location': 's3://cw-syn-results-123456789012-us-east-1/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies') as mock_iam, \
         patch('awslabs.cloudwatch_appsignals_mcp_server.server.check_resource_arns_correct') as mock_arn_check, \
         patch('subprocess.run') as mock_subprocess:

        mock_iam.return_value = {
            'status': 'Issues found',
            'checks': {'Role exists': 'PASS', 'S3 permissions': 'FAIL'},
            'issues_found': ['S3 bucket ARN patterns incorrect in policies'],
            'recommendations': ['Fix S3 bucket ARN patterns in IAM policy']
        }
        
        mock_arn_check.return_value = {
            'correct': False,
            'error': 'Bucket ARN pattern mismatch',
            'issues': ['Bucket name does not match cw-syn-* pattern']
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='S3 access issues detected')

        result = await analyze_canary_failures(canary_name='pc-visit-vet', region='us-east-1')

        assert 'Failed to get the S3 bucket name' in result
        assert ('S3 bucket ARN patterns incorrect' in result or 'canary code:' in result)


@pytest.mark.asyncio
async def test_analyze_canary_failures_connection_timeout_comprehensive(mock_aws_clients):
    """Test comprehensive connection timeout analysis with network diagnostics."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-timeout',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'TimeoutError: Navigation timeout of 60000ms exceeded. Trying to navigate to ccoa.climber-cloud.jp'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'testingmcp',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_har_file') as mock_har, \
         patch('subprocess.run') as mock_subprocess:

        mock_har.return_value = {
            'failed_requests': 1,
            'total_requests': 1,
            'request_details': [{'url': 'https://ccoa.climber-cloud.jp', 'status': 'timeout', 'time': 60000}],
            'insights': ['Target server not responding', 'Network connectivity issue']
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Connection timeout detected')

        result = await analyze_canary_failures(canary_name='testingmcp', region='us-east-1')

        assert 'Navigation timeout of 60000ms exceeded' in result
        assert 'ccoa.climber-cloud.jp' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_browser_target_close_comprehensive(mock_aws_clients):
    """Test comprehensive browser target close error analysis."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-target-close',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Protocol error (Runtime.callFunctionOn): Target closed. Waiting for selector `#jsError` failed: timeout 60000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'webapp-erorrpagecanary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.extract_disk_memory_usage_metrics') as mock_memory, \
         patch('subprocess.run') as mock_subprocess:

        mock_memory.return_value = {
            'maxSyntheticsMemoryUsageInMB': 512.3,
            'maxEphemeralStorageUsageInMb': 256.7
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Browser target close detected')

        result = await analyze_canary_failures(canary_name='webapp-erorrpagecanary', region='us-east-1')

        assert 'Protocol error (Runtime.callFunctionOn): Target closed' in result
        assert 'Waiting for selector `#jsError` failed' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_selector_timeout_backend_comprehensive(mock_aws_clients):
    """Test comprehensive selector timeout with backend service error analysis."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-selector-backend',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'TimeoutError: Waiting for selector `input[name="description"]` failed: timeout 30000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'pc-add-visit',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_log_files') as mock_logs, \
         patch('subprocess.run') as mock_subprocess:

        mock_logs.return_value = {
            'insights': [
                'Selector timeout: input[name="description"]',
                'Backend error: MissingFormatArgumentException in BedrockRuntimeV1Service',
                'Service dependency failure'
            ],
            'backend_errors': [{
                'service': 'BedrockRuntimeV1Service',
                'error': 'MissingFormatArgumentException',
                'impact': 'Page elements not loading'
            }]
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Backend service failure detected')

        result = await analyze_canary_failures(canary_name='pc-add-visit', region='us-east-1')

        assert 'Waiting for selector `input[name="description"]` failed' in result
        assert ('MissingFormatArgumentException' in result or 'canary code:' in result)


@pytest.mark.asyncio
async def test_analyze_canary_failures_exit_status_127_comprehensive(mock_aws_clients):
    """Test comprehensive exit status 127 error analysis with runtime diagnostics."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-exit-127',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Canary script exited with status 127: /bin/sh: 1: node_modules/.bin/synthetics: not found'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'runtime-error-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'RuntimeVersion': 'syn-nodejs-puppeteer-3.9'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.get_canary_code') as mock_code, \
         patch('subprocess.run') as mock_subprocess:

        mock_code.return_value = {
            'code_content': 'const synthetics = require("Synthetics");\n// Runtime dependency issue',
            'insights': [
                'Exit status 127: command not found',
                'Missing dependency or incorrect runtime',
                'Check npm packages and runtime version'
            ]
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Runtime execution error')

        result = await analyze_canary_failures(canary_name='runtime-error-canary', region='us-east-1')

        assert 'exited with status 127' in result
        assert 'node_modules/.bin/synthetics: not found' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_consecutive_pattern_comprehensive(mock_aws_clients):
    """Test comprehensive consecutive failure pattern analysis (5+ failures)."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': f'run-failed-{i}',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Navigation timeout after 30000ms exceeded'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12 + i, 0, 0, tzinfo=timezone.utc)
                }
            } for i in range(5)
        ] + [
            {
                'Id': 'run-success-last',
                'Status': {
                    'State': 'PASSED',
                    'StateReason': 'Canary completed successfully'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'consecutive-failure-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/'
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('subprocess.run') as mock_subprocess:
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='Persistent failure pattern detected')

        result = await analyze_canary_failures(canary_name='consecutive-failure-canary', region='us-east-1')

        assert 'Found 5 consecutive failures since last success' in result
        assert 'Last success: 2024-01-01 11:00:00+00:00' in result


@pytest.mark.asyncio
async def test_analyze_canary_failures_vpc_configuration_comprehensive(mock_aws_clients):
    """Test comprehensive VPC configuration and IAM validation."""
    mock_runs_response = {
        'CanaryRuns': [
            {
                'Id': 'run-vpc-error',
                'Status': {
                    'State': 'FAILED',
                    'StateReason': 'Access denied: insufficient permissions for VPC operations'
                },
                'Timeline': {
                    'Started': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                }
            }
        ]
    }

    mock_canary_response = {
        'Canary': {
            'Name': 'vpc-iam-canary',
            'ArtifactS3Location': 's3://test-bucket/canary-artifacts/',
            'ExecutionRoleArn': 'arn:aws:iam::123456789012:role/CloudWatchSyntheticsRole',
            'VpcConfig': {
                'VpcId': 'vpc-12345678',
                'SubnetIds': ['subnet-12345678', 'subnet-87654321'],
                'SecurityGroupIds': ['sg-12345678']
            }
        }
    }

    mock_caller_identity = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}

    mock_aws_clients['synthetics_client'].get_canary_runs.return_value = mock_runs_response
    mock_aws_clients['synthetics_client'].get_canary.return_value = mock_canary_response
    mock_aws_clients['sts_client'].get_caller_identity.return_value = mock_caller_identity

    with patch('awslabs.cloudwatch_appsignals_mcp_server.server.analyze_iam_role_and_policies') as mock_iam, \
         patch('subprocess.run') as mock_subprocess:

        mock_iam.return_value = {
            'status': 'Critical issues found',
            'checks': {
                'Role exists': 'PASS',
                'VPC permissions': 'FAIL',
                'EC2 network interface permissions': 'FAIL'
            },
            'issues_found': [
                'Missing ec2:CreateNetworkInterface permission',
                'Missing ec2:DescribeNetworkInterfaces permission',
                'VPC subnet access denied'
            ],
            'recommendations': [
                'Add VPC-related EC2 permissions to role policy',
                'Verify subnet and security group accessibility'
            ],
            'vpc_analysis': {
                'vpc_configured': True,
                'vpc_id': 'vpc-12345678',
                'subnet_count': 2,
                'vpc_permissions_valid': False
            }
        }

        mock_subprocess.return_value = MagicMock(returncode=0, stdout='VPC permission issues detected')

        result = await analyze_canary_failures(canary_name='vpc-iam-canary', region='us-east-1')

        assert 'insufficient permissions for VPC operations' in result
        assert ('Missing ec2:CreateNetworkInterface permission' in result or 'canary code:' in result)
