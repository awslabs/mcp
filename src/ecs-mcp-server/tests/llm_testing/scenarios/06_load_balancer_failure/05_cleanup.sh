#!/bin/bash

# Script to clean up resources created for load balancer health check failure testing
# Usage: ./05_cleanup.sh [cluster-name] [service-name]

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
        echo "Could not find a recent scenario-06-cluster. Please provide a cluster name."
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

    if [ -z "$SERVICE_NAME" ]; then
        echo "No service found in cluster $CLUSTER_NAME. Proceeding with cleanup of other resources."
    fi
else
    SERVICE_NAME=$2
fi

echo "Starting cleanup of resources..."

# Step 1: Find the load balancer and target group
echo "Step 1: Finding load balancer and target group associated with the service..."

# First try to get the target group from the service if it exists
if [ -n "$SERVICE_NAME" ]; then
    SERVICE_DETAILS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME 2>/dev/null)
    if [ $? -eq 0 ]; then
        TARGET_GROUP_ARN=$(echo $SERVICE_DETAILS | jq -r '.services[0].loadBalancers[0].targetGroupArn')

        if [ -n "$TARGET_GROUP_ARN" ] && [ "$TARGET_GROUP_ARN" != "null" ]; then
            echo "Found target group: $TARGET_GROUP_ARN"

            # Get the load balancer ARN from the target group
            TARGET_GROUP_DETAILS=$(aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN 2>/dev/null)
            if [ $? -eq 0 ]; then
                LOAD_BALANCER_ARN=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].LoadBalancerArns[0]')
                if [ -n "$LOAD_BALANCER_ARN" ] && [ "$LOAD_BALANCER_ARN" != "null" ]; then
                    echo "Found load balancer: $LOAD_BALANCER_ARN"
                fi
            fi
        fi
    fi
fi

# If we couldn't find them by service, try by name pattern
if [ -z "$TARGET_GROUP_ARN" ] || [ "$TARGET_GROUP_ARN" == "null" ]; then
    echo "Trying to find target group by name pattern..."
    TARGET_GROUPS=$(aws elbv2 describe-target-groups --query "TargetGroups[?starts_with(TargetGroupName, 'scenario-06-tg')].TargetGroupArn" --output text)
    if [ -n "$TARGET_GROUPS" ]; then
        TARGET_GROUP_ARN=$(echo $TARGET_GROUPS | tr '\t' '\n' | head -1)
        echo "Found target group: $TARGET_GROUP_ARN"

        # Get the load balancer ARN from the target group
        TARGET_GROUP_DETAILS=$(aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN 2>/dev/null)
        if [ $? -eq 0 ]; then
            LOAD_BALANCER_ARN=$(echo $TARGET_GROUP_DETAILS | jq -r '.TargetGroups[0].LoadBalancerArns[0]')
            if [ -n "$LOAD_BALANCER_ARN" ] && [ "$LOAD_BALANCER_ARN" != "null" ]; then
                echo "Found load balancer: $LOAD_BALANCER_ARN"
            fi
        fi
    fi
fi

# If we still couldn't find the load balancer, try by name pattern
if [ -z "$LOAD_BALANCER_ARN" ] || [ "$LOAD_BALANCER_ARN" == "null" ]; then
    echo "Trying to find load balancer by name pattern..."
    LOAD_BALANCERS=$(aws elbv2 describe-load-balancers --query "LoadBalancers[?starts_with(LoadBalancerName, 'scenario-06-alb')].LoadBalancerArn" --output text)
    if [ -n "$LOAD_BALANCERS" ]; then
        LOAD_BALANCER_ARN=$(echo $LOAD_BALANCERS | tr '\t' '\n' | head -1)
        echo "Found load balancer: $LOAD_BALANCER_ARN"
    fi
fi

# Step 2: Update service to 0 tasks if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 2: Updating service $SERVICE_NAME to 0 tasks..."
    aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 > /dev/null 2>&1
    echo "Waiting for tasks to stop..."
    sleep 10
