# Get Enablement Guide Samples

Sample infrastructure and applications using **AWS CDK** and **Terraform**, across EC2, ECS, and AgentCore environments for testing the `get_enablement_guide` tool.

---

## Overview

These samples are designed to verify enablement flows:

| Category | IaC Tool | Language(s) | Description |
|-----------|-----------|--------------|--------------|
| EC2 | CDK | Python | Simple Flask app running on EC2 |
| ECS | CDK / Terraform | Python, Node.js, Java | Containerized apps deployed on ECS Fargate |
| AgentCore | CDK / Terraform | Python | Agent-based observability stack |

---

## Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed and authenticated to ECR
- Node.js & npm installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Terraform installed (`brew install terraform` or download from [terraform.io](https://www.terraform.io/downloads))

---

## EC2 Sample (CDK)

### Step 1: Push Sample App to ECR

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

### Step 2: Deploy the CDK Stack

```bash
cd ../../infrastructure/ec2/cdk
npm install
cdk deploy PythonFlaskCdkStack
```

### Step 3: Clean Up

```bash
cdk destroy PythonFlaskCdkStack
```

---

## ECS Samples

ECS samples demonstrate containerized deployments using multiple programming languages (Python, Node.js, Java) and two IaC frameworks (CDK and Terraform).

### Prerequisite

Before deploying ECS samples, make sure you have **completed Step 1 in the EC2 sample section** — pushing the sample application image to ECR.  
All ECS deployments (both CDK and Terraform) pull this same image from your ECR repository.

### Languages Supported
- Python
- Node.js
- Java

Each version is located under:
- CDK: `infrastructure/ecs/cdk`
- Terraform: `infrastructure/ecs/terraform`

---

### ECS (CDK)

#### Python

##### Deploy
```bash
cd ../../infrastructure/ecs/cdk
npm install
cdk deploy python-flask
```

##### Clean up
```bash
cdk destroy python-flask
```

#### Node.js

##### Deploy
```bash
cd ../../infrastructure/ecs/cdk
npm install
cdk deploy nodejs-express
```

##### Clean up
```bash
cdk destroy nodejs-express
```

#### Java

##### Deploy
```bash
cd ../../infrastructure/ecs/cdk
npm install
cdk deploy java-springboot
```

##### Clean up
```bash
cdk destroy java-springboot
```

---

### ECS (Terraform)

#### Python

##### Deploy
```bash
cd infrastructure/ecs/terraform
./scripts/deploy.sh python-flask
```

##### Clean up
```bash
./scripts/destroy.sh python-flask
```

#### Node.js

##### Deploy
```bash
cd infrastructure/ecs/terraform
./scripts/deploy.sh nodejs-express
```

##### Clean up
```bash
./scripts/destroy.sh nodejs-express
```

#### Java

##### Deploy
```bash
cd infrastructure/ecs/terraform
./scripts/deploy.sh java-springboot
```

##### Clean up
```bash
./scripts/destroy.sh java-springboot
```

---

## AgentCore Samples

### AgentCore (CDK)
**Deploy**

```bash
cd infrastructure/agent/cdk
npm install
cdk deploy
```


**Clean Up**
```bash
cdk destroy
```

---

### AgentCore (Terraform)

**Deploy**
```bash
cd infrastructure/agent/terraform
terraform init
terraform apply
```


**Clean Up**
```bash
terraform destroy
```

---

## Notes

- Each module can be deployed independently.
- Clean up resources after each test to avoid unexpected conflicts.
- Default regions and account IDs are inferred from your AWS CLI configuration.
