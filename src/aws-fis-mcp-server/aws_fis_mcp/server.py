"""AWS FIS FastMCP Server implementation."""

import sys
import argparse
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
    set_write_mode,
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

def run_server(allow_writes: bool = False):
    """Run the FastMCP server."""
    # Set the write mode globally
    set_write_mode(allow_writes)
    
    mode_str = "read-write" if allow_writes else "read-only"
    print(f"Starting AWS FIS MCP server in {mode_str} mode...", file=sys.stderr)
    print("Server is ready to accept connections.", file=sys.stderr)
    app.run()

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="AWS FIS MCP Server")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Enable write operations (create, start, stop, delete experiments). Default is read-only mode."
    )
    
    args = parser.parse_args()
    run_server(allow_writes=args.allow_writes)

if __name__ == "__main__":
    main()
