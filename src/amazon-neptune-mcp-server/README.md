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

<table>
<tr>
<td width="49%" valign="top" style="text-align: center;">

<a href="https://cursor.com/install-mcp?name=Neptune%20Query&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW5lcHR1bmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJJTkZPIiwiTkVQVFVORV9FTkRQT0lOVCI6IjxJTlNFUlQgTkVQVFVORSBFTkRQT0lOVCBJTiBGT1JNQVQgU1BFQ0lGSUVEIEJFTE9XPiJ9fQ%3D%3D">
<img src="https://cursor.com/deeplink/mcp-install-light.svg" alt="Install MCP Server" style="height: 20px;">
</a>

</td>
<td width="2%" style="border-left: 1px solid #e1e5e9; padding: 0;"></td>
<td width="49%" valign="top" style="text-align: center;">

<a href="https://insiders.vscode.dev/redirect/mcp/install?name=Neptune%20Query&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%2C%22NEPTUNE_ENDPOINT%22%3A%22%3CINSERT%20NEPTUNE%20ENDPOINT%20IN%20FORMAT%20SPECIFIED%20BELOW%3E%22%7D%7D">
<img src="https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white" alt="Install on VS Code" style="height: 20px;">
</a>

</td>
</tr>
</table>

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
