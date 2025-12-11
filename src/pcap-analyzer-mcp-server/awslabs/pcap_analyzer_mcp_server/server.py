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

"""PCAP Analyzer MCP Server - Comprehensive network packet capture and analysis."""

import asyncio
import json
import logging
import os
import psutil
import time
from datetime import datetime
from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pathlib import Path
from typing import Any, Dict, List, Optional


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration
PCAP_STORAGE_DIR = os.getenv('PCAP_STORAGE_DIR', './pcap_storage')
MAX_CAPTURE_DURATION = int(os.getenv('MAX_CAPTURE_DURATION', '3600'))
WIRESHARK_PATH = os.getenv('WIRESHARK_PATH', 'tshark')

# Ensure storage directory exists
Path(PCAP_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

# Active capture sessions
active_captures: Dict[str, Dict[str, Any]] = {}


class PCAPAnalyzerServer:
    """PCAP Analyzer MCP Server with 31 comprehensive network analysis tools."""

    def __init__(self):
        """Initialize the PCAP Analyzer server."""
        self.server = Server('pcap-analyzer-mcp-server')
        self._setup_tools()

    def _setup_tools(self):
        """Set up all 31 network analysis tools."""

        # Network Interface Management (1 tool)
        @self.server.list_tools()  # pragma: no cover
        async def handle_list_tools() -> list[Tool]:  # pragma: no cover
            """List all available PCAP analysis tools."""
            return [
                # Network Interface Management
                Tool(
                    name='list_network_interfaces',
                    description='List available network interfaces for packet capture',
                    inputSchema={
                        'type': 'object',
                        'properties': {},
                    },
                ),
                # Packet Capture Management (4 tools)
                Tool(
                    name='start_packet_capture',
                    description='Start packet capture on specified interface',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'interface': {
                                'type': 'string',
                                'description': "Network interface to capture on (e.g., 'en0')",
                            },
                            'duration': {
                                'type': 'integer',
                                'description': 'Capture duration in seconds (default: 60)',
                                'default': 60,
                            },
                            'capture_filter': {
                                'type': 'string',
                                'description': "BPF filter for capture (e.g., 'tcp port 80')",
                            },
                            'output_file': {
                                'type': 'string',
                                'description': 'Custom output filename (optional)',
                            },
                        },
                        'required': ['interface'],
                    },
                ),
                Tool(
                    name='stop_packet_capture',
                    description='Stop an active packet capture session',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'capture_id': {
                                'type': 'string',
                                'description': 'ID of the capture session to stop',
                            },
                        },
                        'required': ['capture_id'],
                    },
                ),
                Tool(
                    name='get_capture_status',
                    description='Get status of all active capture sessions',
                    inputSchema={
                        'type': 'object',
                        'properties': {},
                    },
                ),
                Tool(
                    name='list_captured_files',
                    description='List all captured pcap files in storage directory',
                    inputSchema={
                        'type': 'object',
                        'properties': {},
                    },
                ),
                # Basic PCAP Analysis (4 tools)
                Tool(
                    name='analyze_pcap_file',
                    description='Analyze a pcap file and generate insights',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file or filename in storage',
                            },
                            'analysis_type': {
                                'type': 'string',
                                'description': 'Type of analysis (summary, protocols)',
                                'default': 'summary',
                            },
                            'display_filter': {
                                'type': 'string',
                                'description': "Wireshark display filter (e.g., 'tcp.port == 80')",
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='extract_http_requests',
                    description='Extract HTTP requests from pcap file',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'limit': {
                                'type': 'integer',
                                'description': 'Maximum number of requests to extract',
                                'default': 100,
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='generate_traffic_timeline',
                    description='Generate traffic timeline with specified time intervals',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'time_interval': {
                                'type': 'integer',
                                'description': 'Time interval in seconds for timeline',
                                'default': 60,
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='search_packet_content',
                    description='Search for specific patterns in packet content',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'search_pattern': {
                                'type': 'string',
                                'description': 'Pattern to search for in packet content',
                            },
                            'case_sensitive': {
                                'type': 'boolean',
                                'description': 'Whether search should be case sensitive',
                                'default': False,
                            },
                            'limit': {
                                'type': 'integer',
                                'description': 'Maximum number of matches to return',
                                'default': 50,
                            },
                        },
                        'required': ['pcap_file', 'search_pattern'],
                    },
                ),
                # Network Performance Analysis (2 tools)
                Tool(
                    name='analyze_network_performance',
                    description='Analyze network performance metrics from pcap file',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_network_latency',
                    description='Analyze network latency and response times',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                # TLS/SSL Security Analysis (6 tools)
                Tool(
                    name='analyze_tls_handshakes',
                    description='Analyze TLS handshakes including SNI, certificate details',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_sni_mismatches',
                    description='Analyze SNI mismatches and correlate with connection resets',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='extract_certificate_details',
                    description='Extract SSL certificate details and validate against SNI',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_tls_alerts',
                    description='Analyze TLS alert messages that indicate handshake failures',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_connection_lifecycle',
                    description='Analyze complete connection lifecycle from SYN to FIN/RST',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='extract_tls_cipher_analysis',
                    description='Analyze TLS cipher suite negotiations and compatibility issues',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                # TCP Protocol Analysis (5 tools)
                Tool(
                    name='analyze_tcp_retransmissions',
                    description='Analyze TCP retransmissions and packet loss patterns',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_tcp_zero_window',
                    description='Analyze TCP zero window conditions and flow control issues',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_tcp_window_scaling',
                    description='Analyze TCP window scaling and flow control mechanisms',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_packet_timing_issues',
                    description='Analyze packet timing issues and duplicate packets',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_congestion_indicators',
                    description='Analyze network congestion indicators and quality metrics',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                # Advanced Network Analysis (5 tools)
                Tool(
                    name='analyze_dns_resolution_issues',
                    description='Analyze DNS resolution issues and query patterns',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_expert_information',
                    description='Analyze Wireshark expert information for network issues',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'severity_filter': {
                                'type': 'string',
                                'description': 'Filter by severity (Chat, Note, Warn, Error)',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_protocol_anomalies',
                    description='Analyze protocol anomalies and malformed packets',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_network_topology',
                    description='Analyze network topology and routing information',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_security_threats',
                    description='Analyze potential security threats and suspicious activities',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                # Performance & Quality Metrics (4 tools)
                Tool(
                    name='generate_throughput_io_graph',
                    description='Generate throughput I/O graph data with specified time intervals',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'time_interval': {
                                'type': 'integer',
                                'description': 'Time interval in seconds for I/O graph',
                                'default': 1,
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_bandwidth_utilization',
                    description='Analyze bandwidth utilization and traffic patterns',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'time_window': {
                                'type': 'integer',
                                'description': 'Time window in seconds for bandwidth calculation',
                                'default': 10,
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_application_response_times',
                    description='Analyze application layer response times and performance',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                            'protocol': {
                                'type': 'string',
                                'description': 'Protocol to analyze (http, https, dns, ftp)',
                                'default': 'http',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
                Tool(
                    name='analyze_network_quality_metrics',
                    description='Analyze network quality metrics including jitter and packet loss',
                    inputSchema={
                        'type': 'object',
                        'properties': {
                            'pcap_file': {
                                'type': 'string',
                                'description': 'Path to pcap file',
                            },
                        },
                        'required': ['pcap_file'],
                    },
                ),
            ]

        @self.server.call_tool()  # pragma: no cover
        async def handle_call_tool(
            name: str, arguments: dict
        ) -> list[TextContent]:  # pragma: no cover
            """Handle tool calls for PCAP analysis operations."""
            try:
                if name == 'list_network_interfaces':
                    return await self._list_network_interfaces()
                elif name == 'start_packet_capture':
                    return await self._start_packet_capture(**arguments)
                elif name == 'stop_packet_capture':
                    return await self._stop_packet_capture(**arguments)
                elif name == 'get_capture_status':
                    return await self._get_capture_status()
                elif name == 'list_captured_files':
                    return await self._list_captured_files()
                elif name == 'analyze_pcap_file':
                    return await self._analyze_pcap_file(**arguments)
                elif name == 'extract_http_requests':
                    return await self._extract_http_requests(**arguments)
                elif name == 'generate_traffic_timeline':
                    return await self._generate_traffic_timeline(**arguments)
                elif name == 'search_packet_content':
                    return await self._search_packet_content(**arguments)
                elif name == 'analyze_network_performance':
                    return await self._analyze_network_performance(**arguments)
                elif name == 'analyze_network_latency':
                    return await self._analyze_network_latency(**arguments)
                elif name == 'analyze_tls_handshakes':
                    return await self._analyze_tls_handshakes(**arguments)
                elif name == 'analyze_sni_mismatches':
                    return await self._analyze_sni_mismatches(**arguments)
                elif name == 'extract_certificate_details':
                    return await self._extract_certificate_details(**arguments)
                elif name == 'analyze_tls_alerts':
                    return await self._analyze_tls_alerts(**arguments)
                elif name == 'analyze_connection_lifecycle':
                    return await self._analyze_connection_lifecycle(**arguments)
                elif name == 'extract_tls_cipher_analysis':
                    return await self._extract_tls_cipher_analysis(**arguments)
                elif name == 'analyze_tcp_retransmissions':
                    return await self._analyze_tcp_retransmissions(**arguments)
                elif name == 'analyze_tcp_zero_window':
                    return await self._analyze_tcp_zero_window(**arguments)
                elif name == 'analyze_tcp_window_scaling':
                    return await self._analyze_tcp_window_scaling(**arguments)
                elif name == 'analyze_packet_timing_issues':
                    return await self._analyze_packet_timing_issues(**arguments)
                elif name == 'analyze_congestion_indicators':
                    return await self._analyze_congestion_indicators(**arguments)
                elif name == 'analyze_dns_resolution_issues':
                    return await self._analyze_dns_resolution_issues(**arguments)
                elif name == 'analyze_expert_information':
                    return await self._analyze_expert_information(**arguments)
                elif name == 'analyze_protocol_anomalies':
                    return await self._analyze_protocol_anomalies(**arguments)
                elif name == 'analyze_network_topology':
                    return await self._analyze_network_topology(**arguments)
                elif name == 'analyze_security_threats':
                    return await self._analyze_security_threats(**arguments)
                elif name == 'generate_throughput_io_graph':
                    return await self._generate_throughput_io_graph(**arguments)
                elif name == 'analyze_bandwidth_utilization':
                    return await self._analyze_bandwidth_utilization(**arguments)
                elif name == 'analyze_application_response_times':
                    return await self._analyze_application_response_times(**arguments)
                elif name == 'analyze_network_quality_metrics':
                    return await self._analyze_network_quality_metrics(**arguments)
                else:
                    raise ValueError(f'Unknown tool: {name}')
            except Exception as e:
                logger.error(f'Error in tool {name}: {str(e)}')
                return [TextContent(type='text', text=f'Error: {str(e)}')]

    async def _run_tshark_command(self, args: List[str]) -> str:
        """Run tshark command and return output."""
        try:
            cmd = [WIRESHARK_PATH] + args
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                raise RuntimeError(f'tshark command failed: {stderr.decode()}')

            return stdout.decode()
        except Exception as e:
            raise RuntimeError(f'Failed to execute tshark: {str(e)}')

    def _resolve_pcap_path(self, pcap_file: str) -> str:
        """Resolve pcap file path with security validation."""
        # Security: Validate file extension first
        if not pcap_file.endswith('.pcap'):
            raise ValueError("Only .pcap files are allowed")
        
        # Security: Prevent path traversal attacks  
        if '../' in pcap_file or '/..' in pcap_file:
            raise ValueError("Path traversal patterns not allowed")
            
        # Security: Only allow safe characters in filename
        import string
        allowed_chars = string.ascii_letters + string.digits + '.-_/'
        if not all(c in allowed_chars for c in pcap_file):
            raise ValueError("Invalid characters in file path")

        # Handle relative paths by checking storage directory first
        if not os.path.isabs(pcap_file):
            # Check in controlled storage directory
            storage_path = os.path.join(PCAP_STORAGE_DIR, pcap_file)
            if os.path.exists(storage_path):
                return storage_path
            
            # Check current directory (only for .pcap files)
            if os.path.exists(pcap_file):
                return os.path.realpath(pcap_file)
        else:
            # For absolute paths, ensure they exist and are .pcap files
            if os.path.exists(pcap_file):
                return os.path.realpath(pcap_file)

        raise FileNotFoundError(f'PCAP file not found: {pcap_file}')

    async def _list_network_interfaces(self) -> List[TextContent]:
        """List available network interfaces."""
        try:
            interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                stats = psutil.net_if_stats().get(interface)
                if stats and stats.isup:
                    interfaces.append(
                        {
                            'name': interface,
                            'addresses': [addr.address for addr in addrs],
                            'is_up': stats.isup,
                            'speed': stats.speed if stats.speed > 0 else 'Unknown',
                        }
                    )

            result = {'interfaces': interfaces, 'total_count': len(interfaces)}

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error listing interfaces: {str(e)}')]

    async def _start_packet_capture(
        self,
        interface: str,
        duration: int = 60,
        capture_filter: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> List[TextContent]:
        """Start packet capture on specified interface."""
        try:
            # Generate capture ID and filename
            capture_id = f'capture_{int(time.time())}'
            if not output_file:
                output_file = f'{capture_id}.pcap'

            output_path = os.path.join(PCAP_STORAGE_DIR, output_file)

            # Build tshark command
            cmd = [WIRESHARK_PATH, '-i', interface, '-w', output_path]
            if capture_filter:
                cmd.extend(['-f', capture_filter])

            # Start capture process
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Store capture info
            active_captures[capture_id] = {
                'process': process,
                'interface': interface,
                'output_file': output_path,
                'start_time': datetime.now().isoformat(),
                'duration': duration,
                'filter': capture_filter,
            }

            # Schedule stop after duration
            asyncio.create_task(self._auto_stop_capture(capture_id, duration))

            result = {
                'capture_id': capture_id,
                'status': 'started',
                'interface': interface,
                'output_file': output_path,
                'duration': duration,
                'filter': capture_filter,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error starting capture: {str(e)}')]

    async def _auto_stop_capture(self, capture_id: str, duration: int):
        """Automatically stop capture after specified duration."""
        await asyncio.sleep(duration)
        if capture_id in active_captures:
            await self._stop_packet_capture(capture_id)

    async def _stop_packet_capture(self, capture_id: str) -> List[TextContent]:
        """Stop an active packet capture session."""
        try:
            if capture_id not in active_captures:
                return [TextContent(type='text', text=f'Capture {capture_id} not found')]

            capture_info = active_captures[capture_id]
            process = capture_info['process']

            # Terminate the process
            process.terminate()
            await process.wait()

            # Remove from active captures
            del active_captures[capture_id]

            result = {
                'capture_id': capture_id,
                'status': 'stopped',
                'output_file': capture_info['output_file'],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error stopping capture: {str(e)}')]

    async def _analyze_pcap_file(
        self, pcap_file: str, analysis_type: str = 'summary', display_filter: Optional[str] = None
    ) -> List[TextContent]:
        """Analyze a pcap file and generate insights."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            # Build analysis command based on type
            if analysis_type == 'summary':
                args = ['-r', pcap_path, '-q', '-z', 'conv,tcp', '-z', 'prot,colinfo']
            elif analysis_type == 'protocols':
                args = ['-r', pcap_path, '-q', '-z', 'prot,colinfo']
            elif analysis_type == 'conversations':
                args = ['-r', pcap_path, '-q', '-z', 'conv,tcp', '-z', 'conv,udp']
            else:
                args = ['-r', pcap_path, '-q']

            if display_filter:
                args.extend(['-Y', display_filter])

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': analysis_type,
                'filter': display_filter,
                'analysis_output': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing PCAP: {str(e)}')]

    async def _get_capture_status(self) -> List[TextContent]:
        """Get status of all active capture sessions."""
        try:
            result = {'active_captures': len(active_captures), 'captures': []}

            for capture_id, info in active_captures.items():
                result['captures'].append(
                    {
                        'capture_id': capture_id,
                        'interface': info['interface'],
                        'start_time': info['start_time'],
                        'duration': info['duration'],
                        'output_file': info['output_file'],
                        'filter': info.get('filter'),
                    }
                )

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error getting capture status: {str(e)}')]

    async def _list_captured_files(self) -> List[TextContent]:
        """List all captured pcap files in storage directory."""
        try:
            files = []
            storage_path = Path(PCAP_STORAGE_DIR)

            if storage_path.exists():
                for file_path in storage_path.glob('*.pcap'):
                    stat = file_path.stat()
                    files.append(
                        {
                            'filename': file_path.name,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'path': str(file_path),
                        }
                    )

            result = {
                'storage_directory': PCAP_STORAGE_DIR,
                'total_files': len(files),
                'files': files,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error listing captured files: {str(e)}')]

    async def _extract_http_requests(self, pcap_file: str, limit: int = 100) -> List[TextContent]:
        """Extract HTTP requests from pcap file."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'http.request',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'http.request.method',
                '-e',
                'http.request.uri',
                '-e',
                'http.host',
                '-c',
                str(limit),
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'limit': limit,
                'http_requests': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error extracting HTTP requests: {str(e)}')]

    async def _generate_traffic_timeline(
        self, pcap_file: str, time_interval: int = 60
    ) -> List[TextContent]:
        """Generate traffic timeline with specified time intervals."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', f'io,stat,{time_interval}']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'time_interval': time_interval,
                'timeline_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error generating traffic timeline: {str(e)}')]

    async def _search_packet_content(
        self, pcap_file: str, search_pattern: str, case_sensitive: bool = False, limit: int = 50
    ) -> List[TextContent]:
        """Search for specific patterns in packet content."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            # Build search filter
            if case_sensitive:
                filter_expr = f'frame contains "{search_pattern}"'
            else:
                filter_expr = f'frame contains "{search_pattern.lower()}"'

            args = ['-r', pcap_path, '-Y', filter_expr, '-c', str(limit)]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'search_pattern': search_pattern,
                'case_sensitive': case_sensitive,
                'limit': limit,
                'matches': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error searching packet content: {str(e)}')]

    async def _analyze_network_performance(self, pcap_file: str) -> List[TextContent]:
        """Analyze network performance metrics from pcap file."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'conv,tcp', '-z', 'rtp,streams']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'network_performance',
                'performance_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing network performance: {str(e)}')
            ]

    async def _analyze_network_latency(self, pcap_file: str) -> List[TextContent]:
        """Analyze network latency and response times."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'rtt,tcp']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'network_latency',
                'latency_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing network latency: {str(e)}')]

    # TLS/SSL Analysis Methods
    async def _analyze_tls_handshakes(self, pcap_file: str) -> List[TextContent]:
        """Analyze TLS handshakes including SNI and certificate details."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tls.handshake',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tls.handshake.type',
                '-e',
                'tls.handshake.extensions_server_name',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tls_handshakes',
                'handshake_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing TLS handshakes: {str(e)}')]

    async def _analyze_sni_mismatches(self, pcap_file: str) -> List[TextContent]:
        """Analyze SNI mismatches and correlate with connection resets."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tls.handshake.extensions_server_name or tcp.flags.reset eq 1',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tls.handshake.extensions_server_name',
                '-e',
                'tcp.flags.reset',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'sni_mismatches',
                'sni_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing SNI mismatches: {str(e)}')]

    async def _extract_certificate_details(self, pcap_file: str) -> List[TextContent]:
        """Extract SSL certificate details and validate against SNI."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tls.handshake.certificate',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'x509sat.printableString',
                '-e',
                'x509sat.uTF8String',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'certificate_details',
                'certificate_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error extracting certificate details: {str(e)}')
            ]

    async def _analyze_tls_alerts(self, pcap_file: str) -> List[TextContent]:
        """Analyze TLS alert messages that indicate handshake failures."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tls.alert_message',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tls.alert_message.level',
                '-e',
                'tls.alert_message.desc',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tls_alerts',
                'alert_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing TLS alerts: {str(e)}')]

    async def _analyze_connection_lifecycle(self, pcap_file: str) -> List[TextContent]:
        """Analyze complete connection lifecycle from SYN to FIN/RST including TLS handshake."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.flags.syn eq 1 or tcp.flags.fin eq 1 or tcp.flags.reset eq 1 or tls.handshake',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.flags',
                '-e',
                'tls.handshake.type',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'connection_lifecycle',
                'lifecycle_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing connection lifecycle: {str(e)}')
            ]

    async def _extract_tls_cipher_analysis(self, pcap_file: str) -> List[TextContent]:
        """Analyze TLS cipher suite negotiations and compatibility issues."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tls.handshake.ciphersuite',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tls.handshake.ciphersuite',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tls_cipher_analysis',
                'cipher_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing TLS cipher suites: {str(e)}')]

    # TCP Analysis Methods
    async def _analyze_tcp_retransmissions(self, pcap_file: str) -> List[TextContent]:
        """Analyze TCP retransmissions and packet loss patterns."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.analysis.retransmission',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.seq',
                '-e',
                'tcp.analysis.retransmission',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tcp_retransmissions',
                'retransmission_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing TCP retransmissions: {str(e)}')
            ]

    async def _analyze_tcp_zero_window(self, pcap_file: str) -> List[TextContent]:
        """Analyze TCP zero window conditions and flow control issues."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.window_size eq 0',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.window_size',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tcp_zero_window',
                'zero_window_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing TCP zero window: {str(e)}')]

    async def _analyze_tcp_window_scaling(self, pcap_file: str) -> List[TextContent]:
        """Analyze TCP window scaling and flow control mechanisms."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.options.wscale',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.options.wscale',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'tcp_window_scaling',
                'window_scaling_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing TCP window scaling: {str(e)}')]

    async def _analyze_packet_timing_issues(self, pcap_file: str) -> List[TextContent]:
        """Analyze packet timing issues including out-of-order and duplicate packets."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.analysis.out_of_order or tcp.analysis.duplicate_ack',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.analysis.out_of_order',
                '-e',
                'tcp.analysis.duplicate_ack',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'packet_timing_issues',
                'timing_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing packet timing issues: {str(e)}')
            ]

    async def _analyze_congestion_indicators(self, pcap_file: str) -> List[TextContent]:
        """Analyze network congestion indicators and quality metrics."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'expert']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'congestion_indicators',
                'congestion_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing congestion indicators: {str(e)}')
            ]

    # Advanced Analysis Methods
    async def _analyze_dns_resolution_issues(self, pcap_file: str) -> List[TextContent]:
        """Analyze DNS resolution issues and query patterns."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                'dns',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'dns.qry.name',
                '-e',
                'dns.resp.name',
                '-e',
                'dns.flags.rcode',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'dns_resolution_issues',
                'dns_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing DNS resolution issues: {str(e)}')
            ]

    async def _analyze_expert_information(
        self, pcap_file: str, severity_filter: Optional[str] = None
    ) -> List[TextContent]:
        """Analyze Wireshark expert information for network issues."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'expert']
            if severity_filter:
                args.extend(['-z', f'expert,{severity_filter}'])

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'expert_information',
                'severity_filter': severity_filter,
                'expert_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing expert information: {str(e)}')]

    async def _analyze_protocol_anomalies(self, pcap_file: str) -> List[TextContent]:
        """Analyze protocol anomalies and malformed packets."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = [
                '-r',
                pcap_path,
                '-Y',
                '_ws.malformed',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                '_ws.malformed',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'protocol_anomalies',
                'anomaly_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing protocol anomalies: {str(e)}')]

    async def _analyze_network_topology(self, pcap_file: str) -> List[TextContent]:
        """Analyze network topology and routing information."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'endpoints,ip', '-z', 'conv,ip']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'network_topology',
                'topology_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing network topology: {str(e)}')]

    async def _analyze_security_threats(self, pcap_file: str) -> List[TextContent]:
        """Analyze potential security threats and suspicious activities."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            # Look for common security indicators
            args = [
                '-r',
                pcap_path,
                '-Y',
                'tcp.flags.reset eq 1 or icmp.type eq 3 or tcp.analysis.retransmission',
                '-T',
                'fields',
                '-e',
                'frame.time',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
                '-e',
                'tcp.flags.reset',
                '-e',
                'icmp.type',
                '-e',
                'tcp.analysis.retransmission',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'security_threats',
                'threat_indicators': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type='text', text=f'Error analyzing security threats: {str(e)}')]

    # Performance & Quality Metrics
    async def _generate_throughput_io_graph(
        self, pcap_file: str, time_interval: int = 1
    ) -> List[TextContent]:
        """Generate throughput I/O graph data with specified time intervals."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', f'io,stat,{time_interval},BYTES']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'throughput_io_graph',
                'time_interval': time_interval,
                'io_graph_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error generating throughput I/O graph: {str(e)}')
            ]

    async def _analyze_bandwidth_utilization(
        self, pcap_file: str, time_window: int = 10
    ) -> List[TextContent]:
        """Analyze bandwidth utilization and traffic patterns."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', f'io,stat,{time_window},BYTES,FRAMES']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'bandwidth_utilization',
                'time_window': time_window,
                'bandwidth_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing bandwidth utilization: {str(e)}')
            ]

    async def _analyze_application_response_times(
        self, pcap_file: str, protocol: str = 'http'
    ) -> List[TextContent]:
        """Analyze application layer response times and performance."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            if protocol.lower() == 'http':
                filter_expr = 'http'
            elif protocol.lower() == 'https':
                filter_expr = 'tls'
            elif protocol.lower() == 'dns':
                filter_expr = 'dns'
            else:
                filter_expr = protocol

            args = [
                '-r',
                pcap_path,
                '-Y',
                filter_expr,
                '-T',
                'fields',
                '-e',
                'frame.time_relative',
                '-e',
                'ip.src',
                '-e',
                'ip.dst',
            ]

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'application_response_times',
                'protocol': protocol,
                'response_data': output.strip().split('\n') if output.strip() else [],
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(
                    type='text', text=f'Error analyzing application response times: {str(e)}'
                )
            ]

    async def _analyze_network_quality_metrics(self, pcap_file: str) -> List[TextContent]:
        """Analyze network quality metrics including jitter, packet loss, and error rates."""
        try:
            pcap_path = self._resolve_pcap_path(pcap_file)

            args = ['-r', pcap_path, '-q', '-z', 'expert', '-z', 'rtp,streams']

            output = await self._run_tshark_command(args)

            result = {
                'pcap_file': pcap_file,
                'analysis_type': 'network_quality_metrics',
                'quality_data': output,
            }

            return [TextContent(type='text', text=json.dumps(result, indent=2))]
        except Exception as e:
            return [
                TextContent(type='text', text=f'Error analyzing network quality metrics: {str(e)}')
            ]

    async def run(self):
        """Run the PCAP Analyzer MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name='pcap-analyzer-mcp-server',
                    server_version='1.0.0',
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(), experimental_capabilities={}
                    ),
                ),
            )


def main():
    """Run the PCAP Analyzer MCP server."""
    server = PCAPAnalyzerServer()
    asyncio.run(server.run())


if __name__ == '__main__':
    main()
