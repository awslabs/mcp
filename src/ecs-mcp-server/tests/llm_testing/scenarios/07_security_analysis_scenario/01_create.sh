#!/bin/bash

# Script to create ECS cluster with intentional security misconfigurations for LLM testing
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"llm-test-security-cluster-$RANDOM_ID"}
SERVICE_NAME="llm-test-security-service-$RANDOM_ID"
TASK_FAMILY="llm-test-security-task-$RANDOM_ID"

echo "Creating ECS cluster with intentional security misconfigurations for LLM testing..."

# Step 1: Create cluster with security issues (disabled logging)
echo "Step 1: Creating ECS cluster with disabled execute command logging..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME --configuration executeCommandConfiguration='{logging=NONE}'

# Step 2: Register a task definition with security issues
echo "Step 2: Registering task definition with security misconfigurations..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --task-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"security-test-container\",
      \"image\": \"nginx:latest\",
      \"essential\": true,
      \"user\": \"root\",
      \"portMappings\": [{\"containerPort\": 80}],
      \"environment\": [
        {\"name\": \"SECRET_KEY\", \"value\": \"hardcoded-secret-123\"},
        {\"name\": \"DATABASE_PASSWORD\", \"value\": \"admin123\"},
        {\"name\": \"API_TOKEN\", \"value\": \"sk-1234567890abcdef\"}
      ]
    }
  ]"

# Step 3: Create a service with security issues
echo "Step 3: Creating service with security misconfigurations..."

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
echo "Using VPC: $VPC_ID"

# Get a subnet from this VPC
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text)
echo "Using subnet: $SUBNET_ID"

# Create security group with overly permissive rules
SG_ID=$(aws ec2 create-security-group \
  --group-name "llm-test-security-sg-$RANDOM_ID" \
  --description "Security group with intentional security issues for LLM testing" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Add overly permissive inbound rules (security issues)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0

echo "Using security group with permissive rules: $SG_ID"

aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --enable-execute-command

echo "Service creation initiated with intentional security misconfigurations:"
echo "• Execute command logging disabled"
echo "• Container running as root user"
echo "• Hardcoded secrets in environment variables"
echo "• Overly permissive security group rules"
echo "• Public IP assignment enabled"
echo ""
echo "Wait a few minutes for the service to stabilize."
echo "Then run the 02_validate.sh script to verify the setup."
