#!/usr/bin/env python3
"""
PCAP Analyzer MCP Server - Network Traffic Analysis
Built with FastMCP framework for analyzing network traffic using PCAP Analyzer/tshark
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any

from fastmcp import Context, FastMCP

# Optional imports for advanced analysis
try:
    from scapy.all import DNS, IP, TCP, UDP, rdpcap

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Initialize the FastMCP server
mcp = FastMCP("pcap-analyzer")


# Security validation for environment variables
def validate_executable_path(path: str) -> str:
    """Validate executable path from environment variable"""
    if not path or not isinstance(path, str):
        raise ValueError("Invalid executable path")

    # Resolve to absolute path
    resolved_path = os.path.realpath(path)

    # Check if file exists and is executable
    if not os.path.isfile(resolved_path):
        raise ValueError(f"Executable not found: {resolved_path}")

    if not os.access(resolved_path, os.X_OK):
        raise ValueError(f"File is not executable: {resolved_path}")

    # Validate path doesn't contain dangerous patterns
    dangerous_patterns = ["..", ";", "|", "&", "`", "$"]
    for pattern in dangerous_patterns:
        if pattern in path:
            raise ValueError(f"Dangerous pattern in path: {pattern}")

    # Ensure it's a tshark executable
    if not (resolved_path.endswith("tshark") or resolved_path.endswith("tshark.exe")):
        raise ValueError("Only tshark executable is allowed")

    return resolved_path


def validate_directory_path(path: str) -> str:
    """Validate directory path from environment variable"""
    if not path or not isinstance(path, str):
        raise ValueError("Invalid directory path")

    # Resolve to absolute path
    resolved_path = os.path.realpath(path)

    # Check for dangerous patterns
    dangerous_patterns = ["..", ";", "|", "&", "`", "$"]
    for pattern in dangerous_patterns:
        if pattern in path:
            raise ValueError(f"Dangerous pattern in path: {pattern}")

    # Create directory if it doesn't exist
    os.makedirs(resolved_path, exist_ok=True)

    return resolved_path


# Configuration with security validation
try:
    TSHARK_PATH = validate_executable_path(
        os.getenv("TSHARK_PATH", "/opt/homebrew/bin/tshark")
    )
except ValueError as e:
    print(f"ERROR: Invalid TSHARK_PATH: {e}")
    # Fallback to common locations
    for fallback_path in [
        "/opt/homebrew/bin/tshark",
        "/usr/bin/tshark",
        "/usr/local/bin/tshark",
    ]:
        try:
            TSHARK_PATH = validate_executable_path(fallback_path)
            print(f"Using fallback tshark path: {TSHARK_PATH}")
            break
        except ValueError:
            continue
    else:
        raise RuntimeError("No valid tshark executable found")

try:
    PCAP_STORAGE_PATH = validate_directory_path(
        os.getenv("PCAP_STORAGE_PATH", "/tmp/pcap_files")
    )
    ANALYSIS_TEMP_DIR = validate_directory_path(
        os.getenv("ANALYSIS_TEMP_DIR", "/tmp/pcap_analysis")
    )
except ValueError as e:
    raise RuntimeError(f"Invalid directory configuration: {e}")

# Validate other environment variables
MAX_CAPTURE_SIZE = os.getenv("MAX_CAPTURE_SIZE", "100MB")
if not re.match(r"^\d+[KMGT]?B$", MAX_CAPTURE_SIZE):
    MAX_CAPTURE_SIZE = "100MB"

try:
    CAPTURE_TIMEOUT = int(os.getenv("CAPTURE_TIMEOUT", "300"))
    if not (1 <= CAPTURE_TIMEOUT <= 3600):  # 1 second to 1 hour
        CAPTURE_TIMEOUT = 300
except (ValueError, TypeError):
    CAPTURE_TIMEOUT = 300

# Ensure directories exist
os.makedirs(PCAP_STORAGE_PATH, exist_ok=True)
os.makedirs(ANALYSIS_TEMP_DIR, exist_ok=True)

# Active capture sessions
active_captures = {}


# Security validation functions
def validate_interface_name(interface: str) -> bool:
    """Validate network interface name to prevent injection attacks"""
    if not interface or not isinstance(interface, str):
        return False
    # Allow alphanumeric, hyphens, underscores, and dots (common in interface names)
    return re.match(r"^[a-zA-Z0-9._-]+$", interface) is not None


def validate_pcap_filename(filename: str) -> bool:
    """Validate PCAP filename to prevent path traversal attacks"""
    if not filename or not isinstance(filename, str):
        return False
    # Prevent path traversal and ensure safe filename
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    # Allow alphanumeric, hyphens, underscores, dots, and plus signs
    return re.match(r"^[a-zA-Z0-9._+-]+\.pcap$", filename) is not None


def validate_display_filter(display_filter: str) -> bool:
    """Validate display filter to prevent injection attacks"""
    if not display_filter or not isinstance(display_filter, str):
        return True  # Empty filter is allowed

    # Basic validation - reject dangerous characters and patterns
    dangerous_patterns = [
        ";",
        "|",
        "&",
        "`",
        "$",
        "$(",
        "${",
        "rm ",
        "del ",
        "format ",
        "exec",
        "eval",
        "../",
        "..\\",
        "/etc/",
        "C:\\Windows\\",
    ]

    display_filter_lower = display_filter.lower()
    for pattern in dangerous_patterns:
        if pattern in display_filter_lower:
            return False

    # Length limit to prevent DoS
    return len(display_filter) <= 1000


def validate_search_pattern(pattern: str) -> bool:
    """Validate search pattern to prevent injection attacks"""
    if not pattern or not isinstance(pattern, str):
        return False

    # Reject dangerous characters
    dangerous_chars = [";", "|", "&", "`", "$", "\n", "\r"]
    for char in dangerous_chars:
        if char in pattern:
            return False

    # Length limit
    return len(pattern) <= 500


def sanitize_path(file_path: str) -> str:
    """Sanitize file path to prevent directory traversal"""
    if not file_path:
        return ""

    # Resolve path and ensure it's within allowed directories
    try:
        resolved_path = os.path.realpath(file_path)

        # Ensure path is within PCAP_STORAGE_PATH or is absolute and safe
        if not os.path.isabs(file_path):
            # Relative path - must be within storage directory
            storage_real = os.path.realpath(PCAP_STORAGE_PATH)
            if not resolved_path.startswith(storage_real):
                raise ValueError("Path outside allowed directory")

        return resolved_path
    except (OSError, ValueError):
        raise ValueError(f"Invalid or unsafe path: {file_path}")


def safe_subprocess_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Safely execute subprocess with validation"""
    if not cmd or not isinstance(cmd, list):
        raise ValueError("Command must be a non-empty list")

    # Validate that first argument is tshark
    if not cmd[0] == TSHARK_PATH:
        raise ValueError("Only tshark commands are allowed")

    # Ensure all arguments are strings
    cmd = [str(arg) for arg in cmd]

    # Set secure defaults
    secure_kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": kwargs.get("timeout", 60),
        "check": False,  # Don't raise on non-zero exit
        "shell": False,  # Never use shell=True
    }
    secure_kwargs.update(kwargs)

    return subprocess.run(cmd, **secure_kwargs)


