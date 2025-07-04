# Tests for Amazon SNS and SQS MCP Server

This directory contains tests for the Amazon SNS and SQS MCP Server.

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
pytest --cov=awslabs.amazon_sns_sqs_mcp_server tests/
```

## Test Structure

- `test_server.py`: Tests for the server functionality, including SNS and SQS tool overrides and validators.
