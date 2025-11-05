# .NET Lambda Function Sample

This is a sample AWS Lambda function written in C# that demonstrates:

- API Gateway integration
- S3 service calls using AWS SDK for .NET
- CloudWatch logging

## Prerequisites

- .NET 8 SDK
- AWS CLI configured

## Building

```bash
dotnet publish -c Release -o bin/Release/net8.0/publish
cd bin/Release/net8.0/publish
zip -r function.zip .
```

This creates `function.zip` which can be deployed to AWS Lambda.

## Handler

The Lambda handler is: `LambdaSample::LambdaSample.Function::FunctionHandler`

## Functionality

The function:
1. Calls S3 List Buckets in your account
2. Returns a response with bucket count