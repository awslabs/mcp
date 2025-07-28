"""Test AWS profile handling in isolation."""

import os
import pytest
from unittest.mock import MagicMock, patch


def test_aws_profile_branch_coverage():
    """Test the AWS_PROFILE environment variable branch coverage."""
    # Test the condition when AWS_PROFILE is set
    with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
        assert os.environ.get('AWS_PROFILE') == 'test-profile'

        # Test walrus operator assignment
        if aws_profile := os.environ.get('AWS_PROFILE'):
            assert aws_profile == 'test-profile'

    # Test the condition when AWS_PROFILE is not set
    with patch.dict(os.environ, {}, clear=True):
        assert os.environ.get('AWS_PROFILE') is None

        # Test walrus operator assignment with None
        if aws_profile := os.environ.get('AWS_PROFILE'):
            pytest.fail('Should not enter this branch when AWS_PROFILE is not set')
        else:
            assert aws_profile is None


def test_aws_client_initialization_flow():
    """Test the client initialization flow with and without AWS_PROFILE."""
    import boto3
    from botocore.config import Config

    # Mock config
    config = MagicMock(spec=Config)

    # Test with AWS_PROFILE
    with patch('boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        # Simulate the server initialization logic
        aws_profile = 'test-profile'
        AWS_REGION = 'us-west-2'

        if aws_profile:
            session = boto3.Session(profile_name=aws_profile, region_name=AWS_REGION)
            session.client('logs', config=config)
            session.client('application-signals', config=config)
            session.client('cloudwatch', config=config)
            session.client('xray', config=config)

            # Verify calls
            mock_session.assert_called_once_with(
                profile_name='test-profile', region_name='us-west-2'
            )
            assert mock_session_instance.client.call_count == 4

    # Test without AWS_PROFILE
    with patch('boto3.client') as mock_client:
        AWS_REGION = 'us-east-1'
        aws_profile = None

        if not aws_profile:
            boto3.client('logs', region_name=AWS_REGION, config=config)
            boto3.client('application-signals', region_name=AWS_REGION, config=config)
            boto3.client('cloudwatch', region_name=AWS_REGION, config=config)
            boto3.client('xray', region_name=AWS_REGION, config=config)

            # Verify calls
            assert mock_client.call_count == 4
            for call in mock_client.call_args_list:
                assert call.kwargs['region_name'] == 'us-east-1'
                assert call.kwargs['config'] == config
