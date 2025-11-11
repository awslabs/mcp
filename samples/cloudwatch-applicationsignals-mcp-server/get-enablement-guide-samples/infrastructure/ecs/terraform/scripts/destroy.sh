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
    echo ""
    echo "To destroy all infrastructure, use: terraform destroy"
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

echo "Destroying from account: $AWS_ACCOUNT_ID"
echo "Destroying from region: $AWS_REGION"

echo "=================================================="
echo "Destroying ECS Terraform Stack: $APP_NAME"
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
    echo "Error: Terraform not initialized. Run deploy.sh first or run 'terraform init'."
    exit 1
fi

# Destroy the infrastructure
echo "Destroying Terraform infrastructure..."
terraform destroy -var-file="$CONFIG_FILE" -auto-approve

echo ""
echo "=================================================="
echo "Teardown complete!"
echo "=================================================="
echo ""
echo "Note: ECR repositories and images are retained for future use."
echo "To also remove ECR repositories, run:"
echo "  aws ecr describe-repositories --query 'repositories[*].repositoryName' --output table"
echo "  aws ecr delete-repository --repository-name <repo-name> --force"
