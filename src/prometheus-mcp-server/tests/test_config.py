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

"""Tests for configuration loading and validation."""

from argparse import Namespace
from unittest.mock import MagicMock, patch


def test_load_config_defaults():
    """Test loading configuration with default values."""
    from awslabs.prometheus_mcp_server.consts import DEFAULT_AWS_REGION, DEFAULT_SERVICE_NAME
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = Namespace(config=None, profile=None, region=None, url=None, debug=False)

    # Execute
    with patch('os.path.exists', return_value=False), patch('os.getenv', return_value=None), patch('awslabs.prometheus_mcp_server.server.load_dotenv'):
        config = load_config(args)

    # Assert
    assert config['aws_profile'] is None
    assert config['aws_region'] == DEFAULT_AWS_REGION
    assert config['prometheus_url'] == ''
    assert config['service_name'] == DEFAULT_SERVICE_NAME


def test_load_config_from_file():
    """Test loading configuration from a file."""
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = Namespace(config='config.json', profile=None, region=None, url=None, debug=False)
    config_data = {
        'aws_profile': 'test-profile',
        'aws_region': 'us-west-2',
        'prometheus_url': 'https://test-prometheus.amazonaws.com',
        'service_name': 'custom-service',
    }

    # Execute
    with (
        patch('os.path.exists', return_value=True),
        patch('builtins.open', create=True),
        patch('json.load', return_value=config_data),
        patch('os.getenv', return_value=None),
    ):
        config = load_config(args)

    # Assert
    assert config['aws_profile'] == 'test-profile'
    assert config['aws_region'] == 'us-west-2'
    assert config['prometheus_url'] == 'https://test-prometheus.amazonaws.com'
    assert config['service_name'] == 'custom-service'


def test_load_config_from_env_vars():
    """Test loading configuration from environment variables."""
    from awslabs.prometheus_mcp_server.consts import (
        ENV_AWS_PROFILE,
        ENV_AWS_REGION,
        ENV_AWS_SERVICE_NAME,
        ENV_PROMETHEUS_URL,
    )
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = Namespace(config=None, profile=None, region=None, url=None, debug=False)

    # Execute
    with patch('os.path.exists', return_value=False), patch('os.getenv') as mock_getenv, patch('awslabs.prometheus_mcp_server.server.load_dotenv'):
        mock_getenv.side_effect = lambda key, default=None: {
            ENV_AWS_PROFILE: 'env-profile',
            ENV_AWS_REGION: 'us-east-2',
            ENV_PROMETHEUS_URL: 'https://env-prometheus.amazonaws.com',
            ENV_AWS_SERVICE_NAME: 'env-service',
        }.get(key, default)

        config = load_config(args)

    # Assert
    assert config['aws_profile'] == 'env-profile'
    assert config['aws_region'] == 'us-east-2'
    assert config['prometheus_url'] == 'https://env-prometheus.amazonaws.com'
    assert config['service_name'] == 'env-service'


def test_load_config_from_args():
    """Test loading configuration from command line arguments."""
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = Namespace(
        config=None,
        profile='arg-profile',
        region='eu-west-1',
        url='https://arg-prometheus.amazonaws.com',
        debug=True,
    )

    # Execute
    with (
        patch('os.path.exists', return_value=False),
        patch('os.getenv', return_value=None),
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
    ):
        config = load_config(args)

    # Assert
    assert config['aws_profile'] == 'arg-profile'
    assert config['aws_region'] == 'eu-west-1'
    assert config['prometheus_url'] == 'https://arg-prometheus.amazonaws.com'
    mock_logger.level.assert_called_once_with('DEBUG')


