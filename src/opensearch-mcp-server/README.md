# AWS Labs opensearch MCP Server

An AWS Labs Model Context Protocol (MCP) server for opensearch.

## Instructions

Instructions for using this opensearch MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.

## Installation

```bash
# Install using uv (recommended)
uv tool install awslabs.opensearch-mcp-server

# Or install using pip
pip install awslabs.opensearch-mcp-server
```


## Amazon Q

Example for Amazon Q Developer CLI (~/.aws/amazonq/mcp.json):

```json
{
  "mcpServers": {
    "awslabs.opensearch-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.opensearch-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[The AWS region to run in]",
      },
      "transportType": "stdio"
    }
  }
}
```

## Development

### Running Tests
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=awslabs.opensearch_mcp_server
```

### Local Development
```bash
# Install in development mode
uv pip install -e .

# Run the server directly
python -m awslabs.opensearch_mcp_server.server
```

## Contributing

Contributions are welcome! Please see the main repository's [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [AWS OpenSearch documentation](https://docs.aws.amazon.com/opensearch-service/?icmpid=docs_homepage_analytics)
2. Review the [MCP specification](https://modelcontextprotocol.io/)
3. Open an issue in the [GitHub repository](https://github.com/awslabs/mcp)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
