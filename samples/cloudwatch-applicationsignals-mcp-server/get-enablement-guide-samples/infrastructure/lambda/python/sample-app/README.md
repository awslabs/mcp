# Python Lambda Function Sample

This is a sample AWS Lambda function written in Python that demonstrates:

- API Gateway integration
- S3 service calls using boto3
- CloudWatch logging

## Prerequisites

- Python 3.12
- pip

## Building

```bash
pip install -r requirements.txt -t .
zip -r function.zip . --exclude="*.pyc" "__pycache__/*"
```

This creates `function.zip` which can be deployed to AWS Lambda.

## Handler

The Lambda handler is: `lambda_function.lambda_handler`

## Functionality

The function:
1. Calls S3 List Buckets in your account
2. Returns a response with bucket count