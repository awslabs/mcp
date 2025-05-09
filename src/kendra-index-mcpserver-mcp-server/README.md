# awslabs kendra-index-mcpserver MCP Server

An AWS Labs Model Context Protocol (MCP) server for kendra-index-mcpserver


Example usage MCP Configuration:
"awslabs.aws-kendra-index-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "[absolute path to mcp repo]/src/kendra-index-mcpserver-mcp-server/awslabs/kendra_index_mcpserver_mcp_server",
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
