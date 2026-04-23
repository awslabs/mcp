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

"""Unit tests for Policy client wrapper."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.policy_client import (
    MCP_USER_AGENT,
    _policy_clients,
    get_policy_client,
)
from unittest.mock import MagicMock, patch


PATCH_SESSION = (
    'awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.policy_client.boto3.Session'
)


def _extract_config(mock_session):
    """Extract the Config object from a mock session.client() call."""
    call_kwargs = mock_session.client.call_args
    return call_kwargs.kwargs.get('config')


class TestGetPolicyClient:
    """Tests for get_policy_client."""

    def setup_method(self):
        """Clear client cache before each test."""
        _policy_clients.clear()

    @patch.dict('os.environ', {}, clear=True)
    @patch(PATCH_SESSION)
    def test_creates_client_with_defaults(self, mock_session_cls):
        """Creates client with default region and correct service."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_cls.return_value = mock_session

        client = get_policy_client()

        mock_session_cls.assert_called_once_with(region_name='us-east-1')
        mock_session.client.assert_called_once()
        assert mock_session.client.call_args[0][0] == 'bedrock-agentcore-control'
        assert client is mock_client

    @patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'}, clear=True)
    @patch(PATCH_SESSION)
    def test_uses_env_region(self, mock_session_cls):
        """Uses AWS_REGION environment variable when set."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_policy_client()

        mock_session_cls.assert_called_once_with(region_name='eu-west-1')

    @patch(PATCH_SESSION)
    def test_uses_explicit_region(self, mock_session_cls):
        """Uses explicitly specified region over env var."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_policy_client(region_name='ap-southeast-1')

        mock_session_cls.assert_called_once_with(region_name='ap-southeast-1')

    @patch(PATCH_SESSION)
    def test_caches_client(self, mock_session_cls):
        """Returns cached client on subsequent calls with same region."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        c1 = get_policy_client(region_name='us-east-1')
        c2 = get_policy_client(region_name='us-east-1')

        assert c1 is c2
        assert mock_session_cls.call_count == 1

    @patch(PATCH_SESSION)
    def test_different_regions_different_clients(self, mock_session_cls):
        """Different regions produce different cached clients."""
        mock_s1 = MagicMock()
        mock_s2 = MagicMock()
        mock_s1.client.return_value = MagicMock()
        mock_s2.client.return_value = MagicMock()
        mock_session_cls.side_effect = [mock_s1, mock_s2]

        c1 = get_policy_client(region_name='us-east-1')
        c2 = get_policy_client(region_name='us-west-2')

        assert c1 is not c2
        assert mock_session_cls.call_count == 2

    @patch(PATCH_SESSION)
    def test_user_agent_tracking(self, mock_session_cls):
        """Policy client has the policy user-agent suffix."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_policy_client(region_name='us-east-1')

        config = _extract_config(mock_session)
        assert config is not None
        assert config.user_agent_extra == MCP_USER_AGENT
        assert 'policy' in config.user_agent_extra

    @patch(PATCH_SESSION)
    def test_user_agent_has_no_control_suffix(self, mock_session_cls):
        """Single-client primitive uses plain 'policy' (no '-control' qualifier)."""
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session_cls.return_value = mock_session

        get_policy_client(region_name='us-east-1')

        config = _extract_config(mock_session)
        assert config is not None
        # Plain primitive name, not 'policy-control' or 'policy-data'
        assert 'policy-control' not in config.user_agent_extra
        assert 'policy-data' not in config.user_agent_extra
