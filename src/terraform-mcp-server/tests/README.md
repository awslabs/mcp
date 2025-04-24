# Terraform MCP Server Tests

This directory contains tests for the Terraform MCP Server.

## Test Structure

The tests are organized as follows:

- `conftest.py`: Contains pytest fixtures used across multiple test files
- `test_models.py`: Tests for the data models
- `test_server.py`: Tests for the MCP server functionality
- `test_command_impl.py`: Tests for the Terraform command execution implementation
- `test_execute_terraform_command.py`: Dedicated tests for the execute_terraform_command implementation
- `test_run_checkov_scan.py`: Dedicated tests for the run_checkov_scan implementation
- `test_search_user_provided_module.py`: Dedicated tests for the search_user_provided_module implementation
- `test_resources.py`: Tests for the resource implementations
- `test_tool_implementations.py`: Tests for the tool implementations
- `test_utils.py` and `test_utils_additional.py`: Tests for utility functions
- `test_parameter_annotations.py`: Tests for parameter annotations

## Running Tests

To run the tests, you can use the following command from the root of the repository:

```bash
cd mcp/src/terraform-mcp-server
pytest tests/
```

Or use the provided script:

```bash
cd mcp/src/terraform-mcp-server
./run_tests.sh
```

To run a specific test file:

```bash
pytest tests/test_models.py
```

To run a specific test:

```bash
pytest tests/test_models.py::TestTerraformExecutionRequest::test_terraform_execution_request_creation
```

## Test Coverage

To run the tests with coverage:

```bash
./run_tests.sh --coverage
```

To generate a coverage report:

```bash
./run_tests.sh --coverage --report
```

This will generate a coverage report in the `htmlcov` directory.

## Verbose Output

To run the tests with verbose output:

```bash
./run_tests.sh --verbose
```

## Mocking

The tests use mocking to avoid making actual system calls. The mocks are defined in `conftest.py` and include:

- `mock_terraform_command_output`: Mock outputs for Terraform commands
- `mock_checkov_output`: Mock outputs for Checkov scans
- `mock_subprocess`: Mock for subprocess module
- `mock_os_path`: Mock for os.path module
- `mock_aws_provider_docs`: Mock AWS provider documentation data
- `mock_awscc_provider_docs`: Mock AWSCC provider documentation data
- `mock_aws_ia_modules`: Mock AWS-IA modules data

These mocks are used to simulate the behavior of the Terraform CLI, Checkov, and other external dependencies without making actual system calls.

## Test Files

### test_models.py

Tests for the data models used in the Terraform MCP server, including:

- `TerraformExecutionRequest`: Request model for Terraform command execution
- `TerraformExecutionResult`: Result model for Terraform command execution
- `CheckovScanRequest`: Request model for Checkov scan execution
- `CheckovScanResult`: Result model for Checkov scan execution
- `CheckovVulnerability`: Model for security vulnerabilities found by Checkov
- `TerraformAWSProviderDocsResult`: Model for AWS provider documentation results
- `TerraformAWSCCProviderDocsResult`: Model for AWSCC provider documentation results
- `ModuleSearchResult`: Model for Terraform module search results
- `SubmoduleInfo`: Model for Terraform submodule information
- `TerraformVariable`: Model for Terraform variable definitions
- `TerraformOutput`: Model for Terraform output definitions

### test_server.py

Tests for the MCP server functionality, including:

- Server initialization
- Tool registration
- Resource registration
- Command-line argument parsing

### test_command_impl.py

Tests for the Terraform command execution implementation, including:

- Successful command execution
- Error handling
- Security checks
- Output parsing

### test_resources.py

Tests for the resource implementations, including:

- AWS provider resources listing
- AWSCC provider resources listing
- Terraform development workflow guide
- AWS best practices

### test_tool_implementations.py

Tests for the tool implementations, including:

- AWS provider documentation search
- AWSCC provider documentation search
- AWS-IA modules search

### test_execute_terraform_command.py

Dedicated tests for the execute_terraform_command implementation, including:

- Testing the clean_output_text helper function
- Testing AWS region environment variable setting
- Testing exception handling
- Testing output error handling
- Testing JSON parsing error handling
- Testing complex output structures with nested values

### test_run_checkov_scan.py

Dedicated tests for the run_checkov_scan implementation, including:

- Testing the _clean_output_text function
- Testing JSON output parsing
- Testing with absolute and relative paths
- Testing security checks for dangerous patterns
- Testing CLI output parsing
- Testing error handling and exception handling

### test_search_user_provided_module.py

Dedicated tests for the search_user_provided_module implementation, including:

- Testing the parse_module_url function for different URL formats
- Testing the get_module_details function with successful responses
- Testing the get_module_details function with error responses
- Testing the search_user_provided_module_impl function with successful responses
- Testing the search_user_provided_module_impl function with registry prefix in URL
- Testing the search_user_provided_module_impl function with invalid URL
- Testing the search_user_provided_module_impl function when module is not found
- Testing the search_user_provided_module_impl function when an exception occurs
- Testing the extraction of outputs from README when not available in module details
- Testing the format_json helper function for serializing objects
