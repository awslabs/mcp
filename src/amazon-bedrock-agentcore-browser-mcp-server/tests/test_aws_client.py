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

"""Tests for AWS client utilities."""

import os
import pytest
from awslabs.amazon_bedrock_agentcore_browser_mcp_server import aws_client
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


class TestGetSession:
    """Test cases for _get_session."""

    def test_get_session_default_no_env_vars(self):
        """Test session creation with no environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.Session'
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.region_name = 'us-west-2'
                mock_session_class.return_value = mock_session

                session, region = aws_client._get_session()

                mock_session_class.assert_called_once_with()
                assert session == mock_session
                assert region == 'us-west-2'

    def test_get_session_with_aws_profile(self):
        """Test session creation with AWS_PROFILE environment variable."""
        with patch.dict(os.environ, {'AWS_PROFILE': 'my-profile'}, clear=True):
            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.Session'
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.region_name = 'eu-west-1'
                mock_session_class.return_value = mock_session

                session, region = aws_client._get_session()

                mock_session_class.assert_called_once_with(profile_name='my-profile')
                assert session == mock_session
                assert region == 'eu-west-1'

    def test_get_session_with_aws_region(self):
        """Test session creation with AWS_REGION environment variable."""
        with patch.dict(os.environ, {'AWS_REGION': 'ap-south-1'}):
            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.Session'
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.region_name = 'us-east-1'
                mock_session_class.return_value = mock_session

                session, region = aws_client._get_session()

                assert region == 'ap-south-1'

    def test_get_session_with_region_name_param(self):
        """Test session creation with explicit region_name parameter."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.Session'
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.region_name = 'us-west-2'
                mock_session_class.return_value = mock_session

                session, region = aws_client._get_session(region_name='ca-central-1')

                assert region == 'ca-central-1'

    def test_get_session_fallback_to_us_east_1(self):
        """Test session creation falls back to us-east-1 when no region is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.Session'
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.region_name = None
                mock_session_class.return_value = mock_session

                session, region = aws_client._get_session()

                assert region == 'us-east-1'


class TestGetClient:
    """Test cases for _get_client."""

    def test_get_client_creates_new_client(self):
        """Test that _get_client creates a new client on first call."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_session.client.return_value = mock_client
            mock_get_session.return_value = (mock_session, 'us-east-1')

            client = aws_client._get_client('bedrock-agentcore')

            assert client == mock_client
            mock_session.client.assert_called_once()
            call_args = mock_session.client.call_args
            assert call_args[0][0] == 'bedrock-agentcore'
            assert call_args[1]['region_name'] == 'us-east-1'
            assert 'config' in call_args[1]
            assert 'md/awslabs#mcp#agentcore-browser#' in call_args[1]['config'].user_agent_extra

    def test_get_client_returns_cached_client(self):
        """Test that _get_client returns cached client on second call."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_session.client.return_value = mock_client
            mock_get_session.return_value = (mock_session, 'us-east-1')

            # First call
            client1 = aws_client._get_client('bedrock-agentcore')
            # Second call
            client2 = aws_client._get_client('bedrock-agentcore')

            assert client1 == client2
            # Session.client should only be called once (cached)
            mock_session.client.assert_called_once()

    def test_get_client_different_service_creates_separate_cache_entry(self):
        """Test that different service names create separate cached clients."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_session.client.side_effect = [mock_client1, mock_client2]
            mock_get_session.return_value = (mock_session, 'us-east-1')

            client1 = aws_client._get_client('bedrock-agentcore')
            client2 = aws_client._get_client('bedrock-agentcore-control')

            assert client1 != client2
            assert mock_session.client.call_count == 2

    def test_get_client_different_region_creates_separate_cache_entry(self):
        """Test that different regions create separate cached clients."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            mock_session.client.side_effect = [mock_client1, mock_client2]

            # Different regions for each call
            mock_get_session.side_effect = [
                (mock_session, 'us-east-1'),
                (mock_session, 'us-west-2'),
            ]

            client1 = aws_client._get_client('bedrock-agentcore', region_name='us-east-1')
            client2 = aws_client._get_client('bedrock-agentcore', region_name='us-west-2')

            assert client1 != client2
            assert mock_session.client.call_count == 2


class TestGetDataPlaneClient:
    """Test cases for get_data_plane_client."""

    def test_get_data_plane_client(self):
        """Test that get_data_plane_client delegates to _get_client."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = aws_client.get_data_plane_client()

            mock_get_client.assert_called_once_with('bedrock-agentcore', None)
            assert client == mock_client

    def test_get_data_plane_client_with_region(self):
        """Test that get_data_plane_client passes region to _get_client."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = aws_client.get_data_plane_client(region_name='eu-central-1')

            mock_get_client.assert_called_once_with('bedrock-agentcore', 'eu-central-1')
            assert client == mock_client


class TestGetControlPlaneClient:
    """Test cases for get_control_plane_client."""

    def test_get_control_plane_client(self):
        """Test that get_control_plane_client delegates to _get_client."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = aws_client.get_control_plane_client()

            mock_get_client.assert_called_once_with('bedrock-agentcore-control', None)
            assert client == mock_client

    def test_get_control_plane_client_with_region(self):
        """Test that get_control_plane_client passes region to _get_client."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = aws_client.get_control_plane_client(region_name='ap-northeast-1')

            mock_get_client.assert_called_once_with('bedrock-agentcore-control', 'ap-northeast-1')
            assert client == mock_client


class TestSignWebsocketHeaders:
    """Test cases for sign_websocket_headers."""

    def test_sign_websocket_headers_happy_path(self):
        """Test successful SigV4 header generation."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_credentials = MagicMock()
            mock_frozen_creds = MagicMock()
            mock_frozen_creds.access_key = 'fake-access-key'
            mock_frozen_creds.secret_key = 'fake-secret-key'  # noqa: S105
            mock_frozen_creds.token = 'fake-token'
            mock_credentials.get_frozen_credentials.return_value = mock_frozen_creds
            mock_session.get_credentials.return_value = mock_credentials
            mock_get_session.return_value = (mock_session, 'us-west-2')

            ws_url = 'wss://example.com:443/path?query=value'

            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.SigV4Auth'
            ) as mock_signer_class:
                mock_signer = MagicMock()
                mock_signer_class.return_value = mock_signer

                with patch(
                    'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.AWSRequest'
                ) as mock_request_class:
                    mock_request = MagicMock()
                    mock_request.headers = {
                        'Authorization': 'AWS4-HMAC-SHA256 ...',
                        'X-Amz-Date': '20260320T120000Z',
                        'X-Amz-Security-Token': 'session-token',
                        'Host': 'example.com',
                    }
                    mock_request_class.return_value = mock_request

                    result = aws_client.sign_websocket_headers(ws_url)

                    # Verify request created with wss:// converted to https://
                    mock_request_class.assert_called_once()
                    call_args = mock_request_class.call_args[1]
                    assert call_args['method'] == 'GET'
                    assert call_args['url'] == 'https://example.com/path'
                    assert call_args['headers']['Host'] == 'example.com'

                    # Verify signer configured correctly
                    mock_signer_class.assert_called_once_with(
                        mock_frozen_creds, 'bedrock-agentcore', 'us-west-2'
                    )
                    mock_signer.add_auth.assert_called_once_with(mock_request)

                    # Verify headers returned
                    assert 'Authorization' in result
                    assert 'X-Amz-Date' in result
                    assert 'X-Amz-Security-Token' in result
                    assert 'Host' in result

    def test_sign_websocket_headers_no_credentials(self):
        """Test sign_websocket_headers raises error when no credentials available."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_session.get_credentials.return_value = None
            mock_get_session.return_value = (mock_session, 'us-east-1')

            with pytest.raises(
                RuntimeError, match='No AWS credentials available for SigV4 signing'
            ):
                aws_client.sign_websocket_headers('wss://example.com/path')

    def test_sign_websocket_headers_with_region(self):
        """Test sign_websocket_headers with explicit region."""
        with patch(
            'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client._get_session'
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_credentials = MagicMock()
            mock_frozen_creds = MagicMock()
            mock_credentials.get_frozen_credentials.return_value = mock_frozen_creds
            mock_session.get_credentials.return_value = mock_credentials
            mock_get_session.return_value = (mock_session, 'ap-southeast-1')

            with patch(
                'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.SigV4Auth'
            ) as mock_signer_class:
                mock_signer = MagicMock()
                mock_signer_class.return_value = mock_signer

                with patch(
                    'awslabs.amazon_bedrock_agentcore_browser_mcp_server.aws_client.AWSRequest'
                ) as mock_request_class:
                    mock_request = MagicMock()
                    mock_request.headers = {'Authorization': 'AWS4-HMAC-SHA256 ...'}
                    mock_request_class.return_value = mock_request

                    aws_client.sign_websocket_headers(
                        'wss://example.com/path', region_name='ap-southeast-1'
                    )

                    mock_get_session.assert_called_once_with('ap-southeast-1')
                    mock_signer_class.assert_called_once_with(
                        mock_frozen_creds, 'bedrock-agentcore', 'ap-southeast-1'
                    )


class TestHandleAwsErrors:
    """Test cases for handle_aws_errors decorator."""

    def test_handle_aws_errors_success(self):
        """Test decorator passes through successful function results."""

        @aws_client.handle_aws_errors('test operation')
        def successful_function():
            return {'result': 'success'}

        result = successful_function()

        assert result == {'result': 'success'}

    def test_handle_aws_errors_client_error(self):
        """Test decorator handles ClientError."""

        @aws_client.handle_aws_errors('test operation')
        def failing_function():
            error_response = {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'The requested resource was not found',
                }
            }
            raise ClientError(error_response, 'GetBrowserSession')

        result = failing_function()

        assert result == {
            'error': 'ResourceNotFoundException',
            'message': 'The requested resource was not found',
        }

    def test_handle_aws_errors_client_error_missing_fields(self):
        """Test decorator handles ClientError with missing error fields."""

        @aws_client.handle_aws_errors('test operation')
        def failing_function():
            error_response = {'Error': {}}
            raise ClientError(error_response, 'GetBrowserSession')

        result = failing_function()

        assert result['error'] == 'Unknown'
        assert 'message' in result

    def test_handle_aws_errors_generic_exception(self):
        """Test decorator handles generic Exception."""

        @aws_client.handle_aws_errors('test operation')
        def failing_function():
            raise ValueError('Something went wrong')

        result = failing_function()

        assert result == {'error': 'UnexpectedError', 'message': 'Something went wrong'}

    def test_handle_aws_errors_preserves_function_metadata(self):
        """Test decorator preserves function metadata via functools.wraps."""

        @aws_client.handle_aws_errors('test operation')
        def documented_function():
            """This is a documented function."""
            return {'status': 'ok'}

        assert documented_function.__name__ == 'documented_function'
        assert documented_function.__doc__ == 'This is a documented function.'

    def test_handle_aws_errors_with_args_and_kwargs(self):
        """Test decorator works with functions that have arguments."""

        @aws_client.handle_aws_errors('test operation')
        def function_with_params(arg1, arg2, kwarg1=None):
            return {'arg1': arg1, 'arg2': arg2, 'kwarg1': kwarg1}

        result = function_with_params('value1', 'value2', kwarg1='value3')

        assert result == {'arg1': 'value1', 'arg2': 'value2', 'kwarg1': 'value3'}
