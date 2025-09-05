#!/bin/bash

# Script to clean up resources created for MCP Inspector troubleshooting tool integration tests
# Usage: ./03_cleanup.sh [cluster-name] [service-name] [security-group-id]

# Set script location as base directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧹 Starting cleanup of MCP integration test resources..."

# If no cluster name is provided, look for the most recently created cluster matching our pattern
if [ -z "$1" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text)

    # Loop through clusters to find one matching our pattern
    for CLUSTER_ARN in $CLUSTERS; do
        CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$CLUSTER_NAME" == *"mcp-integration-test-cluster"* ]]; then
            echo "🔍 Found test cluster: $CLUSTER_NAME"
            break
        fi
    done

    if [ -z "$CLUSTER_NAME" ] || [[ "$CLUSTER_NAME" != *"mcp-integration-test-cluster"* ]]; then
        echo "❌ Could not find a recent mcp-integration-test-cluster. Please provide a cluster name."
        echo "Usage: $0 <cluster-name> [service-name] [security-group-id]"
        exit 1
    fi
else
    CLUSTER_NAME=$1
fi

# If no service name is provided, look for services in the cluster
if [ -z "$2" ]; then
    SERVICES=$(aws ecs list-services --cluster $CLUSTER_NAME --query 'serviceArns[*]' --output text 2>/dev/null)

    # Loop through services to find one matching our pattern
    for SERVICE_ARN in $SERVICES; do
        SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F/ '{print $3}')
        if [[ "$SERVICE_NAME" == *"mcp-integration-test-service"* ]]; then
            echo "🔍 Found test service: $SERVICE_NAME"
            break
        fi
    done

    if [ -z "$SERVICE_NAME" ]; then
        echo "⚠️ No service found matching 'mcp-integration-test-service' pattern in cluster $CLUSTER_NAME."
        echo "   Proceeding with cluster cleanup only."
    fi
else
    SERVICE_NAME=$2
fi

# If no security group ID is provided, try to find security groups with our pattern
if [ -z "$3" ]; then
    SG_LIST=$(aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId,GroupName]' --output json 2>/dev/null)
    SG_ID=$(echo $SG_LIST | jq -r '.[] | select(.[1] | contains("mcp-integration-test-sg")) | .[0]' | head -1)

    if [ -z "$SG_ID" ] || [ "$SG_ID" == "null" ]; then
        echo "⚠️ Could not find a security group with 'mcp-integration-test-sg' in the name."
        echo "   Skipping security group cleanup."
    else
        echo "🔍 Found test security group: $SG_ID"
    fi
else
    SG_ID=$3
fi

echo ""
echo "Cleaning up resources:"
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Security Group: $SG_ID"
echo ""

# Step 1: Update service to 0 tasks if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 1: Updating service $SERVICE_NAME to 0 tasks..."
    aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Service updated to 0 tasks"
        echo "⏱️ Waiting 15 seconds for tasks to stop..."
        sleep 15
    else
        echo "⚠️ Failed to update service (may not exist)"
    fi
fi

# Step 2: Delete service if it exists
if [ -n "$SERVICE_NAME" ]; then
    echo "Step 2: Deleting service $SERVICE_NAME..."
    aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Service deletion initiated"
        echo "⏱️ Waiting 15 seconds for service deletion..."
        sleep 15
    else
        echo "⚠️ Failed to delete service (may not exist)"
    fi
fi

# Step 3: Find and deregister task definition
echo "Step 3: Finding and deregistering task definitions..."
TASK_DEF_ARNS=$(aws ecs list-task-definitions --family-prefix mcp-integration-test-task --query 'taskDefinitionArns[*]' --output text 2>/dev/null)

if [ -n "$TASK_DEF_ARNS" ] && [ "$TASK_DEF_ARNS" != "None" ]; then
    for TASK_DEF_ARN in $TASK_DEF_ARNS; do
        echo "   Deregistering task definition $TASK_DEF_ARN..."
        aws ecs deregister-task-definition --task-definition $TASK_DEF_ARN > /dev/null 2>&1
    done
    echo "✅ Task definitions deregistered"
else
    echo "⚠️ No task definitions found to deregister"
fi

# Step 4: Delete the cluster
echo "Step 4: Deleting cluster $CLUSTER_NAME..."
aws ecs delete-cluster --cluster $CLUSTER_NAME > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Cluster deletion initiated"
else
    echo "⚠️ Failed to delete cluster (may not exist)"
fi

# Step 5: Delete the security group if found
if [ -n "$SG_ID" ] && [ "$SG_ID" != "null" ]; then
    echo "Step 5: Deleting security group $SG_ID..."
    # Retry logic for security group deletion (may be in use temporarily)
    MAX_RETRIES=5
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        aws ec2 delete-security-group --group-id $SG_ID > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Security group deleted successfully"
            break
        else
            echo "⚠️ Security group deletion failed. It may still be in use. Retrying in 10 seconds..."
            sleep 10
            RETRY_COUNT=$((RETRY_COUNT + 1))
        fi
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "❌ Could not delete security group after $MAX_RETRIES attempts."
        echo "   It may still be in use by other resources."
        echo "   Manual cleanup: aws ec2 delete-security-group --group-id $SG_ID"
    fi
else
    echo "Step 5: No security group to delete"
fi

# Step 6: Delete CloudWatch log groups
echo "Step 6: Deleting CloudWatch log groups..."
LOG_GROUPS=$(aws logs describe-log-groups --log-group-name-prefix "/ecs/${CLUSTER_NAME}" --query 'logGroups[*].logGroupName' --output text 2>/dev/null)

if [ -n "$LOG_GROUPS" ] && [ "$LOG_GROUPS" != "None" ]; then
    echo "$LOG_GROUPS" | tr '\t' '\n' | while read -r GROUP; do
        if [ -n "$GROUP" ]; then
            echo "   Deleting log group: $GROUP"
            aws logs delete-log-group --log-group-name "$GROUP" > /dev/null 2>&1
        fi
    done
    echo "✅ CloudWatch log groups cleaned up"
else
    echo "⚠️ No CloudWatch log groups found to delete"
fi

echo ""
echo "🎯 Cleanup completed!"
echo "   All MCP integration test resources should be removed."
echo "   If any resources remain, they can be cleaned up manually using the AWS CLI or console."
echo ""
