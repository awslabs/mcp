"""Main entry point for the AWS Elastic Beanstalk MCP Server."""

import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from mcp.server.fastmcp import Context, FastMCP

# Configure logging
logging.basicConfig(
    level=os.environ.get("FASTMCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = FastMCP(
    name="awslabs.elastic-beanstalk-mcp-server",
    description="AWS Elastic Beanstalk MCP Server for managing Elastic Beanstalk applications and environments",
)

# Initialize AWS client
def get_eb_client():
    """Get the Elastic Beanstalk client."""
    return boto3.client("elasticbeanstalk")


@server.tool()
def list_applications(ctx: Context) -> Dict[str, Any]:
    """List all Elastic Beanstalk applications in your AWS account."""
    try:
        client = get_eb_client()
        response = client.describe_applications()
        return {"applications": response["Applications"]}
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        return {"error": str(e)}


@server.tool()
def describe_application(ctx: Context, application_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Elastic Beanstalk application.
    
    Args:
        application_name: Name of the Elastic Beanstalk application
    """
    try:
        client = get_eb_client()
        response = client.describe_applications(ApplicationNames=[application_name])
        if response["Applications"]:
            return {"application": response["Applications"][0]}
        return {"error": f"Application {application_name} not found"}
    except Exception as e:
        logger.error(f"Error describing application {application_name}: {e}")
        return {"error": str(e)}


@server.tool()
def list_environments(ctx: Context, application_name: Optional[str] = None) -> Dict[str, Any]:
    """List all Elastic Beanstalk environments or environments for a specific application.
    
    Args:
        application_name: Name of the Elastic Beanstalk application (optional)
    """
    try:
        client = get_eb_client()
        kwargs = {}
        if application_name:
            kwargs["ApplicationName"] = application_name
        
        response = client.describe_environments(**kwargs)
        return {"environments": response["Environments"]}
    except Exception as e:
        logger.error(f"Error listing environments: {e}")
        return {"error": str(e)}


@server.tool()
def describe_environment(
    ctx: Context, 
    environment_id: Optional[str] = None, 
    environment_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed information about a specific Elastic Beanstalk environment.
    
    Args:
        environment_id: ID of the Elastic Beanstalk environment (optional)
        environment_name: Name of the Elastic Beanstalk environment (optional)
    """
    if not environment_id and not environment_name:
        return {"error": "Either environment_id or environment_name must be provided"}
    
    try:
        client = get_eb_client()
        kwargs = {}
        if environment_id:
            kwargs["EnvironmentIds"] = [environment_id]
        if environment_name:
            kwargs["EnvironmentNames"] = [environment_name]
        
        response = client.describe_environments(**kwargs)
        if response["Environments"]:
            return {"environment": response["Environments"][0]}
        return {"error": "Environment not found"}
    except Exception as e:
        logger.error(f"Error describing environment: {e}")
        return {"error": str(e)}


@server.tool()
def create_application(
    ctx: Context, 
    application_name: str, 
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new Elastic Beanstalk application.
    
    Args:
        application_name: Name of the Elastic Beanstalk application
        description: Description of the application (optional)
    """
    try:
        client = get_eb_client()
        kwargs = {"ApplicationName": application_name}
        if description:
            kwargs["Description"] = description
        
        response = client.create_application(**kwargs)
        return {"application": response["Application"]}
    except Exception as e:
        logger.error(f"Error creating application {application_name}: {e}")
        return {"error": str(e)}


@server.tool()
def create_environment(
    ctx: Context,
    application_name: str,
    environment_name: str,
    solution_stack_name: str,
    tier: str = "WebServer",
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new Elastic Beanstalk environment.
    
    Args:
        application_name: Name of the Elastic Beanstalk application
        environment_name: Name of the environment
        solution_stack_name: Solution stack name (platform)
        tier: Environment tier (WebServer or Worker), defaults to WebServer
        description: Description of the environment (optional)
    """
    try:
        client = get_eb_client()
        kwargs = {
            "ApplicationName": application_name,
            "EnvironmentName": environment_name,
            "SolutionStackName": solution_stack_name,
            "Tier": {
                "Name": tier,
                "Type": "Standard"
            }
        }
        
        if description:
            kwargs["Description"] = description
        
        response = client.create_environment(**kwargs)
        return {"environment": response}
    except Exception as e:
        logger.error(f"Error creating environment {environment_name}: {e}")
        return {"error": str(e)}


@server.tool()
def terminate_environment(
    ctx: Context,
    environment_name: str,
    force_terminate: bool = False
) -> Dict[str, Any]:
    """Terminate an Elastic Beanstalk environment.
    
    Args:
        environment_name: Name of the Elastic Beanstalk environment
        force_terminate: Force termination even if there are issues (optional)
    """
    try:
        client = get_eb_client()
        kwargs = {"EnvironmentName": environment_name}
        if force_terminate:
            kwargs["ForceTerminate"] = True
        
        response = client.terminate_environment(**kwargs)
        return {"status": "Terminating", "environment": response}
    except Exception as e:
        logger.error(f"Error terminating environment {environment_name}: {e}")
        return {"error": str(e)}


@server.tool()
def list_available_solution_stacks(ctx: Context) -> Dict[str, Any]:
    """List all available solution stacks (platforms) for Elastic Beanstalk."""
    try:
        client = get_eb_client()
        response = client.list_available_solution_stacks()
        return {
            "solution_stacks": response["SolutionStacks"],
            "solution_stack_details": response.get("SolutionStackDetails", [])
        }
    except Exception as e:
        logger.error(f"Error listing solution stacks: {e}")
        return {"error": str(e)}


@server.tool()
def update_environment(
    ctx: Context,
    environment_name: str,
    description: Optional[str] = None,
    option_settings: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Update an Elastic Beanstalk environment configuration.
    
    Args:
        environment_name: Name of the Elastic Beanstalk environment
        description: New description for the environment (optional)
        option_settings: Array of configuration option settings (optional)
    """
    try:
        client = get_eb_client()
        kwargs = {"EnvironmentName": environment_name}
        
        if description:
            kwargs["Description"] = description
        
        if option_settings:
            formatted_options = []
            for option in option_settings:
                formatted_options.append({
                    "Namespace": option["namespace"],
                    "OptionName": option["option_name"],
                    "Value": option["value"]
                })
            kwargs["OptionSettings"] = formatted_options
        
        response = client.update_environment(**kwargs)
        return {"environment": response}
    except Exception as e:
        logger.error(f"Error updating environment {environment_name}: {e}")
        return {"error": str(e)}


@server.tool()
def restart_app_server(ctx: Context, environment_name: str) -> Dict[str, Any]:
    """Restart the application server for an Elastic Beanstalk environment.
    
    Args:
        environment_name: Name of the Elastic Beanstalk environment
    """
    try:
        client = get_eb_client()
        response = client.restart_app_server(EnvironmentName=environment_name)
        return {"status": "Restarting", "response": response}
    except Exception as e:
        logger.error(f"Error restarting app server for {environment_name}: {e}")
        return {"error": str(e)}


def main():
    """Run the MCP server."""
    server.run()


if __name__ == "__main__":
    main()