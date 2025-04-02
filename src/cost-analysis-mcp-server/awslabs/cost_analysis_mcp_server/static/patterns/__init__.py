from importlib import resources

with (
    resources.files('awslabs.cost_analysis_mcp_server.static.patterns')
    .joinpath('BEDROCK.md')
    .open('r') as f
):
    BEDROCK = f.read()
