#!/bin/bash

# Script to validate that the ECS task has resource constraint failures
# Usage: ./02_validate.sh [cluster-name] [task-family]

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
        echo "Could not find a recent scenario-05-cluster. Please provide a cluster name or run 01_create.sh first."
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# Debug: List all task definitions to see what's available
echo "Listing all task definitions..."
ALL_TASK_DEFS=$(aws ecs list-task-definitions --query 'taskDefinitionArns[*]' --output text)
echo "Available task definitions: $ALL_TASK_DEFS"

# If no task family is provided, look for task definitions matching our pattern
if [ -z "$2" ]; then
    # Try multiple times with a delay
    MAX_RETRIES=5
    RETRY_COUNT=0
    TASK_DEFS=""

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        TASK_DEFS=$(aws ecs list-task-definitions --family-prefix scenario-05-task --query 'taskDefinitionArns[*]' --output text)

        if [ -n "$TASK_DEFS" ]; then
            echo "Found task definitions matching pattern."
            # Get the most recent task definition
            TASK_DEF_ARN=$(echo $TASK_DEFS | tr ' ' '\n' | head -1)
            TASK_FAMILY=$(echo $TASK_DEF_ARN | awk -F/ '{print $2}' | cut -d ':' -f 1)
            echo "Found task definition: $TASK_FAMILY"
            break
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Task definition not found, waiting 5 seconds (attempt $RETRY_COUNT/$MAX_RETRIES)..."
            sleep 5
        fi
    done

    if [ -z "$TASK_DEFS" ]; then
        # Extract the suffix from cluster name to match our task definition
        CLUSTER_SUFFIX=""
        if [[ $CLUSTER_NAME =~ scenario-05-cluster-([a-z0-9]+)$ ]]; then
            CLUSTER_SUFFIX="${BASH_REMATCH[1]}"
            echo "Extracted cluster suffix: $CLUSTER_SUFFIX"

            # Try to find a task definition with matching suffix if we found one
            if [ ! -z "$CLUSTER_SUFFIX" ]; then
                SPECIFIC_PATTERN="scenario-05-task-$CLUSTER_SUFFIX"
                echo "Looking for task definition with pattern: $SPECIFIC_PATTERN"

                # Directly use the expected task family name from the cluster suffix
                TASK_FAMILY="scenario-05-task-$CLUSTER_SUFFIX"
                echo "Setting task family to: $TASK_FAMILY"

                # Verify this task definition exists
                TASK_DEF_ARN=$(aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --query 'taskDefinition.taskDefinitionArn' --output text 2>/dev/null)

                if [ -n "$TASK_DEF_ARN" ] && [ "$TASK_DEF_ARN" != "None" ]; then
                    echo "Verified task definition exists: $TASK_DEF_ARN"
                else
                    echo "⚠️ Could not verify task definition $TASK_FAMILY exists."
                    echo "Available task definitions matching pattern:"
                    aws ecs list-task-definitions --family-prefix "scenario-05-task" --query 'taskDefinitionArns' --output text

                    # One more attempt - try looking for the newest task definition with our pattern
                    echo "Trying to find the most recent task definition matching our pattern..."
                    NEWEST_TASK=$(aws ecs list-task-definitions --family-prefix "scenario-05-task" --sort DESC --query 'taskDefinitionArns[0]' --output text)

                    if [ -n "$NEWEST_TASK" ] && [ "$NEWEST_TASK" != "None" ]; then
                        TASK_FAMILY=$(echo $NEWEST_TASK | awk -F/ '{print $2}' | cut -d ':' -f 1)
                        echo "Using most recent task definition: $TASK_FAMILY"
                    else
                        echo "Failed to find any task definition with our pattern"
                        # We'll continue to the broader search below
                    fi
                fi
            fi
        fi

        # If we still don't have a task definition, try a broader search but be more careful
        if [ -z "$TASK_DEFS" ] && [ -z "$TASK_FAMILY" ]; then
            echo "Looking for scenario-05-task pattern..."
            # Be more specific with the grep pattern to match only our task family
            TASK_DEFS=$(aws ecs list-task-definitions --query 'taskDefinitionArns[*]' --output text | grep "scenario-05-task-")

            if [ -n "$TASK_DEFS" ]; then
                echo "Found task definitions with scenario-05-task- pattern."
                # Sort to get the most recent task if multiple match
                TASK_DEF_ARN=$(echo $TASK_DEFS | tr ' ' '\n' | sort -r | head -1)
                TASK_FAMILY=$(echo $TASK_DEF_ARN | awk -F/ '{print $2}' | cut -d ':' -f 1)
                echo "Selected newest task definition: $TASK_FAMILY"
            else
                echo "Could not find any task definition matching 'scenario-05-task-' pattern."
                echo "Please run 01_create.sh first."
                exit 1
            fi
        fi
    fi
