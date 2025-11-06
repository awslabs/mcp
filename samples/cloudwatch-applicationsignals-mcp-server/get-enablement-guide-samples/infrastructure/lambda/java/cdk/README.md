# Java Lambda Function with CDK

This directory contains AWS CDK code to deploy a Java Lambda function with Application Load Balancer.

## Prerequisites

- AWS CLI configured
- Node.js and npm installed
- Java 17 and Maven installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

Or manually:

```bash
# Build the Java function
cd ../sample-app
mvn clean package

# Deploy with CDK
cd ../cdk
npm install
npm run build
npm run deploy
```

## Cleanup

```bash
npm run destroy
```