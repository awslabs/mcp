#!/bin/bash

# ECS Security Analysis LLM Testing Scenario - Validation
# This script validates that the test cluster is ready for LLM testing
# Usage: ./02_validate.sh [cluster-name]

# Set script location and source utilities
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Configuration
SCENARIO_NAME="07_security_analysis_scenario"
TEST_REGION="us-east-1"

# If no cluster name is provided, look for the most recently created cluster matching our pattern
if [ -z "$1" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text)

    # Loop through clusters to find one matching our pattern
    for CLUSTER_ARN in $CLUSTERS; do
        CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$CLUSTER_NAME" == *"llm-test-security-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"llm-test-security-cluster"* ]]; then
        echo "Could not find a recent llm-test-security-cluster. Please provide a cluster name or run 01_create.sh first."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# Find the corresponding task definition family
TASK_DEFINITION_FAMILY=$(echo "$CLUSTER_NAME" | sed 's/llm-test-security-cluster/llm-test-security-task/')

echo "🧪 Starting ECS Security Analysis LLM Testing Validation"
echo "========================================================="
echo ""
echo "Scenario: $SCENARIO_NAME"
echo "Test Cluster: $CLUSTER_NAME"
echo "Region: $TEST_REGION"
echo ""

# Check if cluster exists (created by 01_create.sh)
echo "🔍 Checking if test cluster exists..."
if aws ecs describe-clusters --clusters "$TEST_CLUSTER_NAME" --region "$TEST_REGION" &>/dev/null; then
    echo "✅ Test cluster '$TEST_CLUSTER_NAME' found"
else
    echo "❌ Test cluster '$TEST_CLUSTER_NAME' not found. Run 01_create.sh first."
    exit 1
fi

# Get cluster status
CLUSTER_STATUS=$(aws ecs describe-clusters --clusters "$TEST_CLUSTER_NAME" --region "$TEST_REGION" \
    --query 'clusters[0].status' --output text)

if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
    echo "✅ Test cluster is ACTIVE"
else
    echo "⚠️  Test cluster status: $CLUSTER_STATUS"
fi

# Check if task definition exists
echo "🔍 Checking if test task definition exists..."
if aws ecs describe-task-definition --task-definition "$TASK_DEFINITION_FAMILY" --region "$TEST_REGION" &>/dev/null; then
    echo "✅ Task definition '$TASK_DEFINITION_FAMILY' found"

    # Get task definition details to verify security misconfigurations
    echo "🔍 Verifying intentional security misconfigurations..."

    # Check for privileged container
    PRIVILEGED=$(aws ecs describe-task-definition --task-definition "$TASK_DEFINITION_FAMILY" --region "$TEST_REGION" \
        --query 'taskDefinition.containerDefinitions[0].privileged' --output text)

    if [ "$PRIVILEGED" == "true" ]; then
        echo "✅ Found privileged container (intentional security issue)"
    else
        echo "⚠️  Privileged container not found - may affect test results"
    fi

    # Check for hardcoded secrets in environment variables
    ENV_VARS=$(aws ecs describe-task-definition --task-definition "$TASK_DEFINITION_FAMILY" --region "$TEST_REGION" \
        --query 'taskDefinition.containerDefinitions[0].environment[?name==`SECRET_KEY`].value' --output text)

    if [ -n "$ENV_VARS" ]; then
        echo "✅ Found hardcoded secrets in environment variables (intentional security issue)"
    else
        echo "⚠️  Hardcoded secrets not found - may affect test results"
    fi

else
    echo "❌ Task definition '$TASK_DEFINITION_FAMILY' not found. Run 01_create.sh first."
    exit 1
fi

# Check cluster configuration for security issues
echo "🔍 Checking cluster configuration..."
EXECUTE_COMMAND_CONFIG=$(aws ecs describe-clusters --clusters "$TEST_CLUSTER_NAME" --region "$TEST_REGION" \
    --query 'clusters[0].configuration.executeCommandConfiguration.logging' --output text 2>/dev/null)

if [ "$EXECUTE_COMMAND_CONFIG" == "NONE" ] || [ "$EXECUTE_COMMAND_CONFIG" == "None" ]; then
    echo "✅ Execute command logging disabled (intentional security issue)"
else
    echo "⚠️  Execute command logging status: $EXECUTE_COMMAND_CONFIG"
fi

# Summary
echo ""
echo "📋 Test Environment Summary:"
echo "   • Cluster: $TEST_CLUSTER_NAME (Status: $CLUSTER_STATUS)"
echo "   • Region: $TEST_REGION"
echo "   • Task Definition: $TASK_DEFINITION_FAMILY"
echo "   • Security Issues: Intentionally configured for testing"
echo ""
echo "✅ Test ECS infrastructure created successfully"
echo ""
echo "⚠️  Note: This cluster has intentional security issues for testing purposes"
echo ""
echo "🎯 Ready for LLM testing scenarios!"
echo "   Use the prompts in 03_prompts.txt to test the security analysis tools."
echo ""
echo "The scenario is now ready for LLM troubleshooting testing."
