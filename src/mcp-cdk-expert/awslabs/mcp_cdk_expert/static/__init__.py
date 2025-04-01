from importlib import resources


with resources.files('awslabs.mcp_cdk_expert.static').joinpath('CDK_GENERAL_GUIDANCE.md').open('r') as f:
    CDK_GENERAL_GUIDANCE = f.read()
