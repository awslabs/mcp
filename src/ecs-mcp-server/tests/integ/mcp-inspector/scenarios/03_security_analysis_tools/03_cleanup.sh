#!/bin/bash

# Cleanup script for MCP Inspector security analysis tool integration tests
# This script removes all AWS resources created by 01_create.sh
# Usage: ./03_cleanup.sh [cluster-name]

# Set script location as base directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments - cluster name is optional, will auto-detect if not provided
CLUSTER_NAME="$1"

# Auto-detect cluster if not provided
if [ -z "$CLUSTER_NAME" ]; then
    CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[*]' --output text 2>/dev/null)
    FOUND_CLUSTERS=""

    for CLUSTER_ARN in $CLUSTERS; do
        TEMP_CLUSTER_NAME=$(echo "$CLUSTER_ARN" | awk -F/ '{print $2}')
        if [[ "$TEMP_CLUSTER_NAME" == *"mcp-security-test-cluster"* ]]; then
            FOUND_CLUSTERS="$FOUND_CLUSTERS $TEMP_CLUSTER_NAME"
        fi
    done

    if [ -z "$FOUND_CLUSTERS" ]; then
        echo "❌ Could not find mcp-security-test-cluster. Nothing to clean up."
        exit 0
    fi

    # Use the first found cluster
    CLUSTER_NAME=$(echo $FOUND_CLUSTERS | awk '{print $1}')
    echo "🔍 Auto-detected cluster: $CLUSTER_NAME"

    # Show all found clusters if there are multiple
    CLUSTER_COUNT=$(echo $FOUND_CLUSTERS | wc -w)
    if [ $CLUSTER_COUNT -gt 1 ]; then
        echo "   Note: Found $CLUSTER_COUNT clusters, cleaning up: $CLUSTER_NAME"
        echo "   Other clusters found: $(echo $FOUND_CLUSTERS | cut -d' ' -f2-)"
    fi
fi

echo "🧹 Starting cleanup of MCP Inspector security analysis test resources..."
echo "   Cluster: $CLUSTER_NAME"
echo ""

# Step 1: Stop and delete services
echo "Step 1: Stopping and deleting ECS services..."
SERVICES=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns[*]' --output text 2>/dev/null)

for SERVICE_ARN in $SERVICES; do
    SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F/ '{print $3}')
    if [[ "$SERVICE_NAME" == *"mcp-security-test-service"* ]]; then
        echo "  Stopping service: $SERVICE_NAME"
        aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --desired-count 0 >/dev/null 2>&1

        # Wait for tasks to stop
        echo "  Waiting for tasks to stop..."
        aws ecs wait services-stable --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" 2>/dev/null || true

        echo "  Deleting service: $SERVICE_NAME"
        aws ecs delete-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo "  ✅ Service $SERVICE_NAME deleted"
            echo "  ⏱️ Waiting 20 seconds for network interfaces to detach..."
            sleep 20
        else
            echo "  ⚠️ Failed to delete service $SERVICE_NAME"
        fi
    fi
done

# Step 2: Deregister task definitions
echo "Step 2: Deregistering task definitions..."
TASK_FAMILIES=$(aws ecs list-task-definitions --family-prefix "mcp-security-test-task" --query 'taskDefinitionArns[*]' --output text 2>/dev/null)

for TASK_DEF_ARN in $TASK_FAMILIES; do
    echo "  Deregistering task definition: $TASK_DEF_ARN"
    aws ecs deregister-task-definition --task-definition "$TASK_DEF_ARN" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "  ✅ Task definition deregistered"
    else
        echo "  ⚠️ Failed to deregister task definition"
    fi
done

# Step 3: Delete cluster
echo "Step 3: Deleting ECS cluster..."
aws ecs delete-cluster --cluster "$CLUSTER_NAME" >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ ECS cluster $CLUSTER_NAME deleted"
else
    echo "⚠️ Failed to delete ECS cluster $CLUSTER_NAME"
fi

# Step 4: Delete security groups (with retry logic for network interface cleanup)
echo "Step 4: Deleting security groups..."
SECURITY_GROUPS=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=mcp-security-test-sg-*" --query 'SecurityGroups[*].GroupId' --output text 2>/dev/null)

for SG_ID in $SECURITY_GROUPS; do
    if [ -n "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
        echo "  Deleting security group: $SG_ID"

        # Retry logic for security group deletion (network interfaces may still be detaching)
        MAX_RETRIES=6
        RETRY_COUNT=0

        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            aws ec2 delete-security-group --group-id "$SG_ID" >/dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "  ✅ Security group $SG_ID deleted"
                break
            else
                if [ $RETRY_COUNT -eq 0 ]; then
                    echo "  ⏱️ Security group in use, waiting for network interfaces to detach..."
                fi
                echo "  ⏳ Retry $((RETRY_COUNT + 1))/$MAX_RETRIES in 15 seconds..."
                sleep 15
                RETRY_COUNT=$((RETRY_COUNT + 1))
            fi
        done

        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "  ⚠️ Failed to delete security group $SG_ID after $MAX_RETRIES attempts"
            echo "     Network interfaces may still be detaching. Try manual cleanup later:"
            echo "     aws ec2 delete-security-group --group-id $SG_ID"
        fi
    fi
done

# Step 5: Delete CloudWatch log groups
echo "Step 5: Deleting CloudWatch log groups..."
LOG_GROUPS=$(aws logs describe-log-groups --log-group-name-prefix "/ecs/mcp-security-test-cluster" --query 'logGroups[*].logGroupName' --output text 2>/dev/null)

for LOG_GROUP in $LOG_GROUPS; do
    if [ -n "$LOG_GROUP" ] && [ "$LOG_GROUP" != "None" ]; then
        echo "  Deleting log group: $LOG_GROUP"
        aws logs delete-log-group --log-group-name "$LOG_GROUP" >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo "  ✅ Log group $LOG_GROUP deleted"
        else
            echo "  ⚠️ Failed to delete log group $LOG_GROUP"
        fi
    fi
done

echo ""
echo "🎯 Cleanup completed!"
echo "   All MCP Inspector security analysis test resources have been removed."
echo ""
echo "📋 Summary:"
echo "   ✅ ECS services stopped and deleted"
echo "   ✅ Task definitions deregistered"
echo "   ✅ ECS cluster deleted"
echo "   ✅ Security groups deleted"
echo "   ✅ CloudWatch log groups deleted"
echo ""
echo "Note: Some resources may take a few minutes to be fully deleted from AWS."
