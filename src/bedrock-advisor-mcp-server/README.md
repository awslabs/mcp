# Amazon Bedrock Advisor MCP Server

An AWS Labs Model Context Protocol (MCP) server that provides intelligent recommendations for Amazon Bedrock foundation models. This server helps you discover, compare, and select the most suitable Bedrock models for your specific use cases.

## Features

- **Intelligent Model Recommendations**: Get personalized model suggestions based on your requirements
- **Comprehensive Model Information**: Access detailed specs, capabilities, pricing, and availability
- **Model Comparison**: Compare multiple models side-by-side across various dimensions
- **Cost Analysis**: Estimate costs and get optimization recommendations
- **Availability Checking**: Verify model availability across AWS regions
- **Search & Discovery**: Find models using natural language queries
- **Real-time Data**: Uses live AWS Bedrock API data for up-to-date information

## Available Tools

### Core Recommendation Tools
- `recommend_model` - Get intelligent model recommendations based on criteria
- `get_model_info` - Get detailed information about a specific model

### Discovery & Search Tools
- `list_models` - List all available models with optional filtering
- `search_models` - Search models using natural language queries
- `get_models_by_provider` - Get all models from a specific provider
- `get_models_by_capabilities` - Find models matching specific capabilities

### Comparison Tools
- `compare_models` - Compare multiple models side-by-side
- `compare_model_availability` - Compare availability across regions

### Cost Analysis Tools
- `estimate_cost` - Estimate costs for specific usage patterns
- `compare_costs` - Compare costs across multiple models

### Availability Tools
- `check_model_availability` - Check model availability in regions
- `check_region_availability` - Check what models are available in a region
- `get_supported_regions` - Get all Bedrock-supported regions

### Data Management Tools
- `refresh_model_data` - Refresh data from AWS Bedrock API
- `get_data_status` - Get current data status and freshness

## Installation

```bash
# Install using uv
uv add awslabs.bedrock-advisor-mcp-server

# Or install using pip
pip install awslabs.bedrock-advisor-mcp-server
```

## Configuration

### AWS Credentials

The server requires AWS credentials to access the Bedrock API. Configure your credentials using one of these methods:

```bash
# Using AWS CLI
aws configure

# Using environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### MCP Configuration

Add the server to your MCP client configuration:

```json
{
  "mcpServers": {
    "bedrock-advisor": {
      "command": "bedrock-advisor-mcp-server",
      "args": []
    }
  }
}
```

## Usage Examples

### Get Model Recommendations

```python
# Get recommendations for code generation
recommend_model(
    use_case={"primary": "code-generation", "complexity": "moderate"},
    performance_requirements={"accuracy_priority": "high"},
    cost_constraints={"budget_priority": "medium"}
)
```

### Compare Models

```python
# Compare Claude and Nova models
compare_models(
    model_ids=[
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "amazon.nova-premier-v1:0"
    ],
    include_detailed_analysis=True
)
```

### Estimate Costs

```python
# Estimate monthly costs
estimate_cost(
    model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
    usage={
        "expected_requests_per_month": 10000,
        "avg_input_tokens": 500,
        "avg_output_tokens": 200
    }
)
```

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- AWS CLI configured with appropriate permissions

### Setup

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/bedrock-advisor-mcp-server

# Install dependencies
uv sync --all-groups

# Run tests
uv run pytest

# Run the server
uv run bedrock-advisor-mcp-server
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.bedrock_advisor_mcp_server

# Run specific test file
uv run pytest tests/unit/test_server.py
```

## AWS Permissions

The server requires the following AWS permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel",
                "bedrock:ListModelCustomizationJobs",
                "pricing:GetProducts"
            ],
            "Resource": "*"
        }
    ]
}
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For support, please:
1. Check the [documentation](https://awslabs.github.io/mcp/)
2. Search existing [issues](https://github.com/awslabs/mcp/issues)
3. Create a new issue if needed

## Related Projects

- [AWS CDK MCP Server](../cdk-mcp-server/) - AWS CDK infrastructure management
- [AWS Cost Analysis MCP Server](../cost-analysis-mcp-server/) - AWS cost analysis and optimization
- [AWS Documentation MCP Server](../aws-documentation-mcp-server/) - AWS documentation search and retrieval
