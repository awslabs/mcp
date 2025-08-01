import sys
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

awslabs_directory = Path(__file__).parent.parent
qs_mcp_directory = awslabs_directory.parent
sys.path.append(str(awslabs_directory))
sys.path.append(str(qs_mcp_directory))

import awslabs.aws_quicksight_dashboards_mcp_server.resources.bar_chart as bar_chart
import awslabs.aws_quicksight_dashboards_mcp_server.resources.highchart as highchart
import awslabs.aws_quicksight_dashboards_mcp_server.resources.kpi as kpi
import awslabs.aws_quicksight_dashboards_mcp_server.resources.line_chart as line_chart
import awslabs.aws_quicksight_dashboards_mcp_server.resources.pivot_table as pivot_table
import awslabs.aws_quicksight_dashboards_mcp_server.resources.table as table
import awslabs.aws_quicksight_dashboards_mcp_server.quicksight as qs

mcp = FastMCP(
        name="aws-quicksight-dashboards-mcp",
        instructions="""
        If there are multiple instructions given to you, complete them one at a time.
        If a user wants to add a visual, do not remove any visuals. Simply add a visual.
        If a user wants to edit an existing visual, you should think of this as two steps.
        1. Remove existing visual,
        2. Create another visual with different content,
        Do not delete any visuals unless the user explicitly tells you to or wants to edit an existing visual.
        Also, if there are any ambiguities in the direction, always ask to confirm.
        For example, if the instruction tells to create a new line chart but does not specify in which sheet, ask where to add the chart.
        """,
        log_level="INFO",
    )

# Registar Tools for MCP
bar_chart.register_tool(mcp)
highchart.register_tool(mcp)
kpi.register_tool(mcp)
line_chart.register_tool(mcp)
pivot_table.register_tool(mcp)
table.register_tool(mcp)
qs.register_tool(mcp)

def main():
    """Entry point for the MCP server."""
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
