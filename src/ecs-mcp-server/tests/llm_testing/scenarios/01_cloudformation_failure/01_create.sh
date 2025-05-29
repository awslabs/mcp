#!/bin/bash

# Script to create a CloudFormation stack that will fail
# Usage: ./01_create.sh [stack-name]

# Set script location as base directory and source shared functions
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$DIR")")"
source "$BASE_DIR/utils/aws_helpers.sh"

# Set variables
RANDOM_ID=$(generate_random_id)
STACK_NAME=${1:-"scenario-01-stack-$RANDOM_ID"}
TEMPLATE_FILE="invalid_cfn_template.yaml"

echo "Creating CloudFormation stack $STACK_NAME with invalid configuration..."

# Create a temporary invalid CloudFormation template
cat > $TEMPLATE_FILE << EOF
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: scenario-01-cluster

  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: scenario-01-task
      RequiresCompatibilities:
        - FARGATE
      NetworkMode: awsvpc
      Cpu: 256
      Memory: 512
      ContainerDefinitions:
        - Name: scenario-01-container
          # Invalid image name will cause failure
          Image: "scenario-01-image:latest"
          Essential: true

  ECSService:
    Type: AWS::ECS::Service
    Properties:
      ServiceName: scenario-01-service
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: 1
      LaunchType: FARGATE
      # Missing required NetworkConfiguration will cause failure
EOF

# Create the stack with the invalid template
aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://$TEMPLATE_FILE \
  --capabilities CAPABILITY_IAM

echo "Stack creation initiated. This will fail due to missing NetworkConfiguration in ECS Service."
echo "Wait a few minutes for the failure to occur and then check the stack status:"
echo "aws cloudformation describe-stacks --stack-name $STACK_NAME"
