#!/bin/bash

# Script to clean up the ECS task and related resources
# Usage: ./05_cleanup.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# If no cluster name is provided, look for clusters matching our pattern
if [ -z "$1" ]; then
    # Find all clusters matching our pattern
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text | tr '\t' '\n' | grep "scenario-03-cluster" | sed 's/.*cluster\///')

    if [ -z "$CLUSTERS" ]; then
        echo "No scenario-03-cluster clusters found to clean up."
        exit 0
    fi

    echo "Found the following test clusters to clean up:"
    echo "$CLUSTERS"
    echo ""

    # Clean up each cluster and associated resources
    for CLUSTER_NAME in $CLUSTERS; do
        echo "Cleaning up ECS resources for cluster $CLUSTER_NAME..."

        # Find task definitions matching our pattern
        TASK_FAMILIES=$(aws ecs list-task-definition-families --status ACTIVE --family-prefix "scenario-03-task" --query 'families[*]' --output text)

        # Deregister each task definition
        for TASK_FAMILY in $TASK_FAMILIES; do
            TASK_REVISION=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition.revision' --output text 2>/dev/null)
            if [ -n "$TASK_REVISION" ]; then
                echo "Deregistering task definition $TASK_FAMILY:$TASK_REVISION..."
                aws ecs deregister-task-definition --task-definition "${TASK_FAMILY}:${TASK_REVISION}" > /dev/null
            fi
        done

        # Delete the cluster
        echo "Deleting ECS cluster $CLUSTER_NAME..."
        aws ecs delete-cluster --cluster $CLUSTER_NAME

        # Delete the associated CloudWatch log group
        LOG_GROUP="/ecs/${CLUSTER_NAME}"
        echo "Deleting CloudWatch log group $LOG_GROUP..."
        aws logs delete-log-group --log-group-name $LOG_GROUP 2>/dev/null || true
    done

    echo "All test clusters and associated resources have been cleaned up."
    exit 0
else
    CLUSTER_NAME=$1
fi

echo "Cleaning up ECS resources for cluster $CLUSTER_NAME..."

# Step 1: Find and deregister task definitions
echo "Step 1: Deregistering task definitions..."
TASK_FAMILIES=$(aws ecs list-task-definition-families --status ACTIVE --family-prefix "scenario-03-task" --query 'families[*]' --output text)

for TASK_FAMILY in $TASK_FAMILIES; do
    # Only process if it's related to our cluster
    if [[ "$TASK_FAMILY" == *"$CLUSTER_NAME"* || "$TASK_FAMILY" == *"scenario-03-task"* ]]; then
        TASK_REVISION=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition.revision' --output text 2>/dev/null)
        if [ -n "$TASK_REVISION" ]; then
            echo "Deregistering task definition $TASK_FAMILY:$TASK_REVISION..."
            aws ecs deregister-task-definition --task-definition "${TASK_FAMILY}:${TASK_REVISION}" > /dev/null
        fi
    fi
done

# Step 2: Delete the cluster
echo "Step 2: Deleting ECS cluster..."
aws ecs delete-cluster --cluster $CLUSTER_NAME

# Step 3: Delete the associated CloudWatch log group
LOG_GROUP="/ecs/${CLUSTER_NAME}"
echo "Step 3: Deleting CloudWatch log group $LOG_GROUP..."
aws logs delete-log-group --log-group-name $LOG_GROUP 2>/dev/null || true

echo "Cleanup complete. All resources have been removed."
