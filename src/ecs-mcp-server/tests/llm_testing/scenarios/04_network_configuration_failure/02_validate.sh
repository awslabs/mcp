#!/bin/bash

# Script to validate that the ECS service has network configuration failures
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
        if [[ "$CLUSTER_NAME" == *"scenario-04-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"scenario-04-cluster"* ]]; then
        echo "Could not find a recent scenario-04-cluster. Please provide a cluster name or run 01_create.sh first."
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
        if [[ "$SERVICE_NAME" == *"scenario-04-service"* ]]; then
            echo "Found test service: $SERVICE_NAME"
            break
        fi
    done

    if [ -z "$SERVICE_NAME" ] || [[ "$SERVICE_NAME" != *"scenario-04-service"* ]]; then
        echo "Could not find a service matching 'scenario-04-service' pattern in cluster $CLUSTER_NAME."
        echo "The service may not have been created yet. Please run 01_create.sh first."
        exit 1
    fi
else
    SERVICE_NAME=$2
fi

echo "Checking status of service $SERVICE_NAME in cluster $CLUSTER_NAME..."

# Get service status
SERVICE_DETAILS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME)
DESIRED_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].desiredCount')
RUNNING_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].runningCount')
PENDING_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].pendingCount')

echo "Service desired count: $DESIRED_COUNT"
echo "Service running count: $RUNNING_COUNT"
echo "Service pending count: $PENDING_COUNT"

if [ "$RUNNING_COUNT" -eq "$DESIRED_COUNT" ]; then
    echo "⚠️ Unexpected result: Service has all tasks running. Network restrictions should cause tasks to fail."
    echo "Checking tasks to see if they are actually healthy..."
    TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[*]' --output text)
    if [ -n "$TASKS" ]; then
        TASK_ARN=$(echo $TASKS | tr ' ' '\n' | head -1)
        TASK_DETAILS=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN)
        CONTAINER_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].lastStatus')
        HEALTH_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].healthStatus')
        echo "Container status: $CONTAINER_STATUS"
        echo "Health status: $HEALTH_STATUS"

        if [ "$HEALTH_STATUS" != "HEALTHY" ]; then
            echo "✅ Task is running but not healthy, possibly due to network restrictions."
        else
            echo "❌ Task appears to be healthy. Network restrictions may not be effective."
            exit 1
        fi
    fi
else
    echo "✅ Service does not have all desired tasks running, indicating a potential failure."
fi

# Check for task failures
echo "Checking for failed task deployments..."
STOPPED_TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --desired-status STOPPED --query 'taskArns[*]' --output text)
if [ -n "$STOPPED_TASKS" ]; then
    echo "✅ Found stopped tasks: $STOPPED_TASKS"

    # Check the stopped reason for the first task
    TASK_ARN=$(echo $STOPPED_TASKS | tr ' ' '\n' | head -1)
    TASK_DETAILS=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN)
    STOPPED_REASON=$(echo $TASK_DETAILS | jq -r '.tasks[0].stoppedReason')
    echo "Task stopped reason: $STOPPED_REASON"

    # Look for network-related failures in the stopped reason
    if [[ "$STOPPED_REASON" == *"network"* ]] || [[ "$STOPPED_REASON" == *"connectivity"* ]] || [[ "$STOPPED_REASON" == *"CannotPullContainerError"* ]]; then
        echo "✅ Task failure appears to be network-related as expected."
    else
        echo "⚠️ Task failure may not be network-related. Stopped reason: $STOPPED_REASON"
    fi
fi

# Get service events
echo "Service events (showing recent events that may indicate network issues):"
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:5]'

# Check if there are any failures in the service events
SERVICE_EVENTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events[0:10]')
echo "$SERVICE_EVENTS" | grep -i -e "fail" -e "error" -e "unable" -e "network" -e "connect"

if [ $? -eq 0 ]; then
    echo "✅ Found network-related error messages in service events."
    echo "Scenario is now ready for LLM troubleshooting testing."
else
    echo "❓ No clear network-related failure pattern detected in service events."
    echo "Wait a few more minutes and run this script again."
fi

echo -e "\nFor reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "SERVICE_NAME=$SERVICE_NAME"
