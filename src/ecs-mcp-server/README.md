# Amazon ECS MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.ecs-mcp-server.svg)](https://pypi.org/project/awslabs.ecs-mcp-server/)

An MCP server for containerizing applications, deploying applications to Amazon Elastic Container Service (ECS), troubleshooting ECS deployments, and managing ECS resources. This server enables AI assistants to help users with the full lifecycle of containerized applications on AWS.

## Features

- **Containerization Guidance**: Provides best practices and guidance for containerizing web applications
- **ECS Deployment**: Deploy containerized applications to AWS ECS using Fargate
- **Load Balancer Integration**: Automatically configure Application Load Balancers (ALBs) for web traffic
- **Infrastructure as Code**: Generate and apply CloudFormation templates for ECS infrastructure
- **URL Management**: Return public ALB URLs for immediate access to deployed applications
- **Circuit Breaker**: Implement deployment circuit breaker with automatic rollback
- **Container Insights**: Enable enhanced container insights for monitoring
- **VPC Endpoints**: Configure VPC endpoints for secure access to AWS services without internet exposure
- **Security Best Practices**: Implement AWS security best practices for container deployments
- **Resource Management**: List and explore ECS resources such as task definitions, services, clusters, and tasks
- **ECR Integration**: View repositories and container images in Amazon ECR

Customers can use the `containerize_app` tool to help them containerize their applications with best practices and deploy them to Amazon ECS. The `create_ecs_infrastructure` tool automates infrastructure deployment using CloudFormation, while `get_deployment_status` returns the status of deployments and provide the URL of the set up Application Load Balancer. When resources are no longer needed, the `delete_ecs_infrastructure` tool allows for easy cleanup and removal of all deployed components.

Customers can list and view their ECS resources (clusters, services, tasks, task definitions) and access their ECR resources (container images) using the `ecs_resource_management` tool. When running into ECS deployment issues, they can use the `ecs_troubleshooting_tool` to diagnose and resolve common problems.

## Installation

```bash
# Install using uv
uv pip install awslabs.ecs-mcp-server

# Or install using pip
pip install awslabs.ecs-mcp-server
```

You can also run the MCP server directly from a local clone of the GitHub repository:

```bash
# Clone the repository
git clone https://github.com/awslabs/ecs-mcp-server.git

# Run the server directly using uv
uv --directory /path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server run main.py
```

## Usage Environments

The ECS MCP Server is currently in development and is designed for the following environments:

- **Development and Prototyping**: Ideal for local application development, testing containerization approaches, and rapidly iterating on deployment configurations.
- **Learning and Exploration**: Excellent for users who want to learn about containerization, ECS, and AWS infrastructure.
- **Testing and Staging**: Suitable for integration testing and pre-production validation in non-critical environments.

**Not Recommended For**:
- **Production Workloads**: As this tool is still in active development, it is not suited for production deployments or business-critical applications.
- **Regulated or Sensitive Workloads**: Not suitable for applications handling sensitive data or subject to regulatory compliance requirements.

**Important Note on Troubleshooting Tools**: Even the troubleshooting tools should be used with caution in production environments. Always set `ALLOW_SENSITIVE_DATA=false` and `ALLOW_WRITE=false` flags when connecting to production accounts to prevent accidental exposure of sensitive information or unintended infrastructure modifications.

## Production Considerations

While the ECS MCP Server is primarily designed for development, testing, and non-critical environments, certain components can be considered for controlled production use with appropriate safeguards.

### Allowlisted Actions for Production

The following operations are read-only and relatively safe for production environments when used with appropriate IAM permissions. Note: they can return sensitive information, so ensure `ALLOW_SENSITIVE_DATA=false` is set in production configurations.

| Tool | Operation | Production Safety |
|------|-----------|-------------------|
| `ecs_resource_management` | `list` operations (clusters, services, tasks) | ✅ Safe - Read-only |
| `ecs_resource_management` | `describe` operations (clusters, services, tasks) | ✅ Safe - Read-only |
| `ecs_troubleshooting_tool` | `fetch_service_events` | ✅ Safe - Read-only |
| `ecs_troubleshooting_tool` | `get_ecs_troubleshooting_guidance` | ✅ Safe - Read-only |
| `get_deployment_status` | Status checking | ✅ Safe - Read-only |

The following operations modify resources and should be used with extreme caution in production:

| Tool | Operation | Production Safety |
|------|-----------|-------------------|
| `create_ecs_infrastructure` | Creating resources | ⚠️ High Risk - Creates infrastructure |
| `delete_ecs_infrastructure` | Deleting resources | 🛑 Dangerous - Deletes infrastructure |
| `containerize_app` | Generate container configs | 🟡 Medium Risk - Local changes only |

### When to Consider Production Use

The ECS MCP Server may be appropriate for production environments in the following scenarios:

1. **Read-only monitoring**: Using resource management tools with read-only IAM policies
2. **Troubleshooting non-critical issues**: Using diagnostic tools to gather logs and status information
3. **Sandbox or isolated environments**: Using deployment tools in production-like environments that are isolated from core services

### When to Avoid Production Use

Avoid using ECS MCP Server in production for:

1. Critical business infrastructure
2. Applications handling sensitive customer data
3. High-throughput or high-availability services
4. Regulated workloads with compliance requirements
5. Infrastructure lacking proper backup and disaster recovery procedures

## Configuration

