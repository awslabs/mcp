#!/usr/bin/env python3
"""Script to debug the EKS MCP Server tool registration process."""

import os
import sys
import json
import subprocess
import time
import uuid
import argparse

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
        stderr_line = server_process.stderr.readline()
        if stderr_line:
            print(f"STDERR: {stderr_line.strip()}")
            stderr_buffer += stderr_line
        
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
    
    print(f"Initialization response received with server info: {init_response.get('result', {}).get('serverInfo', {})}")
    
    # Step 3: Send initialized notification
    init_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
