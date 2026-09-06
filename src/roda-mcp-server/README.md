# Registry of Open Data on AWS (RODA) MCP Server

Model Context Protocol (MCP) server for discovering and exploring datasets from the [Registry of Open Data on AWS (RODA)](https://registry.opendata.aws/). The Registry hosts hundreds of publicly available datasets including climate data, genomics, satellite imagery, and more on Amazon Simple Storage Service (S3).

## Features

- Discover datasets across 1,000+ open datasets on AWS
- Search by keyword, organization, license, or topic in natural language
- Find related datasets and explore by domain
- Always surfaces license information
- Preview and sample datasets for early evaluation
- Curated next steps on how to access datasets
- For public datasets without controlled access:
  - preview S3 bucket structure
  - sample file directly in conversation

## Basic Usage

Ask your AI assistants in natural language:
  * "What open data are on AWS?"
  * "Show me datasets related to land surface temperature."
  * "Get more details about 1000 Genomes."
  * "Preview the file structure of CHIRPS and sample a file."

For more example on how to use the MCP server, check out [Example Usage](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/examples/example_usage.md).

> [!NOTE]
> Each dataset on RODA has specific license terms. Please review them before accessing or using the data.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
1. Install Python 3.10+ using `uv python install 3.10`


## Available Tools

| Tool | Description |
|------|-------------|
| `search_datasets` | Search by keyword with optional filters for tags, organization, and license type |
| `list_datasets` | List all datasets with optional tag filtering |
| `get_dataset_details` | Get complete details for a specific dataset including resources and access info |
| `discover_by_organization` | Find datasets managed by a specific organization (e.g., NASA, NOAA) |
| `discover_by_license` | Find datasets by license type (e.g., Creative Commons, MIT) |
| `find_related_datasets` | Find datasets related to a given dataset based on shared tags |
| `get_knowledge_base_stats` | Get registry statistics including top tags, organizations, and resource types |
| `preview_dataset` | Show S3 bucket structure for datasets (no download, no AWS account needed). This is only available for public datasets without controlled access. You should review and agree to the dataset license before previewing datasets.|
| `sample_dataset` | Read the first 100KB of a specific file from a public dataset's S3 bucket. This is only available for public datasets without controlled access. You should review and agree to the dataset license before sampling datasets.|
| `search_stac_endpoints` | Find datasets with STAC (SpatioTemporal Asset Catalog) API endpoints |

Datasets on the Registry fall into three access tiers, due to different compliance reasons:
- Open and free; hosted in a public S3 bucket and don't require AWS account to use
- Open, but require AWS credentials and requester pay
- Controlled access, particularly in health domains, and requires additional steps to access the datasets

For the datasets that are open and free, we offer a preview into S3 buckets, as well as capability to sample a file to help users quickly evaluate the datasets. For other datasets, we provide access instructions to users on how to access the datasets.

To learn more about how we designed this MCP server, check out [High-Level Design](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/docs/high-level-design.md).

## Setup

### Using uv

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

**For Linux/MacOS users:**

```json
{
  "mcpServers": {
    "awslabs.roda-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.roda-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**For Windows users:**

```json
{
  "mcpServers": {
    "awslabs.roda-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.roda-mcp-server@latest",
        "awslabs.roda-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Using Claude Code CLI

```
# Add RODA MCP
claude mcp add roda-mcp uvx awslabs.roda-mcp-server@latest

# List installed server
claude mcp list
```


## Security
Check out [Security](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/SECURITY.md) for security considerations on this MCP server.

## License
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").


## Disclaimer
This roda-mcp-server package is provided "as is" without warranty of any kind, express or implied, and is intended for development, testing, and evaluation purposes only. We do not provide any guarantee on the quality, performance, or reliability of this package. LLMs are non-deterministic and they make mistakes, we advise you to always thoroughly test and follow the best practices of your organization before using these tools on customer facing accounts. Users of this package are solely responsible for implementing proper security controls and MUST use AWS Identity and Access Management (IAM) to manage access to AWS resources. You are responsible for configuring appropriate IAM policies, roles, and permissions, and any security vulnerabilities resulting from improper IAM configuration are your sole responsibility. By using this package, you acknowledge that you have read and understood this disclaimer and agree to use the package at your own risk.
