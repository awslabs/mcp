"""
Unit tests for the fetch_task_logs function.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_task_logs

# ----------------------------------------------------------------------------
# Basic Functionality Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@mock.patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_logs_found(mock_get_aws_client):
    """Test when CloudWatch logs are found."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
                "metricFilterCount": 0,
                "arn": "arn:aws:logs:us-west-2:123456789012:log-group:/ecs/test-cluster/test-app:*",
                "storedBytes": 1234,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef0",
                "creationTime": int(timestamp.timestamp()) * 1000,
                "firstEventTimestamp": int(timestamp.timestamp()) * 1000,
                "lastEventTimestamp": int(timestamp.timestamp()) * 1000,
                "lastIngestionTime": int(timestamp.timestamp()) * 1000,
                "uploadSequenceToken": "1234567890",
                "arn": (
                    "arn:aws:logs:us-west-2:123456789012:log-group:/ecs/test-cluster/test-app:"
                    "log-stream:ecs/test-app/1234567890abcdef0"
                ),
                "storedBytes": 1234,
            }
        ]
    }

    # Mock get_log_events response
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "INFO: Application starting",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=1)).timestamp()) * 1000,
                "message": "WARN: Configuration file not found, using defaults",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=1)).timestamp())
                * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                "message": "ERROR: Failed to connect to database",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp())
                * 1000,
            },
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Configure get_aws_client mock to return our mock client
    mock_get_aws_client.return_value = mock_logs_client

    # Pass the logs client directly to isolate from get_aws_client issues
    result = await fetch_task_logs(
        "test-app", "test-cluster", None, 3600, logs_client=mock_logs_client
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_groups"]) == 1
    assert len(result["log_entries"]) == 3
    assert result["error_count"] == 1
    assert result["warning_count"] == 1
    assert result["info_count"] == 1


@pytest.mark.anyio
async def test_no_logs_found():
    """Test when no CloudWatch logs are found."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Mock describe_log_groups response with no log groups
    mock_logs_client.describe_log_groups.return_value = {"logGroups": []}

    # Call the function with the mock client directly
    result = await fetch_task_logs(
        "test-app", "test-cluster", None, 3600, logs_client=mock_logs_client
    )

    # Verify the result
    assert result["status"] == "not_found"


@pytest.mark.anyio
async def test_with_filter_pattern():
    """Test retrieving logs with a filter pattern."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef0",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response with filtered events
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                "message": "ERROR: Failed to connect to database",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp())
                * 1000,
            }
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function with a filter pattern
    result = await fetch_task_logs(
        "test-app", "test-cluster", None, 3600, "ERROR", logs_client=mock_logs_client
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["error_count"] == 1
    assert result["warning_count"] == 0
    assert result["info_count"] == 0


# ----------------------------------------------------------------------------
# Time Window Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_with_explicit_start_time():
    """Test with explicit start_time parameter."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef0",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "INFO: Application starting",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            }
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function with explicit start_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs(
        "test-app",
        "test-cluster",
        None,
        3600,
        None,
        start_time=start_time,
        logs_client=mock_logs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1


@pytest.mark.anyio
async def test_with_explicit_end_time():
    """Test with explicit end_time parameter."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef0",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "INFO: Application starting",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            }
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function with explicit end_time
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs(
        "test-app",
        "test-cluster",
        None,
        3600,
        None,
        end_time=end_time,
        logs_client=mock_logs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["info_count"] == 1


@pytest.mark.anyio
async def test_with_start_and_end_time():
    """Test with both start_time and end_time parameters."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef0",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "INFO: Application starting",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            }
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function with both start_time and end_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs(
        "test-app",
        "test-cluster",
        None,
        3600,
        None,
        start_time=start_time,
        end_time=end_time,
        logs_client=mock_logs_client,
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["info_count"] == 1


# ----------------------------------------------------------------------------
# Task ID and Log Pattern Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_with_specific_task_id():
    """Test retrieving logs for a specific task ID."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/abcdef1234567890",
                "creationTime": int(timestamp.timestamp()) * 1000,
            },
            {
                "logStreamName": "ecs/test-app/1234567890abcdef",
                "creationTime": int(timestamp.timestamp()) * 1000,
            },
        ]
    }

    # Mock get_log_events response
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "INFO: Task specific log",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            }
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function with a specific task ID
    # pragma: allowlist secret
    result = await fetch_task_logs(
        "test-app", "test-cluster", task_id="1234567890abcdef", logs_client=mock_logs_client
    )

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["log_entries"][0]["message"] == "INFO: Task specific log"

    # Verify that describe_log_streams was called correctly
    mock_logs_client.describe_log_streams.assert_called()
    # Validate the parameters individually for better readability
    call_args = mock_logs_client.describe_log_streams.call_args[1]
    assert call_args["logGroupName"] == "/ecs/test-cluster/test-app"
    assert call_args["logStreamNamePrefix"] == "1234567890abcdef"  # pragma: allowlist secret
    assert call_args["orderBy"] == "LastEventTime"
    assert call_args["descending"] is True


