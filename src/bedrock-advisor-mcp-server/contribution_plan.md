# Contribution Plan for AWS Labs MCP Repository

## Project Overview

The goal is to contribute to the [awslabs/mcp](https://github.com/awslabs/mcp) repository by enhancing the Bedrock Advisor MCP Server. This server provides intelligent recommendations for Amazon Bedrock foundation models based on specific use case requirements.

## Understanding the Repository Structure

The awslabs/mcp repository follows a specific structure for MCP servers:

```
src/
└── server-name-mcp-server/
    ├── awslabs/
    │   └── server_name_mcp_server/
    │       ├── __init__.py
    │       ├── server.py
    │       ├── models/
    │       ├── services/
    │       └── utils/
    ├── pyproject.toml
    ├── README.md
    └── tests/
```

## Contribution Approach

### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub
git clone https://github.com/your-username/mcp.git
cd mcp
```

### 2. Create a New Branch

```bash
git checkout -b feature/bedrock-advisor-enhancement
```

### 3. Understand the Existing Implementation

- Review the existing Bedrock Advisor MCP Server code
- Understand the MCP protocol and how it's implemented
- Identify areas for improvement or new features

### 4. Implement Enhancements

Potential enhancements to consider:

1. **Model Compatibility Feature**

   - Add a new tool to check compatibility between different Bedrock models
   - Help users understand which models can be used interchangeably
   - Provide guidance on migrating between models

2. **Enhanced Cost Estimation**

   - Improve the existing cost estimation tool with more detailed breakdowns
   - Add support for comparing costs across similar models
   - Provide more optimization recommendations

3. **Use Case Templates**
   - Add pre-configured templates for common use cases
   - Include recommended models, configurations, and sample prompts

### 5. Add Tests

- Write unit tests for new functionality
- Ensure existing tests pass with the changes
- Add integration tests if necessary

### 6. Update Documentation

- Update the README.md with new features
- Add examples for new tools
- Update any relevant documentation

### 7. Prepare the Pull Request

- Ensure code meets project standards (ruff, pyright, etc.)
- Write a clear PR description explaining the changes
- Reference any related issues

## Development Environment Setup

1. **Create a virtual environment**:

```bash
cd src/bedrock-advisor-mcp-server
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install development dependencies**:

```bash
uv pip install -e ".[dev]"
```

3. **Install pre-commit hooks**:

```bash
pre-commit install
```

## Testing

1. **Run unit tests**:

```bash
pytest
```

2. **Test with an MCP client**:

Configure the MCP server in your MCP client configuration:

```json
{
  "mcpServers": {
    "bedrock-advisor": {
      "command": "python",
      "args": ["-m", "awslabs.bedrock_advisor_mcp_server"],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": ["list_models", "get_model_info"]
    }
  }
}
```

## Next Steps

1. Choose a specific enhancement to implement
2. Set up the development environment
3. Implement the enhancement
4. Add tests
5. Update documentation
6. Submit the PR
