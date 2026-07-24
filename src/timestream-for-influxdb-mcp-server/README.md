# AWS Labs Timestream for InfluxDB MCP Server

An AWS Labs Model Context Protocol (MCP) server for Timestream for InfluxDB. This server provides tools to interact with AWS Timestream for InfluxDB APIs, allowing you to create and manage database instances, clusters, parameter groups, and more. It also includes tools to interact with InfluxDB's write and query APIs.

## Features

- Create, update, list, describe, and delete Timestream for InfluxDB database instances
- Create, update, list, describe, and delete Timestream for InfluxDB database clusters
- Manage DB parameter groups
- Tag management for Timestream for InfluxDB resources
- Manage InfluxDB 2 buckets and organizations
- Write and query data using InfluxDB 2 APIs


## Pre-requisites
1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
    - You need an AWS account with appropriate permissions
    - Configure AWS credentials with `aws configure` or environment variables
    - Consider starting with Read-only permission if you don't want the LLM to modify any resources
4. *(Only for InfluxDB v3 data operations)* Install **Node.js ≥ 20.11** — required to build and run the separate InfluxDB 3 MCP server (see [InfluxDB v3 data operations](#influxdb-v3-data-operations)).

## Installation

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.timestream-for-influxdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.timestream-for-influxdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudGltZXN0cmVhbS1mb3ItaW5mbHV4ZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Timestream%20for%20InfluxDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

You can modify the settings of your MCP client to run your local server (e.g. for Kiro, `~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "awslabs.timestream-for-influxdb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.timestream-for-influxdb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "INFLUXDB_URL": "https://your-influxdb-endpoint:8086",
        "INFLUXDB_TOKEN": "your-influxdb-token",
        "INFLUXDB_ORG": "your-influxdb-org",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
> **Note:** The `INFLUXDB_URL` / `INFLUXDB_TOKEN` / `INFLUXDB_ORG` variables are **optional** and apply to **InfluxDB v2** data operations only (default port **8086**). Control-plane tools (clusters, instances, parameter groups, tags) work with AWS credentials alone. For **InfluxDB v3** data operations (port 8181), see [InfluxDB v3 data operations](#influxdb-v3-data-operations).

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.timestream-for-influxdb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.timestream-for-influxdb-mcp-server@latest",
        "awslabs.timestream-for-influxdb-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "INFLUXDB_URL": "https://your-influxdb-endpoint:8086",
        "INFLUXDB_TOKEN": "your-influxdb-token",
        "INFLUXDB_ORG": "your-influxdb-org",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### InfluxDB Connection Security

InfluxDB tools use the `INFLUXDB_URL`, `INFLUXDB_TOKEN`, and `INFLUXDB_ORG`
environment variables when no connection parameters are supplied in a tool call.

Connection parameters are treated as a single trust boundary:

- If a tool call supplies any connection parameter, it must supply all parameters
  required by that tool. Server environment credentials are never used to complete
  a partial caller-supplied configuration.
- A caller-supplied URL must match `INFLUXDB_URL` or an entry in the optional,
  comma-separated `INFLUXDB_ALLOWED_URLS` environment variable.
- Configure additional endpoints before allowing tool calls to target them. For
  example, set `INFLUXDB_ALLOWED_URLS` to
  `https://influxdb-a.example.com:8086,https://influxdb-b.example.com:8086`.

This is a breaking change for clients that previously supplied only some connection
parameters and relied on environment-variable fallback for the others. Update those
clients to either omit all connection parameters or provide a complete configuration
for an operator-approved URL.


### Available Tools

The Timestream for InfluxDB MCP server provides the following tools:

#### AWS Timestream for InfluxDB Management

##### Database Cluster Management
- `CreateDbCluster`: Create a new Timestream for InfluxDB database cluster
- `GetDbCluster`: Retrieve information about a specific DB cluster
- `DeleteDbCluster`: Delete a Timestream for InfluxDB database cluster
- `ListDbClusters`: List all Timestream for InfluxDB database clusters
- `UpdateDbCluster`: Update a Timestream for InfluxDB database cluster
- `LsInstancesOfCluster`: List DB instances belonging to a specific cluster
- `ListClustersByStatus`: List DB clusters filtered by status

##### Database Instance Management
- `CreateDbInstance`: Create a new Timestream for InfluxDB database instance
- `GetDbInstance`: Retrieve information about a specific DB instance
- `DeleteDbInstance`: Delete a Timestream for InfluxDB database instance
- `ListDbInstances`: List all Timestream for InfluxDB database instances
- `UpdateDbInstance`: Update a Timestream for InfluxDB database instance
- `LsInstancesByStatus`: List DB instances filtered by status

##### Parameter Group Management
- `CreateDbParamGroup`: Create a new DB parameter group
- `GetDbParameterGroup`: Retrieve information about a specific DB parameter group
- `ListDbParamGroups`: List all DB parameter groups

##### Tag Management
- `ListTagsForResource`: List all tags on a Timestream for InfluxDB resource
- `TagResource`: Add tags to a Timestream for InfluxDB resource
- `UntagResource`: Remove tags from a Timestream for InfluxDB resource

#### InfluxDB Data Operations

##### Write API
- `InfluxDBWritePoints`: Write data points to InfluxDB
- `InfluxDBWriteLP`: Write data in Line Protocol format to InfluxDB

##### Query API
- `InfluxDBQuery`: Query data from InfluxDB using Flux query language

##### Bucket Management
- `InfluxDBListBuckets`: List all buckets in InfluxDB
- `InfluxDBCreateBucket`: Create a new bucket in InfluxDB

##### Organization Management
- `InfluxDBListOrgs`: List all organizations in InfluxDB
- `InfluxDBCreateOrg`: Create a new organization in InfluxDB

## InfluxDB v3 data operations

This MCP server covers the **AWS control plane** (clusters, instances, parameter groups, tags) and **InfluxDB v2 data** operations (Flux query, writes, buckets, organizations). **InfluxDB v3 data operations** (SQL queries, v3 schema, v3 token management) are provided by a separate, InfluxData-maintained MCP server: [`influxdata/influxdb3_mcp_server`](https://github.com/influxdata/influxdb3_mcp_server). The [Kiro Power](#kiro-power)'s `kiro_power/mcp.json` references both servers.

### Set up the InfluxDB 3 MCP server

Requires **Node.js ≥ 20.11**. It is not published to npm yet, so clone and build it (or use the Docker option in its README):

```bash
git clone https://github.com/influxdata/influxdb3_mcp_server.git
cd influxdb3_mcp_server
npm install
npm run build   # produces build/index.js
```

Then add it to your MCP client config alongside this server:

```json
{
  "mcpServers": {
    "influxdb3": {
      "command": "node",
      "args": ["/absolute/path/to/influxdb3_mcp_server/build/index.js"],
      "env": {
        "INFLUX_DB_INSTANCE_URL": "https://your-influxdb-v3-endpoint:8181/",
        "INFLUX_DB_TOKEN": "your-influxdb-v3-token",
        "INFLUX_DB_PRODUCT_TYPE": "core"
      }
    }
  }
}
```

- `INFLUX_DB_PRODUCT_TYPE`: use `core` for a single-node V3 cluster, `enterprise` for multi-node.
- If the `node` on your PATH is older than 20.11, point `command` at an absolute path to a Node ≥ 20.11 binary.

See the [InfluxDB 3 MCP server README](https://github.com/influxdata/influxdb3_mcp_server) for Cloud Dedicated/Clustered/Serverless variants and the full tool list.

## AI Rules

This repository also contains AI Rules (Steering). These markdown files serve as simple
context and guidance for best practices and patterns that AI assistants automatically apply
when generating code to improve the quality of agentic development.

Recommended path:
* [Kiro Power](#kiro-power) - button-click installation

Alternative:
The [Timestream for InfluxDB power](https://github.com/awslabs/mcp/tree/main/src/timestream-for-influxdb-mcp-server/kiro_power/) can also be cloned into your tool's respective `rules` directory
for use with other coding assistants.

### Kiro Power

To setup the Kiro power:
1. Install directly from the [Kiro Powers Registry](https://kiro.dev/launch/powers/amazon-timestream-for-influxdb/)
2. Once redirected to the Power in the IDE either:
   1. Select the **`Try Power`** button. Suggested for people who want:
      - The AI to guide MCP server setup
      - An interactive onboarding experience with Timestream for InfluxDB to create a new instance or cluster
   2. Open a new Kiro chat and ask anything related to Timestream for InfluxDB
      - The Kiro agent will automatically activate the power if it identifies the power as valuable for completing
        the user's task.
