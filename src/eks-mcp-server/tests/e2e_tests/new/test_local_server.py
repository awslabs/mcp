#!/usr/bin/env python3
"""Script to test the local EKS MCP Server with hybrid node tools."""

import os
import sys
import json
import subprocess
import time
import uuid
import argparse
import signal

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from new.test_config import EKS_CLUSTER_CONFIG, AWS_CONFIG

def extract_json_from_output(output_buffer):
    """Extract a complete JSON object from the output buffer."""
    if "{" not in output_buffer or "}" not in output_buffer:
        return None, output_buffer, False
    
    try:
        start = output_buffer.find("{")
        end = output_buffer.rfind("}") + 1
        json_text = output_buffer[start:end]
        json_object = json.loads(json_text)
        remaining = output_buffer[end:]
        return json_object, remaining, True
    except json.JSONDecodeError:
        return None, output_buffer, False

def wait_for_response(server_process, request_id, timeout=30):
    """Wait for a specific response from the server process."""
    start_time = time.time()
    buffer = ""
    stderr_buffer = ""
    
    print(f"Waiting for response with ID: {request_id}")
    
    while time.time() - start_time < timeout:
        # Check if the process is still running
        if server_process.poll() is not None:
            print(f"Server process terminated with code {server_process.returncode}")
            if stderr_buffer:
                print(f"Accumulated stderr: {stderr_buffer}")
            return None
        
        # Try to read from stderr (non-blocking)
        try:
            stderr_line = server_process.stderr.readline()
            if stderr_line:
                print(f"STDERR: {stderr_line.strip()}")
                stderr_buffer += stderr_line
        except:
            pass
        
        # Try to read a line from stdout
        line = server_process.stdout.readline()
        if line:
            print(f"STDOUT: {line.strip()}")
            buffer += line
            
            # Try to extract a JSON object
            json_obj, buffer, success = extract_json_from_output(buffer)
            if success and json_obj.get("id") == request_id:
                return json_obj
        else:
            # No more output available right now, wait a bit
            time.sleep(0.1)
    
    print(f"Timeout waiting for response with ID: {request_id}")
    return None

def initialize_server(server_process):
    """Perform the initialization handshake with the server."""
    print("Performing server initialization handshake...")
    
    # Step 1: Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": False
                    }
                }
            },
            "clientInfo": {
                "name": "python-eks-mcp-client",
                "version": "1.0.0"
            }
        }
    }
    
    print(f"Sending initialization request: {json.dumps(init_request, indent=2)}")
    server_process.stdin.write(json.dumps(init_request) + "\n")
    server_process.stdin.flush()
    
    # Step 2: Wait for initialization response
    init_response = wait_for_response(server_process, "init-1")
    if not init_response:
        print("Failed to receive initialization response")
        return False
    
    print(f"Initialization response received")
    
    # Step 3: Send initialized notification
    init_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    
    print(f"Sending initialized notification")
    server_process.stdin.write(json.dumps(init_notification) + "\n")
    server_process.stdin.flush()
    
    # Give the server a moment to process
    time.sleep(1)
    
    return True

def list_available_tools(server_process):
    """List all available tools from the server."""
    # Create a unique request ID
    request_id = f"list-tools-{int(time.time())}"
    
    # Create the request
    list_request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/list",
        "params": {}
    }
    
    print(f"\n=== LISTING AVAILABLE TOOLS ===")
    
    # Send the request
    server_process.stdin.write(json.dumps(list_request) + "\n")
    server_process.stdin.flush()
    
    # Wait for the response
    response = wait_for_response(server_process, request_id)
    
    if not response or "result" not in response or "tools" not in response["result"]:
        print("Failed to get list of tools")
        return []
    
    tools = response["result"]["tools"]
    print(f"\nAvailable tools ({len(tools)}):")
    for tool in tools:
        print(f"- {tool.get('name')}: {tool.get('description', '')[:60]}...")
    
    return [tool.get('name') for tool in tools]

def execute_tool(server_process, tool_name, arguments):
    """Execute a tool on the server."""
    # Create a unique request ID
    request_id = f"tool-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    # Create the request
    tool_request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    print(f"\n=== EXECUTING TOOL: {tool_name} ===")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    # Send the request
    server_process.stdin.write(json.dumps(tool_request) + "\n")
    server_process.stdin.flush()
    
    # Wait for the response
    response = wait_for_response(server_process, request_id)
    
    if response:
        print(f"\nResponse received for {tool_name}:")
        print(json.dumps(response, indent=2))
        
        # Check for errors in the response
        if "error" in response:
            print(f"\nError in response: {response['error'].get('message', 'Unknown error')}")
            return False, response
        
        # Check if we got an "unknown tool" error in the result
        if "result" in response:
            result = response["result"]
            if isinstance(result, dict) and result.get("isError") is True:
                if "content" in result and result["content"]:
                    for content_item in result["content"]:
                        if content_item.get("type") == "text" and "Unknown tool" in content_item.get("text", ""):
                            print(f"\nTool not found: {tool_name}")
                            return False, response
            
            print(f"\nTool {tool_name} executed successfully!")
            return True, response
    else:
        print(f"\nNo response received for {tool_name}")
        return False, None

def save_response(response, tool_name):
    """Save the response to a file."""
    if response:
        filename = f"{tool_name.replace('/', '_')}_local_response.json"
        with open(filename, "w") as f:
            json.dump(response, f, indent=2)
        print(f"Response saved to {filename}")

