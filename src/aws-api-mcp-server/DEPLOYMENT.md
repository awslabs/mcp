# AWS API MCP Server - AgentCore Deployment Guide

This guide provides detailed instructions for deploying the AWS API MCP Server via AWS Marketplace to Amazon Bedrock AgentCore. For the marketplace listing, see: [AWS Marketplace - AWS API MCP Server](https://aws.amazon.com/marketplace/pp/prodview-lqqkwbcraxsgw). The Container from AWS Marketplace is free to download, but after deployment, Bedrock AgentCore Usage Fees will apply.

## Overview

The AWS API MCP Server enables AI assistants to interact with AWS services through the Model Context Protocol (MCP). When deployed to Bedrock AgentCore Runtime, it provides secure, scalable access to AWS APIs with built-in authentication and session isolation.


## Security Best Practices

### Single User Only

This deployment architecture is designed for individual use and does not provide sufficient multi-tenant security isolation. AgentCore's session isolation protects against data leakage between requests but not between different users accessing the same deployment.

* Do NOT use in multi-user environments
* Deploy separate instances if multiple users need access

### Least Privilege Principles

You are responsible for determining and configuring the appropriate permissions for your specific use case. We recommend following security best practices by starting with minimal access and expanding permissions only as needed.

* Start with read-only permissions and incrementally add access based on your requirements
* Use custom IAM policies tailored to your specific AWS services and resources
* Apply condition statements to further restrict access (by region, time, resource tags, etc.)
* Regularly review and audit permissions to ensure they remain appropriate for your use case

### Credential Management

The MCP server operates using the IAM role specified during deployment, completely separate from your local AWS credentials. Understanding this separation is crucial for proper security configuration and troubleshooting.

* Never assign administrator credentials to the execution role
* Your local AWS credentials are only used for client authentication (SigV4 method)
* Monitor AWS CloudTrail logs to track all actions performed by the MCP server

### Prompt Injection Risks

AI assistants executing AWS commands can be vulnerable to prompt injection attacks where malicious input tricks the client agent into running unintended commands. Implement defense-in-depth strategies to mitigate these risks.

* Use scoped-down IAM credentials with minimal permissions necessary
* Be cautious when connecting to untrusted data sources (e.g., CloudWatch logs containing user input)
* Consider MCP clients that support command validation with human-in-the-loop approval
* Remember that prompt injection is an inherent LLM vulnerability, not specific to MCP servers

### Endpoint Access

AgentCore endpoints implement authentication barriers that prevent unauthorized access, therefore the endpoint URL does not need to be treated as confidential information. You are responsible for properly configuring AgentCore with either SigV4 or JWT authentication.

* The endpoint URL alone does not grant access to your AWS resources
* Access requires valid authentication (AWS credentials for SigV4 or Cognito JWT tokens)
* You must configure AgentCore with your chosen authentication method during deployment

### Understanding AWS API Authentication on AgentCore

AgentCore handles all inbound authentication at the runtime level, which means the MCP server itself runs without any inbound authentication mechanisms. This architectural design centralizes security control at the platform level rather than within individual MCP servers.

* Your MCP server runs with `AUTH_TYPE=no-auth` (required parameter for AgentCore deployment)
* The `no-auth` setting disables any internal MCP server authentication since AgentCore provides this functionality
* The API MCP Server does not currently support any inbound authentication features
* All AWS API calls execute with the IAM role you specify during deployment

## Prerequisites

* AWS Account
* Basic understanding of IAM roles and policies
* MCP-compatible client (Claude Desktop, Cursor, etc.)



## Getting Started

### Step 1: Choose Your Authentication Method

#### SigV4 Authentication Setup

**How it works**:

1. Your MCP client uses local AWS credentials
2. MCP Proxy for AWS handles SigV4 signing and forwards requests to AgentCore
3. AgentCore validates the signature and routes to your MCP server

**Requirements**:

* AWS credentials configured locally (`aws configure`)
* MCP Proxy for AWS: https://github.com/aws/mcp-proxy-for-aws

#### MCP Proxy for AWS

The MCP Proxy for AWS is essential for SigV4 authentication because standard MCP clients don't natively support AWS IAM authentication. The proxy acts as a lightweight bridge that automatically handles SigV4 request signing using your local AWS credentials. The proxy is automatically downloaded when you configure your MCP client using `uvx`, ensuring you always get the latest version.

#### JWT Authentication Setup

**How it works**:

1. AgentCore automatically creates Cognito User Pool and Client
2. You authenticate with Cognito to get a JWT token
3. Your MCP client uses the JWT token to authenticate with AgentCore

**Requirements**:

* Manual token generation and refresh
* MCP client that supports bearer token authentication

## Step 2: Create IAM Role and Policies

### Create Custom IAM Role

This role defines what AWS account can assume it and ensures only your AgentCore runtime can execute with these permissions.

```
# 1. Create trust policy (replace YOUR_ACCOUNT_ID with your AWS account ID)
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AssumeRolePolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "YOUR_ACCOUNT_ID"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:bedrock-agentcore:*:YOUR_ACCOUNT_ID:*"
                }
            }
        }
    ]
}
EOF

# 2. Create IAM role
aws iam create-role \
  --role-name aws-api-mcp-execution-role \
  --assume-role-policy-document file://trust-policy.json
```



### Attach Required AgentCore Permissions

AgentCore requires specific permissions for logging, monitoring, and runtime operations. These are mandatory for the runtime to function properly:


```
# Create base AgentCore permissions policy (replace YOUR_ACCOUNT_ID)
cat > agentcore-base-permissions.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRImageAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": [
                "arn:aws:ecr:us-east-1:709825985650:repository/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/bedrock-agentcore/runtimes/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
            ]
        },
        {
            "Sid": "ECRTokenAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets"
            ],
            "Resource": [ "*" ]
        },
        {
            "Effect": "Allow",
            "Resource": "*",
            "Action": "cloudwatch:PutMetricData",
            "Condition": {
                "StringEquals": {
                    "cloudwatch:namespace": "bedrock-agentcore"
                }
            }
        },
        {
            "Sid": "GetAgentAccessToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
            ],
            "Resource": [
              "arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:workload-identity-directory/default",
              "arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT_ID:workload-identity-directory/default/workload-identity/*"
            ]
        }
    ]
}
EOF

# Attach the base AgentCore permissions
aws iam put-role-policy \
  --role-name aws-api-mcp-execution-role \
  --policy-name AgentCoreBasePermissions \
  --policy-document file://agentcore-base-permissions.json
```



### Add AWS API Permissions

Now add the specific AWS API permissions your MCP server needs. These permissions determine which AWS services and resources your MCP server can access on your behalf. Start with minimal permissions:

**Option 1: Read-Only Access (Recommended to start)**

```
aws iam attach-role-policy \
  --role-name aws-api-mcp-execution-role \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```


**Option 2: Custom Policy for Specific Services**

```
# Example: S3 and EC2 read access
cat > custom-aws-permissions.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-specific-bucket",
                "arn:aws:s3:::your-specific-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeImages"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "ec2:Region": "us-east-1"
                }
            }
        }
    ]
}
EOF

aws iam put-role-policy \
  --role-name aws-api-mcp-execution-role \
  --policy-name CustomAWSPermissions \
  --policy-document file://custom-aws-permissions.json
```

### Step 3: Deploy to AgentCore

#### Deploy with Custom Role

This creates the managed container runtime that hosts your MCP server with the specified IAM role and environment configuration.

Important Notes:

* Always specify —role-arn to avoid AWS creating a default role with broad permissions
* Note down the agent-runtime-id from the response - you'll need it to describe the runtime and find the endpoint URL
* The latest container image version can be found in the [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-lqqkwbcraxsgw) - select the most recent version from the available options

```
aws bedrock-agentcore-control create-agent-runtime \
  --region us-east-1 \
  --agent-runtime-name "awsapimcpserver" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "709825985650.dkr.ecr.us-east-1.amazonaws.com/amazon-web-services/aws-api-mcp-server:LATEST_VERSION"
    }
  }' \
  --role-arn "arn:aws:iam::YOUR_ACCOUNT_ID:role/aws-api-mcp-execution-role" \
  --network-configuration '{"networkMode": "PUBLIC"}' \
  --protocol-configuration '{"serverProtocol": "MCP"}' \
  --environment-variables '{
    "AUTH_TYPE": "no-auth",
    "AWS_API_MCP_HOST": "0.0.0.0",
    "AWS_API_MCP_PORT": "8000",
    "AWS_API_MCP_STATELESS_HTTP": "true",
    "AWS_API_MCP_TRANSPORT": "streamable-http",
    "AWS_API_MCP_ALLOWED_HOSTS": "*",
    "AWS_API_MCP_ALLOWED_ORIGINS": "*"
  }'
```



## Step 4: Get Your Endpoint URL

The endpoint URL is how your MCP client connects to your deployed server, requiring proper URL encoding of the runtime ARN.

```
# Get your runtime details
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id "YOUR_RUNTIME_ID" \
  --region us-east-1
```


**Endpoint URL Format**:

```
https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{url-encoded-arn}/invocations?qualifier=DEFAULT
```


**ARN Encoding** (required - see [AWS docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#runtime-mcp-invoke-server)):

```
# Replace : with %3A and / with %2F
# Original: arn:aws:bedrock-agentcore:us-east-1:123456789:runtime/hosted_agent_abc123
# Encoded:  arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A123456789%3Aruntime%2Fhosted_agent_abc123
```

**Quick encoding with sed:**
```bash
# Replace YOUR_ARN with your actual runtime ARN
echo "YOUR_ARN" | sed 's/:/%3A/g; s/\//%2F/g'
```



## Step 5: Configure Your MCP Client

This configures your AI assistant to connect to your AgentCore-hosted MCP server using your chosen authentication method.

### For SigV4 Authentication

**Claude Desktop / Cursor Configuration:**

```
{
  "aws-api-mcp-server": {
    "autoApprove": [],
    "disabled": false,
    "timeout": 600,
    "type": "stdio",
    "command": "uvx",
    "args": [
      "mcp-proxy-for-aws@latest",
      "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/YOUR_ENCODED_ARN/invocations?qualifier=DEFAULT",
      "--region",
      "us-east-1"
    ],
    "env": {}
  }
}
```


**Note**: Use `git+` URL to get latest proxy updates instead of PyPI.


### For JWT Authentication

**Get Bearer Token:**

```
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "YOUR_COGNITO_CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=test,PASSWORD=YOUR_PASSWORD \
  --region us-east-1 \
  --query 'AuthenticationResult.AccessToken' \
  --output text)
```


Configure your MCP client to use the bearer token with your AgentCore endpoint.


## Important Limitations

### AgentCore-Specific Constraints

#### File Operations

* **Downloads Work But Are Inaccessible**: Files are trapped in ephemeral containers
* **Stateless Execution**: Each request uses a fresh container instance
* **No File Persistence**: Downloaded files cannot be accessed by clients due to session isolation
* **Makes file-based workflows impossible** in stateless deployments

#### Streaming Operations

* **No Real-time Streaming**: AgentCore buffers all responses before returning them to clients
* **Internal Streaming Only**: Server handles streaming internally but returns complete responses
* **Streaming irrelevant for interactive use cases** since you never get real-time data back

#### Security and Access Model

* **Single User Design**: Not suitable for multi-user environments
* **IAM Role Execution**: All AWS API calls use the deployment IAM role
* **Credential Isolation**: Server cannot access your local AWS credentials
* **Endpoint sharing is safe**: Requires explicit authentication to access

## Troubleshooting

### No Tools Showing Up

1. **Check IAM Permissions**: Ensure the execution role has necessary permissions for basic AWS operations
2. **Verify Authentication**: Confirm your client is properly authenticated
3. **Check CloudWatch Logs**: Review logs for the AgentCore runtime for detailed error information

### Access Denied Errors

1. **Review IAM Policies**: Ensure the execution role has permissions for the specific AWS service and operations
2. **Check Resource ARNs**: Verify resource-specific permissions in your policies
3. **Validate Conditions**: Review any condition statements that might be blocking access

### Connection Issues

1. **Verify Endpoint URL**: Ensure the AgentCore endpoint is correctly formatted and ARN is properly URL-encoded
2. **Check Region**: Confirm you're using the correct AWS region in both deployment and client configuration
3. **Authentication Method**: Verify you're using the correct authentication method for your client setup

### Permission Debugging

* The execution role determines what AWS APIs are accessible to the MCP server
* Check which role is actually being used: custom role vs. auto-generated default role
* Use AWS CloudTrail to see what API calls are being made and which role is executing them

## Support and Resources

* **Report Issues on GitHub**: [Create New Issue](https://github.com/awslabs/mcp/issues/new/choose)
* **MCP Proxy for AWS**: https://github.com/aws/mcp-proxy-for-aws
* **AgentCore Documentation**: [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
* **Bedrock AgentCore Runtime MCP Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html
* **MCP Protocol Documentation**: [Model Context Protocol](https://modelcontextprotocol.io/)

## Known Issues

1. **File Downloads**: Files downloaded in stateless mode cannot be accessed by clients, some operations that require access to filesystem will not be supported when deployed to Bedrock AgentCore Runtime
2. **Response Streaming**: Real-time streaming is not supported through AgentCore - all responses are buffered
3. **Elicitation**: AgentCore does not support [MCP elicitation](https://modelcontextprotocol.io/specification/draft/client/elicitation).
