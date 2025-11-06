# Node.js Lambda Function Sample

This directory contains a complete Node.js Lambda function sample with deployment options using both Terraform and AWS CDK.

## Structure

```
node/
├── sample-app/          # Node.js Lambda function source code
│   ├── src/             # TypeScript source files
│   ├── package.json     # npm dependencies
│   ├── tsconfig.json    # TypeScript configuration
│   └── README.md        # Build instructions
├── cdk/                 # AWS CDK deployment
│   ├── bin/             # CDK app entry point
│   ├── lib/             # CDK stack definitions
│   ├── package.json     # CDK dependencies
│   ├── deploy.sh        # Deployment script
│   └── README.md        # CDK instructions
└── terraform/           # Terraform deployment
    ├── lambda/          # Lambda function configuration
    └── alb-proxy/       # Application Load Balancer configuration
```

## Quick Start

### Using CDK

```bash
cd cdk
./deploy.sh
```

### Using Terraform

```bash
# Build the function
cd sample-app
npm install
npm run compile

# Deploy with Terraform
cd ../terraform/lambda
terraform init
terraform apply
```

## Function Details

- **Runtime**: Node.js 20
- **Handler**: `index.handler`
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Architecture**: x86_64 (configurable)

The function demonstrates S3 integration and logging capabilities.