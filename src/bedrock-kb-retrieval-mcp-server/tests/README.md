# Bedrock Knowledge Base Retrieval MCP Server Tests

This directory contains tests for the Bedrock Knowledge Base Retrieval MCP Server.

## Test Structure

The tests are organized as follows:

- `conftest.py`: Contains pytest fixtures used across multiple test files
- `test_models.py`: Tests for the data models
- `test_clients.py`: Tests for the AWS client initialization functions
- `test_discovery.py`: Tests for the knowledge base discovery functionality
- `test_runtime.py`: Tests for the knowledge base query functionality
- `test_server.py`: Tests for the MCP server functionality

## Running Tests

To run the tests, you can use the following command from the root of the repository:

```bash
cd mcp/src/bedrock-kb-retrieval-mcp-server
pytest tests/
```

To run a specific test file:

```bash
pytest tests/test_models.py
```

To run a specific test:

```bash
pytest tests/test_models.py::TestDataSource::test_data_source_creation
```

## Test Coverage

To run the tests with coverage:

```bash
pytest --cov=awslabs.bedrock_kb_retrieval_mcp_server tests/
```

To generate a coverage report:

```bash
pytest --cov=awslabs.bedrock_kb_retrieval_mcp_server --cov-report=html tests/
```

This will generate a coverage report in the `htmlcov` directory.

## Mocking

The tests use mocking to avoid making actual AWS API calls. The mocks are defined in `conftest.py` and include:

- `mock_bedrock_agent_runtime_client`: A mock for the Bedrock Agent Runtime client
- `mock_bedrock_agent_client`: A mock for the Bedrock Agent client
- `mock_boto3`: A mock for the boto3 module

These mocks are used to simulate the behavior of the AWS services without making actual API calls.
