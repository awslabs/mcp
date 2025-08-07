#!/usr/bin/env python3
"""CloudWAN MCP Server startup script with proper module path resolution."""

import os
import sys
from pathlib import Path

def setup_python_path():
    """Set up Python path for proper module resolution."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Add to Python path if not already present
    script_str = str(script_dir)
    if script_str not in sys.path:
        sys.path.insert(0, script_str)
    
    # Also add to PYTHONPATH environment variable
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if script_str not in current_pythonpath:
        if current_pythonpath:
            os.environ["PYTHONPATH"] = f"{script_str}:{current_pythonpath}"
        else:
            os.environ["PYTHONPATH"] = script_str

def main():
    """Main entry point with path setup."""
    setup_python_path()
    
    try:
        from awslabs.cloudwan_mcp_server.server import main as server_main
        server_main()
    except ImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        print("Make sure you're running from the correct directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()