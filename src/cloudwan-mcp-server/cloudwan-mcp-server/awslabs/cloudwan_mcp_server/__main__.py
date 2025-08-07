"""Main entry point for CloudWAN MCP server."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from awslabs.cloudwan_mcp_server.server import main

if __name__ == "__main__":
    main()
