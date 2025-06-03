# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Template Renderer.

Handles rendering of templates for CloudFormation/SAM deployments.
"""

import os
from .registry import DeploymentTypes, get_template_for_deployment
from awslabs.aws_serverless_mcp_server.models import DeployWebAppRequest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger


def get_jinja_filters():
    """Get Jinja2 custom filters.

    Returns:
        dict: Dictionary of filter functions
    """

    def cf_ref(value):
        """CloudFormation Ref function."""
        return f'{{ "Ref": "{value}" }}'

    def cf_get_att(resource, attribute):
        """CloudFormation GetAtt function."""
        return f'{{ "Fn::GetAtt": ["{resource}", "{attribute}"] }}'

    def cf_sub(value):
        """CloudFormation Sub function."""
        return f'{{ "Fn::Sub": "{value}" }}'

    return {'cf_ref': cf_ref, 'cf_get_att': cf_get_att, 'cf_sub': cf_sub}


def get_jinja_tests():
    """Get Jinja2 custom tests.

    Returns:
        dict: Dictionary of test functions
    """

    def equals(value, other):
        """Test if two values are equal."""
        return value == other

    def exists(value):
        """Test if a value exists (not None and not empty string)."""
        return value is not None and value != ''

    return {'equals': equals, 'exists': exists}


async def render_template(request: DeployWebAppRequest) -> str:
    """Render a template with the given parameters.

    Args:
        request: Deployment request parameters

    Returns:
        str: Rendered template as a string

    Raises:
        Exception: If template rendering fails
    """
    # Determine the deployment type
    deployment_type = DeploymentTypes(request.deployment_type.lower())

    # Get the appropriate framework
    framework = None
    if (
        deployment_type == DeploymentTypes.BACKEND
        and request.backend_configuration
        and request.backend_configuration.framework
    ):
        framework = request.backend_configuration.framework
    elif (
        deployment_type == DeploymentTypes.FRONTEND
        and request.frontend_configuration
        and request.frontend_configuration.framework
    ):
        framework = request.frontend_configuration.framework
    elif deployment_type == DeploymentTypes.FULLSTACK:
        # For fullstack, we might use a combined framework name
        backend_framework = None
        frontend_framework = None

        if request.backend_configuration:
            backend_framework = request.backend_configuration.framework

        if request.frontend_configuration:
            frontend_framework = request.frontend_configuration.framework

        if backend_framework and frontend_framework:
            framework = f'{backend_framework}-{frontend_framework}'

    # Get the template for this deployment
    template = await get_template_for_deployment(deployment_type, framework)
    logger.debug(f'Using template: {template.name} at {template.path}')

    try:
        # Get the template directory
        template_dir = os.path.dirname(template.path)
        template_name = os.path.basename(template.path)

        # Create Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=False,
            lstrip_blocks=False,
        )

        # Add custom filters and tests
        env.filters.update(get_jinja_filters())
        env.tests.update(get_jinja_tests())

        # Load the template
        jinja_template = env.get_template(template_name)

        # Create a description for the template
        description = f'{request.project_name} - {deployment_type.value} deployment'

        # Prepare template variables
        params_dict = request.dict() if hasattr(request, 'dict') else vars(request)
        template_vars = {**params_dict, 'description': description}
        logger.info(f'Template variables: {template_vars}')

        # Render the template
        rendered_template = jinja_template.render(**template_vars)

        logger.debug('Template rendered successfully')
        return rendered_template
    except Exception as error:
        logger.error(f'Error rendering template: {error}')
        raise Exception(f'Failed to render template: {str(error)}')
