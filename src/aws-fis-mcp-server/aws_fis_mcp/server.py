"""AWS FIS FastMCP Server implementation."""

import sys
from mcp.server.fastmcp import FastMCP

from aws_fis_mcp.tools import (
    list_experiment_templates,
    get_experiment_template,
    list_experiments,
    get_experiment,
    start_experiment,
    stop_experiment,
    create_experiment_template,
    delete_experiment_template,
    list_action_types,
    generate_template_example,
)

# Create a FastMCP server
app = FastMCP()

# Register all tools
app.tool()(list_experiment_templates)
app.tool()(get_experiment_template)
app.tool()(list_experiments)
app.tool()(get_experiment)
app.tool()(start_experiment)
app.tool()(stop_experiment)
app.tool()(create_experiment_template)
app.tool()(delete_experiment_template)
app.tool()(list_action_types)
app.tool()(generate_template_example)

def run_server():
    """Run the FastMCP server."""
    print("Starting AWS FIS MCP server...", file=sys.stderr)
    print("Server is ready to accept connections.", file=sys.stderr)
    app.run()

def main():
    """Main entry point for the application."""
    run_server()

if __name__ == "__main__":
    main()
