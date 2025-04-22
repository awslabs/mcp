"""Implementation of user provided module from the Terraform registry search tool."""

import re
import requests
import traceback
from awslabs.terraform_mcp_server.impl.tools.utils import (
    clean_description,
    extract_outputs_from_readme,
    get_github_release_details,
    get_variables_tf,
)
from awslabs.terraform_mcp_server.models import (
    SearchUserProvidedModuleRequest,
    SearchUserProvidedModuleResult,
    TerraformOutput,
    TerraformVariable,
)
from loguru import logger
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse


async def search_user_provided_module_impl(
    request: SearchUserProvidedModuleRequest,
) -> SearchUserProvidedModuleResult:
    """Analyze a Terraform module from the registry.

    This tool takes a Terraform registry module URL and analyzes its input variables,
    output variables, README, and other details to provide comprehensive information
    about the module.

    Parameters:
        request: Details about the Terraform module to analyze

    Returns:
        A SearchUserProvidedModuleResult object containing module information
    """
    logger.info(f'Analyzing Terraform module: {request.module_url}')

    try:
        # Parse the module URL to extract namespace, name, and provider
        module_parts = parse_module_url(request.module_url)
        if not module_parts:
            return SearchUserProvidedModuleResult(
                status='error',
                module_name='unknown',
                module_url=request.module_url,
                module_version='unknown',
                module_description='',
                variables=[],
                outputs=[],
                readme_content=None,
                error_message=f'Invalid module URL format: {request.module_url}. Expected format: [namespace]/[name]/[provider] or registry.terraform.io/[namespace]/[name]/[provider]',
            )

        namespace, name, provider = module_parts

        # Fetch module details from Terraform Registry
        module_details = await get_module_details(namespace, name, provider, request.version)
        if not module_details:
            return SearchUserProvidedModuleResult(
                status='error',
                module_name=name,
                module_url=request.module_url,
                module_version=request.version or 'latest',
                module_description='',
                variables=[],
                outputs=[],
                readme_content=None,
                error_message=f'Failed to fetch module details from Terraform Registry: {request.module_url}',
            )

        # Extract module information
        module_version = module_details.get('version', request.version or 'latest')
        module_description = clean_description(module_details.get('description', ''))
        readme_content = module_details.get('readme_content', '')

        # Get variables and outputs
        variables = []
        outputs = []

        # Extract variables from module details
        if 'variables' in module_details and module_details['variables']:
            variables = [TerraformVariable(**var_data) for var_data in module_details['variables']]
        elif 'root' in module_details and 'inputs' in module_details['root']:
            # Extract from registry API format
            for var_name, var_data in module_details['root']['inputs'].items():
                variables.append(
                    TerraformVariable(
                        name=var_name,
                        type=var_data.get('type', ''),
                        description=var_data.get('description', ''),
                        default=var_data.get('default'),
                        required=var_data.get('required', True),
                    )
                )

        # Extract outputs from module details
        if 'outputs' in module_details and module_details['outputs']:
            outputs = [
                TerraformOutput(name=output['name'], description=output.get('description', ''))
                for output in module_details['outputs']
            ]
        elif 'root' in module_details and 'outputs' in module_details['root']:
            # Extract from registry API format
            for output_name, output_data in module_details['root']['outputs'].items():
                outputs.append(
                    TerraformOutput(
                        name=output_name,
                        description=output_data.get('description', ''),
                    )
                )
        elif readme_content:
            # Try to extract outputs from README
            extracted_outputs = extract_outputs_from_readme(readme_content)
            if extracted_outputs:
                outputs = [
                    TerraformOutput(name=output['name'], description=output.get('description', ''))
                    for output in extracted_outputs
                ]

        # Create the result
        result = SearchUserProvidedModuleResult(
            status='success',
            module_name=name,
            module_url=request.module_url,
            module_version=module_version,
            module_description=module_description,
            variables=variables,
            outputs=outputs,
            readme_content=readme_content,
            error_message=None,
        )

        return result

    except Exception as e:
        logger.error(f'Error analyzing Terraform module: {e}')
        logger.debug(f'Stack trace: {traceback.format_exc()}')
        return SearchUserProvidedModuleResult(
            status='error',
            module_name=request.module_url.split('/')[-2]
            if '/' in request.module_url
            else 'unknown',
            module_url=request.module_url,
            module_version=request.version or 'latest',
            module_description='',
            variables=[],
            outputs=[],
            readme_content=None,
            error_message=f'Error analyzing Terraform module: {str(e)}',
        )


def parse_module_url(module_url: str) -> Optional[Tuple[str, str, str]]:
    """Parse a Terraform module URL to extract namespace, name, and provider.

    Args:
        module_url: The module URL or identifier (e.g., "hashicorp/consul/aws" or "registry.terraform.io/hashicorp/consul/aws")

    Returns:
        Tuple containing (namespace, name, provider) or None if invalid format
    """
    # Handle URLs with scheme (http://, https://)
    if '://' in module_url:
        parsed_url = urlparse(module_url)
        if parsed_url.netloc == 'registry.terraform.io':
            # Extract path and remove leading slash
            path = parsed_url.path.lstrip('/')
            parts = path.split('/')
        else:
            # Not a registry URL format
            return None
    # Handle registry prefix without scheme
    elif module_url.startswith('registry.terraform.io/'):
        # Create a proper URL and parse it
        parsed_url = urlparse(f'https://{module_url}')
        if parsed_url.netloc == 'registry.terraform.io':
            # Extract path and remove leading slash
            path = parsed_url.path.lstrip('/')
            parts = path.split('/')
        else:
            # Should not happen with the startswith check
            return None
    else:
        # Simple module path format (namespace/name/provider)
        parts = module_url.split('/')

    # Ensure we have at least namespace/name/provider
    if len(parts) < 3:
        return None

    namespace = parts[0]
    name = parts[1]
    provider = parts[2]

    return namespace, name, provider


