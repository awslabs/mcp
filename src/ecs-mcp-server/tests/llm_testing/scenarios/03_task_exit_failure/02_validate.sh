#!/bin/bash

# Script to validate that the ECS task has failed as expected
# Usage: ./02_validate.sh [cluster-name] [task-arn]

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
        if [[ "$CLUSTER_NAME" == *"scenario-03-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"scenario-03-cluster"* ]]; then
        echo "Could not find a recent scenario-03-cluster. Please provide a cluster name or run 01_create.sh first."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# If no task ARN is provided, look for stopped tasks in the cluster
if [ -z "$2" ]; then
    # Try to find stopped tasks, with retries if none found initially
    MAX_RETRIES=10
    RETRY_DELAY=10  # seconds
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "Looking for stopped tasks in cluster $CLUSTER_NAME (attempt $(($RETRY_COUNT + 1))/$MAX_RETRIES)..."
        TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status STOPPED --query 'taskArns[*]' --output text)

        if [ -n "$TASKS" ]; then
            echo "Found stopped task(s)!"
            break
        fi

        # Look for running tasks to see if anything is still in progress
        RUNNING_TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status RUNNING --query 'taskArns[*]' --output text)
        if [ -n "$RUNNING_TASKS" ]; then
            echo "Task is still running. Waiting for it to complete..."
        else
            # Try checking if any tasks are in the PENDING state
            PENDING_TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status PENDING --query 'taskArns[*]' --output text)
            if [ -n "$PENDING_TASKS" ]; then
                echo "Task is pending. Waiting for it to start and complete..."
            else
                echo "No tasks found in any state (running, pending, or stopped)."
            fi
        fi

        echo "Waiting $RETRY_DELAY seconds before checking again..."
        sleep $RETRY_DELAY
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done

    if [ -z "$TASKS" ]; then
        echo "No stopped tasks found in cluster $CLUSTER_NAME after $MAX_RETRIES attempts."
        echo "The task may have failed to launch or may be taking longer than expected to complete."
        echo "Run 'aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status STOPPED' to check manually."
        exit 1
    fi

    # Take the most recent task
    TASK_ARN=$(echo $TASKS | tr '\t' '\n' | head -1)
    echo "Found stopped task: $TASK_ARN"
else
    TASK_ARN=$2
fi

echo "Checking status of task $TASK_ARN in cluster $CLUSTER_NAME..."

# Get task details
TASK_DETAILS=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Error getting task details. Make sure the task ARN is valid and the task exists."
    exit 1
fi

# Check if task has stopped
TASK_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].lastStatus')
STOPPED_REASON=$(echo $TASK_DETAILS | jq -r '.tasks[0].stoppedReason')

echo "Task status: $TASK_STATUS"

if [ "$TASK_STATUS" != "STOPPED" ] && [ "$TASK_STATUS" != "DEPROVISIONING" ] && [ "$TASK_STATUS" != "DEPROVISIONED" ]; then
    echo "Task is not stopped yet. Current status: $TASK_STATUS"
    echo "Wait a few more moments and try again."
    exit 1
fi

echo "Task is in terminal state: $TASK_STATUS"

# Get container exit code
CONTAINER_NAME=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].name')
CONTAINER_EXIT_CODE=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].exitCode')
CONTAINER_REASON=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].reason')

echo "Container name: $CONTAINER_NAME"
echo "Container exit code: $CONTAINER_EXIT_CODE"

if [ "$CONTAINER_EXIT_CODE" == "1" ]; then
    echo "✅ Task has failed with exit code 1 as expected."

    # Get task definition details to find log configuration
    TASK_DEF_ARN=$(echo $TASK_DETAILS | jq -r '.tasks[0].taskDefinitionArn')
    TASK_DEF=$(aws ecs describe-task-definition --task-definition $TASK_DEF_ARN)

    LOG_GROUP=$(echo $TASK_DEF | jq -r '.taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"')
    LOG_PREFIX=$(echo $TASK_DEF | jq -r '.taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-stream-prefix"')

    if [ -n "$LOG_GROUP" ]; then
        echo "Log group: $LOG_GROUP"

        # Find the log stream for this task
        TASK_ID=$(echo $TASK_ARN | awk -F/ '{print $3}')
        LOG_STREAMS=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --log-stream-name-prefix "${LOG_PREFIX}/${CONTAINER_NAME}/${TASK_ID}" --query 'logStreams[*].logStreamName' --output text)

        if [ -n "$LOG_STREAMS" ]; then
            LOG_STREAM=$(echo $LOG_STREAMS | tr '\t' '\n' | head -1)
            echo "Log stream: $LOG_STREAM"

            # Get log events
            echo -e "\nLatest log events:"
            aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name $LOG_STREAM --limit 10 --query 'events[*].message' --output text | tr '\t' '\n'

            # Check for expected error message
            DB_URL_ERROR=$(aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name $LOG_STREAM --query 'events[*].message' --output text | grep -c "DATABASE_URL")

            if [ $DB_URL_ERROR -gt 0 ]; then
                echo -e "\n✅ Found expected error about missing DATABASE_URL environment variable in logs."
                echo "Scenario is now ready for LLM troubleshooting testing."
                echo "Use the prompts in 03_prompts.txt to test Cline's troubleshooting capabilities."
            else
                echo -e "\n⚠️ Did not find expected error message about DATABASE_URL in logs."
            fi
        else
            echo "No log streams found for this task."
        fi
    else
        echo "No log configuration found for this task."
    fi
else
    echo "❌ Task did not fail with the expected exit code 1. Exit code: $CONTAINER_EXIT_CODE"
fi

echo -e "\nTask details:"
echo "Task definition ARN: $(echo $TASK_DETAILS | jq -r '.tasks[0].taskDefinitionArn')"
echo "Stopped reason: $STOPPED_REASON"
echo "Container reason: $CONTAINER_REASON"

echo -e "\nFor reference, save these values for Cline prompts:"
echo "CLUSTER_NAME: $CLUSTER_NAME"
echo "TASK_ARN: $TASK_ARN"
echo "LOG_GROUP: $LOG_GROUP"
