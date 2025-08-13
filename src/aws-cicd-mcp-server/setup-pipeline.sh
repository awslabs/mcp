#!/bin/bash

ACCOUNT_ID="008732538448"
REGION="ap-south-1"

echo "Setting up Java CI/CD Pipeline..."

# 1. Create S3 buckets
echo "Creating S3 buckets..."
aws s3 mb s3://java-app-source-${ACCOUNT_ID} --region ${REGION}
aws s3 mb s3://java-app-artifacts-${ACCOUNT_ID} --region ${REGION}

# 2. Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository --repository-name java-app --region ${REGION}

# 3. Create CodeBuild project
echo "Creating CodeBuild project..."
aws codebuild create-project \
  --name java-app-build \
  --source type=S3,location=java-app-source-${ACCOUNT_ID}/source.zip \
  --artifacts type=S3,location=java-app-artifacts-${ACCOUNT_ID} \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/amazonlinux2-x86_64-standard:3.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
  --service-role arn:aws:iam::${ACCOUNT_ID}:role/CodeBuildServiceRole \
  --region ${REGION}

# 4. Create CodeDeploy application
echo "Creating CodeDeploy application..."
aws deploy create-application \
  --application-name java-app \
  --compute-platform ECS \
  --region ${REGION}

# 5. Create CodeDeploy deployment group
echo "Creating CodeDeploy deployment group..."
aws deploy create-deployment-group \
  --application-name java-app \
  --deployment-group-name ecs-deployment-group \
  --service-role-arn arn:aws:iam::${ACCOUNT_ID}:role/CodeDeployServiceRole \
  --ecs-services serviceName=java-app-service,clusterName=java-app-cluster \
  --region ${REGION}

# 6. Create CodePipeline
echo "Creating CodePipeline..."
aws codepipeline create-pipeline \
  --cli-input-json file://pipeline-config.json \
  --region ${REGION}

echo "Pipeline setup complete!"
echo "Next steps:"
echo "1. Upload your Java source code to s3://java-app-source-${ACCOUNT_ID}/source.zip"
echo "2. Create ECS cluster 'java-app-cluster' and service 'java-app-service'"
echo "3. Create required IAM roles: CodePipelineServiceRole, CodeBuildServiceRole, CodeDeployServiceRole"
