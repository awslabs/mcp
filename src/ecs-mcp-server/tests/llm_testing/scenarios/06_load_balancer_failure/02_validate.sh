#!/bin/bash

# Script to validate that the ECS service has load balancer health check failures
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
        if [[ "$CLUSTER_NAME" == *"scenario-06-cluster"* ]]; then
            echo "Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"scenario-06-cluster"* ]]; then
        echo "Could not find a recent scenario-06-cluster. Please provide a cluster name or run 01_create.sh first."
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
        if [[ "$SERVICE_NAME" == *"scenario-06-service"* ]]; then
            echo "Found test service: $SERVICE_NAME"
            break
        fi
    done

    if [ -z "$SERVICE_NAME" ] || [[ "$SERVICE_NAME" != *"scenario-06-service"* ]]; then
        echo "Could not find a service matching 'scenario-06-service' pattern in cluster $CLUSTER_NAME."
        echo "The service may not have been created yet. Please run 01_create.sh first."
        exit 1
    fi
else
    SERVICE_NAME=$2
fi

echo "Checking status of service $SERVICE_NAME in cluster $CLUSTER_NAME..."

# Get service details to find the load balancer info
SERVICE_DETAILS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME)
DESIRED_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].desiredCount')
RUNNING_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].runningCount')
PENDING_COUNT=$(echo $SERVICE_DETAILS | jq -r '.services[0].pendingCount')

echo "Service desired count: $DESIRED_COUNT"
echo "Service running count: $RUNNING_COUNT"
echo "Service pending count: $PENDING_COUNT"

# Extract target group ARN from service details
TARGET_GROUP_ARN=$(echo $SERVICE_DETAILS | jq -r '.services[0].loadBalancers[0].targetGroupArn')
if [ -z "$TARGET_GROUP_ARN" ] || [ "$TARGET_GROUP_ARN" == "null" ]; then
    echo "❌ Service does not have a target group attached. This test requires a load balancer."
    exit 1
else
    echo "Found target group: $TARGET_GROUP_ARN"
fi

# Check target group health check configuration
echo "Checking target group health check configuration..."
TARGET_GROUP_DETAILS=$(aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN)
HEALTH_CHECK_PATH=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].HealthCheckPath')
HEALTH_CHECK_PORT=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].HealthCheckPort')
HEALTH_CHECK_PROTOCOL=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].HealthCheckProtocol')

echo "Health check path: $HEALTH_CHECK_PATH"
echo "Health check port: $HEALTH_CHECK_PORT"
echo "Health check protocol: $HEALTH_CHECK_PROTOCOL"

if [[ "$HEALTH_CHECK_PATH" == *"nonexistent"* ]]; then
    echo "✅ Health check path is configured to a non-existent path as expected."
else
    echo "❌ Health check path does not appear to be misconfigured: $HEALTH_CHECK_PATH"
    echo "Expected a path containing 'nonexistent'."
fi

# Check target health in the target group
echo "Checking target health in target group..."
TARGETS=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN)
TARGET_COUNT=$(echo $TARGETS | jq '.TargetHealthDescriptions | length')

if [ $TARGET_COUNT -eq 0 ]; then
    echo "No targets registered to the target group yet."
    echo "Tasks may still be starting up. Wait a few moments and try again."
else
    UNHEALTHY_COUNT=0
    for (( i=0; i<$TARGET_COUNT; i++ )); do
        TARGET_HEALTH=$(echo $TARGETS | jq -r ".TargetHealthDescriptions[$i].TargetHealth.State")
        TARGET_IP=$(echo $TARGETS | jq -r ".TargetHealthDescriptions[$i].Target.Id")
        TARGET_REASON=$(echo $TARGETS | jq -r ".TargetHealthDescriptions[$i].TargetHealth.Reason")
        echo "Target $TARGET_IP health: $TARGET_HEALTH"
        echo "Reason: $TARGET_REASON"

        if [ "$TARGET_HEALTH" != "healthy" ]; then
            UNHEALTHY_COUNT=$((UNHEALTHY_COUNT + 1))
        fi
    done

    if [ $UNHEALTHY_COUNT -gt 0 ]; then
        echo "✅ Found $UNHEALTHY_COUNT unhealthy targets as expected."
    else
        echo "❌ All targets are healthy. This is unexpected for this test scenario."
    fi
fi

# Check for service events related to load balancer issues
echo "Checking service events for load balancer issues..."
SERVICE_EVENTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].events')
echo "$SERVICE_EVENTS" | grep -i -e "health" -e "check" -e "load balancer" -e "target" -e "unhealthy"

if [ $? -eq 0 ]; then
    echo "✅ Found load balancer health check related messages in service events."
else
    echo "❓ No clear load balancer health check related messages found in service events."
fi

# Get running tasks to check their status
echo "Checking task status..."
TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --desired-status RUNNING --query 'taskArns' --output text)

if [ -n "$TASKS" ]; then
    TASK_ARN=$(echo $TASKS | tr '\t' '\n' | head -1)
    echo "Found running task: $TASK_ARN"

    # Get task details
    TASK_DETAILS=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN)
    LAST_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].lastStatus')
    HEALTH_STATUS=$(echo $TASK_DETAILS | jq -r '.tasks[0].healthStatus')

    echo "Task status: $LAST_STATUS"
    echo "Health status: $HEALTH_STATUS"

    if [ "$LAST_STATUS" == "RUNNING" ]; then
        echo "✅ Task is running but likely failing load balancer health checks."
    fi
else
    echo "No running tasks found for service $SERVICE_NAME."
    echo "Tasks might be failing to start. Use 'aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --desired-status STOPPED' to check for stopped tasks."
fi

echo -e "\nLoad balancer DNS name for testing:"
LB_ARN=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].LoadBalancerArns[0]')
LB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $LB_ARN --query 'LoadBalancers[0].DNSName' --output text)
echo "http://$LB_DNS/"
echo "Note: Accessing this URL will likely return a 502 Bad Gateway error due to failed health checks."

echo -e "\nScenario is now ready for LLM troubleshooting testing."
echo "For reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "SERVICE_NAME=$SERVICE_NAME"
echo "TARGET_GROUP_ARN=$TARGET_GROUP_ARN"
echo "HEALTH_CHECK_PATH=$HEALTH_CHECK_PATH"
