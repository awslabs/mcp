#!/bin/bash

# Script to create ECS service with load balancer health check failures
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"scenario-06-cluster-$RANDOM_ID"}
SERVICE_NAME="scenario-06-service-$RANDOM_ID"
TASK_FAMILY="scenario-06-task-$RANDOM_ID"
LB_NAME="scenario-06-alb-$RANDOM_ID"
TG_NAME="scenario-06-tg-$RANDOM_ID"
LOG_GROUP="/ecs/${CLUSTER_NAME}/${TASK_FAMILY}"

echo "Creating ECS cluster, load balancer, and service with health check failures..."

# Step 1: Create cluster
echo "Step 1: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME

# Step 2: Create CloudWatch log group
echo "Step 2: Creating CloudWatch log group..."
aws logs create-log-group --log-group-name $LOG_GROUP

# Step 3: Get default VPC
echo "Step 3: Getting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
echo "Using VPC: $VPC_ID"

# Step 4: Get subnets from this VPC (at least two for ALB)
echo "Step 4: Getting subnets from VPC..."
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0:2].SubnetId" --output text)
SUBNET_ID_1=$(echo $SUBNET_IDS | awk '{print $1}')
SUBNET_ID_2=$(echo $SUBNET_IDS | awk '{print $2}')
echo "Using subnets: $SUBNET_ID_1 $SUBNET_ID_2"

# Step 5: Create security group for ALB
echo "Step 5: Creating security group for ALB..."
SG_DESCRIPTION="Security group for load balancer testing"
ALB_SG_ID=$(aws ec2 create-security-group --group-name scenario-06-sg-$RANDOM_ID --description "$SG_DESCRIPTION" --vpc-id $VPC_ID --query 'GroupId' --output text)
echo "Created security group for ALB: $ALB_SG_ID"

# Step 6: Allow inbound HTTP on the security group
echo "Step 6: Configuring security group to allow HTTP..."
aws ec2 authorize-security-group-ingress --group-id $ALB_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0

# Step 7: Create the Application Load Balancer
echo "Step 7: Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name $LB_NAME \
  --subnets $SUBNET_ID_1 $SUBNET_ID_2 \
  --security-groups $ALB_SG_ID \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)
echo "Created ALB: $ALB_ARN"

# Wait for the ALB to be active
echo "Waiting for ALB to become active..."
aws elbv2 wait load-balancer-available --load-balancer-arns $ALB_ARN

# Step 8: Create a target group with incorrectly configured health check
echo "Step 8: Creating target group with misconfigured health check..."
TG_ARN=$(aws elbv2 create-target-group \
  --name $TG_NAME \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/nonexistent-path" \
  --health-check-interval-seconds 10 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 2 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)
echo "Created target group: $TG_ARN"

# Step 9: Create listener on the ALB that forwards to the target group
echo "Step 9: Creating listener on ALB..."
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --query 'Listeners[0].ListenerArn' \
  --output text)
echo "Created listener: $LISTENER_ARN"

# Step 10: Register a task definition with nginx container
echo "Step 10: Registering task definition with nginx container..."
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  --execution-role-arn $(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text) \
  --container-definitions "[
    {
      \"name\": \"scenario-06-container\",
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
      \"portMappings\": [{\"containerPort\": 80, \"hostPort\": 80}]
    }
  ]"

# Step 11: Create service with the load balancer
echo "Step 11: Creating service with ALB integration..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID_1],securityGroups=[$ALB_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=scenario-06-container,containerPort=80"

echo "Service creation initiated. The tasks will launch but fail the load balancer health checks."
echo "The health check is configured to look for /nonexistent-path which nginx won't serve."
echo "Wait a few minutes for the tasks to start and then run the 02_validate.sh script to check the failure status."
echo ""
echo "For reference, save these values for Cline prompts:"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "SERVICE_NAME=$SERVICE_NAME"
echo "LOAD_BALANCER_ARN=$ALB_ARN"
echo "TARGET_GROUP_ARN=$TG_ARN"
