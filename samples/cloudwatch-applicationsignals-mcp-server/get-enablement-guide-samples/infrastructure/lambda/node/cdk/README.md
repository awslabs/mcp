# Lambda ALB CDK

This CDK application converts the Terraform Lambda and ALB resources to AWS CDK.

## Prerequisites

1. Build the sample application first:
   ```bash
   cd ../sample-app
   npm install
   npm run compile
   ```

2. Install CDK dependencies:
   ```bash
   npm install
   ```

## Deployment

1. Build the CDK application:
   ```bash
   npm run build
   ```

2. Deploy the stack:
   ```bash
   npm run deploy
   ```

## Configuration

You can customize the deployment using CDK context variables:

```bash
cdk deploy -c functionName=my-function -c runtime=nodejs20.x -c architecture=arm64
```

## Cleanup

```bash
npm run destroy
```

## Outputs

After deployment, you'll get:
- ALB URL
- Lambda function role name