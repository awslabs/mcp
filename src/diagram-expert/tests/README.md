# Diagram Expert MCP Server Tests

This directory contains tests for the diagram-expert MCP server. The tests are organized by module and cover all aspects of the server's functionality.

## Test Structure

- `test_models.py`: Tests for the data models used by the server
- `test_scanner.py`: Tests for the code scanning functionality
- `test_diagrams.py`: Tests for the diagram generation functionality
- `test_server.py`: Tests for the MCP server tools

## Running the Tests

To run the tests, use the following command from the root directory of the project:

```bash
pytest -xvs src/diagram-expert/tests/
```

To run a specific test file:

```bash
pytest -xvs src/diagram-expert/tests/test_models.py
```

To run a specific test class:

```bash
pytest -xvs src/diagram-expert/tests/test_models.py::TestDiagramType
```

To run a specific test:

```bash
pytest -xvs src/diagram-expert/tests/test_models.py::TestDiagramType::test_diagram_type_values
```

## Test Coverage

To generate a test coverage report, use the following command:

```bash
pytest --cov=ai3_diagrams_expert src/diagram-expert/tests/
```

For a more detailed HTML coverage report:

```bash
pytest --cov=ai3_diagrams_expert --cov-report=html src/diagram-expert/tests/
```

This will generate a coverage report in the `htmlcov` directory. Open `htmlcov/index.html` in a web browser to view the report.

## Test Dependencies

The tests require the following dependencies:

- pytest
- pytest-asyncio
- pytest-cov (for coverage reports)

These dependencies are included in the project's development dependencies.

## Test Fixtures

The test fixtures are defined in `conftest.py` and include:

- `temp_workspace_dir`: A temporary directory for diagram output
- `aws_diagram_code`: Example AWS diagram code
- `sequence_diagram_code`: Example sequence diagram code
- `flow_diagram_code`: Example flow diagram code
- `invalid_diagram_code`: Invalid diagram code
- `dangerous_diagram_code`: Diagram code with dangerous functions
- `example_diagrams`: A dictionary of example diagrams for different types

## Adding New Tests

When adding new tests, follow these guidelines:

1. Place tests in the appropriate file based on the module being tested
2. Use descriptive test names that clearly indicate what is being tested
3. Use pytest fixtures for common setup and teardown
4. Use pytest.mark.asyncio for async tests
5. Use mocks for external dependencies
6. Add docstrings to test classes and methods
