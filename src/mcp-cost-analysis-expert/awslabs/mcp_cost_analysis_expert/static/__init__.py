from importlib import resources

with (
    resources.files('awslabs.mcp_cost_analysis_expert.static')
    .joinpath('COST_REPORT_TEMPLATE.md')
    .open('r') as f
):
    COST_REPORT_TEMPLATE = f.read()
