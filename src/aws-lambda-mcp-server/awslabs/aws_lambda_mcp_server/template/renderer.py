"""
Template Renderer

Handles rendering of templates for CloudFormation/SAM deployments.
"""

import logging
import os
from typing import Dict, Any, Optional
import pybars
from .registry import DeploymentTypes, get_template_for_deployment

# Set up logging
logger = logging.getLogger(__name__)


def register_helpers(compiler):
    """
    Register Handlebars helpers

    Args:
        compiler: Handlebars compiler
    """
    # Helper to check if two values are equal
    def if_equals(this, arg1, arg2, options):
        if arg1 == arg2:
            return options['fn'](this)
        else:
            return options['inverse'](this)

    # Helper to check if a value exists
    def if_exists(this, value, options):
        if value is not None and value != '':
            return options['fn'](this)
        else:
            return options['inverse'](this)

    # Helper to iterate over object properties
    def each_in_object(this, obj, options):
        result = ''
        for key, value in obj.items():
            result += options['fn']({'key': key, 'value': value})
        return result

    # Helper for CloudFormation intrinsic functions
    def cf(this, fn_name, *args):
        if fn_name == 'Ref':
            return f'{{ "Ref": "{args[0]}" }}'
        elif fn_name == 'GetAtt':
            return f'{{ "Fn::GetAtt": ["{args[0]}", "{args[1]}"] }}'
        elif fn_name == 'Sub':
            return f'{{ "Fn::Sub": "{args[0]}" }}'
        else:
            return f'{{ "Fn::{fn_name}": {args} }}'

    # Register the helpers
    compiler.register_helper('ifEquals', if_equals)
    compiler.register_helper('ifExists', if_exists)
    compiler.register_helper('eachInObject', each_in_object)
    compiler.register_helper('cf', cf)


async def render_template(params: Dict[str, Any]) -> str:
    """
    Render a template with the given parameters

    Args:
        params: Deployment parameters

    Returns:
        str: Rendered template as a string

    Raises:
        Exception: If template rendering fails
    """
    # Create a Handlebars compiler
    compiler = pybars.Compiler()

    # Register Handlebars helpers
    register_helpers(compiler)

    # Determine the deployment type
    deployment_type = DeploymentTypes(params.get('deploymentType', '').lower())

    # Get the appropriate framework
    framework = None
    if deployment_type == DeploymentTypes.BACKEND and params.get('backendConfiguration', {}).get('framework'):
        framework = params['backendConfiguration']['framework']
    elif deployment_type == DeploymentTypes.FRONTEND and params.get('frontendConfiguration', {}).get('framework'):
        framework = params['frontendConfiguration']['framework']
    elif deployment_type == DeploymentTypes.FULLSTACK:
        # For fullstack, we might use a combined framework name
        backend_framework = params.get('backendConfiguration', {}).get('framework')
        frontend_framework = params.get('frontendConfiguration', {}).get('framework')
        if backend_framework and frontend_framework:
            framework = f"{backend_framework}-{frontend_framework}"

    # Get the template for this deployment
    template = await get_template_for_deployment(deployment_type, framework)
    logger.debug(f"Using template: {template.name} at {template.path}")

    try:
        # Read the template file
        with open(template.path, 'r') as f:
            template_content = f.read()

        # Create a description for the template
        description = f"{params.get('projectName', 'Unnamed project')} - {deployment_type} deployment"

        # Compile the template
        compiled_template = compiler.compile(template_content)

        # Add description to params
        params_with_description = {**params, 'description': description}

        # Render the template with parameters
        rendered_template = compiled_template(params_with_description)

        logger.debug('Template rendered successfully')
        return rendered_template
    except Exception as error:
        logger.error(f"Error rendering template: {error}")
        raise Exception(f"Failed to render template: {str(error)}")
