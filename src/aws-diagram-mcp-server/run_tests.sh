#!/bin/bash

# run_tests.sh - Test runner for AWS Diagram MCP Server
# This script runs the test suite with options for coverage and verbosity

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
COVERAGE=false
VERBOSE=false
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            HELP=true
            shift
            ;;
    esac
done

# Show help message
if [ "$HELP" = true ]; then
    echo "Usage: ./run_tests.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --coverage    Run tests with coverage report"
    echo "  -v, --verbose     Run tests in verbose mode"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                  # Run all tests"
    echo "  ./run_tests.sh --coverage       # Run tests with coverage"
    echo "  ./run_tests.sh --verbose        # Run tests with verbose output"
    echo "  ./run_tests.sh -c -v            # Run tests with coverage and verbose output"
    exit 0
fi

echo -e "${GREEN}AWS Diagram MCP Server - Test Suite${NC}"
echo "======================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed.${NC}"
    echo "Please install uv from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if pytest is installed, if not install it
echo -e "${YELLOW}Checking test dependencies...${NC}"
if ! uv pip show pytest &> /dev/null || ! uv pip show pytest-asyncio &> /dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    uv pip install -e ".[dev]"
else
    echo -e "${GREEN}Test dependencies already installed.${NC}"
fi

# Build pytest command
PYTEST_CMD="uv run pytest"

# Add verbosity flags
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -xvs"
else
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Add coverage flags
if [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}Running tests with coverage...${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=awslabs.aws_diagram_mcp_server --cov-report=term-missing"
else
    echo -e "${YELLOW}Running tests...${NC}"
fi

# Add tests directory
PYTEST_CMD="$PYTEST_CMD tests/"

# Run the tests
echo ""
echo -e "${YELLOW}Executing: $PYTEST_CMD${NC}"
echo ""

if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi