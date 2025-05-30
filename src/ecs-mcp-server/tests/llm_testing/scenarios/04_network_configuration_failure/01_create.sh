#!/bin/bash

# Script to create ECS service with network configuration failures
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"scenario-04-cluster-$RANDOM_ID"}
SERVICE_NAME="scenario-04-service-$RANDOM_ID"
TASK_FAMILY="scenario-04-task-$RANDOM_ID"
SG_NAME="scenario-04-sg-$RANDOM_ID"
LOG_GROUP="/ecs/${CLUSTER_NAME}/${TASK_FAMILY}"

echo "Creating ECS cluster, task definition, and service with network configuration failures..."

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

# Step 5: Create an overly restrictive security group
echo "Step 5: Creating overly restrictive security group..."
SG_DESCRIPTION="Security group with no outbound access for testing network failures"
SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME --description "$SG_DESCRIPTION" --vpc-id $VPC_ID --query 'GroupId' --output text)
echo "Created security group: $SG_NAME ($SG_ID)"

# Step 6: Remove all outbound rules - this will prevent container from accessing internet or other services
echo "Step 6: Removing all default outbound rules from security group..."
aws ec2 revoke-security-group-egress --group-id $SG_ID --ip-permissions '[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]'

# Step 7: Register a task definition with nginx container that needs internet access
echo "Step 7: Registering task definition with nginx container..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"scenario-04-container\",
      \"image\": \"nginx:latest\",
      \"essential\": true,
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"${LOG_GROUP}\",
          \"awslogs-region\": \"$(aws configure get region)\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"portMappings\": [{\"containerPort\": 80, \"hostPort\": 80}],
      \"healthCheck\": {
        \"command\": [\"CMD-SHELL\", \"curl -f http://localhost/ || exit 1\"],
        \"interval\": 30,
        \"timeout\": 5,
        \"retries\": 3
      }
    }
  ]"

# Step 8: Create service with restrictive security group
echo "Step 8: Creating service with restricted security group..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"

echo "Service creation initiated. This will fail due to network restrictions."
echo "The restricted security group prevents outbound traffic, so the container will fail to pull images and make network connections."
echo "Wait a few minutes for the tasks to attempt to start and fail."
echo "Then run the 02_validate.sh script to check the failure status."
echo ""
echo "For reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "SERVICE_NAME=$SERVICE_NAME"
echo "SECURITY_GROUP_ID=$SG_ID"