def check_tshark_available() -> bool:
    """Check if tshark is available on the system"""
    try:
        result = safe_subprocess_run([TSHARK_PATH, "--version"], timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return False


def get_network_interfaces() -> list[dict[str, str]]:
    """Get available network interfaces"""
    try:
        result = safe_subprocess_run([TSHARK_PATH, "-D"], timeout=10)
        interfaces = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split(".", 1)
                if len(parts) == 2:
                    interfaces.append(
                        {"id": parts[0].strip(), "name": parts[1].strip()}
                    )
        return interfaces
    except Exception as e:
        return [{"error": f"Failed to get interfaces: {str(e)}"}]


@mcp.tool
async def list_network_interfaces(ctx: Context) -> dict[str, Any]:
    """List available network interfaces for packet capture"""
    await ctx.info("Retrieving available network interfaces...")

    if not check_tshark_available():
        return {
            "error": "tshark is not available. Please install Wireshark.",
            "install_help": "Install with: brew install wireshark (macOS) or apt-get install tshark (Ubuntu)",
        }

    interfaces = get_network_interfaces()
    try:
        version_result = safe_subprocess_run([TSHARK_PATH, "--version"], timeout=10)
        tshark_version = (
            version_result.stdout.split("\n")[0] if version_result.stdout else "Unknown"
        )
    except Exception:
        tshark_version = "Unknown"

    return {"interfaces": interfaces, "tshark_version": tshark_version}


@mcp.tool
async def start_packet_capture(
    interface: str,
    duration: int = 60,
    capture_filter: str | None = None,
    output_file: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Start packet capture on specified interface

    Args:
        interface: Network interface to capture on (e.g., "en0", "eth0")
        duration: Capture duration in seconds (default: 60)
        capture_filter: BPF filter for capture (e.g., "tcp port 80")
        output_file: Custom output filename (optional)
    """
    if not validate_interface_name(interface):
        return {"error": "Invalid interface name"}

    if not (1 <= duration <= CAPTURE_TIMEOUT):
        return {"error": f"Duration must be between 1 and {CAPTURE_TIMEOUT} seconds"}

    if capture_filter and not validate_display_filter(capture_filter):
        return {"error": "Invalid capture filter"}

    # Generate capture ID and filename
    capture_id = f"capture_{int(time.time())}"
    if output_file:
        if not validate_pcap_filename(output_file):
            return {"error": "Invalid output filename"}
        pcap_file = os.path.join(PCAP_STORAGE_PATH, output_file)
    else:
        pcap_file = os.path.join(PCAP_STORAGE_PATH, f"{capture_id}.pcap")

    await ctx.info(f"Starting packet capture on {interface} for {duration} seconds...")

    try:
        # Build tshark command
        cmd = [
            TSHARK_PATH,
            "-i",
            interface,
            "-a",
            f"duration:{duration}",
            "-w",
            pcap_file,
        ]
        if capture_filter:
            cmd.extend(["-f", capture_filter])

        # Start capture process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Store active capture
        active_captures[capture_id] = {
            "process": process,
            "interface": interface,
            "start_time": datetime.now().isoformat(),
            "duration": duration,
            "output_file": pcap_file,
            "filter": capture_filter,
        }

        return {
            "capture_id": capture_id,
            "interface": interface,
            "duration": duration,
            "output_file": pcap_file,
            "filter": capture_filter,
            "status": "started",
        }

    except Exception as e:
        return {"error": f"Failed to start capture: {str(e)}"}


@mcp.tool
async def stop_packet_capture(capture_id: str, ctx: Context = None) -> dict[str, Any]:
    """Stop an active packet capture session"""
    if capture_id not in active_captures:
        return {"error": f"Capture ID {capture_id} not found"}

    capture_info = active_captures[capture_id]
    process = capture_info["process"]

    await ctx.info(f"Stopping packet capture {capture_id}...")

    try:
        # Terminate the process
        process.terminate()
        process.wait(timeout=10)

        # Remove from active captures
        del active_captures[capture_id]

        # Check if output file was created
        output_file = capture_info["output_file"]
        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

        return {
            "capture_id": capture_id,
            "status": "stopped",
            "output_file": output_file,
            "file_size_bytes": file_size,
            "packets_captured": "unknown",  # Would need to parse file to get exact count
        }

    except Exception as e:
        return {"error": f"Failed to stop capture: {str(e)}"}


@mcp.tool
async def analyze_pcap_file(
    pcap_file: str,
    analysis_type: str = "summary",
    display_filter: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Analyze a pcap file and generate insights

    Args:
        pcap_file: Path to pcap file or filename in storage directory
        analysis_type: Type of analysis (summary, protocols, conversations, security)
        display_filter: Display filter (e.g., "tcp.port == 80")
    """
    # Resolve file path
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing {pcap_file} with {analysis_type} analysis...")

    try:
        if analysis_type == "summary":
            return await _analyze_summary(pcap_file, display_filter, ctx)
        elif analysis_type == "protocols":
            return await _analyze_protocols(pcap_file, display_filter, ctx)
        elif analysis_type == "conversations":
            return await _analyze_conversations(pcap_file, display_filter, ctx)
        elif analysis_type == "security":
            return await _analyze_security(pcap_file, display_filter, ctx)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}

    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}


