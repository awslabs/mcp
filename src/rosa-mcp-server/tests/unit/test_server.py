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

"""Tests for the ROSA MCP Server."""

from awslabs.rosa_mcp_server.server import create_server, main
from unittest.mock import MagicMock, patch


class TestCreateServer:
    """Tests for server creation."""

    def test_create_server_returns_fastmcp_instance(self):
        """Test that create_server returns a FastMCP server."""
        server = create_server()
        assert server is not None
        assert server.name == 'awslabs.rosa-mcp-server'

    def test_create_server_has_instructions(self):
        """Test that created server has instructions set."""
        server = create_server()
        assert server.instructions is not None
        assert 'ROSA' in server.instructions

    def test_create_server_instructions_mention_ocm_token(self):
        """Test that instructions mention OCM_TOKEN for authentication."""
        server = create_server()
        assert 'OCM_TOKEN' in server.instructions


class TestMain:
    """Tests for the main entry point."""

    @patch('awslabs.rosa_mcp_server.server.OCMClient')
    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server', '--allow-write'])
    @patch.dict('os.environ', {'OCM_TOKEN': 'test-token'})
    def test_allow_write_flag(self, mock_fastmcp_class, mock_ocm_class):
        """Test that --allow-write flag enables write operations."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        mock_fastmcp_class.return_value = mock_mcp
        mock_ocm_class.return_value = MagicMock()

        result = main()

        assert result is not None

    @patch('awslabs.rosa_mcp_server.server.OCMClient')
    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server', '--allow-sensitive-data-access'])
    @patch.dict('os.environ', {'OCM_TOKEN': 'test-token'})
    def test_allow_sensitive_data_access_flag(self, mock_fastmcp_class, mock_ocm_class):
        """Test that --allow-sensitive-data-access flag enables sensitive data."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        mock_fastmcp_class.return_value = mock_mcp
        mock_ocm_class.return_value = MagicMock()

        result = main()

        assert result is not None

    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server'])
    @patch.dict('os.environ', {'OCM_TOKEN': ''}, clear=False)
    def test_default_read_only_mode_no_ocm_token(self, mock_fastmcp_class):
        """Test that server starts with AWS-only tools when OCM_TOKEN is not set."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        mock_fastmcp_class.return_value = mock_mcp

        result = main()

        assert result is not None

    @patch('awslabs.rosa_mcp_server.server.OCMClient')
    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server', '--allow-write', '--allow-sensitive-data-access'])
    @patch.dict('os.environ', {'OCM_TOKEN': 'test-token'})
    def test_all_flags_enabled(self, mock_fastmcp_class, mock_ocm_class):
        """Test that both flags can be enabled simultaneously."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        mock_fastmcp_class.return_value = mock_mcp
        mock_ocm_class.return_value = MagicMock()

        result = main()

        assert result is not None

    @patch('awslabs.rosa_mcp_server.server.OCMClient')
    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server'])
    @patch.dict('os.environ', {'OCM_TOKEN': 'test-token'})
    def test_ocm_client_created_with_token(self, mock_fastmcp_class, mock_ocm_class):
        """Test that OCMClient is instantiated when OCM_TOKEN is available."""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        mock_fastmcp_class.return_value = mock_mcp
        mock_ocm_class.return_value = MagicMock()

        main()

        mock_ocm_class.assert_called_once()


class TestToolRegistration:
    """Tests that tools are registered correctly."""

    @patch('awslabs.rosa_mcp_server.server.OCMClient')
    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server'])
    @patch.dict('os.environ', {'OCM_TOKEN': 'test-token'})
    def test_ocm_tools_are_registered(self, mock_fastmcp_class, mock_ocm_class):
        """Test that all OCM-based tools are registered when token is available."""
        mock_mcp = MagicMock()
        registered_tools = []

        def track_tool(name):
            def decorator(func):
                registered_tools.append(name)
                return func
            return decorator

        mock_mcp.tool = track_tool
        mock_fastmcp_class.return_value = mock_mcp
        mock_ocm_class.return_value = MagicMock()

        main()

        expected_tools = [
            # Cluster handler
            'rosa_list_clusters',
            'rosa_describe_cluster',
            'rosa_create_cluster',
            'rosa_delete_cluster',
            'rosa_list_versions',
            'rosa_list_upgrades',
            'rosa_upgrade_cluster',
            'rosa_get_cluster_credentials',
            'rosa_get_install_logs',
            # Auth handler
            'rosa_whoami',
            'rosa_manage_idp',
            # Machine pool handler
            'rosa_manage_machinepool',
            # Networking handler
            'rosa_manage_ingress',
            # K8s handler
            'rosa_list_resources',
            'rosa_get_pod_logs',
            'rosa_get_events',
            'rosa_apply_yaml',
            'rosa_get_nodes',
            # CloudWatch handler
            'rosa_get_cloudwatch_logs',
            'rosa_get_cloudwatch_metrics',
            # IAM handler
            'rosa_manage_iam',
        ]

        for tool_name in expected_tools:
            assert tool_name in registered_tools, f'Tool {tool_name} was not registered'

    @patch('awslabs.rosa_mcp_server.server.FastMCP')
    @patch('sys.argv', ['server'])
    @patch.dict('os.environ', {'OCM_TOKEN': ''}, clear=False)
    @patch('awslabs.rosa_mcp_server.ocm_client.OCMClient._load_ocm_config', return_value={})
    def test_aws_only_tools_registered_without_ocm_token(
        self, mock_ocm_config, mock_fastmcp_class
    ):
        """Test that AWS-only tools are registered even without OCM_TOKEN."""
        mock_mcp = MagicMock()
        registered_tools = []

        def track_tool(name):
            def decorator(func):
                registered_tools.append(name)
                return func
            return decorator

        mock_mcp.tool = track_tool
        mock_fastmcp_class.return_value = mock_mcp

        main()

        # AWS-only tools should always be registered
        aws_tools = [
            'rosa_get_cloudwatch_logs',
            'rosa_get_cloudwatch_metrics',
            'rosa_manage_iam',
        ]

        for tool_name in aws_tools:
            assert tool_name in registered_tools, f'AWS tool {tool_name} was not registered'

        # OCM-based tools should NOT be registered
        ocm_tools = [
            'rosa_list_clusters',
            'rosa_describe_cluster',
            'rosa_whoami',
            'rosa_list_machinepools',
            'rosa_list_ingresses',
        ]

        for tool_name in ocm_tools:
            assert tool_name not in registered_tools, (
                f'OCM tool {tool_name} should not be registered without OCM_TOKEN'
            )
