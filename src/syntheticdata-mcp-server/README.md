# Synthetic Data MCP Server

A Model Context Protocol (MCP) server for generating, validating, and managing synthetic data.

## Overview

This MCP server provides tools for generating synthetic data based on business descriptions, executing pandas code safely, validating data structures, and loading data to storage systems like S3.

## Features

- **Business-Driven Generation**: Generate synthetic data instructions based on business descriptions
- **Data Generation Instructions**: Generate structured data generation instructions from business descriptions
- **Safe Pandas Code Execution**: Run pandas code in a restricted environment with automatic DataFrame detection
- **JSON Lines Validation**: Validate and convert JSON Lines data to CSV format
- **Data Validation**: Validate data structure, referential integrity, and save as CSV files
- **Referential Integrity Checking**: Validate relationships between tables
- **Data Quality Assessment**: Identify potential issues in data models (3NF validation)
- **Storage Integration**: Load data to various storage targets (S3) with support for:
  - Multiple file formats (CSV, JSON, Parquet)
  - Partitioning options
  - Storage class configuration
  - Encryption settings

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.syntheticdata-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuc3ludGhldGljZGF0YS1tY3Atc2VydmVyIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImF1dG9BcHByb3ZlIjpbXSwiZGlzYWJsZWQiOmZhbHNlfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Synthetic%20Data%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.syntheticdata-mcp-server%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |

```json
{
  "mcpServers": {
    "awslabs.syntheticdata-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.syntheticdata-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "autoApprove": [],
      "disabled": false
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.syntheticdata-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.syntheticdata-mcp-server@latest",
        "awslabs.syntheticdata-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


NOTE: Your credentials will need to be kept refreshed from your host

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

## Usage

### Getting Data Generation Instructions

```python
response = await server.get_data_gen_instructions(
    business_description="An e-commerce platform with customers, orders, and products"
)
```

### Executing Pandas Code

```python
response = await server.execute_pandas_code(
    code="your_pandas_code_here",
    workspace_dir="/path/to/workspace",
    output_dir="data"
)
```

### Validating and Saving Data

```python
response = await server.validate_and_save_data(
    data={
        "customers": [{"id": 1, "name": "John"}],
        "orders": [{"id": 101, "customer_id": 1}]
    },
    workspace_dir="/path/to/workspace",
    output_dir="data"
)
```

### Loading to Storage

```python
response = await server.load_to_storage(
    data={
        "customers": [{"id": 1, "name": "John"}]
    },
    targets=[{
        "type": "s3",
        "config": {
            "bucket": "my-bucket",
            "prefix": "data/",
            "format": "parquet"
        }
    }]
)
```
