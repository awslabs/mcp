# Agent Tool Testing with DeepEval

This module provides utilities for testing agents using DeepEval's tool correctness metrics.

## Overview

The tool testing framework allows you to:

1. Define test cases with expected tool calls
2. Run the agent against these test cases
3. Verify that the correct tools were called
4. Get metrics and insights about tool usage correctness

## Components

* `agent_tool_test.py`: Core testing functionality
* `agent_test_dataset.py`: Dataset management for test cases
* `agent_test_harness.py`: Test harness for running agents with MCP
* `tests/test_agent_tools.py`: Pytest integration
* `examples/agent_test_cases.yaml`: Example test cases

## Usage

### Basic Usage

```python
from awslabs.agent_test.agent_tool_test import AgentToolTest

# Configure agent test
test = AgentToolTest(
    mcp_args=["awslabs.mcp-server"],
    mcp_env={"AWS_REGION": "us-west-2"},
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    region_name="us-west-2"
)

# Run a test
result = test.run_test(
    prompt="What's the weather in Seattle?",
    expected_tools=["get_weather"]
)

print(f"Score: {result['score']}")
print(f"Reason: {result['reason']}")
```

### Using Test Cases from YAML/JSON

```python
from awslabs.agent_test.agent_test_dataset import AgentEvaluationDataset
from awslabs.agent_test.agent_tool_test import AgentToolTest
import asyncio

# Load test cases
dataset = AgentEvaluationDataset.from_yaml("tests/test_cases.yaml")

# Configure agent test
test = AgentToolTest(
    mcp_args=["awslabs.mcp-server"],
    mcp_env={"AWS_REGION": "us-west-2"},
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    region_name="us-west-2"
)

# Run tests
async def run_tests():
    results = []
    for test_case in dataset:
        test_result = await test.create_test_case(
            prompt=test_case.input,
            expected_tools=test_case.expected_tools
        )
        results.append(test_result)
    return results

results = asyncio.run(run_tests())
```

## Integration with pytest

To run tests using pytest and DeepEval's test runner:

```bash
# Install DeepEval
pip install deepeval

# Run tests using pytest directly
pytest tests/test_agent_tools.py
```

You can set environment variables to configure the tests:

* `AGENT_TEST_DATASET`: Path to a YAML or JSON test case file
* `AGENT_TEST_MODEL_ID`: Bedrock model ID to use
* `AGENT_TEST_REGION`: AWS region for Bedrock
* `AGENT_TEST_MCP_SERVER`: MCP server to use for tests

## Creating Test Cases

Test cases can be defined in YAML or JSON format. Each test case should include:

```yaml
- input: "What's the weather in San Francisco?"  # The prompt to send to the agent
  expected_tools: ["get_weather"]                # List of tool names that should be called
  description: "Weather query test"              # Optional description
```

See `examples/agent_test_cases.yaml` for more examples.
