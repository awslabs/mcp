# Use importlib_resources for backward compatibility with Python < 3.7
try:
    # Try to use the built-in module first (Python 3.7+)
    from importlib import resources
except ImportError:
    # Fall back to the backport for older Python versions
    import importlib_resources as resources

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('MCP_INSTRUCTIONS.md')
    .open('r') as f
):
    MCP_INSTRUCTIONS = f.read()

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('TERRAFORM_WORKFLOW_GUIDE.md')
    .open('r') as f
):
    TERRAFORM_WORKFLOW_GUIDE = f.read()

with (
    resources.files('awslabs.terraform_mcp_server.static')
    .joinpath('AWS_TERRAFORM_BEST_PRACTICES.md')
    .open('r') as f
):
    AWS_TERRAFORM_BEST_PRACTICES = f.read()
