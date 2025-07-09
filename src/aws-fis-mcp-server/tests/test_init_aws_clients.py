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

"""Tests for AWS client initialization functionality."""

import awslabs.aws_fis_mcp_server.server as server_module
import pytest
from awslabs.aws_fis_mcp_server.server import initialize_aws_clients
from unittest.mock import MagicMock, patch


class TestInitializeAwsClients:
    """Test cases for initialize_aws_clients function."""

    @patch('boto3.Session')
    def test_initialize_aws_clients_without_profile(self, mock_session_class):
        """Test initializing AWS clients without a profile."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_fis_client = MagicMock()
        mock_s3_client = MagicMock()
        mock_re_client = MagicMock()
        mock_cfn_client = MagicMock()
        mock_config_client = MagicMock()

        mock_session.client.side_effect = [
            mock_fis_client,
            mock_s3_client,
            mock_re_client,
            mock_cfn_client,
            mock_config_client,
        ]

        initialize_aws_clients('us-west-2')

        # Verify session was created correctly
        mock_session_class.assert_called_once_with(region_name='us-west-2')

        # Verify all clients were created
        assert mock_session.client.call_count == 5

        # Verify global variables were set
        assert server_module.aws_fis == mock_fis_client
        assert server_module.s3 == mock_s3_client
        assert server_module.resource_explorer == mock_re_client
        assert server_module.cloudformation == mock_cfn_client
        assert server_module.aws_config_client == mock_config_client

    @patch('boto3.Session')
    def test_initialize_aws_clients_with_profile(self, mock_session_class):
        """Test initializing AWS clients with a profile."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_fis_client = MagicMock()
        mock_s3_client = MagicMock()
        mock_re_client = MagicMock()
        mock_cfn_client = MagicMock()
        mock_config_client = MagicMock()

        mock_session.client.side_effect = [
            mock_fis_client,
            mock_s3_client,
            mock_re_client,
            mock_cfn_client,
            mock_config_client,
        ]

        initialize_aws_clients('eu-west-1', 'test-profile')

        # Verify session was created with profile
        mock_session_class.assert_called_once_with(
            profile_name='test-profile', region_name='eu-west-1'
        )

        # Verify all clients were created
        assert mock_session.client.call_count == 5

    @patch('boto3.Session')
    def test_initialize_aws_clients_exception_handling(self, mock_session_class):
        """Test error handling during client initialization."""
        mock_session_class.side_effect = Exception('AWS credentials not found')

        with pytest.raises(Exception, match='AWS credentials not found'):
            initialize_aws_clients('us-east-1')

    @patch('boto3.Session')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_initialize_aws_clients_success_logging(self, mock_logger, mock_session_class):
        """Test success logging during client initialization."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = MagicMock()

        initialize_aws_clients('us-east-1')

        # Verify success log was called
        mock_logger.info.assert_called_with(
            'AWS clients initialized successfully in region us-east-1'
        )

    @patch('boto3.Session')
    @patch('awslabs.aws_fis_mcp_server.server.logger')
    def test_initialize_aws_clients_error_logging(self, mock_logger, mock_session_class):
        """Test error logging during client initialization."""
        error_msg = 'Network timeout'
        mock_session_class.side_effect = Exception(error_msg)

        with pytest.raises(Exception):
            initialize_aws_clients('us-east-1')

        # Verify error log was called
        mock_logger.error.assert_called_with(f'Error initializing AWS clients: {error_msg}')
