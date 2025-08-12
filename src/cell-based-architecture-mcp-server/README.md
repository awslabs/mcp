# Cell-Based Architecture MCP Server

An AWS Labs Model Context Protocol (MCP) server that provides expert guidance on cell-based architecture patterns based on the AWS Well-Architected whitepaper "Reducing the Scope of Impact with Cell-Based Architecture".

## Overview

This MCP server helps users understand and implement cell-based architecture patterns, from complete beginners to expert practitioners. Content is organized following the whitepaper's logical structure for progressive learning.

## Features

### Tools

- **query-cell-concepts**: Query cell-based architecture concepts with progressive complexity levels
- **get-implementation-guidance**: Get stage-specific implementation guidance following the whitepaper methodology
- **analyze-cell-design**: Analyze cell-based architecture designs and provide recommendations
- **validate-architecture**: Validate architecture against cell-based architecture principles

### Resources

- **cell-architecture-guide**: Complete guide organized by whitepaper sections
- **implementation-patterns**: Common implementation patterns and AWS service integration examples
- **best-practices**: Best practices and troubleshooting guidance

## Installation

### Using uv (recommended)

```bash
uv add awslabs.cell-based-architecture-mcp-server
```

### Using pip

```bash
pip install awslabs.cell-based-architecture-mcp-server
```

## Usage

### With MCP Client

Add to your MCP client configuration:

```json
{
  "awslabs.cell-based-architecture-mcp-server": {
    "command": "awslabs.cell-based-architecture-mcp-server",
    "env": {
      "FASTMCP_LOG_LEVEL": "INFO"
    }
  }
}
```

### Direct Usage

```bash
# Run the server directly
awslabs.cell-based-architecture-mcp-server

# With custom log level
FASTMCP_LOG_LEVEL=DEBUG awslabs.cell-based-architecture-mcp-server
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector awslabs.cell-based-architecture-mcp-server
```

## Examples

### Query Basic Concepts (Beginner)

```python
# Query basic cell-based architecture concepts
query_cell_concepts(
    concept="cell isolation",
    detail_level="beginner"
)
```

### Get Implementation Guidance

```python
# Get design stage guidance
get_implementation_guidance(
    stage="design",
    aws_services=["lambda", "dynamodb", "api-gateway"],
    experience_level="intermediate"
)
```

### Analyze Architecture Design

```python
# Analyze a cell design
analyze_cell_design(
    architecture_description="My system uses isolated Lambda functions with separate DynamoDB tables per customer segment",
    focus_areas=["isolation", "fault_tolerance"]
)
```

## Progressive Learning Path

The server supports users at different experience levels:

### Beginners
- Start with `query-cell-concepts` using `detail_level="beginner"`
- Focus on whitepaper sections: `introduction`, `shared_responsibility`, `what_is_cell_based`
- Use the `cell-architecture-guide` resource for foundational concepts

### Intermediate Users
- Use `get-implementation-guidance` for practical guidance
- Explore `implementation-patterns` resource for common patterns
- Focus on design and planning stages

### Expert Users
- Access advanced topics like cell sizing, placement, migration
- Use `analyze-cell-design` and `validate-architecture` tools
- Focus on operational aspects and best practices

## Environment Variables

- `FASTMCP_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

## Development

### Setup

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/cell-based-architecture-mcp-server
uv sync --all-groups
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov --cov-report=term-missing

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run awslabs/cell_based_architecture_mcp_server/server.py
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type checking
uv run pyright
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the AWS Labs MCP server patterns
4. Add tests for new functionality
5. Run the full test suite and code quality checks
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Related Resources

- [AWS Well-Architected Whitepaper: Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/reducing-scope-of-impact-with-cell-based-architecture.html)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [AWS Labs MCP Servers](https://github.com/awslabs/mcp)