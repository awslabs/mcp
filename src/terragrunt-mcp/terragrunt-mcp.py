#!/usr/bin/env python3
"""
Terragrunt MCP Server

This server provides a way to run terragrunt commands through the Model Context Protocol.
It assumes that terraform and terragrunt are already installed on the system.
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP
# Initialize FastMCP server
mcp = FastMCP("terragrunt-mcp")

@mcp.tool()
async def run_terragrunt(path: str, command: str, args: str = "") -> str:
    """Run a terragrunt command in the specified directory.
    
    Args:
        path: Directory path where terragrunt command should be executed
        command: Terragrunt command to run (plan, apply, destroy, etc.)
        args: Additional arguments to pass to the terragrunt command
    
    Returns:
        Output from terragrunt command
    """
    # Check if command is "apply" and block it
    if command.lower() == "apply":
        return "Error: The 'apply' command is not allowed for safety reasons. Please use 'plan' to review changes first."
    
    # Validate path exists
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist"
    
    # Change to the specified directory
    original_dir = os.getcwd()
    try:
        os.chdir(path)
        
        # Check if terragrunt.hcl exists in the directory
        if not os.path.exists("terragrunt.hcl"):
            return f"Error: No terragrunt.hcl file found in '{path}'"
        
        # Get folder name from path for the filename
        folder_name = os.path.basename(os.path.normpath(path))
        
        # Generate timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Create filename with date and folder name
        output_filename = f"terragrunt_{command}_{timestamp}_{folder_name}.log"
        output_filepath = os.path.join(original_dir, output_filename)
        
        # Construct the terragrunt command
        terragrunt_cmd = ["terragrunt", command]
        
        # Add any additional arguments
        if args:
            terragrunt_cmd.extend(args.split())
        
        # Run the terragrunt command
        try:
            result = subprocess.run(
                terragrunt_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Format the command output
            output = f"Command: {' '.join(terragrunt_cmd)}\n"
            output += f"Exit Code: {result.returncode}\n\n"
            
            if result.stdout:
                output += "STDOUT:\n" + result.stdout + "\n"
            
            if result.stderr:
                output += "STDERR:\n" + result.stderr + "\n"
            
            # Save output to file
            try:
                with open(output_filepath, 'w') as f:
                    f.write(output)
                output += f"\nCommand output saved to: {output_filepath}"
            except Exception as file_error:
                output += f"\nError saving output to file: {str(file_error)}"
                
            return output
            
        except Exception as e:
            error_msg = f"Error executing terragrunt command: {str(e)}"
            
            # Try to save error to file as well
            try:
                with open(output_filepath, 'w') as f:
                    f.write(error_msg)
                error_msg += f"\nError message saved to: {output_filepath}"
            except:
                pass
                
            return error_msg
            
    finally:
        # Always return to the original directory
        os.chdir(original_dir)
@mcp.tool()
async def list_terragrunt_commands() -> str:
    """List common terragrunt commands and their descriptions.
    
    Returns:
        A formatted list of common terragrunt commands and their descriptions
    """
    commands = {
        "plan": "Show changes required by the current configuration",
        "apply": "Apply the changes required to reach the desired state",
        "destroy": "Destroy the Terraform-managed infrastructure",
        "validate": "Validate the configuration files",
        "fmt": "Reformat your configuration in the standard style",
        "init": "Initialize a working directory for terragrunt",
        "output": "Show output values from your root module",
        "import": "Import existing infrastructure into Terraform state",
        "state": "Advanced state management",
        "graph": "Generate a visual representation of dependency graph",
        "console": "Interactive console for Terraform interpolations",
        "refresh": "Update local state file against real resources",
        "show": "Show the current state or a saved plan"
    }
    
    output = "Common Terragrunt Commands:\n\n"
    for cmd, desc in commands.items():
        output += f"* {cmd}: {desc}\n"
        
    return output

if __name__ == "__main__":
    # Initialize and run the server with stdio transport
    mcp.run(transport='stdio')