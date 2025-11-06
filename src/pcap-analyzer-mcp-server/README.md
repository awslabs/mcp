# PCAP Analyzer MCP Server

A Model Context Protocol (MCP) server for comprehensive network traffic analysis using PCAP Analyzer and tshark.

## Features

- **Network Interface Detection**: List available network interfaces for packet capture
- **Packet Capture**: Start and stop network packet capture sessions with real-time monitoring
- **Comprehensive PCAP Analysis**: Advanced analysis of PCAP files including:
  - Protocol distribution and hierarchy analysis
  - Network conversation and endpoint analysis
  - Security threat detection and vulnerability assessment
  - Performance metrics and network quality analysis
  - TLS/SSL handshake and certificate analysis
  - DNS resolution and query pattern analysis
  - TCP flow control and congestion analysis
  - Bandwidth utilization and throughput analysis
  - Network topology and routing information
- **Security Features**: Input validation, path sanitization, and secure subprocess execution
- **Real-time Monitoring**: Track active capture sessions and network performance metrics

## Prerequisites

- **tshark** (part of Wireshark): Required for packet capture and analysis
  - macOS: `brew install wireshark`
  - Ubuntu: `sudo apt-get install tshark`
- **Python 3.10+**: Required for running the server
- **Network Permissions**: May require elevated privileges for packet capture

## Installation

### Using uv (recommended)

```bash
uv add awslabs.pcap-analyzer-mcp-server
```

### Using pip

```bash
pip install awslabs.pcap-analyzer-mcp-server
```

## Usage

### As MCP Server

Add to your MCP client configuration:

```json
{
  "awslabs.pcap-analyzer-mcp-server": {
    "command": "pcap-analyzer-mcp-server",
    "env": {
      "TSHARK_PATH": "/opt/homebrew/bin/tshark",
      "PCAP_STORAGE_PATH": "/tmp/pcap_files",
      "MAX_CAPTURE_SIZE": "100MB",
      "CAPTURE_TIMEOUT": "300"
    }
  }
}
```

### Environment Variables

- `TSHARK_PATH`: Path to tshark executable (default: `/opt/homebrew/bin/tshark`)
- `PCAP_STORAGE_PATH`: Directory for storing captured PCAP files (default: `/tmp/pcap_files`)
- `ANALYSIS_TEMP_DIR`: Temporary directory for analysis (default: `/tmp/pcap_analysis`)
- `MAX_CAPTURE_SIZE`: Maximum capture file size (default: `100MB`)
- `CAPTURE_TIMEOUT`: Maximum capture duration in seconds (default: `300`)

## Available Tools (31 Total)

### Network Interface Management (1 tool)
- `list_network_interfaces`: List available network interfaces for packet capture

### Packet Capture Management (4 tools)
- `start_packet_capture`: Start packet capture on specified interface with filters
- `stop_packet_capture`: Stop active packet capture session
- `get_capture_status`: Get status of all active capture sessions
- `list_captured_files`: List all captured PCAP files in storage directory

### Basic PCAP Analysis (4 tools)
- `analyze_pcap_file`: Comprehensive PCAP file analysis (summary, protocols, conversations, security)
- `extract_http_requests`: Extract HTTP requests from PCAP files
- `generate_traffic_timeline`: Generate traffic timeline analysis with time intervals
- `search_packet_content`: Search for specific patterns in packet content

### Network Performance Analysis (2 tools)
- `analyze_network_performance`: Network performance metrics and statistics
- `analyze_network_latency`: Network latency and response time analysis

### TLS/SSL Security Analysis (6 tools)
- `analyze_tls_handshakes`: TLS handshake analysis including SNI and certificate details
- `analyze_sni_mismatches`: SNI mismatch detection and correlation with connection resets
- `extract_certificate_details`: SSL certificate extraction and validation against SNI
- `analyze_tls_alerts`: TLS alert message analysis for handshake failures
- `analyze_connection_lifecycle`: Complete connection lifecycle analysis (SYN to FIN/RST)
- `extract_tls_cipher_analysis`: TLS cipher suite negotiation and compatibility analysis

### TCP Protocol Analysis (5 tools)
- `analyze_tcp_retransmissions`: TCP retransmission and packet loss pattern analysis
- `analyze_tcp_zero_window`: TCP zero window condition and flow control analysis
- `analyze_tcp_window_scaling`: TCP window scaling and flow control mechanism analysis
- `analyze_packet_timing_issues`: Packet timing analysis (out-of-order, duplicate packets)
- `analyze_congestion_indicators`: Network congestion indicator and quality metrics

### Advanced Network Analysis (5 tools)
- `analyze_dns_resolution_issues`: DNS resolution issue and query pattern analysis
- `analyze_expert_information`: Wireshark expert information for network issue detection
- `analyze_protocol_anomalies`: Protocol anomaly and malformed packet detection
- `analyze_network_topology`: Network topology and routing information analysis
- `analyze_security_threats`: Comprehensive security threat and suspicious activity detection

### Performance & Quality Metrics (4 tools)
- `generate_throughput_io_graph`: Throughput I/O graph generation with time intervals
- `analyze_bandwidth_utilization`: Bandwidth utilization and traffic pattern analysis
- `analyze_application_response_times`: Application layer response time analysis (HTTP, DNS, etc.)
- `analyze_network_quality_metrics`: Network quality metrics (jitter, packet loss, error rates)

## Tool Categories Summary

| Category | Tool Count | Description |
|----------|------------|-------------|
| **Interface Management** | 1 | Network interface detection and listing |
| **Capture Management** | 4 | Packet capture start/stop/status/file management |
| **Basic Analysis** | 4 | Core PCAP analysis and content extraction |
| **Performance** | 2 | Network performance and latency analysis |
| **TLS/SSL Security** | 6 | Comprehensive TLS/SSL security analysis |
| **TCP Protocol** | 5 | Advanced TCP protocol and flow analysis |
| **Advanced Network** | 5 | DNS, topology, security, and anomaly detection |
| **Quality Metrics** | 4 | Throughput, bandwidth, and quality analysis |
| **Total** | **31** | **Complete network analysis toolkit** |

## Security Features

- **Input Validation**: All inputs are validated to prevent injection attacks
- **Path Sanitization**: File paths are sanitized to prevent directory traversal
- **Subprocess Security**: Safe subprocess execution with validation and timeouts
- **Resource Limits**: Configurable limits on capture size and duration
- **Error Handling**: Secure error messages that don't leak sensitive information
- **Network Interface Validation**: Secure network interface name validation
- **Filter Validation**: Display and capture filter validation for security

## Example Usage

### Basic Packet Capture
```json
{
  "tool": "start_packet_capture",
  "arguments": {
    "interface": "en0",
    "duration": 60,
    "capture_filter": "tcp port 443"
  }
}
```

### Comprehensive Analysis
```json
{
  "tool": "analyze_pcap_file",
  "arguments": {
    "pcap_file": "capture_123456.pcap",
    "analysis_type": "security",
    "display_filter": "tls"
  }
}
```

### Security Analysis
```json
{
  "tool": "analyze_security_threats",
  "arguments": {
    "pcap_file": "network_traffic.pcap"
  }
}
```

## Development

### Running Tests

```bash
cd src/pcap-analyzer-mcp-server
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

### Code Quality

```bash
pre-commit run --all-files
```

### MCP Inspector Testing

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/server run pcap_analyzer_server.py
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.