else
    TASK_FAMILY=$2
fi

echo "Checking resource constraint failures for task family $TASK_FAMILY in cluster $CLUSTER_NAME..."

# Check for immediate failures from run-task API calls
echo "Checking for API-level failures..."
IMMEDIATE_FAILURES=$(aws ecs run-task \
  --cluster $CLUSTER_NAME \
  --task-definition $TASK_FAMILY \
  --count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(aws ec2 describe-subnets --filters 'Name=default-for-az,Values=true' --query 'Subnets[0].SubnetId' --output text)],securityGroups=[$(aws ec2 describe-security-groups --filters 'Name=group-name,Values=default' --query 'SecurityGroups[0].GroupId' --output text)],assignPublicIp=ENABLED}" \
  --query 'failures' --output json 2>/dev/null)

if [ -n "$IMMEDIATE_FAILURES" ] && [ "$IMMEDIATE_FAILURES" != "[]" ] && [ "$IMMEDIATE_FAILURES" != "null" ]; then
    echo "✅ Found API-level failures:"
    echo $IMMEDIATE_FAILURES | jq .

    # Check if failure reason contains resource-related keywords
    FAILURE_REASON=$(echo $IMMEDIATE_FAILURES | jq -r '.[0].reason')
    if [[ "$FAILURE_REASON" == *"resource"* ]] || [[ "$FAILURE_REASON" == *"cpu"* ]] || [[ "$FAILURE_REASON" == *"memory"* ]] || [[ "$FAILURE_REASON" == *"vCPU"* ]]; then
        echo "✅ Failure reason is resource-related as expected: $FAILURE_REASON"
    else
        echo "⚠️ Failure reason may not be resource-related. Reason: $FAILURE_REASON"
    fi
else
    echo "No immediate API failures detected. The task may have been accepted but failed later."
fi

# Check for stopped tasks that might have failed due to resource constraints
echo "Checking for failed task launches..."
TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status STOPPED --query 'taskArns[*]' --output text)
if [ -n "$TASKS" ]; then
    echo "✅ Found stopped tasks: $TASKS"

    # Check the stopped reason for the first task
    TASK_ARN=$(echo $TASKS | tr ' ' '\n' | head -1)
    TASK_DETAILS=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN)
    STOPPED_REASON=$(echo $TASK_DETAILS | jq -r '.tasks[0].stoppedReason')
    TASK_DEFINITION=$(echo $TASK_DETAILS | jq -r '.tasks[0].taskDefinitionArn')

    echo "Task stopped reason: $STOPPED_REASON"
    echo "Task definition: $TASK_DEFINITION"

    # Look for resource-related failures in the stopped reason
    if [[ "$STOPPED_REASON" == *"resource"* ]] || [[ "$STOPPED_REASON" == *"cpu"* ]] || [[ "$STOPPED_REASON" == *"memory"* ]] || [[ "$STOPPED_REASON" == *"limit"* ]]; then
        echo "✅ Task failure appears to be resource-related as expected."
    else
        echo "⚠️ Task failure may not be resource-related. Stopped reason: $STOPPED_REASON"
    fi

    # Check container status
    CONTAINER_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].lastStatus')
    CONTAINER_REASON=$(echo $TASK_DETAILS | jq -r '.tasks[0].containers[0].reason')
    echo "Container status: $CONTAINER_STATUS"
    echo "Container reason: $CONTAINER_REASON"

    if [[ "$CONTAINER_REASON" == *"resource"* ]] || [[ "$CONTAINER_REASON" == *"memory"* ]] || [[ "$CONTAINER_REASON" == *"limit"* ]]; then
        echo "✅ Container failure appears to be resource-related as expected."
    fi
else
    echo "No stopped tasks found in cluster $CLUSTER_NAME."
fi

# Check task definition details to confirm it has excessive resources
echo "Checking task definition resource specifications..."
TASK_DEF_DETAILS=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY)
CPU=$(echo $TASK_DEF_DETAILS | jq -r '.taskDefinition.cpu')
MEMORY=$(echo $TASK_DEF_DETAILS | jq -r '.taskDefinition.memory')

echo "Task definition CPU units: $CPU (4096 = 4 vCPU, 16384 = 16 vCPU)"
echo "Task definition memory (MiB): $MEMORY (8192 = 8 GB, 122880 = 120 GB)"

if [ "$CPU" -gt "4096" ] || [ "$MEMORY" -gt "30720" ]; then
    echo "✅ Task definition has high resource requirements as expected."
else
    echo "⚠️ Task definition does not have exceptionally high resource requirements."
    echo "This may not trigger resource constraint failures."
    echo "Consider modifying 01_create.sh to specify higher CPU/memory values."
fi

echo -e "\nScenario is ready for LLM troubleshooting testing."
echo "For reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "TASK_FAMILY=$TASK_FAMILY"
