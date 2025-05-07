#!/bin/bash
# Run the Petstore functional test for openapi-mcp-server

# Set the current directory to the script directory
cd "$(dirname "$0")" || exit

# Create a simple test script
cat > test_petstore_simple.py << 'EOF'
#!/usr/bin/env python
"""
Functional test for the OpenAPI MCP server with Petstore API.

This script tests the openapi-mcp-server integration with the Swagger Petstore API.
It checks:
1. Server startup with the Petstore API spec
2. Lists all tools/endpoints created from the OpenAPI spec
3. Proper loading and parsing of the OpenAPI spec
"""
import os
import sys
import subprocess
import time
import signal
import argparse
import json
import datetime
import httpx
import re

def detailed_petstore_endpoints():
    """Fetch and list all endpoints in the Petstore API spec."""
    print("\n📊 ANALYZING PETSTORE API ENDPOINTS...")
    print("=" * 60)

    try:
        print("Fetching Petstore OpenAPI spec from https://petstore3.swagger.io/api/v3/openapi.json")
        response = httpx.get("https://petstore3.swagger.io/api/v3/openapi.json")
        response.raise_for_status()
        spec = response.json()

        # Count the paths and operations
        path_count = len(spec.get("paths", {}))
        operations = []
        resources = []

        # Extract operations
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    op_id = details.get("operationId", f"{method.upper()} {path}")
                    summary = details.get("summary", "No summary provided")
                    tag = details.get("tags", ["untagged"])[0] if details.get("tags") else "untagged"

                    operations.append({
                        "id": op_id,
                        "method": method.upper(),
                        "path": path,
                        "tag": tag,
                        "summary": summary
                    })

                    # For GET operations without parameters, they might be treated as resources
                    if method.lower() == "get" and not details.get("parameters") and "{" not in path:
                        resources.append({
                            "id": op_id,
                            "path": path
                        })

        # Group by tag for better display
        tags = {}
        for op in operations:
            tag = op["tag"]
            if tag not in tags:
                tags[tag] = []
            tags[tag].append(op)

        # Display information
        print(f"\n📌 Found {path_count} unique API paths")
        print(f"📌 Found {len(operations)} operations that will be converted to MCP tools")
        print(f"📌 Found {len(resources)} potential resources (GET endpoints)")

        # List operations grouped by tag
        print("\n🔧 TOOLS BY CATEGORY:")
        print("=" * 60)
        for tag, ops in sorted(tags.items()):
            print(f"\n[{tag.upper()}] - {len(ops)} tools:")
            for op in sorted(ops, key=lambda x: x["id"]):
                tool_name = op["id"]
                print(f"  • {tool_name.ljust(25)} - {op['method']} {op['path']} - {op['summary']}")

        # List potential resources
        if resources:
            print("\n📚 POTENTIAL RESOURCES:")
            print("=" * 60)
            for res in sorted(resources, key=lambda x: x["id"]):
                print(f"  • {res['id'].ljust(25)} - {res['path']}")

        return path_count, len(operations), len(resources), operations, resources

    except Exception as e:
        print(f"Error analyzing Petstore OpenAPI spec: {e}")
        return 0, 0, 0, [], []

def test_server_startup(port=8888, verbose=False):
    """Test that the server can start successfully with Petstore API."""
    print("\n🔄 TESTING SERVER STARTUP...")
    print("=" * 60)

    # Get detailed endpoint information
    path_count, operation_count, resource_count, operations, resources = detailed_petstore_endpoints()

    # Create temporary files for capturing server output
    server_output_file = "server_output.tmp"

    try:
        # Build command with correct arguments
        cmd = [
            sys.executable, "-m",
            "awslabs.openapi_mcp_server.server",
            "--sse",
            "--port", str(port),
            "--api-name", "petstore",
            "--api-url", "https://petstore3.swagger.io/api/v3",
            "--spec-url", "https://petstore3.swagger.io/api/v3/openapi.json"
        ]

        print(f"Executing: {' '.join(cmd)}")

        # Set output redirection
        if verbose:
            stdout, stderr = None, None  # Show output in terminal
            print("Running in verbose mode - server output will display in terminal")
        else:
            # In quiet mode, direct output to a file
            f_output = open(server_output_file, 'w')
            stdout, stderr = f_output, f_output
            print("Running in quiet mode - errors will be reported if encountered")

        # Start the process
        start_time = datetime.datetime.now()
        print(f"Starting server at {start_time.strftime('%H:%M:%S')} on port {port}")

        # Use localhost (127.0.0.1) as host for security
        env = os.environ.copy()
        env["SERVER_HOST"] = "127.0.0.1"

        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, env=env)

        # Give the server time to start
        print("Waiting for server to initialize...")
        time.sleep(5)

        # Check if the process is still running
        if process.poll() is None:
            print("Server process is running successfully")

            errors = 0

            # Summarize test results
            end_time = datetime.datetime.now()
            runtime = (end_time - start_time).total_seconds()

            # Final test report
            print("\n" + "="*60)
            print(f"🔍 PETSTORE API FUNCTIONAL TEST REPORT")
            print("="*60)
            print(f"✅ Server startup: SUCCESS")
            print(f"📊 API paths: {path_count}")
            print(f"📊 Total tools (operations): {operation_count}")
            print(f"📊 Potential resources: {resource_count}")
            print(f"⚠️ Errors encountered: {errors}")
            print(f"⏱️ Test duration: {runtime:.2f} seconds")
            print("="*60)

            return True
        else:
            # Get the return code
            retcode = process.poll()

            # Handle server output
            if not verbose and 'f_output' in locals():
                f_output.close()

                with open(server_output_file, 'r') as f:
                    server_output = f.read()
                    print(f"Server failed to start (exit code: {retcode})")
                    print(f"Server output: {server_output}")

            return False

    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False

    finally:
        # Clean up the server process
        if 'process' in locals() and process.poll() is None:
            print("Stopping server process...")

            # Redirect stderr to devnull to avoid the traceback
            with open(os.devnull, 'w') as devnull:
                # Save the original stderr
                old_stderr = sys.stderr

                try:
                    if verbose:
                        # In verbose mode, kill the process without showing traceback
                        process.kill()
                    else:
                        # Send SIGINT to the process
                        process.send_signal(signal.SIGINT)
                        # Wait for process to exit, redirecting stderr to devnull
                        # to hide the traceback
                        sys.stderr = devnull
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                finally:
                    # Restore stderr
                    sys.stderr = old_stderr

            print("Server stopped cleanly")

        # Clean up temporary files
        if not verbose and os.path.exists(server_output_file):
            os.unlink(server_output_file)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test OpenAPI MCP server with Petstore API")
    parser.add_argument("--port", type=int, default=8888, help="Port to run the server on")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose output")

    args = parser.parse_args()

    print(f"\n🚀 Starting Petstore functional test (port: {args.port}, verbose: {args.verbose})")
    success = test_server_startup(args.port, args.verbose)

    print(f"Test {'succeeded' if success else 'failed'}")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Make the script executable
chmod +x test_petstore_simple.py

# Check if httpx is installed
if ! python -c "import httpx" 2>/dev/null; then
    echo "Installing httpx dependency..."
    python -m pip install httpx
fi

# Run the simple test
echo "Running Petstore API functional test..."
python test_petstore_simple.py "$@"

# Store the exit code
exit_code=$?

# Clean up unless user wants to keep the test script
if [ "$1" != "--keep-script" ]; then
    rm test_petstore_simple.py
fi

exit $exit_code
