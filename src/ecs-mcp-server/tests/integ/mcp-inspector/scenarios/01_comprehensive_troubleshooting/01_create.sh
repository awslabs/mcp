#!/bin/bash

# Script to create ECS infrastructure for MCP Inspector troubleshooting tool integration tests
# This creates an ECS cluster and service with multiple failure scenarios to test all troubleshooting tools
# Usage: ./01_create.sh [cluster-name]

# Set script location as base directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Generate a random 5-letter ID for uniquely naming resources (self-contained)
generate_random_id() {
    python3 -c "import uuid; print(str(uuid.uuid4()).replace('-', '')[:5])"
}

# Set variables with MCP-specific naming
RANDOM_ID=$(generate_random_id)
CLUSTER_NAME=${1:-"mcp-integration-test-cluster-$RANDOM_ID"}
SERVICE_NAME="mcp-integration-test-service-$RANDOM_ID"
TASK_FAMILY="mcp-integration-test-task-$RANDOM_ID"
SG_NAME="mcp-integration-test-sg-$RANDOM_ID"
LOG_GROUP="/ecs/${CLUSTER_NAME}/${TASK_FAMILY}"

echo "🚀 Creating ECS infrastructure for MCP Inspector troubleshooting tool tests..."
echo "   This will create a scenario with multiple failure types to test all tools"
echo ""
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Task Family: $TASK_FAMILY"
echo "   Security Group: $SG_NAME"
echo ""

# Step 1: Create cluster
echo "Step 1: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME
if [ $? -eq 0 ]; then
    echo "✅ ECS cluster created successfully"
else
    echo "❌ Failed to create ECS cluster"
    exit 1
fi

# Step 2: Create CloudWatch log group
echo "Step 2: Creating CloudWatch log group..."
aws logs create-log-group --log-group-name $LOG_GROUP 2>/dev/null || true
echo "✅ CloudWatch log group ready: $LOG_GROUP"

# Step 3: Get default VPC
echo "Step 3: Getting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "❌ No default VPC found. Please create a VPC first."
    exit 1
fi
echo "✅ Using VPC: $VPC_ID"

# Step 4: Get a subnet from this VPC
echo "Step 4: Getting subnet from VPC..."
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text)
if [ "$SUBNET_ID" == "None" ] || [ -z "$SUBNET_ID" ]; then
    echo "❌ No subnet found in VPC $VPC_ID"
    exit 1
fi
echo "✅ Using subnet: $SUBNET_ID"

# Step 5: Create an overly restrictive security group (causes network failures)
echo "Step 5: Creating restrictive security group for network testing..."
SG_DESCRIPTION="Security group with restricted access for MCP integration testing"
SG_ID=$(aws ec2 create-security-group \
    --group-name $SG_NAME \
    --description "$SG_DESCRIPTION" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text)

if [ $? -eq 0 ]; then
    echo "✅ Security group created: $SG_NAME ($SG_ID)"
else
    echo "❌ Failed to create security group"
    exit 1
fi

# Step 6: Remove default outbound rules to cause network connectivity issues
echo "Step 6: Configuring restrictive network rules..."
aws ec2 revoke-security-group-egress \
    --group-id $SG_ID \
    --ip-permissions '[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]' 2>/dev/null || true

# Add minimal HTTPS outbound for ECR (still restrictive but allows some image pulls to work)
aws ec2 authorize-security-group-egress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 2>/dev/null || true

echo "✅ Network restrictions configured (blocks most traffic, allows HTTPS for ECR)"

# Step 7: Register task definition with mix of valid and invalid images
echo "Step 7: Registering task definition with mixed container scenarios..."

# Get the ecsTaskExecutionRole ARN
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text 2>/dev/null)
if [ "$EXECUTION_ROLE_ARN" == "None" ] || [ -z "$EXECUTION_ROLE_ARN" ]; then
    echo "⚠️ ecsTaskExecutionRole not found, proceeding without execution role"
    EXECUTION_ROLE_FLAG=""
else
    EXECUTION_ROLE_FLAG="--execution-role-arn $EXECUTION_ROLE_ARN"
    echo "✅ Using execution role: $EXECUTION_ROLE_ARN"
fi

# Register task definition with multiple containers for comprehensive testing
aws ecs register-task-definition \
  --family $TASK_FAMILY \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 256 \
  --memory 512 \
  $EXECUTION_ROLE_FLAG \
  --container-definitions '[
    {
      "name": "main-container",
      "image": "nginx:latest",
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "'${LOG_GROUP}'",
          "awslogs-region": "'$(aws configure get region)'",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "portMappings": [{"containerPort": 80, "hostPort": 80}],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    },
    {
      "name": "nonexistent-container",
      "image": "nonexistent-repo/nonexistent-image:latest",
      "essential": false,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "'${LOG_GROUP}'",
          "awslogs-region": "'$(aws configure get region)'",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]'

if [ $? -eq 0 ]; then
    echo "✅ Task definition registered successfully"
else
    echo "❌ Failed to register task definition"
    exit 1
fi

# Step 8: Create service with restrictive security group
echo "Step 8: Creating ECS service with restrictive network configuration..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"

if [ $? -eq 0 ]; then
    echo "✅ ECS service created successfully"
else
    echo "❌ Failed to create ECS service"
    exit 1
fi

echo ""
echo "🎯 Infrastructure creation completed!"
echo "   The service will experience multiple types of failures suitable for testing all troubleshooting tools:"
echo "   - Network connectivity issues due to restrictive security group"
echo "   - Image pull failures from nonexistent-container"
echo "   - Task failures and logs will be generated"
echo ""
echo "⏱️ Wait ~30 seconds for tasks to attempt startup and generate failure scenarios..."
echo ""
echo "📝 For reference, save these values:"
echo "   CLUSTER_NAME=$CLUSTER_NAME"
echo "   SERVICE_NAME=$SERVICE_NAME"
echo "   TASK_FAMILY=$TASK_FAMILY"
echo "   VPC_ID=$VPC_ID"
echo "   SECURITY_GROUP_ID=$SG_ID"
echo ""
echo "Next: Run './02_test_all_tools.sh $CLUSTER_NAME $SERVICE_NAME' to test all troubleshooting tools"
