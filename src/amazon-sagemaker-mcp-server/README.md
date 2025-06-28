# Amazon SageMaker MCP Server

## Overview

The Amazon SageMaker Model Context Protocol (MCP) Server is an open-source tool that provides AI assistants with comprehensive access to Amazon SageMaker's machine learning capabilities. This server enables seamless integration between AI coding assistants and SageMaker services, allowing developers to build, train, deploy, and manage machine learning models through natural language interactions.

Key benefits of the SageMaker MCP Server include:

- **Complete ML Lifecycle Management**: Provides tools for the entire machine learning workflow from data preparation to model deployment and monitoring.
- **AI-powered ML Development**: Offers contextual guidance and best practices for machine learning development on AWS.
- **Comprehensive SageMaker Integration**: Supports endpoints, training jobs, processing jobs, AutoML, Feature Store, Pipelines, Studio, and more.
- **Security-first Approach**: Implements built-in guardrails with read-only defaults and controlled access to sensitive operations.
- **Operational Excellence**: Includes monitoring, logging, and troubleshooting capabilities for production ML workloads.

## Features

The SageMaker MCP server provides tools and resources organized into several categories:

### 1. Model Deployment & Inference
- **Endpoint Management**: Create, update, delete, and invoke SageMaker endpoints
- **Model Management**: Create, describe, and manage SageMaker models
- **Real-time Inference**: Invoke endpoints for real-time predictions
- **Batch Transform**: Manage batch inference jobs

### 2. Model Training & Development
- **Training Jobs**: Create, monitor, and manage SageMaker training jobs
- **Processing Jobs**: Run data processing and feature engineering jobs
- **AutoML**: Automated machine learning with SageMaker Autopilot
- **Hyperparameter Tuning**: Optimize model hyperparameters

### 3. Feature Store & Data Management
- **Feature Groups**: Create and manage feature groups in SageMaker Feature Store
- **Feature Ingestion**: Put and get records from feature groups
- **Data Lineage**: Track data lineage and feature transformations

### 4. ML Pipelines & Workflows
- **Pipeline Management**: Create, execute, and monitor SageMaker Pipelines
- **Workflow Orchestration**: Manage complex ML workflows
- **Pipeline Execution**: Start, stop, and monitor pipeline executions

### 5. Development Environment
- **SageMaker Studio**: Manage Studio domains and user profiles
- **Notebook Instances**: Create and manage SageMaker notebook instances
- **Development Tools**: Access to SageMaker's integrated development environment

### 6. Monitoring & Operations
- **Model Monitoring**: Monitor model performance and data drift
- **Metrics & Logging**: Access CloudWatch metrics and logs
- **Quality Monitoring**: Set up model quality monitoring jobs

### 7. Guidance & Best Practices
- **ML Workflow Guidance**: Get recommendations for ML workflows
- **Instance Recommendations**: Get optimal instance type recommendations
- **Best Practices**: Access to SageMaker best practices and patterns

## Prerequisites

- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
- Appropriate IAM permissions for SageMaker operations

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.amazon-sagemaker-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXNhZ2VtYWtlci1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)

You can download the Amazon SageMaker MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Q Developer, Cursor, or Cline.

Add the following code to your MCP client configuration. The SageMaker MCP server uses the default AWS profile by default. Specify a value in AWS_PROFILE if you want to use a different profile. Similarly, adjust the AWS Region and log level values as needed.

