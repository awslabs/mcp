"""
Sample script to demonstrate using the AWS Elastic Beanstalk MCP Server.
This script lists all Elastic Beanstalk applications in your AWS account.
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

# Create a simple MCP client to call the list_applications tool
request = {
    "id": "1",
    "method": "mcp.tool_call",
    "params": {
        "name": "list_applications",
        "parameters": {},
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
    json.dumps(request),
]

try:
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    print("Response:")
    print(json.dumps(json.loads(result.stdout), indent=2))
except subprocess.CalledProcessError as e:
    print(f"Error: {e}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
finally:
    # Clean up
    server_process.terminate()