@mcp.tool
async def extract_http_requests(
    pcap_file: str, limit: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """Extract HTTP requests from pcap file"""
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Extracting HTTP requests from {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "http.request",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "http.request.method",
            "-e",
            "http.request.uri",
            "-e",
            "http.host",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        requests = []
        for line in result.stdout.strip().split("\n")[:limit]:
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 6:
                    requests.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "method": parts[3],
                            "uri": parts[4],
                            "host": parts[5],
                        }
                    )

        return {
            "file": pcap_file,
            "http_requests": requests,
            "total_found": len(requests),
            "limit_applied": limit,
        }

    except Exception as e:
        return {"error": f"Failed to extract HTTP requests: {str(e)}"}


@mcp.tool
async def generate_traffic_timeline(
    pcap_file: str, time_interval: int = 60, ctx: Context = None
) -> dict[str, Any]:
    """Generate traffic timeline with specified time intervals"""
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Generating traffic timeline for {pcap_file}...")

    try:
        cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", f"io,stat,{time_interval}"]
        result = safe_subprocess_run(cmd, timeout=60)

        return {
            "file": pcap_file,
            "time_interval_seconds": time_interval,
            "timeline_data": result.stdout,
            "analysis_type": "traffic_timeline",
        }

    except Exception as e:
        return {"error": f"Failed to generate timeline: {str(e)}"}


@mcp.tool
async def search_packet_content(
    pcap_file: str,
    search_pattern: str,
    case_sensitive: bool = False,
    limit: int = 50,
    ctx: Context = None,
) -> dict[str, Any]:
    """Search for specific patterns in packet content"""
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    if not validate_search_pattern(search_pattern):
        return {"error": "Invalid search pattern"}

    await ctx.info(f"Searching for pattern '{search_pattern}' in {pcap_file}...")

    try:
        # Use tshark to search for pattern in packet data
        filter_expr = f'frame contains "{search_pattern}"'
        if not case_sensitive:
            # tshark is case-insensitive by default for contains
            pass

        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            filter_expr,
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "frame.time",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        matches = []
        for line in result.stdout.strip().split("\n")[:limit]:
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    matches.append(
                        {
                            "frame": parts[0],
                            "timestamp": parts[1],
                            "src_ip": parts[2],
                            "dst_ip": parts[3],
                        }
                    )

        return {
            "file": pcap_file,
            "search_pattern": search_pattern,
            "case_sensitive": case_sensitive,
            "matches": matches,
            "total_matches": len(matches),
            "limit_applied": limit,
        }

    except Exception as e:
        return {"error": f"Failed to search packet content: {str(e)}"}


@mcp.tool
async def list_captured_files(ctx: Context = None) -> dict[str, Any]:
    """List all captured pcap files in storage directory"""
    await ctx.info("Listing captured PCAP files...")

    try:
        files = []
        for filename in os.listdir(PCAP_STORAGE_PATH):
            if filename.endswith(".pcap"):
                filepath = os.path.join(PCAP_STORAGE_PATH, filename)
                file_size = os.path.getsize(filepath)
                file_mtime = os.path.getmtime(filepath)

                files.append(
                    {
                        "filename": filename,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "modified_time": datetime.fromtimestamp(file_mtime).isoformat(),
                    }
                )

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified_time"], reverse=True)

        return {
            "storage_directory": PCAP_STORAGE_PATH,
            "files": files,
            "total_files": len(files),
        }

    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}"}


