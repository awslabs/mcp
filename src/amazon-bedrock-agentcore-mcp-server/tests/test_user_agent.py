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

"""Unit tests for shared user-agent utility."""

import importlib
from awslabs.amazon_bedrock_agentcore_mcp_server.utils import user_agent as ua
from awslabs.amazon_bedrock_agentcore_mcp_server.utils.user_agent import (
    MCP_SERVER_VERSION,
    build_user_agent,
)
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


class TestBuildUserAgent:
    """Tests for build_user_agent."""

    def test_data_plane_only(self):
        """Builds user-agent for data plane (no plane qualifier)."""
        result = build_user_agent('memory')
        assert result == f'agentcore-mcp-server/{MCP_SERVER_VERSION} memory'

    def test_control_plane(self):
        """Builds user-agent with control plane qualifier."""
        result = build_user_agent('memory', 'control')
        expected = f'agentcore-mcp-server/{MCP_SERVER_VERSION} memory-control'
        assert result == expected

    def test_runtime_primitive(self):
        """Works for runtime primitive."""
        result = build_user_agent('runtime')
        assert 'runtime' in result
        assert 'agentcore-mcp-server/' in result

    def test_runtime_control(self):
        """Runtime control plane is distinct from data plane."""
        ctrl = build_user_agent('runtime', 'control')
        data = build_user_agent('runtime')
        assert ctrl != data
        assert 'runtime-control' in ctrl
        assert 'runtime-control' not in data

    def test_browser_primitive(self):
        """Works for browser primitive (single client, no plane)."""
        result = build_user_agent('browser')
        expected = f'agentcore-mcp-server/{MCP_SERVER_VERSION} browser'
        assert result == expected

    def test_code_interpreter_primitive(self):
        """Works for code-interpreter primitive."""
        result = build_user_agent('code-interpreter')
        expected = f'agentcore-mcp-server/{MCP_SERVER_VERSION} code-interpreter'
        assert result == expected

    def test_version_is_consistent(self):
        """All primitives share the same version string."""
        v1 = build_user_agent('memory').split('/')[1].split(' ')[0]
        v2 = build_user_agent('runtime').split('/')[1].split(' ')[0]
        v3 = build_user_agent('browser').split('/')[1].split(' ')[0]
        assert v1 == v2 == v3 == MCP_SERVER_VERSION


class TestPackageVersionFallback:
    """Tests for version detection fallback."""

    def test_package_not_found_fallback(self):
        """MCP_SERVER_VERSION falls back to 'unknown' when package metadata is missing."""
        with patch('importlib.metadata.version', side_effect=PackageNotFoundError):
            importlib.reload(ua)
            try:
                assert ua.MCP_SERVER_VERSION == 'unknown'
                result = ua.build_user_agent('memory')
                assert result == 'agentcore-mcp-server/unknown memory'
            finally:
                # Restore module to its normal state for other tests
                importlib.reload(ua)
