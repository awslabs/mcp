from mcp.server.fastmcp import FastMCP
import httpx
import json
from typing import List, Dict, Any, Optional, Union

# Initialize FastMCP server
mcp = FastMCP("aws-service-reference")

# Constants
SERVICE_LIST_URL = "https://servicereference.us-east-1.amazonaws.com/"

# Helper function to fetch service list
async def fetch_service_list() -> List[Dict[str, str]]:
    """Fetch the list of AWS services and their API reference URLs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(SERVICE_LIST_URL)
        response.raise_for_status()
        return response.json()

# Helper function to fetch service details
async def fetch_service_details(url: str) -> Dict[str, Any]:
    """Fetch the complete details for a specific service."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Helper function to find action in service details
def find_action(service_details: Dict[str, Any], action_name: str) -> Optional[Dict[str, Any]]:
    """Find a specific action in the service details."""
    actions = service_details.get("Actions", [])
    return next((action for action in actions if action["Name"].lower() == action_name.lower()), None)

@mcp.tool()
async def list_aws_services() -> str:
    """List all available AWS services."""
    try:
        services = await fetch_service_list()
        service_names = [service["service"] for service in services]
        return "Available AWS services:\n" + "\n".join(service_names)
    except Exception as e:
        return f"Error fetching AWS services: {str(e)}"

@mcp.tool()
async def get_service_actions(service_name: str) -> str:
    """Get API actions for a specific AWS service.
    
    Args:
        service_name: Name of the AWS service (e.g., "s3", "ec2")
    """
    try:
        services = await fetch_service_list()
        service_info = next((s for s in services if s["service"].lower() == service_name.lower()), None)
        
        if not service_info:
            return f"Service '{service_name}' not found. Use list_aws_services to see available services."
            
        service_details = await fetch_service_details(service_info["url"])
        actions = [action["Name"] for action in service_details.get("Actions", [])]
        return f"API actions for {service_name}:\n" + "\n".join(actions)
    except Exception as e:
        return f"Error fetching actions for {service_name}: {str(e)}"

@mcp.tool()
async def get_action_condition_keys(service_name: str, action_name: str) -> str:
    """Get condition keys supported by a specific AWS service action.
    
    Args:
        service_name: Name of the AWS service (e.g., "s3", "ec2")
        action_name: Name of the API action
    """
    try:
        services = await fetch_service_list()
        service_info = next((s for s in services if s["service"].lower() == service_name.lower()), None)
        
        if not service_info:
            return f"Service '{service_name}' not found. Use list_aws_services to see available services."
            
        service_details = await fetch_service_details(service_info["url"])
        action = find_action(service_details, action_name)
        
        if not action:
            return f"Action '{action_name}' not found in service '{service_name}'. Use get_service_actions to see available actions."
            
        condition_keys = action.get("ActionConditionKeys", [])
        if not condition_keys:
            return f"No condition keys found for action '{action_name}' in service '{service_name}'."
            
        return f"Condition keys for {service_name}:{action_name}:\n" + "\n".join(condition_keys)
    except Exception as e:
        return f"Error fetching condition keys: {str(e)}"

@mcp.tool()
async def get_action_resource_types(service_name: str, action_name: str) -> str:
    """Get resource types supported by a specific AWS service action.
    
    Args:
        service_name: Name of the AWS service (e.g., "s3", "ec2")
        action_name: Name of the API action
    """
    try:
        services = await fetch_service_list()
        service_info = next((s for s in services if s["service"].lower() == service_name.lower()), None)
        
        if not service_info:
            return f"Service '{service_name}' not found. Use list_aws_services to see available services."
            
        service_details = await fetch_service_details(service_info["url"])
        action = find_action(service_details, action_name)
        
        if not action:
            return f"Action '{action_name}' not found in service '{service_name}'. Use get_service_actions to see available actions."
            
        resources = action.get("Resources", [])
        if not resources:
            return f"No resource types found for action '{action_name}' in service '{service_name}'."
            
        # Debug logging
        debug_info = f"\nDebug - Action structure:\n{json.dumps(action, indent=2)}"
        debug_info += f"\nDebug - Resources structure:\n{json.dumps(resources, indent=2)}"
        
        try:
            resource_names = [resource["Name"] for resource in resources]
            result = f"Resource types for {service_name}:{action_name}:\n" + "\n".join(resource_names)
            return result + debug_info
        except Exception as e:
            return f"Error processing resources: {str(e)}\n" + debug_info
    except Exception as e:
        return f"Error fetching resource types: {str(e)}"

@mcp.tool()
async def get_action_properties(service_name: str, action_name: str) -> str:
    """Get action properties for a specific AWS service action.
    
    Action properties provide context about what an action is capable of, such as
    write or list capabilities, when used in a policy.
    
    Args:
        service_name: Name of the AWS service (e.g., "s3", "ec2")
        action_name: Name of the API action
    """
    try:
        services = await fetch_service_list()
        service_info = next((s for s in services if s["service"].lower() == service_name.lower()), None)
        
        if not service_info:
            return f"Service '{service_name}' not found. Use list_aws_services to see available services."
            
        service_details = await fetch_service_details(service_info["url"])
        action = find_action(service_details, action_name)
        
        if not action:
            return f"Action '{action_name}' not found in service '{service_name}'. Use get_service_actions to see available actions."
        
        # Extract action properties from annotations
        annotations = action.get("Annotations", {})
        properties = annotations.get("Properties", {})
        
        if not properties:
            return f"No action properties found for action '{action_name}' in service '{service_name}'."
        
        # Format the properties for display
        formatted_properties = []
        for key, value in properties.items():
            formatted_properties.append(f"{key}: {value}")
        
        result = f"Action properties for {service_name}:{action_name}:\n" + "\n".join(formatted_properties)
        return result
    except Exception as e:
        return f"Error fetching action properties: {str(e)}"

if __name__ == "__main__":
    mcp.run() 