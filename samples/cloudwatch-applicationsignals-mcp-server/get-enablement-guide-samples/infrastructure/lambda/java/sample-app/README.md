# Java Lambda Function Sample

This is a sample AWS Lambda function written in Java that demonstrates:

- API Gateway integration
- S3 service calls using AWS SDK for Java v2
- CloudWatch logging

## Prerequisites

- Java 17
- Maven 3.6+

## Building

```bash
mvn clean package
```

This creates `target/lambda-sample-1.0.0.jar` which can be deployed to AWS Lambda.

## Handler

The Lambda handler is: `com.example.Handler::handleRequest`

## Functionality

The function:
1. Calls S3 List Buckets in your account
2. Returns a response with bucket count