@mcp.tool
async def get_capture_status(ctx: Context = None) -> dict[str, Any]:
    """Get status of all active capture sessions"""
    await ctx.info("Getting capture session status...")

    try:
        active_sessions = []
        for capture_id, info in active_captures.items():
            process = info["process"]
            status = "running" if process.poll() is None else "completed"

            active_sessions.append(
                {
                    "capture_id": capture_id,
                    "interface": info["interface"],
                    "start_time": info["start_time"],
                    "duration": info["duration"],
                    "output_file": info["output_file"],
                    "filter": info["filter"],
                    "status": status,
                }
            )

        return {
            "active_captures": active_sessions,
            "total_active": len(active_sessions),
        }

    except Exception as e:
        return {"error": f"Failed to get capture status: {str(e)}"}


@mcp.tool
async def analyze_network_performance(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """Analyze network performance metrics from pcap file"""
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing network performance for {pcap_file}...")

    try:
        # Get basic statistics
        stats_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "io,stat,0"]
        stats_result = safe_subprocess_run(stats_cmd, timeout=60)

        # Get TCP analysis
        tcp_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "tcp,pdu"]
        tcp_result = safe_subprocess_run(tcp_cmd, timeout=60)

        return {
            "file": pcap_file,
            "performance_stats": stats_result.stdout,
            "tcp_analysis": tcp_result.stdout,
            "analysis_type": "network_performance",
        }

    except Exception as e:
        return {"error": f"Failed to analyze network performance: {str(e)}"}


@mcp.tool
async def analyze_tls_handshakes(pcap_file: str, ctx: Context = None) -> dict[str, Any]:
    """
    Analyze TLS handshakes including SNI, certificate details, and handshake success/failure

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TLS handshakes in {pcap_file}...")

    try:
        # Extract TLS handshake information
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tls.handshake",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tls.handshake.type",
            "-e",
            "tls.handshake.extensions_server_name",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        handshakes = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    handshakes.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "handshake_type": parts[3],
                            "sni": parts[4] if len(parts) > 4 else "",
                        }
                    )

        return {
            "file": pcap_file,
            "tls_handshakes": handshakes,
            "total_handshakes": len(handshakes),
            "analysis_type": "tls_handshakes",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TLS handshakes: {str(e)}"}


@mcp.tool
async def analyze_sni_mismatches(pcap_file: str, ctx: Context = None) -> dict[str, Any]:
    """
    Analyze SNI mismatches and correlate with connection resets

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing SNI mismatches in {pcap_file}...")

    try:
        # Get SNI information
        sni_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tls.handshake.extensions_server_name",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tls.handshake.extensions_server_name",
        ]

        sni_result = safe_subprocess_run(sni_cmd, timeout=60)

        # Get connection resets
        rst_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.flags.reset==1",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
        ]

        rst_result = safe_subprocess_run(rst_cmd, timeout=60)

        sni_data = []
        for line in sni_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    sni_data.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "sni": parts[3],
                        }
                    )

        resets = []
        for line in rst_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    resets.append(
                        {"frame": parts[0], "src_ip": parts[1], "dst_ip": parts[2]}
                    )

        return {
            "file": pcap_file,
            "sni_requests": sni_data,
            "connection_resets": resets,
            "total_sni": len(sni_data),
            "total_resets": len(resets),
            "analysis_type": "sni_mismatches",
        }

    except Exception as e:
        return {"error": f"Failed to analyze SNI mismatches: {str(e)}"}


@mcp.tool
async def extract_certificate_details(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Extract SSL certificate details and validate against SNI

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Extracting certificate details from {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tls.handshake.certificate",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "x509sat.printableString",
            "-e",
            "x509sat.uTF8String",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        certificates = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    certificates.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "cert_info": parts[3:] if len(parts) > 3 else [],
                        }
                    )

        return {
            "file": pcap_file,
            "certificates": certificates,
            "total_certificates": len(certificates),
            "analysis_type": "certificate_details",
        }

    except Exception as e:
        return {"error": f"Failed to extract certificate details: {str(e)}"}


