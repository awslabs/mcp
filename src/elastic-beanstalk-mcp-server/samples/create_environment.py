"""
Sample script to demonstrate using the AWS Elastic Beanstalk MCP Server.
This script creates a new Elastic Beanstalk environment.
"""

import json
import os
import subprocess
import sys
import time

# Start the MCP server
server_process = subprocess.Popen(
    ["uvx", "awslabs.elastic-beanstalk-mcp-server@latest"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

# Wait for the server to start
time.sleep(2)

# Get the server address from stdout
server_address = None
for line in server_process.stdout:
    if "Listening on" in line:
        server_address = line.strip().split("Listening on ")[1]
        break

if not server_address:
    print("Failed to start MCP server")
    server_process.terminate()
    sys.exit(1)

# First, create an application if it doesn't exist
app_request = {
    "id": "1",
    "method": "mcp.tool_call",
    "params": {
        "name": "create_application",
        "parameters": {
            "application_name": "my-sample-app",
            "description": "Sample application created via MCP"
        },
    },
}

# Use curl to make the request
curl_cmd = [
    "curl",
    "-X",
    "POST",
    server_address,
    "-H",
    "Content-Type: application/json",
    "-d",
    json.dumps(app_request),
]

try:
    print("Creating application...")
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    print("Application response:")
    print(json.dumps(json.loads(result.stdout), indent=2))
    
    # Now create an environment
    env_request = {
        "id": "2",
        "method": "mcp.tool_call",
        "params": {
            "name": "create_environment",
            "parameters": {
                "application_name": "my-sample-app",
                "environment_name": "my-sample-env",
                "solution_stack_name": "64bit Amazon Linux 2 v5.8.0 running Node.js 18",
                "description": "Sample environment created via MCP"
            },
        },
    }
    
    curl_cmd = [
        "curl",
        "-X",
        "POST",
        server_address,
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(env_request),
    ]
    
    print("Creating environment...")
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    print("Environment response:")
    print(json.dumps(json.loads(result.stdout), indent=2))
    
except subprocess.CalledProcessError as e:
    print(f"Error: {e}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
finally:
    # Clean up
    server_process.terminate()