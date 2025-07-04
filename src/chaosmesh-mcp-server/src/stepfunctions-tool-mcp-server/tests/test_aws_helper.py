"""Tests for the AWS Helper."""

import os
from awslabs.stepfunctions_tool_mcp_server.aws_helper import AwsHelper
from awslabs.stepfunctions_tool_mcp_server.server import __version__
from unittest.mock import ANY, MagicMock, patch


class TestAwsHelper:
    """Tests for the AwsHelper class."""

    def test_get_aws_region_default(self):
        """Test that get_aws_region returns the default region."""
        with patch.dict(os.environ, {}, clear=True):
            region = AwsHelper.get_aws_region()
            assert region == 'us-east-1'

    @patch.dict(os.environ, {'AWS_REGION': 'us-west-2'})
    def test_get_aws_region_from_env(self):
        """Test that get_aws_region returns the region from the environment."""
        region = AwsHelper.get_aws_region()
        assert region == 'us-west-2'

    @patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'})
    def test_get_aws_profile_from_env(self):
        """Test that get_aws_profile returns the profile from the environment."""
        profile = AwsHelper.get_aws_profile()
        assert profile == 'test-profile'

    @patch('boto3.Session')
    def test_create_boto3_client_with_profile(self, mock_boto3_session):
        """Test client creation with profile."""
        mock_session = MagicMock()
        mock_boto3_session.return_value = mock_session

        with patch.object(AwsHelper, 'get_aws_profile', return_value='test-profile'):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                AwsHelper.create_boto3_client('stepfunctions')
                mock_boto3_session.assert_called_once_with(profile_name='test-profile')
                mock_session.client.assert_called_once_with(
                    'stepfunctions', region_name='us-west-2', config=ANY
                )

    @patch('boto3.client')
    def test_create_boto3_client_without_profile(self, mock_boto3_client):
        """Test client creation without profile."""
        with patch.object(AwsHelper, 'get_aws_profile', return_value=None):
            with patch.object(AwsHelper, 'get_aws_region', return_value='us-west-2'):
                AwsHelper.create_boto3_client('stepfunctions')
                mock_boto3_client.assert_called_once_with(
                    'stepfunctions', region_name='us-west-2', config=ANY
                )

    def test_create_boto3_client_user_agent(self):
        """Test that create_boto3_client sets the user agent correctly."""
        mock_session = MagicMock()
        with patch('boto3.Session', return_value=mock_session):
            with patch.object(AwsHelper, 'get_aws_profile', return_value='test-profile'):
                AwsHelper.create_boto3_client('stepfunctions')
                _, kwargs = mock_session.client.call_args
                config = kwargs.get('config')
                assert config is not None
                assert (
                    config.user_agent_extra
                    == f'awslabs/mcp/aws-stepfunctions-tool-mcp-server/{__version__}'
                )
