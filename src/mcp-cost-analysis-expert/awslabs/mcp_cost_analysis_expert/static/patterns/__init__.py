from importlib import resources

with resources.files('awslabs.mcp_cost_analysis_expert.static.patterns').joinpath('BEDROCK.md').open('r') as f:
    BEDROCK = f.read()
