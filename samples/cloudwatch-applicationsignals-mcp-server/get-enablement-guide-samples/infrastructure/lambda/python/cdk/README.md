# Python Lambda Function with CDK

This directory contains AWS CDK code to deploy a Python Lambda function with Application Load Balancer.

## Prerequisites

- AWS CLI configured
- Node.js and npm installed
- Python 3.12 and pip installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

Or manually:

```bash
# Build the Python function
cd ../sample-app
pip install -r requirements.txt -t .
zip -r function.zip . --exclude="*.pyc" "__pycache__/*"

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