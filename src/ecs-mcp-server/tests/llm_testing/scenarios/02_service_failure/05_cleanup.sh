#!/bin/bash

# Script to clean up the ECS service and related resources
# Usage: ./05_cleanup.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# If no cluster name is provided, look for clusters matching our pattern
if [ -z "$1" ]; then
    # Find all clusters matching our pattern
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text | tr '\t' '\n' | grep "scenario-02-cluster" | sed 's/.*cluster\///')

    if [ -z "$CLUSTERS" ]; then
        echo "No scenario-02-cluster clusters found to clean up."
        exit 0
    fi

    echo "Found the following test clusters to clean up:"
    echo "$CLUSTERS"
    echo ""

    # Clean up each cluster and associated resources
    for CLUSTER_NAME in $CLUSTERS; do
        echo "Cleaning up ECS resources for cluster $CLUSTER_NAME..."

        # Find services in this cluster
        SERVICES=$(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns[*]' --output text | tr '\t' '\n' | grep "scenario-02-service" | sed 's/.*service\///')

        # Delete each service
        for SERVICE_NAME in $SERVICES; do
            echo "Deleting ECS service $SERVICE_NAME..."
            aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0
            aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force
        done

        # Find task definitions matching our pattern
        TASK_FAMILIES=$(aws ecs list-task-definition-families --status ACTIVE --family-prefix "scenario-02-task" --query 'families[*]' --output text)

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
    done

    echo "All test clusters and associated resources have been cleaned up."
    exit 0
else
    CLUSTER_NAME=$1

    # If service name is not provided, look for services in the cluster
    if [ -z "$2" ]; then
        # Find services in this cluster
        SERVICES=$(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns[*]' --output text | tr '\t' '\n' | grep "scenario-02-service" | sed 's/.*service\///')
    else
        SERVICES=$2
    fi
fi

echo "Cleaning up ECS resources for cluster $CLUSTER_NAME..."

# Delete each service
for SERVICE_NAME in $SERVICES; do
    # Step 1: Delete the service
    echo "Step 1: Deleting ECS service $SERVICE_NAME..."
    aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0
    aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force
done

# Step 2: Deregister task definition
echo "Step 2: Deregistering task definition..."
TASK_REVISION=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY --query 'taskDefinition.revision' --output text)
if [ -n "$TASK_REVISION" ]; then
    echo "Deregistering $TASK_FAMILY:$TASK_REVISION"
    aws ecs deregister-task-definition --task-definition "${TASK_FAMILY}:${TASK_REVISION}"
else
    echo "Task definition $TASK_FAMILY not found or unable to get revision."
fi

# Step 3: Delete the cluster
echo "Step 3: Deleting ECS cluster..."
aws ecs delete-cluster --cluster $CLUSTER_NAME

echo "Cleanup complete. All resources have been removed."
