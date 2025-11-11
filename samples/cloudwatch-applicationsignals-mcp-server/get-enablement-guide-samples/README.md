# Get Enablement Guide Samples

Sample infrastructure for testing the `get_enablement_guide` tool.

## Testing Requirements

**Important:** All changes to this infrastructure should be tested to ensure the IaC and sample apps work correctly.

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js and npm installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)

### Deploy EC2 CDK Sample

#### Step 1: Push Sample App to ECR

Before deploying the CDK stack, you must build and push the Python Flask sample application to your ECR repository.

```bash
# Navigate to the Python Flask sample app
cd sample-apps/python/flask

# Set your AWS account and region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=$(aws configure get region)

# Create ECR repository (if it doesn't exist)
aws ecr create-repository --repository-name python-flask --region $AWS_REGION || true

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push the Docker image
docker build -t python-flask .
docker tag python-flask:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python-flask:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python-flask:latest
```

#### Step 2: Deploy the CDK Stack

```bash
# Navigate to the CDK directory
cd ../../infrastructure/ec2/cdk

# Install dependencies
npm install

# Deploy the Python Flask stack
cdk deploy PythonFlaskCdkStack

# Clean up when done
cdk destroy PythonFlaskCdkStack
```

This deploys an EC2 instance running the containerized Python Flask sample application pulled from your ECR repository.
