from importlib import resources

with (
    resources.files('awslabs.cost_analysis_mcp_server.static')
    .joinpath('COST_REPORT_TEMPLATE.md')
    .open('r') as f
):
    COST_REPORT_TEMPLATE = f.read()