def main():
    """Test the local EKS MCP Server with hybrid node tools."""
    parser = argparse.ArgumentParser(description='Test the local EKS MCP Server with hybrid node tools')
    
    parser.add_argument(
        '--cluster-name',
        type=str,
        default=EKS_CLUSTER_CONFIG["cluster_name"],
        help='Name of the EKS cluster to test against'
    )
    
    parser.add_argument(
        '--profile',
        type=str,
        default=AWS_CONFIG["profile"],
        help='AWS profile to use for credentials'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging from the server'
    )
    
    parser.add_argument(
        '--tool',
        type=str,
        choices=['get_eks_vpc_config', 'get_eks_dns_status', 'get_policies_for_role', 'get_eks_insights', 'all'],
        default='all',
        help='Specific tool to test (default: all)'
    )
    
    parser.add_argument(
        '--role-name',
        type=str,
        default='AmazonEKSHybridNodesRole',
        help='IAM role name to use with get_policies_for_role tool'
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default=None,
        help='AWS region code to use with tools that support region specification'
    )
    
    parser.add_argument(
        '--insight-category',
        type=str,
        choices=['CONFIGURATION', 'UPGRADE_READINESS'],
        default=None,
        help='Filter insights by category (for get_eks_insights tool)'
    )
    
    parser.add_argument(
        '--insight-id',
        type=str,
        default=None,
        help='Specific insight ID to get details for (for get_eks_insights tool)'
    )
    
    args = parser.parse_args()
    
    # Set up environment variables
    env = os.environ.copy()
    if args.profile:
        env['AWS_PROFILE'] = args.profile
    
    # Set log level
    env['FASTMCP_LOG_LEVEL'] = 'DEBUG' if args.debug else 'INFO'
    env['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    
    # Use the current working directory (this should be the project root)
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    
    # Start the server process - using local module path
    print(f"Starting LOCAL server process from: {cwd}")
    server_cmd = [
        "uv",
        "run",
        "-m", "awslabs.eks_mcp_server.server",
        "--allow-write",
        "--allow-sensitive-data-access"
    ]
    
    server_process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=cwd,
        bufsize=1  # Line buffered
    )
    
    try:
        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(3)
        
        # Check if server is still running
        if server_process.poll() is not None:
            print(f"Server exited with code {server_process.returncode}")
            stderr = server_process.stderr.read()
            print(f"Server stderr: {stderr}")
            return 1
        
        # Initialize the server
        if not initialize_server(server_process):
            print("Failed to initialize server")
            return 1
        
        print("\nServer initialized successfully.")
        
        # List available tools to verify our hybrid tools are present
        available_tools = list_available_tools(server_process)
        
        # Determine which tools to test
        tools_to_test = []
        hybrid_tools = ['get_eks_vpc_config', 'get_eks_dns_status', 'get_policies_for_role', 'get_eks_insights']
        
        if args.tool == 'all':
            tools_to_test = hybrid_tools
        else:
            tools_to_test = [args.tool]
        
        # Check if our hybrid tools are available
        missing_tools = [tool for tool in tools_to_test if tool not in available_tools]
        if missing_tools:
            print(f"\nWARNING: The following hybrid tools are not in the tool list: {missing_tools}")
            print("However, we'll still try to execute them directly.")
        
        # Dictionary to store test results
        results = {tool: False for tool in tools_to_test}
        
        # Test each tool
        for tool in tools_to_test:
            if tool == 'get_eks_vpc_config':
                success, response = execute_tool(
                    server_process,
                    tool,
                    {"cluster_name": args.cluster_name}
                )
                results[tool] = success
                save_response(response, tool)
            
            elif tool == 'get_eks_dns_status':
                success, response = execute_tool(
                    server_process,
                    tool,
                    {
                        "cluster_name": args.cluster_name,
                        "additional_hostnames": ["amazon.com", "aws.amazon.com"]
                    }
                )
                results[tool] = success
                save_response(response, tool)
            
            elif tool == 'get_policies_for_role':
                success, response = execute_tool(
                    server_process,
                    tool,
                    {"role_name": args.role_name}
                )
                results[tool] = success
                save_response(response, tool)
                
            elif tool == 'get_eks_insights':
                # Build tool parameters based on provided arguments
                tool_args = {
                    "cluster_name": args.cluster_name
                }
                
                # Add optional parameters if provided
                if args.insight_id:
                    tool_args["insight_id"] = args.insight_id
                if args.insight_category:
                    tool_args["category"] = args.insight_category
                if args.region:
                    tool_args["region"] = args.region
                
                print(f"Executing get_eks_insights with arguments: {tool_args}")
                success, response = execute_tool(
                    server_process,
                    tool,
                    tool_args
                )
                results[tool] = success
                save_response(response, tool)
        
        # Print summary
        print("\n=== Test Summary ===")
        for tool_name, success in results.items():
            print(f"{tool_name}: {'SUCCESS' if success else 'FAILED'}")
        
        return 0 if all(results.values()) else 1
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    finally:
        # Stop the server process
        print("\nStopping server process...")
        try:
            # Send SIGINT signal first for graceful shutdown
            if server_process.poll() is None:
                if os.name == 'nt':  # Windows
                    server_process.terminate()
                else:  # Unix/Linux
                    server_process.send_signal(signal.SIGINT)
                
                try:
                    server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # If still running after SIGINT, force terminate
                    server_process.terminate()
                    try:
                        server_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # If still running after SIGTERM, kill
                        server_process.kill()
        except Exception as e:
            print(f"Error stopping server: {str(e)}")

if __name__ == "__main__":
    sys.exit(main())