@mcp.tool
async def analyze_tls_alerts(pcap_file: str, ctx: Context = None) -> dict[str, Any]:
    """
    Analyze TLS alert messages that indicate handshake failures

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TLS alerts in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tls.alert",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tls.alert.level",
            "-e",
            "tls.alert.description",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        alerts = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    alerts.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "alert_level": parts[3],
                            "alert_description": parts[4],
                        }
                    )

        return {
            "file": pcap_file,
            "tls_alerts": alerts,
            "total_alerts": len(alerts),
            "analysis_type": "tls_alerts",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TLS alerts: {str(e)}"}


@mcp.tool
async def analyze_connection_lifecycle(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze complete connection lifecycle from SYN to FIN/RST including TLS handshake

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing connection lifecycle in {pcap_file}...")

    try:
        # Get TCP connection establishment (SYN)
        syn_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.flags.syn==1 and tcp.flags.ack==0",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
        ]

        # Get TCP connection termination (FIN/RST)
        fin_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.flags.fin==1 or tcp.flags.reset==1",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.flags",
        ]

        syn_result = safe_subprocess_run(syn_cmd, timeout=60)
        fin_result = safe_subprocess_run(fin_cmd, timeout=60)

        connections = []
        for line in syn_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    connections.append(
                        {
                            "syn_frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                            "status": "established",
                        }
                    )

        terminations = []
        for line in fin_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 6:
                    terminations.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                            "flags": parts[5],
                        }
                    )

        return {
            "file": pcap_file,
            "connection_establishments": connections,
            "connection_terminations": terminations,
            "total_connections": len(connections),
            "total_terminations": len(terminations),
            "analysis_type": "connection_lifecycle",
        }

    except Exception as e:
        return {"error": f"Failed to analyze connection lifecycle: {str(e)}"}


@mcp.tool
async def extract_tls_cipher_analysis(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze TLS cipher suite negotiations and compatibility issues

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TLS cipher suites in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tls.handshake.ciphersuite",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tls.handshake.ciphersuite",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        cipher_suites = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    cipher_suites.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "cipher_suite": parts[3],
                        }
                    )

        return {
            "file": pcap_file,
            "cipher_negotiations": cipher_suites,
            "total_negotiations": len(cipher_suites),
            "analysis_type": "tls_cipher_analysis",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TLS cipher suites: {str(e)}"}


@mcp.tool
async def analyze_tcp_retransmissions(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze TCP retransmissions and packet loss patterns

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TCP retransmissions in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.retransmission",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.seq",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        retransmissions = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 6:
                    retransmissions.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                            "sequence": parts[5],
                        }
                    )

        return {
            "file": pcap_file,
            "retransmissions": retransmissions,
            "total_retransmissions": len(retransmissions),
            "analysis_type": "tcp_retransmissions",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TCP retransmissions: {str(e)}"}


@mcp.tool
async def analyze_network_latency(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze network latency and response times

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing network latency in {pcap_file}...")

    try:
        # Get TCP round trip time analysis
        rtt_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "rtp,streams"]
        rtt_result = safe_subprocess_run(rtt_cmd, timeout=60)

        # Get response time analysis for various protocols
        response_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.ack_rtt",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.analysis.ack_rtt",
        ]

        response_result = safe_subprocess_run(response_cmd, timeout=60)

        latency_data = []
        for line in response_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    latency_data.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "rtt_ms": parts[3],
                        }
                    )

        return {
            "file": pcap_file,
            "rtt_analysis": rtt_result.stdout,
            "latency_measurements": latency_data,
            "total_measurements": len(latency_data),
            "analysis_type": "network_latency",
        }

    except Exception as e:
        return {"error": f"Failed to analyze network latency: {str(e)}"}


@mcp.tool
async def analyze_tcp_zero_window(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze TCP zero window conditions and flow control issues

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TCP zero window conditions in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.window_size == 0",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.window_size",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        zero_windows = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 6:
                    zero_windows.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                            "window_size": parts[5],
                        }
                    )

        return {
            "file": pcap_file,
            "zero_window_events": zero_windows,
            "total_events": len(zero_windows),
            "analysis_type": "tcp_zero_window",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TCP zero window: {str(e)}"}


@mcp.tool
async def generate_throughput_io_graph(
    pcap_file: str, time_interval: int = 1, ctx: Context = None
) -> dict[str, Any]:
    """
    Generate throughput I/O graph data with specified time intervals

    Args:
        pcap_file: Path to pcap file
        time_interval: Time interval in seconds for I/O graph (default: 1)
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Generating throughput I/O graph for {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-q",
            "-z",
            f"io,stat,{time_interval},BYTES()",
        ]
        result = safe_subprocess_run(cmd, timeout=60)

        return {
            "file": pcap_file,
            "time_interval_seconds": time_interval,
            "throughput_data": result.stdout,
            "analysis_type": "throughput_io_graph",
        }

    except Exception as e:
        return {"error": f"Failed to generate throughput I/O graph: {str(e)}"}


@mcp.tool
async def analyze_expert_information(
    pcap_file: str, severity_filter: str | None = None, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze Wireshark expert information for network issues

    Args:
        pcap_file: Path to pcap file
        severity_filter: Filter by severity (Chat, Note, Warn, Error)
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing expert information in {pcap_file}...")

    try:
        cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "expert"]
        if severity_filter:
            cmd.extend(["-Y", f'_ws.expert.severity == "{severity_filter}"'])

        result = safe_subprocess_run(cmd, timeout=60)

        return {
            "file": pcap_file,
            "severity_filter": severity_filter,
            "expert_info": result.stdout,
            "analysis_type": "expert_information",
        }

    except Exception as e:
        return {"error": f"Failed to analyze expert information: {str(e)}"}


@mcp.tool
async def analyze_dns_resolution_issues(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze DNS resolution issues and query patterns

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing DNS resolution issues in {pcap_file}...")

    try:
        # Get DNS queries
        query_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "dns.flags.response == 0",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "dns.qry.name",
            "-e",
            "dns.qry.type",
        ]

        # Get DNS responses
        response_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "dns.flags.response == 1",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "dns.resp.name",
            "-e",
            "dns.flags.rcode",
        ]

        query_result = safe_subprocess_run(query_cmd, timeout=60)
        response_result = safe_subprocess_run(response_cmd, timeout=60)

        queries = []
        for line in query_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    queries.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "query_name": parts[3],
                            "query_type": parts[4],
                        }
                    )

        responses = []
        for line in response_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    responses.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "response_name": parts[3],
                            "response_code": parts[4],
                        }
                    )

        return {
            "file": pcap_file,
            "dns_queries": queries,
            "dns_responses": responses,
            "total_queries": len(queries),
            "total_responses": len(responses),
            "analysis_type": "dns_resolution_issues",
        }

    except Exception as e:
        return {"error": f"Failed to analyze DNS resolution issues: {str(e)}"}


