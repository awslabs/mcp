# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

# Import tool modules
from .tools import (  # bedrock
    data_management,
    domain_management,
    environment,
    glossary,
    project_management,
)

# initialize FastMCP server
mcp = FastMCP("datazone")

# configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Register all tools from modules
domain_management.register_tools(mcp)
project_management.register_tools(mcp)
data_management.register_tools(mcp)
glossary.register_tools(mcp)
environment.register_tools(mcp)


def main():
    """Entry point for console script."""
    try:
        mcp.run(transport="stdio")

        print("DEBUG: Server completed", file=sys.stderr)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down gracefully.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        # Ensure we return a proper JSON response even in case of errors
        error_response = {
            "error": str(e),
            "type": type(e).__name__,
            "message": "MCP server encountered an error",
        }
        print(json.dumps(error_response))
        sys.exit(1)


if __name__ == "__main__":
    # try:
    #     mcp.run(transport='stdio')
    # except Exception as e:
    #     # Ensure we return a proper JSON response even in case of errors
    #     error_response = {
    #         "error": str(e),
    #         "type": type(e).__name__,
    #         "message": "MCP server encountered an error"
    #     }
    #     print(json.dumps(error_response))
    #     sys.exit(1)
    main()