@pytest.mark.anyio
async def test_with_error_logs_and_pattern_summary():
    """Test retrieving logs with errors and generating pattern summary."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response with multiple error logs
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "ERROR: Database connection failed: timeout",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=1)).timestamp()) * 1000,
                "message": "ERROR: Database connection failed: timeout",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=1)).timestamp())
                * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                "message": "ERROR: Invalid configuration parameter: max_connections",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp())
                * 1000,
            },
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 3
    assert result["error_count"] == 3
    assert result["warning_count"] == 0
    assert result["info_count"] == 0

    # Verify pattern summary
    assert len(result["pattern_summary"]) > 0
    assert result["pattern_summary"][0]["count"] == 2  # Two identical error messages
    assert "Database connection failed" in result["pattern_summary"][0]["pattern"]


# ----------------------------------------------------------------------------
# Log Severity Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_with_different_log_severities():
    """Test detecting different log severities."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response with various log severities
    mock_logs_client.get_log_events.return_value = {
        "events": [
            {
                "timestamp": int(timestamp.timestamp()) * 1000,
                "message": "This is a normal log message",
                "ingestionTime": int(timestamp.timestamp()) * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=1)).timestamp()) * 1000,
                "message": "WARN: This is a warning message",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=1)).timestamp())
                * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                "message": "ERROR: This is an error message",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp())
                * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=3)).timestamp()) * 1000,
                "message": "EXCEPTION: This is an exception",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=3)).timestamp())
                * 1000,
            },
            {
                "timestamp": int((timestamp + datetime.timedelta(seconds=4)).timestamp()) * 1000,
                "message": "Task FAILED with exit code 1",
                "ingestionTime": int((timestamp + datetime.timedelta(seconds=4)).timestamp())
                * 1000,
            },
        ],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 5
    assert result["error_count"] == 3  # ERROR, EXCEPTION, FAILED
    assert result["warning_count"] == 1  # WARN
    assert result["info_count"] == 1  # normal message

    # Verify severities
    severities = [entry["severity"] for entry in result["log_entries"]]
    assert severities.count("ERROR") == 3
    assert severities.count("WARN") == 1
    assert severities.count("INFO") == 1


@pytest.mark.anyio
async def test_no_log_entries():
    """Test when no log entries are found."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events response with no events
    mock_logs_client.get_log_events.return_value = {
        "events": [],
        "nextForwardToken": "f/1234567890",
        "nextBackwardToken": "b/1234567890",
    }

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 0
    assert result["error_count"] == 0
    assert result["warning_count"] == 0
    assert result["info_count"] == 0
    assert "No log entries found" in result["message"]


# ----------------------------------------------------------------------------
# Error Handling Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_with_log_stream_error():
    """Test handling errors when getting log streams."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams to raise an error
    mock_logs_client.describe_log_streams.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Log group not found"}},
        "DescribeLogStreams",
    )

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 0
    assert any("error" in group for group in result["log_groups"])
    assert "Error getting log streams" in result["log_groups"][0]["error"]


@pytest.mark.anyio
async def test_with_log_events_error():
    """Test handling errors when getting log events."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Timestamps
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)

    # Mock describe_log_groups response
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/ecs/test-cluster/test-app",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock describe_log_streams response
    mock_logs_client.describe_log_streams.return_value = {
        "logStreams": [
            {
                "logStreamName": "ecs/test-app/1234567890abcdef",
                "creationTime": int(timestamp.timestamp()) * 1000,
            }
        ]
    }

    # Mock get_log_events to raise an error
    mock_logs_client.get_log_events.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Log stream not found"}},
        "GetLogEvents",
    )

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 0
    assert any("error" in group for group in result["log_groups"])
    assert "Error getting log events" in result["log_groups"][0]["error"]


@pytest.mark.anyio
async def test_client_error():
    """Test handling ClientError at the top level."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.AsyncMock()

    # Mock describe_log_groups to raise ClientError
    mock_logs_client.describe_log_groups.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
        "DescribeLogGroups",
    )

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "error"
    assert "AWS API error" in result["error"]
    assert "AccessDeniedException" in result["error"]


@pytest.mark.anyio
async def test_general_exception():
    """Test handling general exceptions."""
    # Mock CloudWatch Logs client that raises exception
    mock_logs_client = mock.AsyncMock()
    mock_logs_client.describe_log_groups.side_effect = Exception("Unexpected error")

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", logs_client=mock_logs_client)

    # Verify the result
    assert result["status"] == "error"
    assert result["error"] == "Unexpected error"