@mcp.tool
async def analyze_tcp_window_scaling(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze TCP window scaling and flow control mechanisms

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing TCP window scaling in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.options.wscale",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
            "-e",
            "tcp.options.wscale",
        ]

        result = safe_subprocess_run(cmd, timeout=60)

        window_scaling = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 6:
                    window_scaling.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                            "window_scale": parts[5],
                        }
                    )

        return {
            "file": pcap_file,
            "window_scaling_events": window_scaling,
            "total_events": len(window_scaling),
            "analysis_type": "tcp_window_scaling",
        }

    except Exception as e:
        return {"error": f"Failed to analyze TCP window scaling: {str(e)}"}


@mcp.tool
async def analyze_packet_timing_issues(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze packet timing issues including out-of-order and duplicate packets

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing packet timing issues in {pcap_file}...")

    try:
        # Get out-of-order packets
        ooo_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.out_of_order",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
        ]

        # Get duplicate packets
        dup_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.duplicate_ack",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
        ]

        ooo_result = safe_subprocess_run(ooo_cmd, timeout=60)
        dup_result = safe_subprocess_run(dup_cmd, timeout=60)

        out_of_order = []
        for line in ooo_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    out_of_order.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                        }
                    )

        duplicates = []
        for line in dup_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    duplicates.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                        }
                    )

        return {
            "file": pcap_file,
            "out_of_order_packets": out_of_order,
            "duplicate_packets": duplicates,
            "total_out_of_order": len(out_of_order),
            "total_duplicates": len(duplicates),
            "analysis_type": "packet_timing_issues",
        }

    except Exception as e:
        return {"error": f"Failed to analyze packet timing issues: {str(e)}"}


@mcp.tool
async def analyze_bandwidth_utilization(
    pcap_file: str, time_window: int = 10, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze bandwidth utilization and traffic patterns

    Args:
        pcap_file: Path to pcap file
        time_window: Time window in seconds for bandwidth calculation (default: 10)
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing bandwidth utilization in {pcap_file}...")

    try:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-q",
            "-z",
            f"io,stat,{time_window},BYTES(),FRAMES()",
        ]
        result = safe_subprocess_run(cmd, timeout=60)

        return {
            "file": pcap_file,
            "time_window_seconds": time_window,
            "bandwidth_data": result.stdout,
            "analysis_type": "bandwidth_utilization",
        }

    except Exception as e:
        return {"error": f"Failed to analyze bandwidth utilization: {str(e)}"}


@mcp.tool
async def analyze_congestion_indicators(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze network congestion indicators and quality metrics

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing congestion indicators in {pcap_file}...")

    try:
        # Get TCP window full events
        window_full_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.window_full",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
        ]

        # Get fast retransmissions
        fast_retrans_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.fast_retransmission",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "tcp.srcport",
            "-e",
            "tcp.dstport",
        ]

        window_result = safe_subprocess_run(window_full_cmd, timeout=60)
        retrans_result = safe_subprocess_run(fast_retrans_cmd, timeout=60)

        window_full_events = []
        for line in window_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    window_full_events.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                        }
                    )

        fast_retransmissions = []
        for line in retrans_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    fast_retransmissions.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "src_port": parts[3],
                            "dst_port": parts[4],
                        }
                    )

        return {
            "file": pcap_file,
            "window_full_events": window_full_events,
            "fast_retransmissions": fast_retransmissions,
            "total_window_full": len(window_full_events),
            "total_fast_retrans": len(fast_retransmissions),
            "analysis_type": "congestion_indicators",
        }

    except Exception as e:
        return {"error": f"Failed to analyze congestion indicators: {str(e)}"}


@mcp.tool
async def analyze_application_response_times(
    pcap_file: str, protocol: str = "http", ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze application layer response times and performance

    Args:
        pcap_file: Path to pcap file
        protocol: Protocol to analyze (http, https, dns, ftp)
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing {protocol} response times in {pcap_file}...")

    try:
        if protocol.lower() == "http":
            cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "http,stat"]
        elif protocol.lower() == "dns":
            cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "dns,tree"]
        else:
            # Generic service response time
            cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", f"srt,{protocol}"]

        result = safe_subprocess_run(cmd, timeout=60)

        return {
            "file": pcap_file,
            "protocol": protocol,
            "response_time_analysis": result.stdout,
            "analysis_type": "application_response_times",
        }

    except Exception as e:
        return {"error": f"Failed to analyze {protocol} response times: {str(e)}"}


