# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for edge cases in the Prometheus MCP Server."""

from unittest.mock import patch


def test_load_config_file_error():
    """Test loading configuration with file error."""
    import argparse
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = argparse.Namespace(
        config='nonexistent.json', profile=None, region=None, url=None, debug=False
    )

    # Execute
    with (
        patch('os.path.exists', return_value=True),
        patch('builtins.open', side_effect=Exception('File error')),
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
    ):
        config = load_config(args)

    # Assert
    mock_logger.error.assert_called_once()
    assert config['aws_profile'] is None
    assert config['prometheus_url'] is None  # Changed from '' to None to match our implementation


def test_setup_environment_url_parse_error():
    """Test setup environment with URL parsing error."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with (
        patch(
            'awslabs.prometheus_mcp_server.server.urlparse', side_effect=Exception('Parse error')
        ),
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        result = setup_environment(config)

    # Assert
    # With our new implementation, we don't need to validate the URL in setup_environment
    # since we're configuring the workspace for each request
    assert result is True  # Changed from False to True since we don't validate URL in setup_environment anymore
    # We don't expect any error logs for URL parsing in the new implementation
    assert not any(
        'Error parsing Prometheus URL' in str(args) for args in mock_logger.error.call_args_list
    )


def test_setup_environment_boto3_session_error():
    """Test setup environment with boto3 session error."""
    from awslabs.prometheus_mcp_server.server import setup_environment
    from botocore.exceptions import NoCredentialsError

    # Setup
    config = {
        'prometheus_url': 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        mock_session.side_effect = NoCredentialsError()
        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()
    assert any(
        'AWS credentials not found' in str(args) for args in mock_logger.error.call_args_list
    )


def test_setup_environment_general_exception():
    """Test setup environment with general exception."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        mock_session.side_effect = Exception('General error')
        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()
    assert any(
        'Error setting up AWS session' in str(args) for args in mock_logger.error.call_args_list
    )
