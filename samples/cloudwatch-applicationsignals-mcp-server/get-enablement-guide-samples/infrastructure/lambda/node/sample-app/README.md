# Node.js Lambda Function Sample

This is a sample AWS Lambda function written in TypeScript that demonstrates:

- API Gateway integration
- S3 service calls using AWS SDK for JavaScript v3
- CloudWatch logging

## Prerequisites

- Node.js 20
- npm

## Building

```bash
npm install
npm run compile
```

This creates `build/function.zip` which can be deployed to AWS Lambda.

## Handler

The Lambda handler is: `index.handler`

## Functionality

The function:
1. Calls S3 List Buckets in your account
2. Returns a response with bucket count