@mcp.tool
async def analyze_network_quality_metrics(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze network quality metrics including jitter, packet loss, and error rates

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing network quality metrics in {pcap_file}...")

    try:
        # Get RTP stream analysis for jitter
        rtp_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "rtp,streams"]
        rtp_result = safe_subprocess_run(rtp_cmd, timeout=60)

        # Get packet loss indicators
        loss_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.analysis.lost_segment",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
        ]
        loss_result = safe_subprocess_run(loss_cmd, timeout=60)

        # Get checksum errors
        checksum_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "tcp.checksum_bad or udp.checksum_bad or ip.checksum_bad",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
        ]
        checksum_result = safe_subprocess_run(checksum_cmd, timeout=60)

        packet_loss = []
        for line in loss_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    packet_loss.append(
                        {"frame": parts[0], "src_ip": parts[1], "dst_ip": parts[2]}
                    )

        checksum_errors = []
        for line in checksum_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 3:
                    checksum_errors.append(
                        {"frame": parts[0], "src_ip": parts[1], "dst_ip": parts[2]}
                    )

        return {
            "file": pcap_file,
            "rtp_analysis": rtp_result.stdout,
            "packet_loss_events": packet_loss,
            "checksum_errors": checksum_errors,
            "total_packet_loss": len(packet_loss),
            "total_checksum_errors": len(checksum_errors),
            "analysis_type": "network_quality_metrics",
        }

    except Exception as e:
        return {"error": f"Failed to analyze network quality metrics: {str(e)}"}


@mcp.tool
async def analyze_protocol_anomalies(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze protocol anomalies and malformed packets

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing protocol anomalies in {pcap_file}...")

    try:
        # Get malformed packets
        malformed_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "_ws.malformed",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "_ws.malformed",
        ]

        result = safe_subprocess_run(malformed_cmd, timeout=60)

        anomalies = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 4:
                    anomalies.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "anomaly_type": parts[3],
                        }
                    )

        return {
            "file": pcap_file,
            "protocol_anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "analysis_type": "protocol_anomalies",
        }

    except Exception as e:
        return {"error": f"Failed to analyze protocol anomalies: {str(e)}"}


@mcp.tool
async def analyze_network_topology(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze network topology and routing information

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing network topology in {pcap_file}...")

    try:
        # Get unique IP addresses and their communication patterns
        endpoints_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "endpoints,ip"]
        endpoints_result = safe_subprocess_run(endpoints_cmd, timeout=60)

        # Get routing information from ICMP and traceroute
        icmp_cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            "icmp",
            "-T",
            "fields",
            "-e",
            "frame.number",
            "-e",
            "ip.src",
            "-e",
            "ip.dst",
            "-e",
            "icmp.type",
            "-e",
            "ip.ttl",
        ]
        icmp_result = safe_subprocess_run(icmp_cmd, timeout=60)

        routing_info = []
        for line in icmp_result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    routing_info.append(
                        {
                            "frame": parts[0],
                            "src_ip": parts[1],
                            "dst_ip": parts[2],
                            "icmp_type": parts[3],
                            "ttl": parts[4],
                        }
                    )

        return {
            "file": pcap_file,
            "network_endpoints": endpoints_result.stdout,
            "routing_information": routing_info,
            "total_routing_packets": len(routing_info),
            "analysis_type": "network_topology",
        }

    except Exception as e:
        return {"error": f"Failed to analyze network topology: {str(e)}"}


@mcp.tool
async def analyze_security_threats(
    pcap_file: str, ctx: Context = None
) -> dict[str, Any]:
    """
    Analyze potential security threats and suspicious activities

    Args:
        pcap_file: Path to pcap file
    """
    if not os.path.isabs(pcap_file):
        pcap_file = os.path.join(PCAP_STORAGE_PATH, pcap_file)

    if not os.path.exists(pcap_file):
        return {"error": f"PCAP file not found: {pcap_file}"}

    await ctx.info(f"Analyzing security threats in {pcap_file}...")

    try:
        security_indicators = []

        # Check for various security threats
        threat_checks = [
            ("Port scans", "tcp.flags.syn==1 and tcp.flags.ack==0"),
            ("Null scans", "tcp.flags == 0"),
            ("FIN scans", "tcp.flags.fin==1 and tcp.flags.ack==0 and tcp.flags.syn==0"),
            (
                "XMAS scans",
                "tcp.flags.fin==1 and tcp.flags.push==1 and tcp.flags.urg==1",
            ),
            ("Large ICMP packets", "icmp and frame.len > 1000"),
            ("Suspicious DNS queries", 'dns and dns.qry.name contains ".."'),
            (
                "HTTP POST to suspicious paths",
                'http.request.method == "POST" and http.request.uri contains ".."',
            ),
            ("Potential DDoS", "icmp.type == 8"),  # ICMP ping floods
            ("ARP spoofing", "arp.duplicate-address-detected"),
            ("Malformed packets", "_ws.malformed"),
        ]

        for threat_name, threat_filter in threat_checks:
            cmd = [
                TSHARK_PATH,
                "-r",
                pcap_file,
                "-Y",
                threat_filter,
                "-T",
                "fields",
                "-e",
                "frame.number",
            ]
            result = safe_subprocess_run(cmd, timeout=30)
            count = len(
                [line for line in result.stdout.strip().split("\n") if line.strip()]
            )

            if count > 0:
                security_indicators.append(
                    {
                        "threat_type": threat_name,
                        "count": count,
                        "filter": threat_filter,
                        "severity": "high"
                        if count > 100
                        else "medium"
                        if count > 10
                        else "low",
                    }
                )

        return {
            "file": pcap_file,
            "security_threats": security_indicators,
            "total_threat_types": len(security_indicators),
            "analysis_type": "security_threats",
        }

    except Exception as e:
        return {"error": f"Failed to analyze security threats: {str(e)}"}


