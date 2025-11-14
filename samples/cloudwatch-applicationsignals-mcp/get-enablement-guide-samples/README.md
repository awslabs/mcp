# Get Enablement Guide Samples

## Overview

These baseline applications are used to test an AI agent's ability to automatically enable AWS Application Signals across different platforms and languages via our `get_enablement_guide` MCP tool.

The testing flow is:
1. **Baseline Setup:** Deploy infrastructure without Application Signals
2. **Agent Modification:** AI agent modifies code to enable Application Signals
3. **Verification:** Re-deploy and verify Application Signals is enabled

## Prerequisites

### General
- AWS CLI configured with appropriate credentials and permissions
- Access to AWS services: Lambda, API Gateway, ECR, EC2, IAM

### For Lambda Deployments

**Build Requirements:**
- **Docker:** Required for building Lambda deployment packages
  - Uses official AWS Lambda runtime images to ensure consistent build environment
  - Matches Lambda execution environment exactly

### For EC2 Containerized Deployments
- Docker with buildx support for multi-platform builds
- AWS ECR repository access

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
| python-django      | docker-apps/python/django    | python-django   |
| java-springboot    | docker-apps/java/spring-boot | java-springboot |
| nodejs-express     | docker-apps/nodejs/express   | nodejs-express  |

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
| python-django      | PythonDjangoCdkStack   |
| java-springboot    | JavaSpringBootCdkStack |
| nodejs-express     | NodejsExpressCdkStack  |

### Lambda

#### Serverless Deployment

Lambda functions are self-contained - each invocation performs S3 bucket listing.

**Deployment is a three-step process:**
1. **Build**: Package Lambda code with dependencies into a deployment artifact
2. **Deploy**: Deploy the packaged artifact using Terraform or CDK
3. **Invoke**: Manually trigger the Lambda to generate traffic

##### Step 1: Build Lambda Deployment Package

Each Lambda function has a `build.sh` script that uses Docker to build the deployment package:
- Uses official AWS Lambda runtime images (e.g., `public.ecr.aws/lambda/python:3.13`)
- Installs dependencies in the exact Lambda execution environment
- Packages the code and dependencies into a zip file
- Outputs the deployment artifact to `infrastructure/lambda/builds/`

```shell
cd infrastructure/lambda/<language>-lambda
./build.sh
```

**Output:** `infrastructure/lambda/builds/{function-name}.zip`

##### Step 2: Deploy Lambda Infrastructure

**Using CDK:**

```shell
cd infrastructure/lambda/cdk

# Install dependencies (first time only)
npm install

cdk deploy <stack-name>

cdk destroy <stack-name>
```

| Language | Config File  | Stack Name           | Function Name   | Build Output              |
|----------|--------------|----------------------|-----------------|---------------------------|
| python   | python.json  | PythonLambdaCdkStack | PythonLambdaCdk | builds/python-lambda.zip  |

**Using Terraform:**

```shell
cd infrastructure/lambda/terraform

# Initialize Terraform (first time only)
terraform init

terraform apply -var="config_file=<config-file>"

terraform destroy -var="config_file=<config-file>"
```

| Language | Config File  | Function Name          | Build Output              |
|----------|--------------|------------------------|---------------------------|
| python   | python.json  | PythonLambdaTerraform  | builds/python-lambda.zip  |

**Note:** You must run the build script before deploying. If you modify Lambda code or dependencies, rebuild before redeploying.

##### Step 3: Invoke Lambda to Generate Traffic

After deployment, manually invoke the Lambda function to start generating internal traffic:

```shell
# For CDK:
aws lambda invoke --function-name PythonLambdaCdk --invocation-type Event /dev/stdout

# For Terraform:
aws lambda invoke --function-name PythonLambdaTerraform --invocation-type Event /dev/stdout
```

Each invocation executes quickly, listing S3 buckets. Invoke multiple times to generate more traffic. Execution logs can be monitored in CloudWatch Logs.
