#!/bin/bash

# Script to validate that the ECS service has failed as expected
# Usage: ./02_validate.sh [cluster-name] [service-name]

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
        if [[ "$CLUSTER_NAME" == *"scenario-02-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"scenario-02-cluster"* ]]; then
        echo "Could not find a recent scenario-02-cluster. Please provide a cluster name or run 01_create.sh first."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# If no service name is provided, look for services in the cluster
if [ -z "$2" ]; then
    SERVICES=$(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns[*]' --output text)

    # Loop through services to find one matching our pattern
    for SERVICE_ARN in $SERVICES; do
        SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F/ '{print $3}')
        if [[ "$SERVICE_NAME" == *"scenario-02-service"* ]]; then
            echo "Found test service: $SERVICE_NAME"
            break
        fi
    done

    if [ -z "$SERVICE_NAME" ] || [[ "$SERVICE_NAME" != *"scenario-02-service"* ]]; then
        echo "Could not find a service matching 'scenario-02-service' pattern in cluster $CLUSTER_NAME."
        echo "Checking if service creation is still in progress..."

        # Check all services in the cluster even if they don't match our pattern
        ALL_SERVICES=$(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns' --output json)
        echo "All services found in cluster: $ALL_SERVICES"

        # Check for task definition existence - it should exist even if service creation failed
        TASK_DEF_FAMILY=$(echo "$CLUSTER_NAME" | sed 's/scenario-02-cluster/scenario-02-task/')
        TASK_DEF=$(aws ecs describe-task-definition --task-definition $TASK_DEF_FAMILY 2>/dev/null)

        if [ $? -eq 0 ]; then
            echo "Found task definition $TASK_DEF_FAMILY - service creation may have failed."
            echo "You can proceed with testing using the task definition directly."
            echo "CLUSTER_NAME=$CLUSTER_NAME"
            echo "TASK_DEFINITION=$TASK_DEF_FAMILY"
            exit 0
        else
            echo "Task definition not found either. Please run 01_create.sh first."
            exit 1
        fi
    fi
else
    SERVICE_NAME=$2
fi

echo "Checking status of service $SERVICE_NAME in cluster $CLUSTER_NAME..."

# Get service status
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME

# Check for task failures
echo "Checking for failed task deployments..."
aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --desired-status STOPPED

# Get events
echo "Service events (showing image pull failures):"
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:5]'

# Check if there are any failures - with retries
MAX_RETRIES=10
RETRY_DELAY=10  # seconds
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Looking for failed tasks for service $SERVICE_NAME (attempt $(($RETRY_COUNT + 1))/$MAX_RETRIES)..."
    FAILED_TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --desired-status STOPPED --query 'taskArns' --output text)

    if [ -n "$FAILED_TASKS" ]; then
        echo "Found failed task(s)!"
        break
    fi

    # Check service events to see if there are failures in the logs
    echo "Checking service events..."
    SERVICE_EVENTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:5]')
    echo "$SERVICE_EVENTS" | grep -q "failures" && echo "🔍 Found failure messages in service events."

    echo "Waiting $RETRY_DELAY seconds before checking again..."
    sleep $RETRY_DELAY
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ -n "$FAILED_TASKS" ]; then
    echo "✅ Service has failed tasks as expected."
    echo "Scenario is now ready for LLM troubleshooting testing."
    echo "Use the prompts in 03_prompts.txt to test Cline's troubleshooting capabilities."
else
    echo "❓ No failed tasks found after $MAX_RETRIES attempts."
    echo "However, service deployment may still have failed without creating tasks."
    echo "Checking service events for failure patterns..."

    SERVICE_EVENTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:5]')
    echo "$SERVICE_EVENTS" | grep -i -e "fail" -e "error" -e "unable" -e "non-existent"

    if [ $? -eq 0 ]; then
        echo "✅ Found error messages in service events. The service is failing to deploy as expected."
        echo "Scenario is now ready for LLM troubleshooting testing."
        echo "Use the prompts in 03_prompts.txt to test Cline's troubleshooting capabilities."
        exit 0
    else
        echo "❌ No clear failure pattern detected in service events."
        echo "Wait a few more minutes and run this script again."
        exit 1
    fi
fi