async def _analyze_summary(
    pcap_file: str, display_filter: str | None, ctx: Context
) -> dict[str, Any]:
    """Generate summary statistics for pcap file"""
    # Validate display filter
    if display_filter and not validate_display_filter(display_filter):
        raise ValueError("Invalid display filter")

    cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "io,stat,0"]
    if display_filter:
        cmd.extend(["-Y", display_filter])

    result = safe_subprocess_run(cmd, timeout=60)

    # Also get basic packet count and file info
    count_cmd = [TSHARK_PATH, "-r", pcap_file, "-T", "fields", "-e", "frame.number"]
    if display_filter:
        count_cmd.extend(["-Y", display_filter])

    count_result = safe_subprocess_run(count_cmd, timeout=60)
    packet_count = len(
        [line for line in count_result.stdout.strip().split("\n") if line.strip()]
    )

    file_size = os.path.getsize(pcap_file)

    return {
        "file": pcap_file,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "total_packets": packet_count,
        "filter_applied": display_filter,
        "tshark_output": result.stdout,
        "analysis_type": "summary",
    }


async def _analyze_protocols(
    pcap_file: str, display_filter: str | None, ctx: Context
) -> dict[str, Any]:
    """Analyze protocol distribution in pcap file"""
    # Validate display filter
    if display_filter and not validate_display_filter(display_filter):
        raise ValueError("Invalid display filter")

    cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "io,phs"]
    if display_filter:
        cmd.extend(["-Y", display_filter])

    result = safe_subprocess_run(cmd, timeout=60)

    return {
        "file": pcap_file,
        "filter_applied": display_filter,
        "protocol_hierarchy": result.stdout,
        "analysis_type": "protocols",
    }


async def _analyze_conversations(
    pcap_file: str, display_filter: str | None, ctx: Context
) -> dict[str, Any]:
    """Analyze network conversations in pcap file"""
    # Validate display filter
    if display_filter and not validate_display_filter(display_filter):
        raise ValueError("Invalid display filter")

    # Get IP conversations
    ip_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "conv,ip"]
    if display_filter:
        ip_cmd.extend(["-Y", display_filter])

    ip_result = safe_subprocess_run(ip_cmd, timeout=60)

    # Get TCP conversations
    tcp_cmd = [TSHARK_PATH, "-r", pcap_file, "-q", "-z", "conv,tcp"]
    if display_filter:
        tcp_cmd.extend(["-Y", display_filter])

    tcp_result = safe_subprocess_run(tcp_cmd, timeout=60)

    return {
        "file": pcap_file,
        "filter_applied": display_filter,
        "ip_conversations": ip_result.stdout,
        "tcp_conversations": tcp_result.stdout,
        "analysis_type": "conversations",
    }


async def _analyze_security(
    pcap_file: str, display_filter: str | None, ctx: Context
) -> dict[str, Any]:
    """Perform security analysis on pcap file"""
    # Validate display filter
    if display_filter and not validate_display_filter(display_filter):
        raise ValueError("Invalid display filter")

    security_findings = []

    # Check for suspicious patterns using tshark
    suspicious_checks = [
        ("Port scans", "tcp.flags.syn==1 and tcp.flags.ack==0"),
        ("DNS queries", "dns"),
        ("HTTP traffic", "http"),
        ("Large packets", "frame.len > 1500"),
        ("Retransmissions", "tcp.analysis.retransmission"),
    ]

    for check_name, check_filter in suspicious_checks:
        cmd = [
            TSHARK_PATH,
            "-r",
            pcap_file,
            "-Y",
            check_filter,
            "-T",
            "fields",
            "-e",
            "frame.number",
        ]
        if display_filter:
            combined_filter = f"({display_filter}) and ({check_filter})"
            cmd[cmd.index(check_filter)] = combined_filter

        result = safe_subprocess_run(cmd, timeout=30)
        count = len(
            [line for line in result.stdout.strip().split("\n") if line.strip()]
        )

        if count > 0:
            security_findings.append(
                {"check": check_name, "count": count, "filter": check_filter}
            )

    return {
        "file": pcap_file,
        "filter_applied": display_filter,
        "security_findings": security_findings,
        "analysis_type": "security",
    }


# Resource for server configuration
@mcp.resource("config://pcap-analyzer-server")
async def get_server_config() -> str:
    """Get current server configuration"""
    config = {
        "tshark_path": TSHARK_PATH,
        "tshark_available": check_tshark_available(),
        "pcap_storage_path": PCAP_STORAGE_PATH,
        "max_capture_size": MAX_CAPTURE_SIZE,
        "capture_timeout": CAPTURE_TIMEOUT,
        "analysis_temp_dir": ANALYSIS_TEMP_DIR,
        "active_captures": len(active_captures),
    }
    return json.dumps(config, indent=2)


def main():
    """Main entry point for the PCAP Analyzer MCP Server"""
    # Check if tshark is available on startup
    if not check_tshark_available():
        print("WARNING: tshark is not available. Please install Wireshark.")
        print("macOS: brew install wireshark")
        print("Ubuntu: sudo apt-get install tshark")

    # Run with STDIO transport by default (for MCP clients)
    mcp.run()


if __name__ == "__main__":
    main()
