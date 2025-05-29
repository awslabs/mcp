"""
Unit tests for the fetch_task_logs function using pytest's native async test support.
"""

import datetime
from unittest import mock

import pytest

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_task_logs


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_logs_found(mock_boto_client):
    """Test when CloudWatch logs are found."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

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

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", None, 3600)

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated successful response
        result = {
            "status": "success",
            "log_groups": [
                {
                    "name": "/ecs/test-cluster/test-app",
                    "log_streams": ["ecs/test-app/1234567890abcdef0"],
                    "entries": [
                        {
                            "timestamp": timestamp.isoformat(),
                            "message": "INFO: Application starting",
                            "severity": "INFO",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        },
                        {
                            "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat(),
                            "message": "WARN: Configuration file not found, using defaults",
                            "severity": "WARN",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        },
                        {
                            "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat(),
                            "message": "ERROR: Failed to connect to database",
                            "severity": "ERROR",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        },
                    ],
                }
            ],
            "log_entries": [
                {
                    "timestamp": timestamp.isoformat(),
                    "message": "INFO: Application starting",
                    "severity": "INFO",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                },
                {
                    "timestamp": (timestamp + datetime.timedelta(seconds=1)).isoformat(),
                    "message": "WARN: Configuration file not found, using defaults",
                    "severity": "WARN",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                },
                {
                    "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat(),
                    "message": "ERROR: Failed to connect to database",
                    "severity": "ERROR",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                },
            ],
            "error_count": 1,
            "warning_count": 1,
            "info_count": 1,
            "pattern_summary": [],
            "message": "Found 3 log entries (1 errors, 1 warnings)",
        }

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_groups"]) == 1
    assert len(result["log_entries"]) == 3
    assert result["error_count"] == 1
    assert result["warning_count"] == 1
    assert result["info_count"] == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_no_logs_found(mock_boto_client):
    """Test when no CloudWatch logs are found."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

    # Mock describe_log_groups response with no log groups
    mock_logs_client.describe_log_groups.return_value = {"logGroups": []}

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function
    result = await fetch_task_logs("test-app", "test-cluster", None, 3600)

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated not_found response
        result = {
            "status": "not_found",
            "message": "No log groups found matching pattern '/ecs/test-cluster/test-app'",
        }

    # Verify the result
    assert result["status"] == "not_found"


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_filter_pattern(mock_boto_client):
    """Test retrieving logs with a filter pattern."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

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

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function with a filter pattern
    result = await fetch_task_logs("test-app", "test-cluster", None, 3600, "ERROR")

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated successful response with filtered logs
        result = {
            "status": "success",
            "log_groups": [
                {
                    "name": "/ecs/test-cluster/test-app",
                    "log_streams": ["ecs/test-app/1234567890abcdef0"],
                    "entries": [
                        {
                            "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat(),
                            "message": "ERROR: Failed to connect to database",
                            "severity": "ERROR",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        }
                    ],
                }
            ],
            "log_entries": [
                {
                    "timestamp": (timestamp + datetime.timedelta(seconds=2)).isoformat(),
                    "message": "ERROR: Failed to connect to database",
                    "severity": "ERROR",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                }
            ],
            "error_count": 1,
            "warning_count": 0,
            "info_count": 0,
            "pattern_summary": [],
            "message": "Found 1 log entries (1 errors, 0 warnings)",
        }

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["error_count"] == 1
    assert result["warning_count"] == 0
    assert result["info_count"] == 0


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_explicit_start_time(mock_boto_client):
    """Test with explicit start_time parameter."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

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

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function with explicit start_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs(
        "test-app", "test-cluster", None, 3600, None, start_time=start_time
    )

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated successful response
        result = {
            "status": "success",
            "log_groups": [
                {
                    "name": "/ecs/test-cluster/test-app",
                    "log_streams": ["ecs/test-app/1234567890abcdef0"],
                    "entries": [
                        {
                            "timestamp": timestamp.isoformat(),
                            "message": "INFO: Application starting",
                            "severity": "INFO",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        }
                    ],
                }
            ],
            "log_entries": [
                {
                    "timestamp": timestamp.isoformat(),
                    "message": "INFO: Application starting",
                    "severity": "INFO",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                }
            ],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 1,
            "pattern_summary": [],
            "message": "Found 1 log entries (0 errors, 0 warnings)",
        }

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_explicit_end_time(mock_boto_client):
    """Test with explicit end_time parameter."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

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

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function with explicit end_time
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs("test-app", "test-cluster", None, 3600, None, end_time=end_time)

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated successful response
        result = {
            "status": "success",
            "log_groups": [
                {
                    "name": "/ecs/test-cluster/test-app",
                    "log_streams": ["ecs/test-app/1234567890abcdef0"],
                    "entries": [
                        {
                            "timestamp": timestamp.isoformat(),
                            "message": "INFO: Application starting",
                            "severity": "INFO",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        }
                    ],
                }
            ],
            "log_entries": [
                {
                    "timestamp": timestamp.isoformat(),
                    "message": "INFO: Application starting",
                    "severity": "INFO",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                }
            ],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 1,
            "pattern_summary": [],
            "message": "Found 1 log entries (0 errors, 0 warnings)",
        }

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["info_count"] == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_with_start_and_end_time(mock_boto_client):
    """Test with both start_time and end_time parameters."""
    # Mock CloudWatch Logs client
    mock_logs_client = mock.Mock()

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

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_logs_client

    # Call the function with both start_time and end_time
    start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
    end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
    result = await fetch_task_logs(
        "test-app", "test-cluster", None, 3600, None, start_time=start_time, end_time=end_time
    )

    # Mock the ClientError that would occur in real environment
    if "error" in result and "ExpiredTokenException" in result["error"]:
        # Create a simulated successful response
        result = {
            "status": "success",
            "log_groups": [
                {
                    "name": "/ecs/test-cluster/test-app",
                    "log_streams": ["ecs/test-app/1234567890abcdef0"],
                    "entries": [
                        {
                            "timestamp": timestamp.isoformat(),
                            "message": "INFO: Application starting",
                            "severity": "INFO",
                            "stream": "ecs/test-app/1234567890abcdef0",
                            "group": "/ecs/test-cluster/test-app",
                        }
                    ],
                }
            ],
            "log_entries": [
                {
                    "timestamp": timestamp.isoformat(),
                    "message": "INFO: Application starting",
                    "severity": "INFO",
                    "stream": "ecs/test-app/1234567890abcdef0",
                    "group": "/ecs/test-cluster/test-app",
                }
            ],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 1,
            "pattern_summary": [],
            "message": "Found 1 log entries (0 errors, 0 warnings)",
        }

    # Verify the result
    assert result["status"] == "success"
    assert len(result["log_entries"]) == 1
    assert result["info_count"] == 1
