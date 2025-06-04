#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Script to run tests for the Bedrock Knowledge Base Retrieval MCP Server

set -e

# Parse command line arguments
COVERAGE=0
REPORT=0
VERBOSE=0
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --coverage)
      COVERAGE=1
      shift
      ;;
    --report)
      REPORT=1
      shift
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    *)
      SPECIFIC_TEST="$1"
      shift
      ;;
  esac
done

# Set up the command
CMD="pytest"

if [ $VERBOSE -eq 1 ]; then
  CMD="$CMD -v"
fi

if [ $COVERAGE -eq 1 ]; then
  CMD="$CMD --cov=awslabs.bedrock_kb_retrieval_mcp_server"

  if [ $REPORT -eq 1 ]; then
    CMD="$CMD --cov-report=html"
  fi
fi

if [ -n "$SPECIFIC_TEST" ]; then
  CMD="$CMD $SPECIFIC_TEST"
else
  CMD="$CMD tests/"
fi

# Run the tests
echo "Running: $CMD"
$CMD

# If coverage report was generated, print the path
if [ $COVERAGE -eq 1 ] && [ $REPORT -eq 1 ]; then
  echo "Coverage report generated in htmlcov/ directory"
  echo "Open htmlcov/index.html in your browser to view the report"
fi
