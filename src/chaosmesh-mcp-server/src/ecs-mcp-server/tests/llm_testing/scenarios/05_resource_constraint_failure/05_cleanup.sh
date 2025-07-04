#!/bin/bash

# Script to clean up resources created for resource constraint failure testing
# Usage: ./05_cleanup.sh [cluster-name] [task-family]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# If no cluster name is provided, look for the most recently created cluster matching our pattern
if [ -z "$1" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text)

    # Loop through clusters to find one matching our pattern
    for CLUSTER_ARN in $CLUSTERS; do
        CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$CLUSTER_NAME" == *"scenario-05-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"scenario-05-cluster"* ]]; then
        echo "Could not find a recent scenario-05-cluster. Please provide a cluster name."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# If no task family is provided, look for task definitions matching our pattern
if [ -z "$2" ]; then
    TASK_DEFS=$(aws ecs list-task-definitions --family-prefix scenario-05-task --query 'taskDefinitionArns[*]' --output text)

    # Get the most recent task definition
    if [ -n "$TASK_DEFS" ]; then
        TASK_DEF_ARN=$(echo $TASK_DEFS | tr ' ' '\n' | head -1)
        TASK_FAMILY=$(echo $TASK_DEF_ARN | awk -F/ '{print $2}' | cut -d ':' -f 1)
        echo "Found task definition: $TASK_FAMILY"
    else
        echo "Could not find a task definition matching 'scenario-05-task' pattern."
        echo "Proceeding with cleanup of other resources."
    fi
else
    TASK_FAMILY=$2
fi

echo "Starting cleanup of resources..."

# Step 1: Stop any running tasks
echo "Step 1: Stopping any running tasks..."
TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --query 'taskArns[*]' --output text)
if [ -n "$TASKS" ]; then
    for TASK_ARN in $TASKS; do
        echo "Stopping task $TASK_ARN..."
        aws ecs stop-task --cluster $CLUSTER_NAME --task $TASK_ARN > /dev/null 2>&1
    done
    echo "Waiting for tasks to stop..."
    sleep 10
fi

# Step 2: Find and deregister task definition
if [ -n "$TASK_FAMILY" ]; then
    echo "Step 2: Finding and deregistering task definition $TASK_FAMILY..."
    TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix $TASK_FAMILY --query 'taskDefinitionArns[0]' --output text)
    if [[ "$TASK_DEF_ARN" != "None" ]] && [ -n "$TASK_DEF_ARN" ]; then
        echo "Deregistering task definition $TASK_DEF_ARN..."
        aws ecs deregister-task-definition --task-definition $TASK_DEF_ARN > /dev/null 2>&1
    fi
else
    echo "Step 2: No task family provided or found. Skipping task definition deregistration."
fi

# Step 3: Delete the cluster
echo "Step 3: Deleting cluster $CLUSTER_NAME..."
aws ecs delete-cluster --cluster $CLUSTER_NAME > /dev/null 2>&1

# Step 4: Delete CloudWatch log group
echo "Step 4: Deleting CloudWatch log group..."
LOG_GROUP="/ecs/${CLUSTER_NAME}/*"
aws logs describe-log-groups --log-group-name-prefix "/ecs/${CLUSTER_NAME}" --query 'logGroups[*].logGroupName' --output text | tr '\t' '\n' | while read -r GROUP; do
    echo "Deleting log group $GROUP..."
    aws logs delete-log-group --log-group-name "$GROUP" > /dev/null 2>&1
done

echo "Cleanup completed."
