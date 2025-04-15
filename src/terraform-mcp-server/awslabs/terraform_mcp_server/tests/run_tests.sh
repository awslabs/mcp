#!/bin/bash
# Script to run the Terraform MCP server tests

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Function to run a test module
run_test() {
    echo "Running $1..."
    cd "$PROJECT_ROOT"
    python -m awslabs.terraform_mcp_server.tests.$1
    echo "Test completed: $1"
}

# Get the test name from the first argument, default to all tests
TEST_NAME=$1
if [ -z "$TEST_NAME" ]; then
    echo "=== Running All Tests ==="
    run_test "test_parameter_annotations"
    run_test "test_tool_implementations"
elif [ "$TEST_NAME" == "params" ]; then
    run_test "test_parameter_annotations"
elif [ "$TEST_NAME" == "tools" ]; then
    run_test "test_tool_implementations"
else
    echo "Unknown test: $TEST_NAME"
    echo "Usage: $0 [params|tools]"
    echo "  params - Run parameter annotation tests"
    echo "  tools  - Run tool implementation tests"
    echo "  (no args) - Run all tests"
    exit 1
fi
