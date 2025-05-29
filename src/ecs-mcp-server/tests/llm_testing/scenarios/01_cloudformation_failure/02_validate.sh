#!/bin/bash

# Script to validate that the CloudFormation stack has failed as expected
# Usage: ./02_validate.sh [stack-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# If no stack name is provided, look for the most recently created stack
if [ -z "$1" ]; then
    STACK_NAME=$(aws cloudformation list-stacks --stack-status-filter CREATE_FAILED ROLLBACK_COMPLETE ROLLBACK_FAILED ROLLBACK_IN_PROGRESS \
        --query "sort_by(StackSummaries, &CreationTime)[-1].StackName" --output text)

    if [[ "$STACK_NAME" == *"scenario-01-stack"* ]]; then
        echo "Found test stack: $STACK_NAME"
    else
        echo "Could not find a recent scenario-01-stack. Please provide a stack name or run 01_create.sh first."
        exit 1
    fi
else
    STACK_NAME=$1
fi

echo "Checking status of stack $STACK_NAME..."

# Get stack status
STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text 2>/dev/null)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "Stack $STACK_NAME does not exist. Make sure you've run 01_create.sh first."
  exit 1
fi

echo "Stack status: $STATUS"

# Check if stack has failed
if [[ $STATUS == *"ROLLBACK"* || $STATUS == *"FAILED"* ]]; then
  echo "✅ Stack has failed as expected."

  # Get specific error information
  echo "Fetching error details..."
  aws cloudformation describe-stack-events \
    --stack-name $STACK_NAME \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].{Resource:LogicalResourceId, Reason:ResourceStatusReason}' \
    --output table

  echo "Stack is now ready for LLM troubleshooting testing."
else
  echo "❌ Stack is not in a failed state. Current status: $STATUS"
  echo "Wait a few more minutes for the failure to occur."
fi