async def get_module_details(
    namespace: str, name: str, provider: str, version: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch detailed information about a Terraform module from the registry.

    Args:
        namespace: The module namespace (e.g., hashicorp)
        name: The module name (e.g., consul)
        provider: The provider (e.g., aws)
        version: Optional specific version to fetch

    Returns:
        Dictionary containing module details
    """
    logger.info(f'Fetching details for module {namespace}/{name}/{provider}')

    try:
        # Get basic module info via API
        details_url = f'https://registry.terraform.io/v1/modules/{namespace}/{name}/{provider}'
        if version:
            details_url += f'/{version}'

        logger.debug(f'Making API request to: {details_url}')

        response = requests.get(details_url)
        response.raise_for_status()

        details = response.json()
        logger.debug(
            f'Received module details. Status code: {response.status_code}, Content size: {len(response.text)} bytes'
        )

        # Get the version
        module_version = version or details.get('version', '')
        if not module_version and 'latest' in details and 'version' in details['latest']:
            module_version = details['latest']['version']

        # Try to get README content and version details
        readme_content = None
        version_details = None

        # APPROACH 1: Try to see if the registry API provides README content directly
        logger.debug('Checking for README content in API response')
        if 'readme' in details and details['readme']:
            readme_content = details['readme']
            logger.info(
                f'Found README content directly in API response: {len(readme_content)} chars'
            )

        # APPROACH 2: Try using the GitHub repo URL for README content and version details
        if 'source' in details:
            source_url = details.get('source')
            # Validate GitHub URL using regex
            if isinstance(source_url, str) and re.match(r'https://github.com/', source_url):
                logger.info(f'Found GitHub source URL: {source_url}')

                # Extract GitHub owner and repo
                github_parts = re.match(r'https://github.com/([^/]+)/([^/]+)', source_url)
                if github_parts:
                    owner, repo = github_parts.groups()
                    logger.info(f'Extracted GitHub repo: {owner}/{repo}')

                    # Get version details from GitHub
                    github_version_info = await get_github_release_details(owner, repo)
                    version_details = github_version_info['details']
                    version_from_github = github_version_info['version']

                    if version_from_github:
                        logger.info(f'Found version from GitHub: {version_from_github}')
                        if not module_version:
                            module_version = version_from_github

                    # Get variables.tf content and parsed variables
                    variables_content, variables = await get_variables_tf(owner, repo, 'main')
                    if variables_content and variables:
                        logger.info(f'Found variables.tf with {len(variables)} variables')
                        details['variables_content'] = variables_content
                        details['variables'] = [var.dict() for var in variables]
                    else:
                        # Try master branch as fallback
                        variables_content, variables = await get_variables_tf(
                            owner, repo, 'master'
                        )
                        if variables_content and variables:
                            logger.info(
                                f'Found variables.tf in master branch with {len(variables)} variables'
                            )
                            details['variables_content'] = variables_content
                            details['variables'] = [var.dict() for var in variables]

                    # If README content not already found, try fetching it from GitHub
                    if not readme_content:
                        logger.debug(f'Fetching README from GitHub source: {source_url}')

                        # Try main branch first, then fall back to master if needed
                        for branch in ['main', 'master']:
                            raw_readme_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md'
                            logger.debug(f'Trying to fetch README from: {raw_readme_url}')

                            readme_response = requests.get(raw_readme_url)
                            if readme_response.status_code == 200:
                                readme_content = readme_response.text
                                logger.info(
                                    f'Successfully fetched README from GitHub ({branch}): {len(readme_content)} chars'
                                )
                                break

        # Add readme_content to details if available
        if readme_content:
            logger.info(f'Successfully extracted README content ({len(readme_content)} chars)')

            # Extract outputs from README content
            outputs = extract_outputs_from_readme(readme_content)
            if outputs:
                logger.info(f'Extracted {len(outputs)} outputs from README')
                details['outputs'] = outputs

            # Trim if too large
            if len(readme_content) > 8000:
                logger.debug(
                    f'README content exceeds 8000 characters ({len(readme_content)}), truncating...'
                )
                readme_content = readme_content[:8000] + '...\n[README truncated due to length]'
                logger.debug('README content truncated')

            details['readme_content'] = readme_content
        else:
            logger.warning('No README content found through any method')

        # Add version details if available
        if version_details:
            logger.info('Adding version details to response')
            details['version_details'] = version_details

        # Add version to details
        details['version'] = module_version

        return details

    except Exception as e:
        logger.error(f'Error fetching module details: {e}')
        logger.debug(f'Stack trace: {traceback.format_exc()}')
        return {}
