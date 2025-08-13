# AWS CI/CD MCP Server

An MCP server for AWS CI/CD services including CodePipeline, CodeBuild, and CodeDeploy operations with security best practices and compliance.

## Features

- **CodePipeline**: Pipeline management, execution control, and monitoring
- **CodeBuild**: Project management, build execution, and log access  
- **CodeDeploy**: Application deployment and monitoring
- **Security**: Read-only mode by default, comprehensive error handling
- **Compliance**: Follows AWS best practices and security guidelines

## Installation

```bash
uvx awslabs.aws-cicd-mcp-server@latest
```

## Configuration

Set environment variables:
- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_PROFILE`: AWS profile to use
- `CICD_READ_ONLY_MODE`: Enable read-only mode (default: true)
- `FASTMCP_LOG_LEVEL`: Logging level (default: INFO)

## Available Tools

### CodePipeline
- `list_pipelines`: List all pipelines in a region
- `get_pipeline_details`: Get detailed pipeline information
- `start_pipeline_execution`: Start pipeline execution (requires write mode)
- `get_pipeline_execution_history`: Get execution history
- `create_pipeline`: Create a new pipeline (requires write mode)
- `update_pipeline`: Update existing pipeline (requires write mode)
- `delete_pipeline`: Delete a pipeline (requires write mode)

### CodeBuild
- `list_projects`: List all CodeBuild projects
- `get_project_details`: Get detailed project information
- `start_build`: Start a build (requires write mode)
- `get_build_logs`: Get build logs and status
- `create_project`: Create a new project (requires write mode)
- `update_project`: Update existing project (requires write mode)
- `delete_project`: Delete a project (requires write mode)

### CodeDeploy
- `list_applications`: List all CodeDeploy applications
- `get_application_details`: Get detailed application information
- `list_deployment_groups`: List deployment groups for an application
- `create_deployment`: Create a new deployment (requires write mode)
- `get_deployment_status`: Get deployment status and details
- `create_application`: Create a new application (requires write mode)
- `create_deployment_group`: Create a deployment group (requires write mode)
- `delete_application`: Delete an application (requires write mode)

## Security

- Read-only mode enabled by default
- Comprehensive error handling and logging
- AWS IAM permissions required for respective services
- Input validation with Pydantic models

## License

Apache-2.0
