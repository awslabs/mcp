#!/bin/bash

# Script to clean up ECS security analysis LLM testing resources
# Usage: ./05_cleanup.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Configuration
REGION="us-east-1"

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
        echo "Could not find a recent llm-test-security-cluster. Please provide a cluster name."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# Derive other resource names from cluster name
RANDOM_ID=$(echo "$CLUSTER_NAME" | sed 's/.*-//')
TASK_FAMILY="llm-test-security-task-$RANDOM_ID"
SERVICE_NAME="llm-test-security-service-$RANDOM_ID"
SG_NAME="llm-test-security-sg-$RANDOM_ID"

echo "Cleaning up ECS security analysis LLM testing resources..."
echo "Cluster: $CLUSTER_NAME"
echo "Task Family: $TASK_FAMILY"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Stop any running tasks
echo "Step 1: Stopping running tasks..."
RUNNING_TASKS=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --region "$REGION" --query 'taskArns[*]' --output text 2>/dev/null || echo "")

if [ -n "$RUNNING_TASKS" ] && [ "$RUNNING_TASKS" != "None" ]; then
    for task in $RUNNING_TASKS; do
        echo "  Stopping task: $task"
        aws ecs stop-task --cluster "$CLUSTER_NAME" --task "$task" --region "$REGION" --reason "LLM testing cleanup" > /dev/null 2>&1 || echo "    Task may already be stopped"
    done
    echo "  Waiting for tasks to stop..."
    sleep 10
else
    echo "  No running tasks found"
fi

# Step 2: Delete services
echo "Step 2: Deleting services..."
if aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --region "$REGION" &>/dev/null; then
    echo "  Scaling down service: $SERVICE_NAME"
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --desired-count 0 --region "$REGION" > /dev/null 2>&1

    echo "  Waiting for service to scale down..."
    sleep 15

    echo "  Deleting service: $SERVICE_NAME"
    aws ecs delete-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --region "$REGION" > /dev/null 2>&1

    echo "  Waiting for service deletion..."
    sleep 10
else
    echo "  Service $SERVICE_NAME not found"
fi

# Step 3: Delete cluster
echo "Step 3: Deleting cluster..."
aws ecs delete-cluster --cluster "$CLUSTER_NAME" --region "$REGION" > /dev/null 2>&1 && echo "  Cluster deletion initiated" || echo "  Cluster may not exist"

# Step 4: Deregister task definitions
echo "Step 4: Deregistering task definitions..."
TASK_DEFINITIONS=$(aws ecs list-task-definitions --family-prefix "$TASK_FAMILY" --region "$REGION" --query 'taskDefinitionArns[*]' --output text 2>/dev/null || echo "")

if [ -n "$TASK_DEFINITIONS" ] && [ "$TASK_DEFINITIONS" != "None" ]; then
    for task_def in $TASK_DEFINITIONS; do
        echo "  Deregistering: $task_def"
        aws ecs deregister-task-definition --task-definition "$task_def" --region "$REGION" > /dev/null 2>&1 || echo "    Task definition may already be deregistered"
    done
else
    echo "  No task definitions found for family: $TASK_FAMILY"
fi

# Step 5: Delete security group
echo "Step 5: Deleting security group..."
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [ "$SG_ID" != "None" ] && [ -n "$SG_ID" ]; then
    echo "  Deleting security group: $SG_ID"
    aws ec2 delete-security-group --group-id "$SG_ID" > /dev/null 2>&1 && echo "  Security group deleted" || echo "  Security group may be in use or already deleted"
else
    echo "  Security group $SG_NAME not found"
fi

# Step 6: Delete CloudWatch log group
echo "Step 6: Deleting CloudWatch log group..."
aws logs delete-log-group --log-group-name "/ecs/llm-test-security" --region "$REGION" > /dev/null 2>&1 && echo "  Log group deleted" || echo "  Log group may not exist"

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "Resources cleaned up:"
echo "• Cluster: $CLUSTER_NAME"
echo "• Service: $SERVICE_NAME"
echo "• Task Definition Family: $TASK_FAMILY"
echo "• Security Group: $SG_NAME"
echo "• CloudWatch Log Group: /ecs/llm-test-security"
