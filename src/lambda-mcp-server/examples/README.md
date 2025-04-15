# MCP Server Sample Lambda Functions

This directory contains sample Lambda functions that demonstrate different use cases for the MCP server. These functions are designed to be deployed using the AWS SAM CLI.

The first two functions (`CustomerInfoFromId` and `CustomerIdFromEmail`) simulate an internal customer infromation system where a customer status can be retrived via a customer ID and the customer ID can be retrieved form the email. In this way, an agent using these two functions as tools can retrive customer information from an email by invoking the two functions.

## Available Functions

### 1. CustomerInfoFromId

- **Purpose**: Retrieves customer status information using a customer ID
- **Input**: `{ "customerId": "string" }`
- **Memory**: 128 MB
- **Timeout**: 3 seconds
- **Runtime**: Python 3.13
- **Architecture**: ARM64

### 2. CustomerIdFromEmail

- **Purpose**: Looks up a customer ID using an email address
- **Input**: `{ "email": "string" }`
- **Memory**: 128 MB
- **Timeout**: 3 seconds
- **Runtime**: Python 3.13
- **Architecture**: ARM64

## Installation

### Prerequisites

1. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
2. Configure AWS credentials with appropriate permissions
3. Python 3.13 installed locally (for local testing)

### Deployment Steps

1. Navigate to the sample functions directory:

   ```bash
   cd src/lambda-mcp-server/Examples/sample_functions
   ```

2. Build the application:

   ```bash
   sam build
   ```

3. Deploy the application:

   ```bash
   sam deploy --guided
   ```

   During the guided deployment, you'll be prompted to:
   - Choose a stack name
   - Select an AWS Region
   - Confirm IAM role creation
   - Allow SAM CLI to create IAM roles
   - Save arguments to samconfig.toml

4. For subsequent deployments, you can use:

   ```bash
   sam deploy
   ```

## Cleanup

To remove all deployed resources:

```bash
sam delete --stack-name <your-stack-name>
```

## Security Considerations

- All functions run on ARM64 architecture for cost optimization
- The default IAM role permissions are used.
- Review and adjust memory and timeout settings based on your specific needs
