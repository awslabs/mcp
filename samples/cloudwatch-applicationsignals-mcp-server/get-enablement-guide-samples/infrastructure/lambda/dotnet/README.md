# .NET Lambda Function Sample

This directory contains a complete .NET Lambda function sample with deployment options using both Terraform and AWS CDK.

## Structure

```
dotnet/
├── sample-app/          # .NET Lambda function source code
│   ├── Function.cs      # C# source file
│   ├── LambdaSample.csproj # .NET project file
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
dotnet publish -c Release -o bin/Release/net8.0/publish
cd bin/Release/net8.0/publish
zip -r function.zip .

# Deploy with Terraform
cd ../../../terraform/lambda
terraform init
terraform apply
```

## Function Details

- **Runtime**: .NET 8
- **Handler**: `LambdaSample::LambdaSample.Function::FunctionHandler`
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Architecture**: x86_64 (configurable)

The function demonstrates S3 integration and logging capabilities.