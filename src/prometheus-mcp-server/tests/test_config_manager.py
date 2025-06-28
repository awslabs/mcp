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

"""Tests for the ConfigManager class."""

import os
from awslabs.prometheus_mcp_server.consts import (
    DEFAULT_AWS_REGION,
    ENV_AWS_PROFILE,
    ENV_AWS_REGION,
)
from awslabs.prometheus_mcp_server.server import ConfigManager
from unittest.mock import MagicMock, patch


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_parse_arguments(self):
        """Test that parse_arguments correctly parses command line arguments."""
        with patch(
            'sys.argv',
            [
                'program',
                '--profile',
                'test-profile',
                '--region',
                'us-west-2',
                '--url',
                'https://example.com',
                '--debug',
            ],
        ):
            args = ConfigManager.parse_arguments()
            assert args.profile == 'test-profile'
            assert args.region == 'us-west-2'
            assert args.url == 'https://example.com'
            assert args.debug is True

    def test_setup_basic_config_with_args(self):
        """Test that setup_basic_config correctly uses command line arguments."""
        args = MagicMock()
        args.profile = 'test-profile'
        args.region = 'us-west-2'
        args.url = 'https://example.com'
        args.debug = True

        with (
            patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
            patch('awslabs.prometheus_mcp_server.server.logger'),
        ):
            config = ConfigManager.setup_basic_config(args)

            assert config['profile'] == 'test-profile'
            assert config['region'] == 'us-west-2'
            assert config['url'] == 'https://example.com'

    def test_setup_basic_config_with_env_vars(self):
        """Test that setup_basic_config correctly uses environment variables when args are not provided."""
        args = MagicMock()
        args.profile = None
        args.region = None
        args.url = None
        args.debug = False

        with (
            patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(
                os.environ,
                {
                    ENV_AWS_PROFILE: 'env-profile',
                    ENV_AWS_REGION: 'eu-west-1',
                    'PROMETHEUS_URL': 'https://env-example.com',
                },
            ),
        ):
            config = ConfigManager.setup_basic_config(args)

            assert config['profile'] == 'env-profile'
            assert config['region'] == 'eu-west-1'
            assert config['url'] == 'https://env-example.com'

    def test_setup_basic_config_with_defaults(self):
        """Test that setup_basic_config correctly uses defaults when neither args nor env vars are provided."""
        args = MagicMock()
        args.profile = None
        args.region = None
        args.url = None
        args.debug = False

        with (
            patch('awslabs.prometheus_mcp_server.server.load_dotenv'),
            patch('awslabs.prometheus_mcp_server.server.logger'),
            patch.dict(os.environ, {}, clear=True),
        ):
            config = ConfigManager.setup_basic_config(args)

            assert config['profile'] is None
            assert config['region'] == DEFAULT_AWS_REGION
            assert config['url'] is None
