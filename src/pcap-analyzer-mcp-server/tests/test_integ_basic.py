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
"""Basic integration test for pcap-analyzer-mcp-server using the official MCP SDK."""

import asyncio
import logging
import os
import pytest
import sys


# Add the testing framework to the path
testing_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'testing')
sys.path.insert(0, testing_path)

# Also add the parent directory to handle relative imports
parent_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, parent_path)

try:
    from testing.pytest_utils import (  # noqa: E402
        MCPTestBase,
        assert_test_results,
        create_test_config,
        create_tool_test_config,
        create_validation_rule,
        setup_logging,
    )
except ImportError:
    # Skip integration tests if testing framework not available
    pytest.skip('Testing framework not available', allow_module_level=True)


# setup constants
PCAP_ANALYZER_SERVER_PY = 'awslabs/pcap_analyzer_mcp_server/server.py'
LIST_NETWORK_INTERFACES_TOOL_NAME = 'list_network_interfaces'
GET_CAPTURE_STATUS_TOOL_NAME = 'get_capture_status'
LIST_CAPTURED_FILES_TOOL_NAME = 'list_captured_files'
NUMBER_OF_TOOLS = 31  # PCAP analyzer has 31 comprehensive network analysis tools

# Setup logging
setup_logging('INFO')
logger = logging.getLogger(__name__)


class TestPCAPAnalyzerMCPServer:
    """Basic integration tests for PCAP Analyzer MCP Server."""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Set up test environment."""
        self.server_path = os.path.join(os.path.dirname(__file__), '..')
        self.test_instance = None
        yield
        if self.test_instance:
            asyncio.run(self.test_instance.teardown())

    @pytest.mark.asyncio
    async def test_basic_protocol(self):
        """Test basic MCP protocol functionality."""
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=['run', '--frozen', PCAP_ANALYZER_SERVER_PY],
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )

        await self.test_instance.setup()

        # Define expected configuration
        expected_config = create_test_config(
            expected_tools={
                'count': NUMBER_OF_TOOLS,  # 31 comprehensive network analysis tools
                'names': [
                    LIST_NETWORK_INTERFACES_TOOL_NAME,
                    GET_CAPTURE_STATUS_TOOL_NAME,
                    LIST_CAPTURED_FILES_TOOL_NAME,
                    'start_packet_capture',
                    'stop_packet_capture',
                    'analyze_pcap_file',
                    'extract_http_requests',
                    'generate_traffic_timeline',
                    'search_packet_content',
                    'analyze_network_performance',
                    'analyze_network_latency',
                    'analyze_tls_handshakes',
                    'analyze_sni_mismatches',
                    'extract_certificate_details',
                    'analyze_tls_alerts',
                    'analyze_connection_lifecycle',
                    'extract_tls_cipher_analysis',
                    'analyze_tcp_retransmissions',
                    'analyze_tcp_zero_window',
                    'analyze_tcp_window_scaling',
                    'analyze_packet_timing_issues',
                    'analyze_congestion_indicators',
                    'analyze_dns_resolution_issues',
                    'analyze_expert_information',
                    'analyze_protocol_anomalies',
                    'analyze_network_topology',
                    'analyze_security_threats',
                    'generate_throughput_io_graph',
                    'analyze_bandwidth_utilization',
                    'analyze_application_response_times',
                    'analyze_network_quality_metrics',
                ],
            },
            expected_resources={
                'count': 0  # This server doesn't provide resources
            },
            expected_prompts={
                'count': 0  # This server doesn't provide prompts
            },
        )

        # Run basic tests
        results = await self.test_instance.run_basic_tests(expected_config)

        # Assert results
        assert_test_results(results, expected_success_count=6)  # 6 basic protocol tests

    @pytest.mark.asyncio
    async def test_list_network_interfaces_tool(self):
        """Test the list network interfaces tool."""
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=['run', '--frozen', PCAP_ANALYZER_SERVER_PY],
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )

        await self.test_instance.setup()

        validation_rules = [
            create_validation_rule('contains', 'interfaces', 'content'),
            create_validation_rule('contains', 'total_count', 'content'),
        ]

        test_config = create_tool_test_config(
            tool_name=LIST_NETWORK_INTERFACES_TOOL_NAME,
            arguments={},
            validation_rules=validation_rules,
        )

        result = await self.test_instance.run_custom_test(test_config)

        assert result.success, f'List network interfaces test failed: {result.error_message}'
        assert 'result' in result.details, 'Response should contain result field'

    @pytest.mark.asyncio
    async def test_get_capture_status_tool(self):
        """Test the get capture status tool."""
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=['run', '--frozen', PCAP_ANALYZER_SERVER_PY],
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )

        await self.test_instance.setup()

        validation_rules = [
            create_validation_rule('contains', 'active_captures', 'content'),
            create_validation_rule('contains', 'captures', 'content'),
        ]

        test_config = create_tool_test_config(
            tool_name=GET_CAPTURE_STATUS_TOOL_NAME,
            arguments={},
            validation_rules=validation_rules,
        )

        result = await self.test_instance.run_custom_test(test_config)

        assert result.success, f'Get capture status test failed: {result.error_message}'
        assert 'result' in result.details, 'Response should contain result field'

    @pytest.mark.asyncio
    async def test_list_captured_files_tool(self):
        """Test the list captured files tool."""
        # Create test instance
        self.test_instance = MCPTestBase(
            server_path=self.server_path,
            command='uv',
            args=['run', '--frozen', PCAP_ANALYZER_SERVER_PY],
            env={'FASTMCP_LOG_LEVEL': 'ERROR'},
        )

        await self.test_instance.setup()

        validation_rules = [
            create_validation_rule('contains', 'storage_directory', 'content'),
            create_validation_rule('contains', 'total_files', 'content'),
            create_validation_rule('contains', 'files', 'content'),
        ]

        test_config = create_tool_test_config(
            tool_name=LIST_CAPTURED_FILES_TOOL_NAME,
            arguments={},
            validation_rules=validation_rules,
        )

        result = await self.test_instance.run_custom_test(test_config)

        assert result.success, f'List captured files test failed: {result.error_message}'
        assert 'result' in result.details, 'Response should contain result field'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
