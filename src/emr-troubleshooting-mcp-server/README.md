# Amazon EMR Troubleshooting MCP Server

This AWS Labs Model Context Protocol (MCP) server provides the capability to troubleshoot Amazon EMR issues by analyzing log files stored in Amazon S3. It offers an integrated knowledge base of known issues and curated recommendations across Apache Spark, Hadoop YARN and HDFS, Apache Hive, Apache HBase, and Presto frameworks. It includes tools to perform ad-hoc log analysis of user provided log snippets and to query log files for existing Amazon EMR log files that are stored in Amazon S3.

## Features

- **Curated Knowledge Base**: 150+ known EMR issues across Spark, YARN, Hadoop, Hive, HBase, Presto, and EMR service components with AWS Knowledge Center links when available
- **EMR Cluster Analysis**: Automatically discovers logs in S3 for provided EMR Cluster ID and uses Amazon Athena for optimized SQL queries across log files to identity known issues and provided aggregrated recommendations on top findings
- **Ad-hoc Log Analysis**: Analyze user-provided log snippets directly in chat to provide recommendations

## Prerequisites

1. This MCP server can only be run locally on the same host as your LLM client.
2. Set up AWS credentials with access to Amazon EMR, Amazon Athena, and Amazon S3.
3. Amazon EMR cluster with logging enabled to S3.
4. Amazon Athena query editor configured.

## Available Tools

- `analyze_emr_logs` - Analyzes EMR log content that is provided directly in chat for quick issue identification
- `analyze_emr_cluster_logs` - Discovers EMR cluster logs in S3 and performs analysis using Amazon Athena

## Usage

Once configured, you can ask your AI assistant to analyze EMR logs and troubleshoot issues:

- **"Analyze the logs for EMR cluster j-20FTFQ6AGIYQ5"**
- **"What issues are present in this EMR log?"**

## Installation

### Option 1: Python (UVX)
#### Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Create and configure an AWS Profile [AWS documentation](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.emr-troubleshooting-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmVtci10cm91Ymxlc2hvb3RpbmctbWNwLXNlcnZlckBsYXRlc3QiXSwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=EMR%20Troubleshooting%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.emr-troubleshooting-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### MCP Config (Q CLI, Cline)
* For Q CLI, update MCP Config Amazon Q Developer CLI (`~/.aws/amazonq/mcp.json`)
* For Cline click on "Configure MCP Servers" option from MCP tab

```json
{
  "mcpServers": {
    "awslabs.emr-troubleshooting-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": ["awslabs.emr-troubleshooting-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "The AWS Profile Name to use for AWS access",
        "AWS_REGION": "The AWS Region where you EMR clusters reside",
        "FASTMCP_LOG_LEVEL": "ERROR"
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
    "awslabs.emr-troubleshooting-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.emr-troubleshooting-mcp-server@latest",
        "awslabs.emr-troubleshooting-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "The AWS Profile Name to use for AWS access",
        "AWS_REGION": "The AWS Region where you EMR clusters reside"
      }
    }
  }
}
```


### Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t awslabs/emr-troubleshooting-mcp-server .
   ```

2. Create an environment file with your AWS credentials:
   ```bash
   # Export credentials from your AWS profile to a file
   aws configure export-credentials --profile your-aws-profile --format env > aws_credentials.env
   # Remove 'export ' prefix from each line
   sed 's/^export //' aws_credentials.env > .env
   ```

3. Configure the MCP server:

```json
{
  "mcpServers": {
    "awslabs.emr-troubleshooting-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env-file", "/path/to/.env",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "--env", "AWS_REGION=us-east-1",
        "awslabs/emr-troubleshooting-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Best Practices
- Use separate AWS profiles for different environments (dev, test, prod)
- Implement proper error handling in your client applications

## Security Considerations
- **Least Privilege Access**: Configure IAM permissions to grant only the minimum necessary permissions for Athena queries and S3 log access
- **Read-Only Access**: Use read-only policies for accessing EMR logs in S3 and executing Athena queries
- **Data Protection**: Be aware that log files may contain sensitive information; ensure appropriate access controls are in place

## Troubleshooting
- If you encounter permission errors, verify your IAM user has the correct policies attached


## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) file for details.
