#!/usr/bin/env python3
"""Minimal MCP tools/call helper that sends properly typed JSON arguments.

Usage:
    python3 mcp_call_tool.py --config <config.json> --server <name> \
        --tool-name <tool> --arguments '{"action":"x","parameters":{"key":"val"}}'

    # List tools:
    python3 mcp_call_tool.py --config <config.json> --server <name> --method tools/list
"""

import argparse
import json
import os
import select
import subprocess
import sys
import time


def read_json_response(proc, timeout=120):
    """Read a single JSON-RPC response line from the server's stdout."""
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        remaining = deadline - time.time()
        ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.5))
        if ready:
            chunk = (
                proc.stdout.read1(4096)
                if hasattr(proc.stdout, "read1")
                else os.read(proc.stdout.fileno(), 4096)
            )
            if not chunk:
                break
            buf += chunk
            # Try to parse complete lines
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Call an MCP tool with typed JSON arguments")
    parser.add_argument("--config", required=True, help="MCP config JSON file path")
    parser.add_argument("--server", required=True, help="Server name from config")
    parser.add_argument("--method", default="tools/call", help="MCP method (default: tools/call)")
    parser.add_argument("--tool-name", help="Tool name (for tools/call)")
    parser.add_argument("--arguments", help="JSON object of tool arguments (for tools/call)")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    server_config = config.get("mcpServers", {}).get(args.server)
    if not server_config:
        print(json.dumps({"error": f"Server '{args.server}' not found in config"}))
        sys.exit(1)

    command = [server_config["command"]] + server_config.get("args", [])
    env_vars = {**os.environ, **server_config.get("env", {})}

    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env_vars,
    )

    try:
        # 1. Send initialize
        init_req = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-call-tool", "version": "1.0.0"},
                },
            }
        )
        proc.stdin.write(init_req.encode() + b"\n")
        proc.stdin.flush()

        resp = read_json_response(proc)
        if not resp or "result" not in resp:
            print(json.dumps({"error": "Initialize failed", "response": resp}))
            sys.exit(1)

        # 2. Send initialized notification
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        proc.stdin.write(notif.encode() + b"\n")
        proc.stdin.flush()
        time.sleep(0.5)

        # 3. Send the actual request
        if args.method == "tools/list":
            request = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
            )
        elif args.method == "tools/call":
            if not args.tool_name or not args.arguments:
                print(json.dumps({"error": "--tool-name and --arguments required for tools/call"}))
                sys.exit(1)
            request = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": args.tool_name, "arguments": json.loads(args.arguments)},
                }
            )
        else:
            print(json.dumps({"error": f"Unsupported method: {args.method}"}))
            sys.exit(1)

        proc.stdin.write(request.encode() + b"\n")
        proc.stdin.flush()

        # Read response (skip notifications, find id=2)
        deadline = time.time() + 120
        while time.time() < deadline:
            resp = read_json_response(proc, timeout=deadline - time.time())
            if resp is None:
                break
            if resp.get("id") == 2:
                result = resp.get("result", resp.get("error", {}))
                print(json.dumps(result, indent=2))
                sys.exit(0)

        print(json.dumps({"error": "No response received for request"}))
        sys.exit(1)

    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
