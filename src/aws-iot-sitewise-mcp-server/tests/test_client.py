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

"""Tests for AWS IoT SiteWise client creation utilities."""

import pytest
from awslabs.aws_iot_sitewise_mcp_server import __version__
from awslabs.aws_iot_sitewise_mcp_server.client import (
    create_sitewise_client,
    create_twinmaker_client,
)
from botocore.config import Config
from unittest.mock import MagicMock, patch


class TestCreateSiteWiseClient:
    """Test cases for create_sitewise_client function."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_default_region(self, mock_boto3_client):
        """Test creating SiteWise client with default region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        result = create_sitewise_client()

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once()
        call_args = mock_boto3_client.call_args

        # Check service name
        assert call_args[0][0] == 'iotsitewise'

        # Check region_name
        assert call_args[1]['region_name'] == 'us-east-1'

        # Check config object
        config = call_args[1]['config']
        assert isinstance(config, Config)
        assert hasattr(config, 'user_agent_extra')
        assert (
            getattr(config, 'user_agent_extra')
            == f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        )

        # Check return value
        assert result == mock_client

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_custom_region(self, mock_boto3_client):
        """Test creating SiteWise client with custom region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        custom_region = 'eu-west-1'

        result = create_sitewise_client(region=custom_region)

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once()
        call_args = mock_boto3_client.call_args

        # Check service name
        assert call_args[0][0] == 'iotsitewise'

        # Check region_name
        assert call_args[1]['region_name'] == custom_region

        # Check config object
        config = call_args[1]['config']
        assert isinstance(config, Config)
        assert hasattr(config, 'user_agent_extra')
        assert (
            getattr(config, 'user_agent_extra')
            == f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        )

        # Check return value
        assert result == mock_client

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_user_agent_format(self, mock_boto3_client):
        """Test that user agent is formatted correctly."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        create_sitewise_client()

        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']

        # Verify user agent format
        expected_user_agent = f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        user_agent = getattr(config, 'user_agent_extra')
        assert user_agent == expected_user_agent

        # Verify it contains version number
        assert __version__ in user_agent
        assert 'awslabs/mcp/aws-iot-sitewise-mcp-server' in user_agent

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_sitewise_client_config_object(self, mock_boto3_client):
        """Test that Config object is properly created and passed."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        create_sitewise_client()

        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']

        # Verify config is a Config instance
        assert isinstance(config, Config)

        # Verify config has the expected user_agent_extra
        assert hasattr(config, 'user_agent_extra')
        assert config.user_agent_extra is not None  # type: ignore[attr-defined]

    def test_create_sitewise_client_integration(self):
        """Integration test to verify actual client creation (without mocking)."""
        # This test verifies the function works end-to-end
        # Note: This will create an actual boto3 client but won't make AWS calls
        try:
            client = create_sitewise_client()

            # Verify it's a boto3 client
            assert hasattr(client, '_service_model')
            assert client._service_model.service_name == 'iotsitewise'

            # Verify region is set correctly
            assert client.meta.region_name == 'us-east-1'

        except Exception as e:
            # If there are credential issues, that's expected in test environment
            # We just want to make sure our function doesn't have syntax errors
            if 'credentials' not in str(e).lower():
                raise


class TestCreateTwinMakerClient:
    """Test cases for create_twinmaker_client function."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_twinmaker_client_default_region(self, mock_boto3_client):
        """Test creating TwinMaker client with default region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        result = create_twinmaker_client()

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once()
        call_args = mock_boto3_client.call_args

        # Check service name
        assert call_args[0][0] == 'iottwinmaker'

        # Check region_name
        assert call_args[1]['region_name'] == 'us-east-1'

        # Check config object
        config = call_args[1]['config']
        assert isinstance(config, Config)
        assert hasattr(config, 'user_agent_extra')
        assert (
            getattr(config, 'user_agent_extra')
            == f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        )

        # Check return value
        assert result == mock_client

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_twinmaker_client_custom_region(self, mock_boto3_client):
        """Test creating TwinMaker client with custom region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        custom_region = 'ap-southeast-2'

        result = create_twinmaker_client(region=custom_region)

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once()
        call_args = mock_boto3_client.call_args

        # Check service name
        assert call_args[0][0] == 'iottwinmaker'

        # Check region_name
        assert call_args[1]['region_name'] == custom_region

        # Check config object
        config = call_args[1]['config']
        assert isinstance(config, Config)
        assert (
            getattr(config, 'user_agent_extra')
            == f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        )

        # Check return value
        assert result == mock_client

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_create_twinmaker_client_user_agent_format(self, mock_boto3_client):
        """Test that user agent is formatted correctly for TwinMaker client."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        create_twinmaker_client()

        call_args = mock_boto3_client.call_args
        config = call_args[1]['config']

        # Verify user agent format
        expected_user_agent = f'awslabs/mcp/aws-iot-sitewise-mcp-server/{__version__}'
        user_agent = getattr(config, 'user_agent_extra')
        assert user_agent == expected_user_agent

        # Verify it contains version number
        assert __version__ in user_agent
        assert 'awslabs/mcp/aws-iot-sitewise-mcp-server' in user_agent

    def test_create_twinmaker_client_integration(self):
        """Integration test to verify actual TwinMaker client creation."""
        # This test verifies the function works end-to-end
        try:
            client = create_twinmaker_client()

            # Verify it's a boto3 client
            assert hasattr(client, '_service_model')
            assert client._service_model.service_name == 'iottwinmaker'

            # Verify region is set correctly
            assert client.meta.region_name == 'us-east-1'

        except Exception as e:
            # If there are credential issues, that's expected in test environment
            if 'credentials' not in str(e).lower():
                raise


class TestClientConsistency:
    """Test cases for consistency between client creation functions."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_both_clients_use_same_user_agent(self, mock_boto3_client):
        """Test that both client functions use the same user agent format."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Create both clients
        create_sitewise_client()
        sitewise_call_args = mock_boto3_client.call_args
        sitewise_config = sitewise_call_args[1]['config']

        mock_boto3_client.reset_mock()

        create_twinmaker_client()
        twinmaker_call_args = mock_boto3_client.call_args
        twinmaker_config = twinmaker_call_args[1]['config']

        # Verify both use the same user agent
        assert getattr(sitewise_config, 'user_agent_extra') == getattr(
            twinmaker_config, 'user_agent_extra'
        )

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_both_clients_use_same_default_region(self, mock_boto3_client):
        """Test that both client functions use the same default region."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # Create both clients with default region
        create_sitewise_client()
        sitewise_call_args = mock_boto3_client.call_args
        sitewise_region = sitewise_call_args[1]['region_name']

        mock_boto3_client.reset_mock()

        create_twinmaker_client()
        twinmaker_call_args = mock_boto3_client.call_args
        twinmaker_region = twinmaker_call_args[1]['region_name']

        # Verify both use the same default region
        assert sitewise_region == twinmaker_region == 'us-east-1'

    def test_version_import_works(self):
        """Test that version import is working correctly."""
        # Verify __version__ is accessible and has expected format
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

        # Verify version format (should be semantic versioning)
        version_parts = __version__.split('.')
        assert len(version_parts) >= 2  # At least major.minor

        # Verify parts are numeric
        for part in version_parts:
            assert (
                part.isdigit()
                or part.replace('-', '')
                .replace('+', '')
                .replace('a', '')
                .replace('b', '')
                .replace('rc', '')
                .isdigit()
            )


