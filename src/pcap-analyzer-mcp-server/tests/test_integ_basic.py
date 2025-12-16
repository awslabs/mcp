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
"""Basic integration test for pcap-analyzer-mcp-server - Developer Guide compliant."""

import json
import pytest
from awslabs.pcap_analyzer_mcp_server.server import PCAPAnalyzerServer
from mcp.types import TextContent


class TestPCAPAnalyzerIntegration:
    """Integration tests for PCAP Analyzer MCP Server following Developer Guide patterns."""

    def setup_method(self):
        """Set up test fixtures for integration testing."""
        self.server = PCAPAnalyzerServer()

    @pytest.mark.asyncio
    async def test_server_initialization_integration(self):
        """Integration test: Server initializes correctly."""
        assert self.server.server.name == 'pcap-analyzer-mcp-server'
        assert hasattr(self.server, '_setup_tools')

    @pytest.mark.asyncio
    async def test_list_network_interfaces_integration(self, mocker):
        """Integration test: Network interface listing with mocked system calls."""
        # Mock system network interfaces
        mock_addrs = mocker.patch('awslabs.pcap_analyzer_mcp_server.server.psutil.net_if_addrs')
        mock_addrs.return_value = {'eth0': [mocker.MagicMock(address='192.168.1.1')]}

        mock_stats = mocker.patch('awslabs.pcap_analyzer_mcp_server.server.psutil.net_if_stats')
        mock_stat = mocker.MagicMock()
        mock_stat.isup = True
        mock_stat.speed = 1000
        mock_stats.return_value = {'eth0': mock_stat}

        # Test integration
        result = await self.server._list_network_interfaces()

        # Validate integration behavior
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert data['total_count'] == 1
        assert data['interfaces'][0]['name'] == 'eth0'

    def test_pcap_path_validation_integration(self):
        """Integration test: Path validation security integration."""
        # Test security validation integration
        with pytest.raises(ValueError, match='Only .pcap files are allowed'):
            self.server._resolve_pcap_path('malicious.txt')

        with pytest.raises(ValueError, match='Path traversal patterns not allowed'):
            self.server._resolve_pcap_path('../../../etc/passwd.pcap')

    @pytest.mark.asyncio
    async def test_tool_error_handling_integration(self):
        """Integration test: Tool error handling integration."""
        # Test error handling integration with non-existent file
        result = await self.server._analyze_pcap_file('nonexistent.pcap')

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error' in result[0].text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
