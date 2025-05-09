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

When specifying the Neptune Endpoint the following formats are expected:

For Neptune Database:
`neptune-db://<Cluster Endpoint>`

For Neptune Analytics:
`neptune-graph://<graph identifier>`