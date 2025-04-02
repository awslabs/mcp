from importlib import resources


with (
    resources.files('awslabs.cdk_mcp_server.static')
    .joinpath('CDK_GENERAL_GUIDANCE.md')
    .open('r') as f
):
    CDK_GENERAL_GUIDANCE = f.read()
