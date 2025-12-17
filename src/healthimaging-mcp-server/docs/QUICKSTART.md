# Quick Start Guide

Get up and running with AWS HealthImaging MCP Server in minutes.

## Prerequisites

- Python 3.10 or higher
- AWS account with HealthImaging access
- AWS credentials configured
- MCP-compatible client (Claude Desktop, Cline, etc.)

## Installation

### Option 1: Using uvx (Recommended)

```bash
uvx awslabs.healthimaging-mcp-server
```

### Option 2: Using pip

```bash
pip install awslabs.healthimaging-mcp-server
```

### Option 3: From Source

```bash
git clone https://github.com/awslabs/healthimaging-mcp-server.git
cd healthimaging-mcp-server
pip install -e .
```

## AWS Setup

### 1. Configure AWS Credentials

Choose one method:

**Method A: AWS CLI**
```bash
aws configure
```

**Method B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

**Method C: Credentials File**
Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

### 2. Set Up IAM Permissions

Create an IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "medical-imaging:ListDatastores",
        "medical-imaging:GetDatastore",
        "medical-imaging:SearchImageSets",
        "medical-imaging:GetImageSet",
        "medical-imaging:GetImageSetMetadata",
        "medical-imaging:GetImageFrame"
      ],
      "Resource": "*"
    }
  ]
}
```

Attach this policy to your IAM user or role.

## MCP Client Configuration

### Claude Desktop

Edit your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default"
      }
    }
  }
}
```

### Cline (VS Code)

Add to your Cline MCP settings:

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server"],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## First Steps

### 1. Verify Installation

Restart your MCP client and verify the server is connected.

### 2. List Data Stores

Ask your AI assistant:
```
"List all HealthImaging data stores in my account"
```

### 3. Search Image Sets

```
"Search for image sets in datastore [your-datastore-id]"
```

### 4. Get Metadata

```
"Get the DICOM metadata for image set [your-image-set-id] in datastore [your-datastore-id]"
```

## Common Use Cases

### Finding Patient Studies

```
"Search for all CT scans for patient ID PATIENT123"
```

### Exploring Data Stores

```
"Show me details about datastore [datastore-id]"
```

### Analyzing Image Sets

```
"Get metadata for image set [image-set-id] and tell me about the study"
```

## Troubleshooting

### Server Not Connecting

1. Check AWS credentials are configured
2. Verify IAM permissions
3. Check MCP client logs
4. Ensure Python 3.10+ is installed

### Permission Errors

```
Error: AccessDeniedException
```

Solution: Verify IAM policy includes required HealthImaging permissions

### Region Issues

```
Error: Could not connect to the endpoint URL
```

Solution: Set correct AWS region in environment or config

### No Data Stores Found

```
Response: {"datastoreSummaries": []}
```

Solution: Create a HealthImaging data store in AWS Console first

## Next Steps

- Read the [API Reference](API.md) for detailed tool documentation
- Check [Architecture](ARCHITECTURE.md) to understand how it works
- See [Examples](../examples/) for more usage patterns
- Review [Contributing](../CONTRIBUTING.md) to contribute

## Getting Help

- GitHub Issues: https://github.com/awslabs/healthimaging-mcp-server/issues
- AWS HealthImaging Docs: https://docs.aws.amazon.com/healthimaging/
- MCP Documentation: https://modelcontextprotocol.io/

## Example Session

Here's a complete example session:

```
You: "List my HealthImaging data stores"

AI: "I found 2 data stores:
     1. prod-imaging-store (ACTIVE)
     2. dev-imaging-store (ACTIVE)"

You: "Search for image sets in prod-imaging-store"

AI: "I found 15 image sets. Here are the first 5:
     - Image Set abc123: CT scan from 2024-01-15
     - Image Set def456: MRI scan from 2024-01-14
     - ..."

You: "Get metadata for image set abc123"

AI: "This is a CT study with:
     - Study Date: 2024-01-15
     - Modality: CT
     - 3 series with 450 total instances
     - Patient ID: PATIENT123"
```

That's it! You're now ready to use AWS HealthImaging with your AI assistant.
