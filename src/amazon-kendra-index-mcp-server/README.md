# awslabs amazon-kendra-index-mcp-server MCP Server

An AWS Labs Model Context Protocol (MCP) server for amazon-kendra-index-mcp-server


Example usage MCP Configuration:
"awslabs.amazon-kendra-index-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "[absolute path to mcp repo]/src/amazon-kendra-index-mcp-server/awslabs/amazon_kendra_index_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "KENDRA_INDEX_ID": "[Your Kendra Index Id]"
        "AWS_PROFILE": "[Your AWS Profile Name]",
        "AWS_REGION": "[Region where your Kendra Index resides]"
      },
      "disabled": false,
      "autoApprove": []
    },
