# Integration Tests

This directory contains integration and manual tests that are not meant to be run in CI/CD pipelines.

## Agent Tool Tests

The tests in this directory use the `AgentToolTest` class to test agent tool usage with DeepEval.
These tests:

- Require specific AWS credentials and configuration
- May incur costs from API calls to Bedrock or other services
- Are suited for manual execution during development and testing

## Running the Tests

To run these integration tests manually, use:

```bash
./run_tests.sh --integ
```

This will run the tests in this directory separately from the standard unit tests.