def test_load_config_precedence():
    """Test configuration precedence (args > env > file > defaults)."""
    from awslabs.prometheus_mcp_server.consts import (
        ENV_AWS_PROFILE,
        ENV_AWS_REGION,
        ENV_AWS_SERVICE_NAME,
        ENV_PROMETHEUS_URL,
    )
    from awslabs.prometheus_mcp_server.server import load_config

    # Setup
    args = Namespace(
        config='config.json',
        profile='arg-profile',  # Should take precedence
        region=None,
        url=None,
        debug=False,
    )

    file_config = {
        'aws_profile': 'file-profile',
        'aws_region': 'eu-central-1',  # Should be overridden by env
        'prometheus_url': 'https://file-prometheus.amazonaws.com',  # Should be used
        'service_name': 'file-service',  # Should be used
    }

    # Execute
    with (
        patch('os.path.exists', return_value=True),
        patch('builtins.open', create=True),
        patch('json.load', return_value=file_config),
        patch('os.getenv') as mock_getenv,
    ):
        mock_getenv.side_effect = lambda key, default=None: {
            ENV_AWS_PROFILE: 'env-profile',  # Should be overridden by arg
            ENV_AWS_REGION: 'us-west-2',  # Should take precedence over file
            ENV_PROMETHEUS_URL: None,
            ENV_AWS_SERVICE_NAME: None,
        }.get(key, default)

        config = load_config(args)

    # Assert
    assert config['aws_profile'] == 'arg-profile'  # From args
    assert config['aws_region'] == 'us-west-2'  # From env
    assert config['prometheus_url'] == 'https://file-prometheus.amazonaws.com'  # From file
    assert config['service_name'] == 'file-service'  # From file


def test_setup_environment_success():
    """Test successful environment setup."""
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
        patch('awslabs.prometheus_mcp_server.server.logger'),
    ):
        mock_session_instance = mock_session.return_value
        mock_credentials = MagicMock()
        mock_credentials.token = None
        mock_session_instance.get_credentials.return_value = mock_credentials

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Arn': 'arn:aws:iam::123456789012:user/test-user'}
        mock_session_instance.client.return_value = mock_sts

        result = setup_environment(config)

    # Assert
    assert result is True
    mock_session.assert_called_once_with(profile_name='test-profile', region_name='us-east-1')
    mock_session_instance.client.assert_called_once_with('sts')
    mock_sts.get_caller_identity.assert_called_once()


def test_setup_environment_no_prometheus_url():
    """Test environment setup with missing Prometheus URL."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': '',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger:
        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()


def test_setup_environment_invalid_url():
    """Test environment setup with invalid Prometheus URL."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': 'invalid-url',
        'aws_region': 'us-east-1',
        'aws_profile': 'test-profile',
    }

    # Execute
    with patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger:
        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()


def test_setup_environment_no_region():
    """Test environment setup with missing AWS region."""
    from awslabs.prometheus_mcp_server.server import setup_environment

    # Setup
    config = {
        'prometheus_url': 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        'aws_region': '',
        'aws_profile': 'test-profile',
    }

    # Execute
    with patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger:
        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()


def test_setup_environment_no_credentials():
    """Test environment setup with missing AWS credentials."""
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
        mock_session_instance = mock_session.return_value
        mock_session_instance.get_credentials.return_value = None

        result = setup_environment(config)

    # Assert
    assert result is False
    mock_logger.error.assert_called()


def test_setup_environment_sts_error():
    """Test environment setup with STS error."""
    from awslabs.prometheus_mcp_server.server import setup_environment
    from botocore.exceptions import ClientError

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
        mock_session_instance = mock_session.return_value
        mock_credentials = MagicMock()
        mock_session_instance.get_credentials.return_value = mock_credentials

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GetCallerIdentity'
        )
        mock_session_instance.client.return_value = mock_sts

        result = setup_environment(config)

    # Assert
    assert result is True  # Should still return True as this is just a warning
    mock_logger.warning.assert_called()


def test_parse_arguments():
    """Test command line argument parsing."""
    from awslabs.prometheus_mcp_server.server import parse_arguments

    # Execute
    with patch('sys.argv', ['server.py', '--profile', 'test-profile', '--region', 'us-west-2',
                           '--url', 'https://test.amazonaws.com', '--debug']):
        args = parse_arguments()

    # Assert
    assert args.profile == 'test-profile'
    assert args.region == 'us-west-2'
    assert args.url == 'https://test.amazonaws.com'
    assert args.debug is True
