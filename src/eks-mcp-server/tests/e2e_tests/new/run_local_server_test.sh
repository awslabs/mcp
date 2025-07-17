#!/bin/bash

# Script to test hybrid node tools in the local EKS MCP Server

# Default values
CLUSTER_NAME="test-eks-hybrid"
DEBUG=false
TOOL="all"
ROLE_NAME="AmazonEKSHybridNodesRole"

# Parse command line options
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --cluster-name)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --role-name)
      ROLE_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--cluster-name NAME] [--debug] [--tool TOOL_NAME] [--role-name ROLE_NAME]"
      exit 1
      ;;
  esac
done

# Build debug flag
DEBUG_FLAG=""
if [[ "$DEBUG" == true ]]; then
  DEBUG_FLAG="--debug"
fi

# Run the test script
echo "Testing local server with cluster: $CLUSTER_NAME, tool: $TOOL, debug: $DEBUG, role: $ROLE_NAME"
cd "$(dirname "$0")"
python3 test_local_server.py --cluster-name "$CLUSTER_NAME" --tool "$TOOL" --role-name "$ROLE_NAME" $DEBUG_FLAG
