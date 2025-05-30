#!/bin/bash

# Script to clean up resources created for network configuration failure testing
# Usage: ./05_cleanup.sh [cluster-name] [service-name] [security-group-id]

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
        echo "Could not find a recent scenario-04-cluster. Please provide a cluster name."
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

    if [ -z "$SERVICE_NAME" ]; then
        echo "No service found in cluster $CLUSTER_NAME. Proceeding with cleanup."
    fi
else
    SERVICE_NAME=$2
fi

# If no security group ID is provided, try to find security groups with our pattern
if [ -z "$3" ]; then
    SG_LIST=$(aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId,GroupName]' --output json)
    SG_ID=$(echo $SG_LIST | jq -r '.[] | select(.[1] | contains("scenario-04-sg")) | .[0]' | head -1)

    if [ -z "$SG_ID" ]; then
        echo "Could not find a security group with 'scenario-04-sg' in the name. Please provide a security group ID."
        # Continue anyway, we'll skip security group deletion
    else
        echo "Found test security group: $SG_ID"
    fi
else
    SG_ID=$3
fi

echo "Starting cleanup of resources..."

# Step 1: Update service to 0 tasks if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 1: Updating service $SERVICE_NAME to 0 tasks..."
    aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 > /dev/null 2>&1
    echo "Waiting for tasks to stop..."
    sleep 10
fi

# Step 2: Delete service if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 2: Deleting service $SERVICE_NAME..."
    aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force > /dev/null 2>&1
    echo "Waiting for service deletion..."
    sleep 10
fi

# Step 3: Find and deregister task definition
echo "Step 3: Finding and deregistering task definition..."
TASK_DEF_ARN=$(aws ecs list-task-definitions --family-prefix scenario-04-task --query 'taskDefinitionArns[0]' --output text)
if [[ "$TASK_DEF_ARN" != "None" ]] && [ -n "$TASK_DEF_ARN" ]; then
    echo "Deregistering task definition $TASK_DEF_ARN..."
    aws ecs deregister-task-definition --task-definition $TASK_DEF_ARN > /dev/null 2>&1
fi

# Step 4: Delete the cluster
echo "Step 4: Deleting cluster $CLUSTER_NAME..."
aws ecs delete-cluster --cluster $CLUSTER_NAME > /dev/null 2>&1

# Step 5: Delete the security group if found
if [ -n "$SG_ID" ]; then
    echo "Step 5: Deleting security group $SG_ID..."
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

# Step 6: Delete CloudWatch log group
echo "Step 6: Deleting CloudWatch log group..."
LOG_GROUP="/ecs/${CLUSTER_NAME}/*"
aws logs describe-log-groups --log-group-name-prefix "/ecs/${CLUSTER_NAME}" --query 'logGroups[*].logGroupName' --output text | tr '\t' '\n' | while read -r GROUP; do
    echo "Deleting log group $GROUP..."
    aws logs delete-log-group --log-group-name "$GROUP" > /dev/null 2>&1
done

echo "Cleanup completed."
