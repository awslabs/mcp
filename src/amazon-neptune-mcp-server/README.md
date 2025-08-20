# AWS Labs Amazon Neptune MCP Server

An Amazon Neptune MCP server that allows for fetching status, schema, and querying using openCypher and Gremlin for Neptune Database and openCypher for Neptune Analytics.

## Features

The Amazon Neptune MCP Server provides the following capabilities:

1. **Run Queries**: Execute openCypher and/or Gremlin queries against the configured database
2. **Schema**: Get the schema in the configured graph as a text string
3. **Status**: Find if the graph is "Available" or "Unavailable" to your server.  This is useful in helping to ensure that the graph is connected.

### AWS Requirements

1. **AWS CLI Configuration**: You must have the AWS CLI configured with credentials and an AWS_PROFILE that has access to Amazon Neptune
2. **Amazon Neptune**: You must have at least one Amazon Neptune Database or Amazon Neptune Analytics graph.
3. **IAM Permissions**: Your IAM role/user must have appropriate permissions to:
   - Access Amazon Neptune
   - Query Amazon Neptune
4. **Access**: The location where you are running the server must have access to the Amazon Neptune instance.  Neptune Database resides in a private VPC so access into the private VPC.  Neptune Analytics can be access either using a public endpoint, if configured, or the access will be needed to the private endpoint.

Note: This server will run any query sent to it, which could include both mutating and read-only actions.  Properly configuring the permissions of the role to allow/disallow specific data plane actions as specified here:
* [Neptune Database](https://docs.aws.amazon.com/neptune/latest/userguide/security.html)
* [Neptune Analytics](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/security.html)


## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-neptune-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW5lcHR1bmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiTkVQVFVORV9FTkRQT0lOVCI6Imh0dHBzOi8veW91ci1uZXB0dW5lLWNsdXN0ZXItaWQucmVnaW9uLm5lcHR1bmUuYW1hem9uYXdzLmNvbTo4MTgyIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Neptune%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A%2F%2Fyour-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Below is an example of how to configure your MCP client, although different clients may require a different format.


```json
{
  "mcpServers": {
    "Neptune Query": {
      "command": "uvx",
      "args": ["awslabs.amazon-neptune-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
      }
    }
  }
}

```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.amazon-neptune-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-neptune-mcp-server@latest",
        "awslabs.amazon-neptune-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
      }
    }
  }
}
```

### Docker Configuration
After building with `docker build -t awslabs/amazon-neptune-mcp-server .`:

```
{
  "mcpServers": {
    "awslabs.amazon-neptune-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/amazon-neptune-mcp-server"
        ],
        "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

When specifying the Neptune Endpoint the following formats are expected:

For Neptune Database:
`neptune-db://<Cluster Endpoint>`

For Neptune Analytics:
`neptune-graph://<graph identifier>`
