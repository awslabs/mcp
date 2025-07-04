#!/bin/bash

# Script to clean up the CloudFormation stack
# Usage: ./05_cleanup.sh [stack-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# If no stack name is provided, look for stacks matching our pattern
if [ -z "$1" ]; then
    # Find all test failure stacks
    STACKS=$(aws cloudformation list-stacks --stack-status-filter CREATE_FAILED ROLLBACK_COMPLETE ROLLBACK_FAILED DELETE_FAILED \
        --query "StackSummaries[?contains(StackName, 'scenario-01-stack')].StackName" --output text)

    if [ -z "$STACKS" ]; then
        echo "No scenario-01-stack stacks found to clean up."
        exit 0
    fi

    echo "Found the following test stacks to clean up:"
    echo "$STACKS"
    echo ""

    # Delete all found stacks
    for STACK_NAME in $STACKS; do
        echo "Deleting CloudFormation stack $STACK_NAME..."
        aws cloudformation delete-stack --stack-name "$STACK_NAME"
        echo "Deletion initiated for $STACK_NAME"
    done

    exit 0
else
    STACK_NAME=$1
fi

echo "Deleting CloudFormation stack $STACK_NAME..."

# Delete the stack
aws cloudformation delete-stack --stack-name $STACK_NAME

echo "Stack deletion initiated. You can check the status with:"
echo "aws cloudformation describe-stacks --stack-name $STACK_NAME"
echo "Resources should be cleaned up within a few minutes."

# Clean up the template file if it exists
if [ -f "invalid_cfn_template.yaml" ]; then
    echo "Removing temporary template file..."
    rm invalid_cfn_template.yaml
fi

echo "Cleanup complete."