```json
{
  "mcpServers": {
    "awslabs.amazon-sagemaker-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.amazon-sagemaker-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "SAGEMAKER_EXECUTION_ROLE": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using temporary credentials

```json
{
  "mcpServers": {
    "awslabs.amazon-sagemaker-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.amazon-sagemaker-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
        "AWS_SESSION_TOKEN": "your-session-token",
        "AWS_REGION": "us-east-1",
        "SAGEMAKER_EXECUTION_ROLE": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration Options

### `--allow-write`
Enables write access mode, which allows mutating operations and creation of resources. By default, the server runs in read-only mode, which restricts operations to only perform read actions, preventing any changes to AWS resources.

Write operations include:
- Creating, updating, and deleting SageMaker endpoints
- Starting and stopping training jobs
- Creating and managing models
- Managing Feature Store feature groups
- Creating and executing pipelines
- Creating and deleting Studio Space apps
- Starting and stopping notebook instances

### `--allow-sensitive-data-access`
Enables access to sensitive data operations, such as:
- Invoking SageMaker endpoints and accessing inference results
- Accessing training job logs and metrics
- Retrieving feature data from Feature Store

## Environment Variables

- `AWS_PROFILE`: AWS profile to use (default: default)
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key ID (for temporary credentials)
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key (for temporary credentials)
- `AWS_SESSION_TOKEN`: AWS session token (for temporary credentials)
- `SAGEMAKER_EXECUTION_ROLE`: Default SageMaker execution role ARN
- `FASTMCP_LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)

## Available Tools

### Endpoint Management
- `list_sm_endpoints`: List all endpoints
- `describe_sm_endpoint`: Get detailed endpoint information
- `invoke_sm_endpoint`: Invoke an endpoint for inference

### Studio & Development
- `list_sm_domains`: List all Studio domains
- `describe_sm_domain`: Get detailed domain information
- `list_sm_space_apps`: List all Studio Space apps with filtering and sorting
- `create_sm_space_app`: Create a new Studio Space app
- `delete_sm_space_app`: Stop/Delete a Studio Space app

### Notebook Instances
- `list_sm_nb_instances`: List all notebook instances
- `describe_sm_nb_instance`: Get detailed notebook instance information
- `start_sm_nb_instance`: Start a notebook instance
- `stop_sm_nb_instance`: Stop a notebook instance

## Available Resources

The server provides access to various SageMaker resources through URI patterns:

- `sagemaker://endpoints` - List of all endpoints
- `sagemaker://endpoints/{endpoint_name}` - Specific endpoint details
- `sagemaker://models` - List of all models
- `sagemaker://models/{model_name}` - Specific model details
- `sagemaker://training-jobs` - List of all training jobs
- `sagemaker://training-jobs/{job_name}` - Specific training job details
- `sagemaker://processing-jobs` - List of all processing jobs
- `sagemaker://processing-jobs/{job_name}` - Specific processing job details
- `sagemaker://automl-jobs` - List of all AutoML jobs
- `sagemaker://automl-jobs/{job_name}` - Specific AutoML job details
- `sagemaker://feature-groups` - List of all feature groups
- `sagemaker://feature-groups/{feature_group_name}` - Specific feature group details
- `sagemaker://pipelines` - List of all pipelines
- `sagemaker://pipelines/{pipeline_name}` - Specific pipeline details
- `sagemaker://domains` - List of all Studio domains
- `sagemaker://domains/{domain_id}` - Specific domain details
- `sagemaker://space-apps` - List of all Studio Space apps
- `sagemaker://space-apps/{domain_id}/{space_name}/{app_type}/{app_name}` - Specific Space app details
- `sagemaker://notebook-instances` - List of all notebook instances
- `sagemaker://notebook-instances/{instance_name}` - Specific notebook instance details

## Usage Examples

### Creating and Deploying a Model

```
Using the SageMaker MCP server, help me:
1. Create a model using a pre-trained container
2. Create an endpoint configuration
3. Deploy the model to an endpoint
4. Test the endpoint with sample data
```

### Training a Custom Model

```
Using the SageMaker MCP server, help me:
1. Create a training job using my custom algorithm
2. Monitor the training progress
3. Create a model from the training artifacts
4. Deploy the trained model to an endpoint
```

### Setting up AutoML

```
Using the SageMaker MCP server, help me:
1. Create an AutoML job for my dataset
2. Monitor the AutoML job progress
3. Deploy the best model from AutoML
4. Get predictions from the deployed model
```

### Managing Feature Store

```
Using the SageMaker MCP server, help me:
1. Create a feature group for my ML features
2. Ingest data into the feature group
3. Retrieve features for training
4. Monitor feature group usage
```

### Managing Studio Space Apps

```
Using the SageMaker MCP server, help me:
1. List all my Studio Space apps
2. Create a new JupyterLab app in a specific space
3. Monitor the app status
4. Stop the app when finished
```

## IAM Permissions

The SageMaker MCP server requires appropriate IAM permissions to access SageMaker services. Here's a sample IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:*",
        "iam:PassRole",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "logs:GetLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Considerations

- The server runs in read-only mode by default to prevent accidental modifications
- Write operations require explicit `--allow-write` flag
- Sensitive data access requires explicit `--allow-sensitive-data-access` flag
- All AWS API calls use the configured AWS credentials and respect IAM permissions
- Endpoint invocations and sensitive data are only accessible with appropriate flags

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure AWS credentials are properly configured
2. **Permission Denied**: Check IAM permissions for SageMaker operations
3. **Region Mismatch**: Ensure AWS_REGION matches your SageMaker resources
4. **Execution Role**: Set SAGEMAKER_EXECUTION_ROLE for operations requiring it

### Debug Mode

Enable debug logging by setting:
```bash
export FASTMCP_LOG_LEVEL=DEBUG
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](../../CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](../../LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in the [GitHub repository](https://github.com/awslabs/mcp/issues)
- Check the [AWS SageMaker documentation](https://docs.aws.amazon.com/sagemaker/)
- Review the [MCP specification](https://modelcontextprotocol.io/)
