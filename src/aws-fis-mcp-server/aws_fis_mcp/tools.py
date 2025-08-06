"""AWS FIS FastMCP Server tools implementation."""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from functools import wraps

import boto3

# Global variable to track write mode
_WRITE_MODE_ENABLED = False

def set_write_mode(enabled: bool) -> None:
    """Set the global write mode."""
    global _WRITE_MODE_ENABLED
    _WRITE_MODE_ENABLED = enabled

def require_write_mode(func):
    """Decorator to require write mode for destructive operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not _WRITE_MODE_ENABLED:
            return json.dumps({
                "error": "Write operations are disabled",
                "message": f"The '{func.__name__}' operation requires write mode. Please restart the server with --allow-writes flag to enable write operations.",
                "operation": func.__name__,
                "read_only_mode": True
            }, indent=2)
        return func(*args, **kwargs)
    return wrapper


def _serialize_datetime(obj: Any) -> Any:
    """
    Recursively serialize datetime objects to ISO format strings.
    
    Args:
        obj: Object that may contain datetime objects
        
    Returns:
        Object with datetime objects converted to ISO format strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    else:
        return obj


def list_experiment_templates(region: str = "us-east-1") -> str:
    """
    List all AWS FIS experiment templates in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        JSON string containing experiment templates information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.list_experiment_templates()
        
        if not response.get('experimentTemplates'):
            return "No experiment templates found in region " + region
        
        # Format the response for better readability
        templates = []
        for template in response['experimentTemplates']:
            templates.append({
                'id': template.get('id'),
                'name': template.get('experimentTemplateId'),
                'description': template.get('description'),
                'creationTime': template.get('creationTime').isoformat() if template.get('creationTime') else None,
                'lastUpdateTime': template.get('lastUpdateTime').isoformat() if template.get('lastUpdateTime') else None,
                'tags': template.get('tags', {})
            })
        
        return json.dumps(templates, indent=2)
    except Exception as e:
        return f"Error listing experiment templates: {str(e)}"


def get_experiment_template(template_id: str, region: str = "us-east-1") -> str:
    """
    Get detailed information about a specific AWS FIS experiment template.
    
    Args:
        template_id: ID of the experiment template to retrieve
        region: AWS region to query (default: us-east-1)
        
    Returns:
        JSON string containing detailed template information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.get_experiment_template(id=template_id)
        
        # Format the response for better readability
        template = response.get('experimentTemplate', {})
        formatted_template = {
            'id': template.get('id'),
            'description': template.get('description'),
            'targets': template.get('targets', {}),
            'actions': template.get('actions', {}),
            'stopConditions': template.get('stopConditions', []),
            'roleArn': template.get('roleArn'),
            'tags': template.get('tags', {})
        }
        
        return json.dumps(formatted_template, indent=2)
    except Exception as e:
        return f"Error retrieving experiment template: {str(e)}"


def list_experiments(region: str = "us-east-1") -> str:
    """
    List all AWS FIS experiments in the specified region.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        JSON string containing experiments information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.list_experiments()
        
        if not response.get('experiments'):
            return "No experiments found in region " + region
        
        # Format the response for better readability
        experiments = []
        for experiment in response['experiments']:
            experiments.append({
                'id': experiment.get('id'),
                'experimentTemplateId': experiment.get('experimentTemplateId'),
                'state': experiment.get('state', {}).get('status'),
                'startTime': experiment.get('startTime').isoformat() if experiment.get('startTime') else None,
                'endTime': experiment.get('endTime').isoformat() if experiment.get('endTime') else None,
                'tags': experiment.get('tags', {})
            })
        
        return json.dumps(experiments, indent=2)
    except Exception as e:
        return f"Error listing experiments: {str(e)}"


def get_experiment(experiment_id: str, region: str = "us-east-1") -> str:
    """
    Get detailed information about a specific AWS FIS experiment.
    
    Args:
        experiment_id: ID of the experiment to retrieve
        region: AWS region to query (default: us-east-1)
        
    Returns:
        JSON string containing detailed experiment information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.get_experiment(id=experiment_id)
        
        # Get the raw experiment data
        experiment = response.get('experiment', {})
        
        # Use the recursive datetime serializer to handle all datetime objects
        serialized_experiment = _serialize_datetime(experiment)
        
        return json.dumps(serialized_experiment, indent=2)
    except Exception as e:
        return f"Error retrieving experiment: {str(e)}"


@require_write_mode
def start_experiment(template_id: str, region: str = "us-east-1", client_token: Optional[str] = None) -> str:
    """
    Start a new AWS FIS experiment based on an experiment template.
    
    Args:
        template_id: ID of the experiment template to use
        region: AWS region to use (default: us-east-1)
        client_token: Optional client token for idempotency
        
    Returns:
        JSON string containing the started experiment information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        
        # Generate a client token if not provided
        if not client_token:
            client_token = str(uuid.uuid4())
        
        response = fis.start_experiment(
            experimentTemplateId=template_id,
            clientToken=client_token
        )
        
        # Get the raw experiment data and serialize datetime objects
        experiment = response.get('experiment', {})
        serialized_experiment = _serialize_datetime(experiment)
        
        return json.dumps(serialized_experiment, indent=2)
    except Exception as e:
        return f"Error starting experiment: {str(e)}"


@require_write_mode
def stop_experiment(experiment_id: str, region: str = "us-east-1") -> str:
    """
    Stop a running AWS FIS experiment.
    
    Args:
        experiment_id: ID of the experiment to stop
        region: AWS region to use (default: us-east-1)
        
    Returns:
        JSON string containing the stopped experiment information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.stop_experiment(id=experiment_id)
        
        # Get the raw experiment data and serialize datetime objects
        experiment = response.get('experiment', {})
        serialized_experiment = _serialize_datetime(experiment)
        
        return json.dumps(serialized_experiment, indent=2)
    except Exception as e:
        return f"Error stopping experiment: {str(e)}"


