# AWS AppSync MCP Server

A Model Context Protocol (MCP) server for AWS AppSync that enables AI assistants to manage and interact with backend APIs.

## Overview

The AWS AppSync MCP Server simplifies the management of APIs by providing capabilities to create graphQL APIs, data sources, resolvers, and other AppSync resources. This allows for streamlined API development and easier integration with AWS backend services through natural language interactions.

## Features

- **API Management**: Create and configure AppSync APIs with various authentication types
- **GraphQL API Creation**: Set up GraphQL APIs with schema definitions and authentication
- **API Key Management**: Generate and manage API keys for authentication
- **API Caching**: Configure caching for improved API performance
- **Data Source Management**: Connect APIs to various AWS backend services (DynamoDB, Lambda, RDS, etc.)
- **Function Management**: Create and manage AppSync functions for complex business logic
- **Channel Namespace Management**: Set up real-time subscriptions with channel namespaces
- **Domain Name Management**: Configure custom domain names for APIs
- **Resolver Management**: Create resolvers to connect GraphQL fields to data sources
- **Schema Management**: Define and update GraphQL schemas
- **Read-Only Mode**: Enable an optional security mode that restricts all operations to read-only, preventing any modifications

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS AppSync
   - You need an AWS account with AWS AppSync enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use AWS AppSync

## Setup

### Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-appsync-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwcHN5bmMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20AppSync%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-appsync-mcp-server%40latest%22%2C%20%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

## Configuration

Add the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`)

### Using AWS Profiles

For standard AWS profile-based authentication:

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-appsync-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using Temporary Credentials

For temporary credentials (such as those from AWS STS, IAM roles, or federation):

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-appsync-mcp-server@latest"],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key", // pragma: allowlist secret
        "AWS_SESSION_TOKEN": "your-session-token",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Enabling Write Operations using `--allow-write`

Enables tools that create or modify resources in the user's AWS account. When this flag is not enabled, the server runs in read-only mode that only allows read operations. This enhances security by preventing any modifications to AppSync resources. In read-only mode:

- Read operations work normally
- Write operations (`create_api`, `create_graphql_api`, `create_datasource`, etc.) are blocked and return a permission error

This mode is particularly useful for:
- Demonstration environments
- Security-sensitive applications
- Integration with public-facing AI assistants
- Protecting production APIs from unintended modifications

Example:
```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-appsync-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Docker Configuration

After building with `docker build -t awslabs/aws-appsync-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "awslabs/aws-appsync-mcp-server:latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Environment Variables

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `AWS_SESSION_TOKEN`: Session token for temporary credentials (used with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Tools

The server exposes the following tools through the MCP interface:

### create_api

Creates a new AppSync API with the given configuration.

```python
create_api(name: str) -> dict
```

### create_graphql_api

Creates a new GraphQL API with authentication and other configuration options.

```python
create_graphql_api(
    name: str,
    authentication_type: str = "API_KEY"
) -> dict
```

### create_api_key

Creates an API key for authentication with an AppSync API.

```python
create_api_key(
    api_id: str,
    description: str = None,
    expires: int = None
) -> dict
```

### create_api_cache

Creates and configures caching for an AppSync API to improve performance.

```python
create_api_cache(
    api_id: str,
    ttl: int = 3600,
    api_caching_behavior: str = "FULL_REQUEST_CACHING",
    type: str = "SMALL"
) -> dict
```

### create_datasource

Creates a data source to connect the API to backend services like DynamoDB, Lambda, or RDS.

```python
create_datasource(
    api_id: str,
    name: str,
    type: str,
    service_role_arn: str = None,
    dynamodb_config: dict = None,
    lambda_config: dict = None,
    elasticsearch_config: dict = None,
    relational_database_config: dict = None
) -> dict
```

### create_function

Creates an AppSync function for reusable business logic.

```python
create_function(
    api_id: str,
    name: str,
    data_source_name: str,
    function_version: str = "2018-05-29",
    request_mapping_template: str = None,
    response_mapping_template: str = None
) -> dict
```

### create_channel_namespace

Creates a channel namespace for real-time subscriptions.

```python
create_channel_namespace(
    api_id: str,
    name: str,
    publish_auth_modes: list = None,
    subscribe_auth_modes: list = None
) -> dict
```

### create_domain_name

Creates a custom domain name for an AppSync API.

```python
create_domain_name(
    domain_name: str,
    certificate_arn: str,
    description: str = None
) -> dict
```

### create_resolver

Creates a resolver to connect GraphQL fields to data sources.

```python
create_resolver(
    api_id: str,
    type_name: str,
    field_name: str,
    data_source_name: str = None,
    request_mapping_template: str = None,
    response_mapping_template: str = None,
    kind: str = "UNIT"
) -> dict
```

### create_schema

Creates or updates the GraphQL schema for an API.

```python
create_schema(
    api_id: str,
    definition: str
) -> dict
```

## Usage Examples

| Prompt | Description |
|--------|-------------|
| `Create a GraphQL API named "blog-api" with API key authentication` | Creates a new GraphQL API with the specified name and authentication type |
| `Add a GraphQL schema with a Post type with an id primary key, content and author fields` | Creates or updates the API schema with custom types and fields |
| `Create a DynamoDB data source for my API connecting to the "posts" table` | Sets up a data source to connect the API to a DynamoDB table |
| `Create a resolver for the "getPosts" query field` | Creates a resolver to handle GraphQL query execution |
| `Set up API caching with 1 hour TTL for better performance` | Configures caching to improve API response times |
| `Create an API key that expires in 30 days` | Generates an API key with a specific expiration date |
| `Create a Lambda data source for custom business logic` | Sets up a data source to connect the API to AWS Lambda functions |


## AWS AppSync Resources

This server uses the AWS AppSync service APIs for:
- GraphQL API creation and management
- Data source configuration (DynamoDB, Lambda, RDS, etc.)
- Resolver creation and management
- Schema definition and updates
- API key and authentication management
- Caching configuration
- Real-time subscription setup

## Security Considerations

- Use AWS profiles for credential management
- Use IAM policies to restrict access to only the required AWS AppSync resources
- Use temporary credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN) from AWS STS for enhanced security
- Implement AWS IAM roles with temporary credentials for applications and services
- Regularly rotate credentials and use the shortest practical expiration time for temporary credentials
- Be aware of AWS AppSync service quotas and limits
- Use the `--allow-write` flag judiciously and only when write operations are necessary

> #### ⚠️ IMPORTANT: YOU ARE RESPONSIBLE FOR YOUR AGENTS
>
> You are solely responsible for the actions and permissions of agents using the MCP server.
>
> - By default, the MCP server operates in **read-only mode**.
> - To enable write access, you must **explicitly configure the MCP with the necessary IAM permissions** and use "--allow-write" flag to enable create operations on AWS AppSync using the MCP server.
> - Always follow the **principle of least privilege**—grant only the permissions necessary for the agent to function.
> - If enabling write operations, **we recommend you take a backup of your data** and carefully validate any instructions generated by your LLM before execution. Perform such actions during a scheduled maintenance window for your application.
> - With AWS AppSync MCP Server, we recommend exercising caution when integrating it into automated workflows.

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-appsync-mcp-server/LICENSE) file for details.
