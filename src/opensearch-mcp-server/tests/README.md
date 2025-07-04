# Tests for Amazon OpenSearch Managed/Serverless/Ingestion MCP Server

This directory contains tests for the Amazon OpenSearch Managed/Serverless/Ingestion MCP Server.

## Running Tests

To run the tests, use the following command from the root directory of the project:

```bash
pytest tests/
```

For more verbose output:

```bash
pytest -v tests/
```

For coverage information:

```bash
pytest --cov=awslabs.opensearch_mcp_server tests/
```

## Test Structure

- `test_server.py`: Tests for the server functionality.
