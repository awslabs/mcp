# Python Lambda Function Sample

This directory contains a complete Python Lambda function sample with deployment options using both Terraform and AWS CDK.

## Structure

```
python/
├── sample-app/          # Python Lambda function source code
│   ├── lambda_function.py # Python source file
│   ├── requirements.txt   # Python dependencies
│   └── README.md         # Build instructions
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
pip install -r requirements.txt -t .
zip -r function.zip . --exclude="*.pyc" "__pycache__/*"

# Deploy with Terraform
cd ../terraform/lambda
terraform init
terraform apply
```

## Function Details

- **Runtime**: Python 3.12
- **Handler**: `lambda_function.lambda_handler`
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Architecture**: x86_64 (configurable)

The function demonstrates S3 integration and logging capabilities.