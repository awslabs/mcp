#!/bin/bash

# Script to create ECS task with resource constraint failures
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"scenario-05-cluster-$RANDOM_ID"}
TASK_FAMILY="scenario-05-task-$RANDOM_ID"
LOG_GROUP="/ecs/${CLUSTER_NAME}/${TASK_FAMILY}"

echo "Creating ECS cluster and task definition with excessive resource requirements..."

# Step 1: Create cluster if it doesn't exist
echo "Step 1: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME

# Step 2: Create CloudWatch log group
echo "Step 2: Creating CloudWatch log group..."
aws logs create-log-group --log-group-name $LOG_GROUP

# Step 3: Get default VPC
echo "Step 3: Getting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
echo "Using VPC: $VPC_ID"

# Step 4: Get a subnet from this VPC
echo "Step 4: Getting subnet from VPC..."
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text)
echo "Using subnet: $SUBNET_ID"

# Step 5: Get a security group from this VPC
echo "Step 5: Getting security group from VPC..."
SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text)
echo "Using security group: $SG_ID"

# Step 6: Register an extreme task definition with either:
# - Memory requirements beyond Fargate maximum (120GB)
# - CPU requirements beyond Fargate maximum (16 vCPU)
# Choose one approach depending on your AWS account limits
echo "Step 6: Registering task definition with excessive resource requirements..."

# Approach 1: Using values at the edge of Fargate limits (CPU: 16 vCPU, Memory: 120 GB)
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 16384 \
  --memory 122880 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"scenario-05-container\",
      \"image\": \"amazonlinux:2\",
      \"essential\": true,
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"${LOG_GROUP}\",
          \"awslogs-region\": \"$(aws configure get region)\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"command\": [
        \"sh\",
        \"-c\",
        \"echo 'Installing stress tool...' && amazon-linux-extras install epel -y && yum update -y && yum install -y stress && echo 'Starting memory-intensive application...' && stress --vm 1 --vm-bytes 118G --vm-keep --timeout 10s || echo 'Failed to allocate memory' && sleep 10\"
      ]
    }
  ]"

# Step 7: Try to run the task
echo "Step 7: Running task with resource constraints..."
TASK_RUN=$(aws ecs run-task \
  --cluster $CLUSTER_NAME \
  --task-definition $TASK_FAMILY \
  --count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}")

# Extract task ARN and any failure reasons
FAILURES=$(echo $TASK_RUN | jq -r '.failures')
if [ "$FAILURES" != "[]" ] && [ "$FAILURES" != "null" ]; then
    FAILURE_REASON=$(echo $TASK_RUN | jq -r '.failures[0].reason')
    echo "Task failed to start: $FAILURE_REASON"
    echo "This is the expected behavior for this test scenario."
else
    TASK_ARN=$(echo $TASK_RUN | jq -r '.tasks[0].taskArn')
    echo "Task launched: $TASK_ARN"
    echo "This task will likely fail due to resource constraints when it attempts to run."
fi

echo "Wait a few moments for task deployment to attempt and fail, then use 02_validate.sh to check status."
echo ""
echo "For reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "TASK_FAMILY=$TASK_FAMILY"
