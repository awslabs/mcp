#!/usr/bin/env python3
"""Script to start the EKS MCP Server and verify it's running correctly."""

import os
import sys
import time
import subprocess
import requests
import argparse
import logging

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from new.test_config import EKS_CLUSTER_CONFIG, AWS_CONFIG, SERVER_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_server(port: int, host: str, allow_write: bool, allow_sensitive_data_access: bool) -> subprocess.Popen:
    """Start the MCP server in a separate process.
    
    Args:
        port: Port to use for the server
        host: Host to use for the server
        allow_write: Whether to enable write access
        allow_sensitive_data_access: Whether to enable sensitive data access
    
    Returns:
        subprocess.Popen: Server process
    """
    # Build command to start the server using uvx
    cmd = [
        "uvx",
        "awslabs.eks-mcp-server@latest"
    ]
    
    # Add flags
    if allow_write:
        cmd.append("--allow-write")
    
    if allow_sensitive_data_access:
        cmd.append("--allow-sensitive-data-access")
    
    # Set up environment variables for the server process
    env = os.environ.copy()
    env["FASTMCP_TRANSPORT"] = "streamable-http"
    env["FASTMCP_HOST"] = host
    env["FASTMCP_PORT"] = str(port)
    env["FASTMCP_LOG_LEVEL"] = "DEBUG"  # Set to DEBUG for more detailed logs
    
    # Set AWS credentials from config if provided
    if AWS_CONFIG.get("profile"):
        env["AWS_PROFILE"] = AWS_CONFIG["profile"]
    
    # Print the command and environment variables
    logger.info(f"Running command: {' '.join(cmd)}")
    logger.info(f"Environment variables: FASTMCP_HOST={host}, FASTMCP_PORT={port}, FASTMCP_TRANSPORT=streamable-http")
    
    # Start the server process
    logger.info(f"Starting MCP server on {host}:{port}")
    server_process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    return server_process

def check_server_status(host: str, port: int, max_retries: int = 10, retry_interval: int = 3) -> bool:
    """Check if the server is running.
    
    Args:
        host: Server host
        port: Server port
        max_retries: Maximum number of retry attempts
        retry_interval: Interval between retries in seconds
    
    Returns:
        bool: True if the server is running, False otherwise
    """
    url = f"http://{host}:{port}/server-info"
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Checking server status ({attempt + 1}/{max_retries})...")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                server_info = response.json()
                logger.info(f"Server is running - {server_info.get('name', 'Unknown')} {server_info.get('version', 'Unknown')}")
                return True
        except requests.RequestException as e:
            logger.warning(f"Server not yet available: {str(e)}")
        
        time.sleep(retry_interval)
    
    logger.error(f"Server did not respond after {max_retries} attempts")
    return False

def monitor_server_logs(server_process: subprocess.Popen, duration: int = 60):
    """Monitor server logs for the specified duration.
    
    Args:
        server_process: Server process
        duration: Duration to monitor logs in seconds
    """
    logger.info(f"Monitoring server logs for {duration} seconds...")
    end_time = time.time() + duration
    
    while time.time() < end_time:
        # Check if the server is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            logger.error(f"Server exited unexpectedly with code {server_process.returncode}")
            if stdout:
                logger.info(f"Server stdout: {stdout}")
            if stderr:
                logger.error(f"Server stderr: {stderr}")
            return
        
        # Try to read output without blocking
        output = server_process.stdout.readline()
        if output:
            logger.info(f"Server: {output.strip()}")
        
        error = server_process.stderr.readline()
        if error:
            logger.error(f"Server error: {error.strip()}")
        
        time.sleep(0.1)

def main():
    """Start the server and monitor it."""
    parser = argparse.ArgumentParser(description='Start EKS MCP Server')
    
    parser.add_argument(
        '--port',
        type=int,
        default=SERVER_CONFIG["port"],
        help=f'Port to use for the MCP server (default: {SERVER_CONFIG["port"]})'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=SERVER_CONFIG["host"],
        help=f'Host to use for the MCP server (default: {SERVER_CONFIG["host"]})'
    )
    
    parser.add_argument(
        '--profile',
        type=str,
        default=AWS_CONFIG.get("profile"),
        help='AWS profile to use for credentials'
    )
    
    parser.add_argument(
        '--monitor',
        type=int,
        default=60,
        help='Duration to monitor server logs in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Update AWS profile if provided
    if args.profile:
        AWS_CONFIG["profile"] = args.profile
        os.environ['AWS_PROFILE'] = args.profile
    
    # Start the server
    server_process = start_server(
        port=args.port,
        host=args.host,
        allow_write=SERVER_CONFIG["allow_write"],
        allow_sensitive_data_access=SERVER_CONFIG["allow_sensitive_data_access"]
    )
    
    # Wait for the server to start
    logger.info("Waiting for server to start...")
    time.sleep(10)
    
    # Check if the server is still running
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        logger.error(f"Server failed to start. Exit code: {server_process.returncode}")
        if stdout:
            logger.info(f"Server stdout: {stdout}")
        if stderr:
            logger.error(f"Server stderr: {stderr}")
        return 1
    
    # Check server status
    is_running = check_server_status(args.host, args.port)
    
    if is_running:
        logger.info("Server is running correctly.")
        monitor_server_logs(server_process, args.monitor)
    else:
        logger.error("Server is not responding to requests.")
    
    # Stop the server
    logger.info("Stopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server did not terminate gracefully, killing...")
        server_process.kill()
        server_process.wait()
    
    return 0 if is_running else 1

if __name__ == "__main__":
    sys.exit(main())
