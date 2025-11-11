#!/bin/bash

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <app-name>"
    echo ""
    echo "Available apps:"
    echo "  python-flask"
    echo "  nodejs-express"
    echo "  java-springboot"
    echo "  dotnet-aspnetcore"
    exit 1
fi

APP_NAME=$1

# Map app name to config file
case "$APP_NAME" in
    python-flask)
        CONFIG_FILE="config/python-flask.tfvars"
        ;;
    nodejs-express)
        CONFIG_FILE="config/nodejs-express.tfvars"
        ;;
    java-springboot)
        CONFIG_FILE="config/java-springboot.tfvars"
        ;;
    dotnet-aspnetcore)
        CONFIG_FILE="config/dotnet-aspnetcore.tfvars"
        ;;
    *)
        echo "Error: Unknown app name: $APP_NAME"
        echo "Available apps: python-flask, nodejs-express, java-springboot, dotnet-aspnetcore"
        exit 1
        ;;
esac

# Get AWS account and region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "Deploying to account: $AWS_ACCOUNT_ID"
echo "Deploying to region: $AWS_REGION"

echo "=================================================="
echo "Deploying ECS Terraform Stack: $APP_NAME"
echo "=================================================="

# Get the absolute path to the ECS Terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ECS_TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"

echo "Working directory: $ECS_TERRAFORM_DIR"

cd "$ECS_TERRAFORM_DIR"

# Check if the config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file $CONFIG_FILE not found!"
    exit 1
fi

echo "Using config file: $CONFIG_FILE"

# Set the AWS region in Terraform
export TF_VAR_aws_region="$AWS_REGION"

# Initialize Terraform if .terraform directory doesn't exist
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
    echo "Terraform initialized successfully!"
    echo ""
fi

# Plan the deployment
echo "Planning Terraform deployment..."
terraform plan -var-file="$CONFIG_FILE" -out=tfplan

echo ""
echo "Applying Terraform deployment..."
terraform apply tfplan

echo ""
echo "=================================================="
echo "Deployment complete!"
echo "=================================================="
echo ""
echo "To check your deployed ECS services, run:"
echo "  aws ecs list-clusters --query 'clusterArns' --output table"
echo "  aws ecs list-services --cluster <cluster-name> --query 'serviceArns' --output table"
echo ""
echo "To get load balancer DNS names:"
echo "  aws elbv2 describe-load-balancers --query 'LoadBalancers[*].[LoadBalancerName,DNSName]' --output table"
echo ""
echo "To get the outputs from this deployment:"
echo "  terraform output"