class TestErrorHandling:
    """Test cases for error handling in client creation."""

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_sitewise_client_boto3_exception_propagation(self, mock_boto3_client):
        """Test that boto3 exceptions are properly propagated for SiteWise client."""
        # Mock boto3.client to raise an exception
        mock_boto3_client.side_effect = Exception('AWS credentials not found')

        with pytest.raises(Exception, match='AWS credentials not found'):
            create_sitewise_client()

    @patch('awslabs.aws_iot_sitewise_mcp_server.client.boto3.client')
    def test_twinmaker_client_boto3_exception_propagation(self, mock_boto3_client):
        """Test that boto3 exceptions are properly propagated for TwinMaker client."""
        # Mock boto3.client to raise an exception
        mock_boto3_client.side_effect = Exception('Invalid region')

        with pytest.raises(Exception, match='Invalid region'):
            create_twinmaker_client()

    def test_invalid_region_parameter_types(self):
        """Test behavior with invalid region parameter types."""
        # Test with None region
        client = create_sitewise_client(region=None)  # type: ignore[arg-type]
        assert client.meta.region_name == 'us-east-1'

        twinmaker_client = create_twinmaker_client(region=None)  # type: ignore[arg-type]
        assert twinmaker_client.meta.region_name == 'us-east-1'

        # Test with non-string region (boto3 should handle this gracefully or raise an error)
        try:
            create_sitewise_client(region=123)  # type: ignore[arg-type]
        except (TypeError, AttributeError, ValueError):
            # This is expected as boto3 expects string
            pass


if __name__ == '__main__':
    pytest.main([__file__])