Add the ECS MCP Server to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ecs-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile", // Optional - uses your local AWS configuration if not specified
        "AWS_REGION": "your-aws-region", // Optional - uses your local AWS configuration if not specified
        "FASTMCP_LOG_LEVEL": "ERROR",
        "FASTMCP_LOG_FILE": "/path/to/ecs-mcp-server.log",
        "ALLOW_WRITE": "false",
        "ALLOW_SENSITIVE_DATA": "false"
      }
    }
  }
}
```

If running from a local repository, configure the MCP client like this:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server",
        "run",
        "main.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "your-aws-region",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "FASTMCP_LOG_FILE": "/path/to/ecs-mcp-server.log",
        "ALLOW_WRITE": "false",
        "ALLOW_SENSITIVE_DATA": "false"
      }
    }
  }
}
```

## Security Controls

The ECS MCP Server includes security controls in your MCP client configuration to prevent accidental changes to infrastructure and limit access to sensitive data:

### ALLOW_WRITE

Controls whether write operations (creating or deleting infrastructure) are allowed.

```bash
# Enable write operations
"ALLOW_WRITE": "true"

# Disable write operations (default)
"ALLOW_WRITE": "false"
```

### ALLOW_SENSITIVE_DATA

Controls whether tools that return logs and detailed resource information are allowed.

```bash
# Enable access to sensitive data
"ALLOW_SENSITIVE_DATA": "true"

# Disable access to sensitive data (default)
"ALLOW_SENSITIVE_DATA": "false"
```

### IAM Best Practices

We strongly recommend creating dedicated IAM roles with least-privilege permissions when using the ECS MCP Server:

1. **Create a dedicated IAM role** specifically for ECS MCP Server operations
2. **Apply least-privilege permissions** by attaching only the necessary policies based on your use case
3. **Use scoped-down resource policies** whenever possible
4. **Apply a permission boundary** to limit the maximum permissions

For detailed example IAM policies tailored for different ECS MCP Server use cases (read-only monitoring, troubleshooting, deployment, and service-specific access), see [EXAMPLE_IAM_POLICIES.md](EXAMPLE_IAM_POLICIES.md).


## MCP Tools

### Deployment Tools

These tools help you containerize applications and deploy them to Amazon ECS with proper infrastructure setup and monitoring.

- **containerize_app**: Generates Dockerfile and container configurations for web applications
- **create_ecs_infrastructure**: Creates AWS infrastructure needed to deploy your containerized application using ECS. This includes:
  - Application Load Balancer (ALB) with public-facing endpoints
  - Network security groups with appropriate inbound/outbound rules
  - IAM roles and policies with least-privilege permissions
  - VPC configurations with public and private subnets (if needed)
  - S3 Gateway endpoint associations for ECR image pulls
  - ECS cluster with capacity provider settings
  - Task definition with CPU/memory allocations and container configs
  - Service configuration with desired count and auto-scaling policies
  - Health check configuration and deployment circuit breakers
- **get_deployment_status**: Gets the status of an ECS deployment and returns the ALB URL
- **delete_ecs_infrastructure**: Deletes the AWS infrastructure created by the ECS MCP Server

### Troubleshooting Tool

The troubleshooting tool helps diagnose and resolve common ECS deployment issues stemming from infrastructure, service, task, and network configuration.

- **ecs_troubleshooting_tool**: Consolidated tool with the following actions:
  - **get_ecs_troubleshooting_guidance**: Initial assessment and troubleshooting path recommendation
  - **fetch_cloudformation_status**: Infrastructure-level diagnostics for CloudFormation stacks
  - **fetch_service_events**: Service-level diagnostics for ECS services
  - **fetch_task_failures**: Task-level diagnostics for ECS task failures
  - **fetch_task_logs**: Application-level diagnostics through CloudWatch logs
  - **detect_image_pull_failures**: Specialized tool for detecting container image pull failures
  - **fetch_network_configuration**: Network-level diagnostics for ECS deployments including VPC, subnets, security groups, and load balancers

### Resource Management

This tool provides read-only access to Amazon ECS resources to help you monitor and understand your deployment environment.

- **ecs_resource_management**: List and describe ECS resources including:
  - Clusters: List all clusters, describe specific cluster details
  - Services: List services in a cluster, describe service configuration
  - Tasks: List running or stopped tasks, describe task details and status
  - Task Definitions: List task definition families, describe specific task definition revisions
  - Container Instances: List container instances, describe instance health and capacity
  - Capacity Providers: List and describe capacity providers associated with clusters
  - ECR repositories and container images

## Example Prompts

### Containerization and Deployment

- "Containerize this Node.js app and deploy it to AWS"
- "Deploy this Flask application to Amazon ECS"
- "Create an ECS deployment for this web application with auto-scaling"
- "Set up a containerized environment for this Django app on Amazon ECS"
- "List all my ECS clusters"
- "Show me details for my-cluster"

### Troubleshooting

- "Help me troubleshoot my ECS deployment"
- "My ECS tasks keep failing, can you diagnose the issue?"
- "The ALB health check is failing for my ECS service"
- "Why can't I access my deployed application?"
- "Check what's wrong with my CloudFormation stack"

### Resource Management

- "Show me my ECS clusters"
- "List all running tasks in my ECS cluster"
- "Describe my ECS service configuration"
- "Get information about my task definition"

## Requirements

- Python 3.10+
- AWS credentials with permissions for ECS, ECR, CloudFormation, and related services
- Docker (for local containerization testing)

## License

This project is licensed under the Apache-2.0 License.
