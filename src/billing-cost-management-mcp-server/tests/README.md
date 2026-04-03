# AWS Billing and Cost Management MCP Server Tests

This directory contains integration tests for the AWS Billing and Cost Management MCP Server. The tests validate that each tool exposed by the server works correctly by making actual AWS API calls.

## Test Structure

The test suite is organized into the following files:

1. **Core Components**
   - `test_boto3_registry.py` - Tests for the `Boto3ToolRegistry` class
   - `test_server.py` - Tests for the server module and tool function creation

2. **AWS Services**
   - `test_cost_optimization_hub.py` - Tests for Cost Optimization Hub tools
   - `test_compute_optimizer.py` - Tests for Compute Optimizer tools
   - `test_cost_explorer.py` - Tests for Cost Explorer tools

3. **Test Configuration**
   - `conftest.py` - Pytest fixtures and configuration

## Running the Tests

First, install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Next, create a `.env` file in the root directory of the project. You can use the `.env.example` file as a template:

```bash
cp .env.example .env
```

Then edit the `.env` file to include your specific configuration. This file is required for both unit and integration tests.

Now, run the tests using pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests for a specific service
pytest tests/test_cost_explorer.py

# Run with code coverage report
pytest --cov=.

# Run a specific test function
pytest tests/test_cost_explorer.py::test_cost_explorer_get_cost_and_usage
```

## AWS Credentials

These tests make actual AWS API calls, so you need to have valid AWS credentials configured. The tests will use the default credentials from your environment.

If you don't have the necessary permissions for certain AWS services, the tests will be skipped with a message indicating the missing permissions.

## Test Coverage

The integration tests cover all tools exposed by the server, including:

1. **Cost Optimization Hub (cost-optimization-hub)**
   - get_recommendation
   - list_recommendations
   - list_recommendation_summaries

2. **Compute Optimizer (compute-optimizer)**
   - get_auto_scaling_group_recommendations
   - get_ebs_volume_recommendations
   - get_ec2_instance_recommendations
   - get_ecs_service_recommendations
   - get_rds_database_recommendations
   - get_lambda_function_recommendations
   - get_idle_recommendations
   - get_effective_recommendation_preferences

3. **Cost Explorer (ce)**
   - get_cost_and_usage
   - get_savings_plans_purchase_recommendation
   - get_reservation_purchase_recommendation

## Test Design

The tests are designed to be non-destructive and read-only. They only retrieve data from AWS services and do not create, modify, or delete any resources.

For tests that require specific resource IDs (like `get_recommendation` or `get_effective_recommendation_preferences`), the tests first call a list operation to find valid IDs to use in the test.

If no resources are available for testing, or if the AWS credentials don't have the necessary permissions, the tests will be skipped rather than failing.

## Test Markers

The tests are marked with the following markers:

- `unit`: Tests that don't make external API calls
- `integration`: Tests that make actual AWS API calls

## Adding New Tests

To add tests for new tools:

1. Identify which service file the test belongs in, or create a new file if needed
2. Create a new test function with the `@pytest.mark.integration` decorator
3. Use the `tool_function_factory` fixture to create the tool function
4. Call the function with appropriate parameters
5. Verify the response structure
6. Handle potential permission errors with try/except
