# MCP Server Sample State Machines

This directory contains sample Step Functions state machines that demonstrate different use cases for the MCP server. These state machines are designed to be deployed using the AWS SAM CLI.

## Available Resources

### Lambda Functions

These Lambda functions serve as the building blocks for our state machines:

1. **CustomerInfoFromId**
   - **Purpose**: Retrieves customer status information using a customer ID
   - **Input**: `{ "customerId": "string" }`
   - **Memory**: 128 MB
   - **Timeout**: 3 seconds
   - **Runtime**: Python 3.13
   - **Architecture**: ARM64

2. **CustomerIdFromEmail**
   - **Purpose**: Looks up a customer ID using an email address
   - **Input**: `{ "email": "string" }`
   - **Memory**: 128 MB
   - **Timeout**: 3 seconds
   - **Runtime**: Python 3.13
   - **Architecture**: ARM64

3. **CustomerCreate**
   - **Purpose**: Creates a new customer record
   - **Input**: See schema below
   - **Memory**: 128 MB
   - **Timeout**: 3 seconds
   - **Runtime**: Python 3.13
   - **Architecture**: ARM64

### State Machines

1. **CustomerCreateStateMachine (EXPRESS)**
   - **Purpose**: Creates a new customer record
   - **Type**: EXPRESS (synchronous execution)
   - **Input**: Same as CustomerCreate Lambda
   - **Description**: Simple wrapper around CustomerCreate Lambda for synchronous execution
   - **Use Case**: Quick, synchronous customer creation operations

2. **GetCustomerInfoWorkflowStateMachine (STANDARD)**
   - **Purpose**: Retrieves customer info using just an email address
   - **Type**: STANDARD (asynchronous execution)
   - **Input**: `{ "email": "string" }`
   - **Description**: Multi-step workflow that:
     1. Gets customer ID from email
     2. Uses that ID to get customer info
   - **Use Case**: Demonstrates chaining multiple Lambda functions in a workflow

## Installation

### Prerequisites

1. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
2. Configure AWS credentials with appropriate permissions
3. Python 3.13 installed locally (for local testing)

### Deployment Steps

1. Navigate to the sample functions directory:

   ```bash
   cd src/stepfunctions-mcp-server/examples/sample_functions
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

- All Lambda functions run on ARM64 architecture for cost optimization
- Express state machine used for quick, synchronous operations
- Standard state machine used for workflow orchestration
- All executions have logging and tracing enabled
- State machines use IAM roles with least privilege permissions
