# AWS Labs amazon-qindex MCP Server

The AWS Labs amazon-qindex MCP Server is a Model Context Protocol (MCP) server designed to facilitate integration with Amazon Q Business's [SearchRelevantContent API](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv-calling-api-idc.html). While the server provides essential tools and functions for authentication and search capabilities using Amazon Q index, it currently serves for Independent Software Vendors (ISVs) who are [AWS registered data accessors](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv.html). The server enables cross-account search capabilities, allowing ISVs who are data accessors to search through enterprise customers' Q index and access relevant content across their data sources using specific authentication and authorization flows.

For Amazon Q Business application owners, direct integration support is not yet available. This MCP server represents a comprehensive solution that aims to serve ISVs.

## Features

- Boto3 client implementation for Q Business interactions
- Support for various authentication methods (IAM credentials, profile-based)
- MCP server implementation for handling Q index requests
- Token-based authorization support
- Error handling and mapping for Q Business API responses

## Tools

#### AuthorizeQIndex
- Generates OIDC authorization URL for Q index authentication
- Required Parameters:
  - idc_region (str): AWS region for IAM Identity Center (e.g., us-west-2)
  - isv_redirect_url (str): Redirect URL registered during ISV registration
  - oauth_state (str): Random string for CSRF protection
  - idc_application_arn (str): Amazon Q Business application ID
- Returns: Authorization URL for user authentication

#### CreateTokenWithIAM
- Creates authentication token using authorization code through IAM
- Required Parameters:
  - idc_application_arn (str): Amazon Q Business application ID
  - redirect_uri (str): Registered redirect URL
  - code (str): Authorization code from OIDC endpoint
  - idc_region (str): AWS region for IAM Identity Center
  - role_arn (str): IAM role ARN to assume
- Returns: Token information including access token, refresh token, and expiration

#### AssumeRoleWithIdentityContext
- Assumes IAM role using identity context from token
- Required Parameters:
  - role_arn (str): IAM role ARN to assume
  - identity_context (str): Identity context from decoded token
  - role_session_name (str): Session identifier (default: "qbusiness-session")
  - idc_region (str): AWS region for IAM Identity Center
- Returns: Temporary AWS credentials

#### SearchRelevantContent
- Searches content within Amazon Q Business application
- Required Parameters:
  - application_id (str): Q Business application identifier
  - query_text (str): Search query text
- Optional Parameters:
  - attribute_filter (AttributeFilter): Document attribute filters
  - content_source (ContentSource): Content source configuration
  - max_results (int): Maximum results to return (1-100)
  - next_token (str): Pagination token
  - qbuiness_region (str): AWS region (default: us-east-1)
  - aws_credentials: Temporary AWS credentials
- Returns: Search results with relevant content matches

## Setup

### Pre-Requisites
- Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python using `uv python install 3.10`

- Two AWS Accounts (one account as ISV running this tester application, another account acting as enterprise customer running Amazon Q Business)
- [Data accessor registered for your ISV](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv-info-to-provide.html)
- IAM Identity Center (IDC) instance setup with user added on enterprise customer AWS account
- Amazon Q Business application setup with IAM IDC as access management on enterprise customer AWS account


### Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.amazon_qindex_mcp_server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uX3FpbmRleF9tY3Bfc2VydmVyIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifX0%3D)

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.amazon_qindex_mcp_server": {
      "command": "uvx",
      "args": ["awslabs.amazon_qindex_mcp_server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

```bash
# Clone the repository
git clone [repository-url]

# Go to root directory of this server
cd <your repo path>/mcp/src/amazon-qindex-mcp-server/

# Install dependencies
pip install -e .
```

## Usage

1. Enter a text prompt describing what you want to query from enterprise data

```
search <your query> on enterprise data
```

2. You also need to provide the following details to proceed with the authentication flow in order to process SearchRelevantContent API

```
application id - (enterprise account's Amazon Q Business application ID)
retriever id - (enterprise account's Amazon Q Business retriever ID)
iam idc arn - (enterprise account's IdC application ARN)
idc region - (Region for the IAM Identity Center instance)
qbuiness region - (enterprise account's Amazon Q Business application region)
redirect url - (ISV's redirect url - this could be anything within allowlisted for the data accessor - ie https://localhost:8081)
iam role arn - (ISV's IAM Role ARN registered with the data accessor)
```

3. After providing the data through above two steps, you will be asked to visit the authorization URL on your browser and after successfully authenticated and taken to redirect url with an authorization code in the URL parameters (it will look like ?code=ABC123...&state=xxx), copy and paste the code portion to the client to resume the process.

```
code is <your authorization code>
```

4. This MCP server will then process CreateTokenWithIAM to create authentication token, AssumeRoleWithIdentityContext to assume the role and get temporary credentials, then finally call SearchRelevantContent to searches user queried content within Amazon Q Business application.

## Testing

Run tests using pytest:
```
pytest --cache-clear -v
```

## Security Considerations

This MCP server implementation is for demonstration purposes only to showcase how to access the SearchRelevantContent API through an MCP server with user-aware authentication. For production use, please consider the following security measures:

### Authentication & Authorization
- Never hardcode credentials or sensitive information in the code
- Implement proper session management and token refresh mechanisms
- Use strong CSRF protection mechanisms for the OAuth flow
- Implement proper validation of all authorization codes and tokens
- Store tokens securely and never log them
- Implement proper token revocation when sessions end
