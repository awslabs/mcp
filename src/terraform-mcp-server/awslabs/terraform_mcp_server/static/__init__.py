from importlib import resources

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