fi

# Step 3: Delete service if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 3: Deleting service $SERVICE_NAME..."
    aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force > /dev/null 2>&1
    echo "Waiting for service deletion..."
    sleep 10
fi

# Step 4: Find and deregister task definition
echo "Step 4: Finding and deregistering task definition..."
TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix scenario-06-task --query 'taskDefinitionArns[0]' --output text)
if [[ "$TASK_DEF_ARN" != "None" ]] && [ -n "$TASK_DEF_ARN" ]; then
    echo "Deregistering task definition $TASK_DEF_ARN..."
    aws ecs deregister-task-definition --task-definition $TASK_DEF_ARN > /dev/null 2>&1
fi

# Step 5: Delete listeners if load balancer found
if [ -n "$LOAD_BALANCER_ARN" ] && [ "$LOAD_BALANCER_ARN" != "null" ]; then
    echo "Step 5: Deleting listeners..."
    LISTENERS=$(aws elbv2 describe-listeners --load-balancer-arn $LOAD_BALANCER_ARN --query 'Listeners[*].ListenerArn' --output text)
    if [ -n "$LISTENERS" ]; then
        for LISTENER_ARN in $LISTENERS; do
            echo "Deleting listener $LISTENER_ARN..."
            aws elbv2 delete-listener --listener-arn $LISTENER_ARN > /dev/null 2>&1
        done
    fi
fi

# Step 6: Delete target group if found
if [ -n "$TARGET_GROUP_ARN" ] && [ "$TARGET_GROUP_ARN" != "null" ]; then
    echo "Step 6: Deleting target group $TARGET_GROUP_ARN..."
    aws elbv2 delete-target-group --target-group-arn $TARGET_GROUP_ARN > /dev/null 2>&1
fi

# Step 7: Delete load balancer if found
if [ -n "$LOAD_BALANCER_ARN" ] && [ "$LOAD_BALANCER_ARN" != "null" ]; then
    echo "Step 7: Deleting load balancer $LOAD_BALANCER_ARN..."
    aws elbv2 delete-load-balancer --load-balancer-arn $LOAD_BALANCER_ARN > /dev/null 2>&1
    echo "Waiting for load balancer deletion..."
    sleep 10
fi

# Step 8: Find and delete security group
echo "Step 8: Finding and deleting security group..."
SG_LIST=$(aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId,GroupName]' --output json)
SG_ID=$(echo $SG_LIST | jq -r '.[] | select(.[1] | contains("scenario-06-sg")) | .[0]' | head -1)
if [ -n "$SG_ID" ]; then
    echo "Found security group: $SG_ID"

    # In case the security group is still in use, we'll retry a few times
    MAX_RETRIES=5
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        aws ec2 delete-security-group --group-id $SG_ID > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "Security group deleted successfully."
            break
        else
            echo "Security group deletion failed. It may still be in use. Retrying in 10 seconds..."
            sleep 10
            RETRY_COUNT=$((RETRY_COUNT + 1))
        fi
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "Could not delete security group after $MAX_RETRIES attempts. It may still be in use by other resources."
        echo "You may need to delete it manually later: aws ec2 delete-security-group --group-id $SG_ID"
    fi
fi

# Step 9: Delete the cluster
echo "Step 9: Deleting cluster $CLUSTER_NAME..."
aws ecs delete-cluster --cluster $CLUSTER_NAME > /dev/null 2>&1

# Step 10: Delete CloudWatch log group
echo "Step 10: Deleting CloudWatch log group..."
LOG_GROUP="/ecs/${CLUSTER_NAME}/*"
aws logs describe-log-groups --log-group-name-prefix "/ecs/${CLUSTER_NAME}" --query 'logGroups[*].logGroupName' --output text | tr '\t' '\n' | while read -r GROUP; do
    echo "Deleting log group $GROUP..."
    aws logs delete-log-group --log-group-name "$GROUP" > /dev/null 2>&1
done

echo "Cleanup completed."
