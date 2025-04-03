from importlib import resources

with resources.files('ai3_terraform_expert.static').joinpath('MCP_INSTRUCTIONS.md').open('r') as f:
    MCP_INSTRUCTIONS = f.read()

with (
    resources.files('ai3_terraform_expert.static')
    .joinpath('TERRAFORM_WORKFLOW_GUIDE.md')
    .open('r') as f
):
    TERRAFORM_WORKFLOW_GUIDE = f.read()
