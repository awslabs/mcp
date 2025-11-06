# .NET Lambda Function with CDK

This directory contains AWS CDK code to deploy a .NET Lambda function with Application Load Balancer.

## Prerequisites

- AWS CLI configured
- Node.js and npm installed
- .NET 8 SDK installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Deployment

Run the deployment script:

```bash
./deploy.sh
```

Or manually:

```bash
# Build the .NET function
cd ../sample-app
dotnet publish -c Release -o bin/Release/net8.0/publish
cd bin/Release/net8.0/publish
zip -r function.zip .

# Deploy with CDK
cd ../../../../cdk
npm install
npm run build
npm run deploy
```

## Cleanup

```bash
npm run destroy
```