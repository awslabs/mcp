# CFN MCP Server with Tool Dependencies

This implementation adds tool dependencies to the CFN MCP Server, enforcing a specific workflow for resource creation and updates.

## Workflow

The tool dependencies feature enforces the following workflow:

1. **Generate Infrastructure Code**: Use `generate_infrastructure_code()` to create the infrastructure code for security scanning.
2. **Run Security Scan**: Use `run_checkov()` to scan the generated code for security issues.
3. **Create/Update Resource**: Use `create_resource()` or `update_resource()` to create or update the resource after security scanning.

## How It Works

The tool dependencies are implemented using the `depends_on` parameter in the tool decorator:

```python
@mcp.tool()
async def generate_infrastructure_code(...) -> dict:
    """Generate infrastructure code for security scanning."""
    # Implementation...

@mcp.tool(depends_on=[generate_infrastructure_code])
async def run_checkov(...) -> dict:
    """Run security scan on generated infrastructure code."""
    # Implementation...

@mcp.tool(depends_on=[run_checkov])
async def create_resource(...) -> dict:
    """Create an AWS resource after security scanning."""
    # Implementation...
```

If a tool is called before its dependencies, a `DependencyError` will be raised with a clear message about which dependencies need to be called first.

## Benefits

- **Enforced Security**: Security scanning is enforced before resource creation/update
- **Clear Workflow**: The workflow is clearly defined and enforced
- **Error Messages**: Clear error messages when dependencies are not met
- **Minimal Instructions**: Reduced need for detailed instructions in the prompt

## Usage

The LLM will automatically follow the required workflow when creating or updating resources:

1. Check environment variables using `check_environment_variables()`
2. Get AWS session info using `get_aws_session_info()` and `get_aws_profile()` - these have `depends_on = [check_environment_variables]`
3. Generate infrastructure code using `generate_infrastructure_code()` - `depends_on = []
4. Run security scan using `run_checkov()`
5. Create or update resource using `create_resource()` or `update_resource()`

The LLM can still call `get_resource()`, `get_resource_request_status()`, `get_resource_schema_information()`, `list_resources()`, and `delete_resource()` as needed without dependencies.
