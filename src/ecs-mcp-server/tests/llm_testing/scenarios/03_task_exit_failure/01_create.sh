#!/bin/bash

# Script to create ECS task with exit code failures
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"scenario-03-cluster-$RANDOM_ID"}
TASK_FAMILY="scenario-03-task-$RANDOM_ID"
LOG_GROUP="/ecs/${CLUSTER_NAME}/${TASK_FAMILY}"

echo "Creating ECS cluster and task definition with container that will exit with error code..."

# Step 1: Create cluster if it doesn't exist
echo "Step 1: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME

# Step 2: Create CloudWatch log group
echo "Step 2: Creating CloudWatch log group..."
aws logs create-log-group --log-group-name $LOG_GROUP

# Step 3: Register a task definition with a container that will exit
echo "Step 3: Registering task definition that exits with error code..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"scenario-03-container\",
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
        \"echo 'Starting application...' && echo 'Checking required environment variables...' && echo 'ERROR: Required environment variable DATABASE_URL is not set' && echo 'ERROR: Application cannot start without database connection' && echo 'Application is shutting down' && exit 1\"
      ]
    }
  ]"

# Step 4: Run the task that will fail
echo "Step 4: Running task that will exit with code 1..."

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
echo "Using VPC: $VPC_ID"

# Get a subnet from this VPC
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text)
echo "Using subnet: $SUBNET_ID"

# Get a security group from this VPC
SG_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text)
echo "Using security group: $SG_ID"

TASK_RUN=$(aws ecs run-task \
  --cluster $CLUSTER_NAME \
  --task-definition $TASK_FAMILY \
  --count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}")

# Extract task ARN for reference
TASK_ARN=$(echo $TASK_RUN | jq -r '.tasks[0].taskArn')

echo "Task launched: $TASK_ARN"
echo "This task will exit with error code 1 after logging error messages."
echo "Expected failure: Exit code 1 due to missing DATABASE_URL environment variable."
echo "Wait a few moments for task to run and fail, then use 02_validate.sh to check status."
echo ""
echo "For reference, save these values:"
echo "CLUSTER_NAME: $CLUSTER_NAME"
echo "TASK_FAMILY: $TASK_FAMILY"
echo "LOG_GROUP: $LOG_GROUP"
echo "TASK_ARN: $TASK_ARN"
