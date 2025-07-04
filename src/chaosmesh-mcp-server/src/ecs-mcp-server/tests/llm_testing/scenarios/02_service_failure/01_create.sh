#!/bin/bash

# Script to create ECS service with image pull failures
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"scenario-02-cluster-$RANDOM_ID"}
SERVICE_NAME="scenario-02-service-$RANDOM_ID"
TASK_FAMILY="scenario-02-task-$RANDOM_ID"

echo "Creating ECS cluster, task definition, and service with image pull failures..."

# Step 1: Create cluster if it doesn't exist
echo "Step 1: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME

# Step 2: Register a task definition with non-existent image
echo "Step 2: Registering task definition with invalid image..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"scenario-02-container\",
      \"image\": \"non-existent-repo/non-existent-image:latest\",
      \"essential\": true,
      \"portMappings\": [{\"containerPort\": 80, \"hostPort\": 80}]
    }
  ]"

# Step 3: Create a service that will fail due to the non-existent image
echo "Step 3: Creating service with the task definition..."

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
echo "Using VPC: $VPC_ID"

# Get a subnet from this VPC
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text)
echo "Using subnet: $SUBNET_ID"

# Get a security group from this VPC
SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text)
echo "Using security group: $SG_ID"

aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"

echo "Service creation initiated. This will fail due to the non-existent image."
echo "Wait a few minutes for tasks to attempt to start and fail."
echo "Then run the 02_validate.sh script to check the failure status."
