# AWS Elastic Beanstalk MCP Server

The AWS Elastic Beanstalk MCP Server provides tools for managing AWS Elastic Beanstalk applications and environments through the Model Context Protocol (MCP).

## Installation

```bash
pip install awslabs.elastic-beanstalk-mcp-server
```

Or using `uvx`:

```bash
uvx awslabs.elastic-beanstalk-mcp-server@latest
```

## Configuration

Add the following to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.elastic-beanstalk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.elastic-beanstalk-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Available Tools

### list_applications

Lists all Elastic Beanstalk applications in your AWS account.

**Parameters:** None

**Example:**
```json
{
  "name": "list_applications",
  "parameters": {}
}
```

### describe_application

Get detailed information about a specific Elastic Beanstalk application.

**Parameters:**
- `application_name` (string): Name of the Elastic Beanstalk application

**Example:**
```json
{
  "name": "describe_application",
  "parameters": {
    "application_name": "my-application"
  }
}
```

### list_environments

List all Elastic Beanstalk environments or environments for a specific application.

**Parameters:**
- `application_name` (string, optional): Name of the Elastic Beanstalk application

**Example:**
```json
{
  "name": "list_environments",
  "parameters": {
    "application_name": "my-application"
  }
}
```

### describe_environment

Get detailed information about a specific Elastic Beanstalk environment.

**Parameters:**
- `environment_id` (string, optional): ID of the Elastic Beanstalk environment
- `environment_name` (string, optional): Name of the Elastic Beanstalk environment

**Example:**
```json
{
  "name": "describe_environment",
  "parameters": {
    "environment_name": "my-environment"
  }
}
```

### create_application

Create a new Elastic Beanstalk application.

**Parameters:**
- `application_name` (string): Name of the Elastic Beanstalk application
- `description` (string, optional): Description of the application

**Example:**
```json
{
  "name": "create_application",
  "parameters": {
    "application_name": "my-new-application",
    "description": "My new Elastic Beanstalk application"
  }
}
```

### create_environment

Create a new Elastic Beanstalk environment.

**Parameters:**
- `application_name` (string): Name of the Elastic Beanstalk application
- `environment_name` (string): Name of the environment
- `solution_stack_name` (string): Solution stack name (platform)
- `tier` (string, optional): Environment tier (WebServer or Worker), default: WebServer
- `description` (string, optional): Description of the environment

**Example:**
```json
{
  "name": "create_environment",
  "parameters": {
    "application_name": "my-application",
    "environment_name": "my-environment",
    "solution_stack_name": "64bit Amazon Linux 2 v5.8.0 running Node.js 18",
    "description": "My production environment"
  }
}
```

### terminate_environment

Terminate an Elastic Beanstalk environment.

**Parameters:**
- `environment_name` (string): Name of the Elastic Beanstalk environment
- `force_terminate` (boolean, optional): Force termination even if there are issues, default: false

**Example:**
```json
{
  "name": "terminate_environment",
  "parameters": {
    "environment_name": "my-environment",
    "force_terminate": false
  }
}
```

### list_available_solution_stacks

List all available solution stacks (platforms) for Elastic Beanstalk.

**Parameters:** None

**Example:**
```json
{
  "name": "list_available_solution_stacks",
  "parameters": {}
}
```

### update_environment

Update an Elastic Beanstalk environment configuration.

**Parameters:**
- `environment_name` (string): Name of the Elastic Beanstalk environment
- `description` (string, optional): New description for the environment
- `option_settings` (array, optional): Array of configuration option settings

**Example:**
```json
{
  "name": "update_environment",
  "parameters": {
    "environment_name": "my-environment",
    "description": "Updated environment description",
    "option_settings": [
      {
        "namespace": "aws:autoscaling:asg",
        "option_name": "MinSize",
        "value": "2"
      },
      {
        "namespace": "aws:autoscaling:asg",
        "option_name": "MaxSize",
        "value": "4"
      }
    ]
  }
}
```

### restart_app_server

Restart the application server for an Elastic Beanstalk environment.

**Parameters:**
- `environment_name` (string): Name of the Elastic Beanstalk environment

**Example:**
```json
{
  "name": "restart_app_server",
  "parameters": {
    "environment_name": "my-environment"
  }
}
```

## Examples

See the [samples](../samples/) directory for example scripts that demonstrate how to use the AWS Elastic Beanstalk MCP Server.