"""Template Registry.

Handles discovery and management of deployment templates.
"""

import os
from enum import Enum
from loguru import logger
from pathlib import Path
from typing import List, Optional


class DeploymentTypes(str, Enum):
    """Deployment types supported by the MCP server."""

    BACKEND = 'backend'
    FRONTEND = 'frontend'
    FULLSTACK = 'fullstack'


class Template:
    """Represents a deployment template with associated metadata.

    Attributes:
        name (str): The name of the template.
        path (str): The filesystem path to the template.
        type (DeploymentTypes): The deployment type of the template.
        framework (Optional[str]): The framework associated with the template, if any.

    Args:
        name (str): The name of the template.
        path (str): The filesystem path to the template.
        type_ (DeploymentTypes): The deployment type of the template.
        framework (Optional[str], optional): The framework associated with the template. Defaults to None.
    """

    def __init__(
        self, name: str, path: str, type_: DeploymentTypes, framework: Optional[str] = None
    ):
        """Initializes a new instance of the class.

        Args:
            name (str): The name of the deployment.
            path (str): The file system path associated with the deployment.
            type_ (DeploymentTypes): The type of deployment.
            framework (Optional[str], optional): The framework used for the deployment. Defaults to None.
        """
        self.name = name
        self.path = path
        self.type = type_
        self.framework = framework


def get_templates_path() -> str:
    """Get the templates directory path.

    Priority:
    1. TEMPLATES_PATH environment variable
    2. Default paths based on installation method

    Returns:
        str: Path to the templates directory
    """
    # Check environment variable first
    templates_path = os.environ.get('TEMPLATES_PATH')
    if templates_path:
        logger.debug(f'Using templates path from environment: {templates_path}')
        return templates_path

    # Try to find templates in standard locations
    # The order is important - we want to prioritize the templates that come with the package
    possible_paths = [
        # 1. When running from source (development mode)
        os.path.join(os.path.dirname(__file__), 'templates'),
        # 2. When installed as a local dependency (most common for projects)
        os.path.join(
            os.getcwd(),
            'venv',
            'lib',
            'python3.9',
            'site-packages',
            'aws_serverless_mcp_server',
            'templates',
        ),
        # 3. When installed globally
        '/usr/local/lib/python3.9/site-packages/aws_lambda_mcp_server/templates',
        # 4. Check if there's a templates directory in the current working directory (least preferred)
        os.path.join(os.getcwd(), 'templates'),
    ]

    logger.debug(f'Searching for templates in possible paths: {", ".join(possible_paths)}')

    for possible_path in possible_paths:
        try:
            # Use Path to check if the directory exists
            path = Path(possible_path)
            if path.exists() and path.is_dir():
                # Check if the directory actually contains template files
                files = (
                    list(path.glob('*.yaml')) + list(path.glob('*.yml')) + list(path.glob('*.j2'))
                )
                if files:
                    logger.debug(f'Found templates at: {possible_path}')
                    return possible_path
                else:
                    logger.debug(f'Directory exists but contains no templates: {possible_path}')
        except Exception as error:
            # Ignore errors and try next path
            logger.debug(f'Error checking path {possible_path}: {error}')

    # Default to templates in current directory as last resort
    default_path = os.path.join(os.getcwd(), 'templates')
    logger.error(f'Could not find templates directory, using current directory: {default_path}')
    return default_path


async def get_template_for_deployment(
    deployment_type: DeploymentTypes, framework: Optional[str] = None
) -> Template:
    """Get the appropriate template for a deployment.

    Args:
        deployment_type: Type of deployment
        framework: Optional framework name

    Returns:
        Template: The template to use for this deployment

    Raises:
        FileNotFoundError: If no template is found
    """
    templates_path = get_templates_path()
    logger.debug(
        f'Looking for template with deployment type: {deployment_type.value}, framework: {framework or "none"}'
    )

    # Define the search order based on the documentation
    search_paths = []

    # 1. Specific template for this deployment type and framework
    if framework:
        search_paths.append(
            os.path.join(templates_path, f'{deployment_type.value}-{framework}.j2')
        )
        search_paths.append(
            os.path.join(templates_path, f'{deployment_type.value}-{framework}.yaml')
        )
        search_paths.append(
            os.path.join(templates_path, f'{deployment_type.value}-{framework}.yml')
        )

    # 2. Default template for this deployment type
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}-default.j2'))
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}-default.yaml'))
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}-default.yml'))

    # 3. Generic template for this deployment type
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}.j2'))
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}.yaml'))
    search_paths.append(os.path.join(templates_path, f'{deployment_type.value}.yml'))

    logger.debug(f'Search paths: {", ".join(search_paths)}')

    # Try each path in order
    for template_path in search_paths:
        logger.info(f'search path: {template_path}')
        if os.path.exists(template_path):
            logger.debug(f'Found template at {template_path}')
            return Template(
                name=os.path.basename(template_path).split('.')[0],
                path=template_path,
                type_=deployment_type,
                framework=framework,
            )

    # If we get here, no template was found
    error_msg = f'No template found for deployment type: {deployment_type}{" and framework: " + framework if framework else ""}'
    logger.error(error_msg)
    logger.error(f'Searched in: {", ".join(search_paths)}')
    raise FileNotFoundError(error_msg)


async def discover_templates() -> List[Template]:
    """Discover all available templates.

    Returns:
        List[Template]: List of available templates
    """
    templates_path = get_templates_path()
    logger.debug(f'Discovering templates in {templates_path}')

    try:
        templates = []

        # Use Path to list files
        path = Path(templates_path)
        if not path.exists():
            logger.error(f'Templates directory does not exist: {templates_path}')
            return []

        files = list(path.glob('*.j2')) + list(path.glob('*.yaml')) + list(path.glob('*.yml'))
        logger.debug(f'Found {len(files)} files in templates directory')

        for file in files:
            name = file.stem
            parts = name.split('-')

            # Skip files that don't match our naming convention
            if not parts:
                logger.debug(f"Skipping file {file} - doesn't match naming convention")
                continue

            # Try to determine the deployment type
            type_str = parts[0].lower()
            try:
                type_ = DeploymentTypes(type_str)
            except ValueError:
                # Skip files that don't start with a valid deployment type
                logger.debug(f'Skipping file {file} - invalid deployment type: {type_str}')
                continue

            # Determine the framework if present
            framework = None
            if len(parts) > 1 and parts[1] != 'default':
                framework = '-'.join(parts[1:])

            templates.append(Template(name=name, path=str(file), type_=type_, framework=framework))

            logger.debug(
                f'Added template: {name}, type: {type_}, framework: {framework or "none"}'
            )

        logger.debug(f'Discovered {len(templates)} templates in {templates_path}')
        return templates
    except Exception as error:
        logger.error(f'Error discovering templates in {templates_path}: {error}')
        raise
