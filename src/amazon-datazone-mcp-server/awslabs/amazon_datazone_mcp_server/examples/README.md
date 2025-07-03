# AWS DataZone MCP Server Examples

This directory contains comprehensive examples demonstrating how to use the AWS DataZone MCP Server in real-world scenarios. The examples are organized by complexity and use case to help you get started quickly.

## Example Categories

### [Basic Examples](./basic/)
Simple, focused examples showing individual operations:
- [Domain Operations](./basic/domain_operations.py) - Get, create, and manage domains

## Quick Start

### Prerequisites

1. **Install the MCP Server**:
   ```bash
   pip install datazone-mcp-server
   ```

2. **Configure AWS Credentials**:
   ```bash
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **Set Up DataZone Domain**:
   You'll need an existing AWS DataZone domain. Set the domain ID:
   ```bash
   export DATAZONE_DOMAIN_ID=dzd_your_domain_id
   ```

### Running Examples

Each example is self-contained and can be run independently:

```bash
# Run a basic example
python examples/basic/domain_operations.py

# Run with custom domain ID
DATAZONE_DOMAIN_ID=dzd_abc123 python examples/basic/domain_operations.py
```

## Example Structure

Each example follows a consistent structure:

```python
"""
Example: [Title]

Description: What this example demonstrates

Prerequisites:
- AWS credentials configured
- DataZone domain available
- Any specific requirements

Usage:
    python example_name.py
"""

import asyncio
from mcp import create_client

async def main():
    """Main example function with clear steps."""
    # Step 1: Setup
    client = await create_client("stdio", ["python", "-m", "datazone_mcp_server.server"])

    # Step 2: Core operations
    # ... example code ...

    # Step 3: Cleanup (if needed)
    # ... cleanup code ...

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Patterns

### Error Handling
```python
try:
    result = await client.call_tool("get_domain", {"identifier": domain_id})
    print(f"Domain found: {result.content[0].text}")
except Exception as e:
    print(f"Error: {e}")
    # Handle specific error types
```

### Configuration Management
```python
import os

# Get configuration from environment
DOMAIN_ID = os.getenv("DATAZONE_DOMAIN_ID", "dzd_default")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
```

### Result Processing
```python
# Parse JSON results
import json

result = await client.call_tool("list_projects", {"domain_identifier": domain_id})
projects = json.loads(result.content[0].text)
for project in projects.get("items", []):
    print(f"Project: {project['name']} (ID: {project['id']})")
```

## Use Case Index

Find examples by your specific use case:

### Data Engineers
- [Data Onboarding Workflow](./workflows/data_onboarding_workflow.py)
- [Asset Operations](./basic/asset_operations.py)
- [Batch Operations](./advanced/batch_operations.py)

### Data Stewards
- [Governance Setup](./workflows/governance_setup_workflow.py)
- [Glossary Management](./basic/glossary_management.py)
- [Data Catalog Workflow](./workflows/data_catalog_workflow.py)

### Platform Engineers
- [Environment Setup](./basic/environment_setup.py)
- [Performance Optimization](./advanced/performance_optimization.py)
- [Security Patterns](./advanced/security_patterns.py)

### Data Analysts
- [Data Subscription Workflow](./workflows/data_subscription_workflow.py)
- [Asset Discovery](./basic/asset_operations.py)
- [Search and Browse](./workflows/data_catalog_workflow.py)

## Troubleshooting

### Common Issues

**Authentication Errors**:
```
Error: NoCredentialsError
```
**Solution**: Ensure AWS credentials are configured. See [Authentication Setup](./best_practices/authentication_setup.py).

**Domain Not Found**:
```
Error: ResourceNotFoundException
```
**Solution**: Verify your `DATAZONE_DOMAIN_ID` is correct and you have access.

**Permission Denied**:
```
Error: AccessDeniedException
```
**Solution**: Check your AWS IAM permissions for DataZone operations.

**macOS Apple Silicon (M1/M2/M3) Configuration Issues**:

**Issue: "ImportError: attempted relative import with no known parent package"**
This commonly occurs when using uv with incorrect Claude Desktop configuration.

 **Correct uv configuration:**
```json
{
    "mcpServers": {
        "datazone": {
            "command": "/Users/username/.local/bin/uv",
            "args": [
                "--directory",
                "/path/to/datazone-mcp-server",
                "run",
                "python",
                "-m",
                "datazone_mcp_server.server"
            ],
            "env": {
                "AWS_DEFAULT_REGION": "us-east-1",
                "DATAZONE_DOMAIN_ID": "dzd_your_domain_id"
            }
        }
    }
}
```

**Issue: uv path varies by installation method**
Check your uv installation path:
```bash
which uv
# Common paths:
# Homebrew: /opt/homebrew/bin/uv
# uv installer: /Users/username/.local/bin/uv
```

**Issue: AWS credentials invalid on macOS**
```bash
# Check current credentials
aws sts get-caller-identity

# If invalid, reconfigure
aws configure
```

### Getting Help

1. Check the [troubleshooting guide](./best_practices/troubleshooting.md)
2. Review AWS DataZone [permissions requirements](https://docs.aws.amazon.com/datazone/latest/userguide/getting-started-permissions.html)
3. Examine the [error handling patterns](./advanced/error_handling_patterns.py)

## Contributing Examples

We welcome contributions of new examples! Please:

1. Follow the established structure and patterns
2. Include comprehensive documentation
3. Test examples with real AWS DataZone domains
4. Submit examples that solve real-world problems

See our [Contributing Guide](../CONTRIBUTING.md) for details.

---

**Need help?** Check out our [documentation](../docs/) or open an [issue](https://github.com/wangtianren/datazone-mcp-server/issues).
