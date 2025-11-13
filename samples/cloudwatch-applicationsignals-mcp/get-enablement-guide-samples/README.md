# Get Enablement Guide Samples

## Overview

These baseline applications are used to test an AI agent's ability to automatically enable AWS Application Signals across different platforms and languages via our `get_enablement_guide` MCP tool.

The testing flow is:
1. **Baseline Setup:** Deploy infrastructure without Application Signals
2. **Agent Modification:** AI agent modifies code to enable Application Signals
3. **Verification:** Re-deploy and verify Application Signals is enabled

## Prerequisites

## Platforms

### EC2

#### Containerized Deployment (Docker)

Applications run as Docker containers on an EC2 instance, with images pulled from Amazon ECR repos.

##### Build and Push Images to ECR

```shell
# Navigate to app directory (see table below)
cd <app-directory>

# Set variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=$(aws configure get region || echo "us-east-1")
export ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/<repo-name>" # See table below

# Authenticate with ECR Public (for base images)
aws ecr-public get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin public.ecr.aws

# Authenticate Docker with ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repository (if it doesn't exist)
aws ecr create-repository --repository-name <repo-name> --region $AWS_REGION 2>/dev/null || true

# Build multi-platform and push to ECR
docker buildx build --platform linux/amd64,linux/arm64 \
  -t $ECR_URI \
  --push \
  .
```

| Language-Framework | App Directory                | ECR Repo        |
|--------------------|------------------------------|-----------------|
| python-flask       | docker-apps/python/flask     | python-flask    |
| java-springboot    | docker-apps/java/spring-boot | java-springboot |

##### Deploy & Cleanup Containerized Infrastructure

**Using CDK:**

```shell
cd infrastructure/ec2/cdk

# Install dependencies (first time only)
npm install

cdk deploy <stack-name>

cdk destroy <stack-name>
```

| Language-Framework | Stack Name             |
|--------------------|------------------------|
| python-flask       | PythonFlaskCdkStack    |
| java-springboot    | JavaSpringBootCdkStack |