@require_write_mode
def create_experiment_template(
    name: str,
    description: str,
    targets: Dict[str, Dict[str, Any]],
    actions: Dict[str, Dict[str, Any]],
    role_arn: str,
    stop_conditions: List[Dict[str, Any]],
    region: str = "us-east-1"
) -> str:
    """
    Create a new AWS FIS experiment template.
    
    Args:
        name: Name for the experiment template
        description: Description of the experiment template
        targets: Dictionary of targets configuration
        actions: Dictionary of actions configuration
        role_arn: ARN of the IAM role to use for the experiment
        stop_conditions: List of stop conditions
        region: AWS region to use (default: us-east-1)
        
    Returns:
        JSON string containing the created template information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        
        response = fis.create_experiment_template(
            clientToken=str(uuid.uuid4()),
            description=description,
            targets=targets,
            actions=actions,
            stopConditions=stop_conditions,
            roleArn=role_arn,
            tags={'Name': name}
        )
        
        # Format the response for better readability
        template = response.get('experimentTemplate', {})
        formatted_template = {
            'id': template.get('id'),
            'description': template.get('description'),
            'creationTime': template.get('creationTime').isoformat() if template.get('creationTime') else None,
            'tags': template.get('tags', {})
        }
        
        return json.dumps(formatted_template, indent=2)
    except Exception as e:
        return f"Error creating experiment template: {str(e)}"


@require_write_mode
def delete_experiment_template(template_id: str, region: str = "us-east-1") -> str:
    """
    Delete an AWS FIS experiment template.
    
    Args:
        template_id: ID of the experiment template to delete
        region: AWS region to use (default: us-east-1)
        
    Returns:
        Success or error message
    """
    try:
        fis = boto3.client('fis', region_name=region)
        fis.delete_experiment_template(id=template_id)
        return f"Successfully deleted experiment template {template_id}"
    except Exception as e:
        return f"Error deleting experiment template: {str(e)}"


def list_action_types(region: str = "us-east-1") -> str:
    """
    List all available AWS FIS action types.
    
    Args:
        region: AWS region to query (default: us-east-1)
        
    Returns:
        JSON string containing action types information
    """
    try:
        fis = boto3.client('fis', region_name=region)
        response = fis.list_actions()  # Fixed: Changed from list_action_types() to list_actions()
        
        if not response.get('actions'):  # Fixed: Changed from 'actionTypes' to 'actions'
            return "No actions found in region " + region
        
        # Format the response for better readability
        actions = []
        for action in response['actions']:  # Fixed: Changed from 'actionTypes' to 'actions'
            actions.append({
                'id': action.get('id'),
                'description': action.get('description'),
                'targets': action.get('targets', {}),
                'parameters': action.get('parameters', {})
            })
        
        return json.dumps(actions, indent=2)
    except Exception as e:
        return f"Error listing actions: {str(e)}"


def generate_template_example(
    target_type: str = "aws:ec2:instance", 
    action_type: str = "aws:ec2:stop-instances",
    region: str = "us-east-1"
) -> str:
    """
    Generate an example AWS FIS experiment template for a given target and action type.
    
    Args:
        target_type: Target resource type (default: aws:ec2:instance)
        action_type: Action type to perform (default: aws:ec2:stop-instances)
        region: AWS region to use (default: us-east-1)
        
    Returns:
        JSON string containing an example template configuration
    """
    try:
        # Example template structure
        template = {
            "description": f"Example experiment template for {action_type} on {target_type}",
            "targets": {
                "MyTargets": {
                    "resourceType": target_type,
                    "resourceArns": ["REPLACE_WITH_ACTUAL_RESOURCE_ARN"],
                    "selectionMode": "ALL"
                }
            },
            "actions": {
                "MyAction": {
                    "actionId": action_type,
                    "parameters": {},
                    "targets": {
                        "Instances": "MyTargets"
                    }
                }
            },
            "stopConditions": [
                {
                    "source": "none"
                }
            ],
            "roleArn": "REPLACE_WITH_ACTUAL_ROLE_ARN",
            "tags": {
                "Name": f"Example-{target_type}-{action_type}"
            }
        }
        
        # Add common parameters based on action type
        if action_type == "aws:ec2:stop-instances":
            template["actions"]["MyAction"]["parameters"] = {
                "startAfter": "PT0M"
            }
        elif action_type == "aws:ec2:reboot-instances":
            template["actions"]["MyAction"]["parameters"] = {
                "startAfter": "PT0M"
            }
        
        return json.dumps(template, indent=2)
    except Exception as e:
        return f"Error generating template example: {str(e)}"
