# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Implementation of specific AWS-IA module search tool for four key modules."""

import asyncio
import re
import requests
import time
import traceback
from .utils import (
    clean_description,
    extract_outputs_from_readme,
    get_github_release_details,
    get_submodules,
    get_variables_tf,
)
from awslabs.terraform_mcp_server.models import ModuleSearchResult, SubmoduleInfo
from loguru import logger
from typing import Dict, List, Optional


# Define the specific modules we want to check
SPECIFIC_MODULES = [
    {'namespace': 'aws-ia', 'name': 'bedrock', 'provider': 'aws'},
    {'namespace': 'aws-ia', 'name': 'opensearch-serverless', 'provider': 'aws'},
    {'namespace': 'aws-ia', 'name': 'sagemaker-endpoint', 'provider': 'aws'},
    {'namespace': 'aws-ia', 'name': 'serverless-streamlit-app', 'provider': 'aws'},
]


async def get_module_details(namespace: str, name: str, provider: str = 'aws') -> Dict:
    """Fetch detailed information about a specific Terraform module.

    Args:
        namespace: The module namespace (e.g., aws-ia)
        name: The module name (e.g., vpc)
        provider: The provider (default: aws)

    Returns:
        Dictionary containing module details including README content and submodules
    """
    logger.info(f'Fetching details for module {namespace}/{name}/{provider}')

    try:
        # Get basic module info via API
        details_url = f'https://registry.terraform.io/v1/modules/{namespace}/{name}/{provider}'
        logger.debug(f'Making API request to: {details_url}')

        response = requests.get(details_url)
        response.raise_for_status()

        details = response.json()
        logger.debug(
            f'Received module details. Status code: {response.status_code}, Content size: {len(response.text)} bytes'
        )

        # Debug log the version info we initially have
        initial_version = details.get('latest_version', 'unknown')
        if 'latest' in details and 'version' in details['latest']:
            initial_version = details['latest']['version']
        logger.debug(f'Initial version from primary API: {initial_version}')

        # Add additional API call to get the latest version if not in details
        if 'latest' not in details or 'version' not in details.get('latest', {}):
            versions_url = f'{details_url}/versions'
            logger.debug(f'Making API request to get versions: {versions_url}')

            versions_response = requests.get(versions_url)
            logger.debug(f'Versions API response code: {versions_response.status_code}')

            if versions_response.status_code == 200:
                versions_data = versions_response.json()
                logger.debug(
                    f'Received versions data with {len(versions_data.get("modules", []))} module versions'
                )

                if versions_data.get('modules') and len(versions_data['modules']) > 0:
                    latest_version = versions_data['modules'][0].get('version', '')
                    details['latest_version'] = latest_version
                    logger.debug(f'Updated latest version to: {latest_version}')
                else:
                    logger.debug('No modules found in versions response')
            else:
                logger.debug(
                    f'Failed to fetch versions. Status code: {versions_response.status_code}'
                )
        else:
            logger.debug('Latest version already available in primary API response')

        # Try to get README content and version details, starting with direct API if available
        readme_content = None
        version_details = None
        version_from_github = ''

        # APPROACH 1: Try to see if the registry API provides README content directly
        logger.debug('APPROACH 1: Checking for README content in API response')
        if 'readme' in details and details['readme']:
            readme_content = details['readme']
            logger.info(
                f'Found README content directly in API response: {len(readme_content)} chars'
            )

        # APPROACH 2: Try using the GitHub repo URL for README content and version details
        if 'source' in details:
            source_url = details.get('source')
            # Properly validate GitHub URL using regex to ensure it's actually from github.com domain
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
                        details['latest_version'] = version_from_github

                    # Get variables.tf content and parsed variables
                    variables_content, variables = await get_variables_tf(owner, repo, 'main')
                    if variables_content and variables:
                        logger.info(f'Found variables.tf with {len(variables)} variables')
                        details['variables_content'] = variables_content
                        details['variables'] = [var.dict() for var in variables]
                    else:
                        # Try master branch as fallback if main didn't work
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
                        logger.debug(
                            f'APPROACH 2: Fetching README from GitHub source: {source_url}'
                        )

                        # Convert HTTPS URL to raw content URL
                        try:
                            # Try main branch first, then fall back to master if needed
                            found_readme_branch = None
                            for branch in ['main', 'master']:
                                raw_readme_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md'
                                logger.debug(f'Trying to fetch README from: {raw_readme_url}')

                                readme_response = requests.get(raw_readme_url)
                                if readme_response.status_code == 200:
                                    readme_content = readme_response.text
                                    found_readme_branch = branch
                                    logger.info(
                                        f'Successfully fetched README from GitHub ({branch}): {len(readme_content)} chars'
                                    )
                                    break

                            # Look for submodules now that we have identified the main branch
                            if found_readme_branch:
                                logger.info(
                                    f'Fetching submodules using {found_readme_branch} branch'
                                )
                                start_time = time.time()
                                submodules = await get_submodules(owner, repo, found_readme_branch)
                                if submodules:
                                    logger.info(
                                        f'Found {len(submodules)} submodules in {time.time() - start_time:.2f} seconds'
                                    )
                                    details['submodules'] = [
                                        submodule.dict() for submodule in submodules
                                    ]
                                else:
                                    logger.info('No submodules found')
                            else:
                                # Try both main branches for submodules if readme wasn't found
                                for branch in ['main', 'master']:
                                    logger.debug(f'Trying {branch} branch for submodules')
                                    start_time = time.time()
                                    submodules = await get_submodules(owner, repo, branch)
                                    if submodules:
                                        logger.info(
                                            f'Found {len(submodules)} submodules in {branch} branch in {time.time() - start_time:.2f} seconds'
                                        )
                                        details['submodules'] = [
                                            submodule.dict() for submodule in submodules
                                        ]
                                        break
                        except Exception as ex:
                            logger.error(f'Error fetching README from GitHub: {ex}')
                            logger.debug(f'Stack trace: {traceback.format_exc()}')

        # Process content we've gathered

        # Add readme_content to details if available
        if readme_content:
            logger.info(f'Successfully extracted README content ({len(readme_content)} chars)')
            logger.debug(f'First 100 characters of README: {readme_content[:100]}...')

            # Extract outputs from README content
            outputs = extract_outputs_from_readme(readme_content)
            if outputs:
                logger.info(f'Extracted {len(outputs)} outputs from README')
                details['outputs'] = outputs
            else:
                logger.info('No outputs found in README')

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
            logger.debug(f'Version details: {version_details}')
            details['version_details'] = version_details

        return details

    except Exception as e:
        logger.error(f'Error fetching module details: {e}')
        # Add stack trace for debugging
        logger.debug(f'Stack trace: {traceback.format_exc()}')
        return {}


async def get_specific_module_info(module_info: Dict[str, str]) -> Optional[ModuleSearchResult]:
    """Get detailed information about a specific module.

    Args:
        module_info: Dictionary with namespace, name, and provider of the module

    Returns:
        ModuleSearchResult object with module details or None if module not found
    """
    namespace = module_info['namespace']
    name = module_info['name']
    provider = module_info['provider']

    try:
        # First, check if the module exists
        details_url = f'https://registry.terraform.io/v1/modules/{namespace}/{name}/{provider}'
        response = requests.get(details_url)

        if response.status_code != 200:
            logger.warning(
                f'Module {namespace}/{name}/{provider} not found (status code: {response.status_code})'
            )
            return None

        module_data = response.json()

        # Get the description and clean it
        description = module_data.get('description', 'No description available')
        cleaned_description = clean_description(description)

        # Create the basic result
        result = ModuleSearchResult(
            name=name,
            namespace=namespace,
            provider=provider,
            version=module_data.get('latest_version', 'unknown'),
            url=f'https://registry.terraform.io/modules/{namespace}/{name}/{provider}',
            description=cleaned_description,
        )

        # Get detailed information including README
        details = await get_module_details(namespace, name, provider)

        if details:
            # Update the version if we got a better one from the details
            if 'latest_version' in details:
                result.version = details['latest_version']

            # Add version details if available
            if 'version_details' in details:
                result.version_details = details['version_details']

            # Get README content
            if 'readme_content' in details and details['readme_content']:
                result.readme_content = details['readme_content']

            # Get input and output counts if available
            if 'root' in details and 'inputs' in details['root']:
                result.input_count = len(details['root']['inputs'])

            if 'root' in details and 'outputs' in details['root']:
                result.output_count = len(details['root']['outputs'])

            # Add submodules if available
            if 'submodules' in details and details['submodules']:
                submodules = [
                    SubmoduleInfo(**submodule_data) for submodule_data in details['submodules']
                ]
                result.submodules = submodules

            # Add variables information if available
            if 'variables' in details and details['variables']:
                from awslabs.terraform_mcp_server.models import TerraformVariable

                variables = [TerraformVariable(**var_data) for var_data in details['variables']]
                result.variables = variables

            # Add variables.tf content if available
            if 'variables_content' in details and details['variables_content']:
                result.variables_content = details['variables_content']

            # Add outputs from README if available
            if 'outputs' in details and details['outputs']:
                from awslabs.terraform_mcp_server.models import TerraformOutput

                outputs = [
                    TerraformOutput(name=output['name'], description=output.get('description'))
                    for output in details['outputs']
                ]
                result.outputs = outputs
                # Update output_count if not already set
                if result.output_count is None:
                    result.output_count = len(outputs)

        return result

    except Exception as e:
        logger.error(f'Error getting info for module {namespace}/{name}/{provider}: {e}')
        return None


async def search_specific_aws_ia_modules_impl(query: str) -> List[ModuleSearchResult]:
    """Search for specific AWS-IA Terraform modules.

    This tool checks for information about four specific AWS-IA modules:
    - aws-ia/bedrock/aws - Amazon Bedrock module for generative AI applications
    - aws-ia/opensearch-serverless/aws - OpenSearch Serverless collection for vector search
    - aws-ia/sagemaker-endpoint/aws - SageMaker endpoint deployment module
    - aws-ia/serverless-streamlit-app/aws - Serverless Streamlit application deployment

    It returns detailed information about these modules, including their README content,
    variables.tf content, and submodules when available.

    The search is performed across module names, descriptions, README content, and variable
    definitions. This allows you to find modules based on their functionality or specific
    configuration options.

    The implementation fetches module information directly from the Terraform Registry API
    and GitHub repositories to ensure the most up-to-date information. Results include
    comprehensive details about each module's structure, configuration options, and usage examples.

    Examples:
        - To get information about all four modules:
          search_specific_aws_ia_modules_impl(query='')

        - To find modules related to Bedrock:
          search_specific_aws_ia_modules_impl(query='bedrock')

        - To find modules related to vector search:
          search_specific_aws_ia_modules_impl(query='vector search')

        - To find modules with specific configuration options:
          search_specific_aws_ia_modules_impl(query='endpoint_name')

    Parameters:
        query: Optional search term to filter modules (empty returns all four modules)

    Returns:
        A list of matching modules with their details, including:
        - Basic module information (name, namespace, version)
        - Module documentation (README content)
        - Input and output parameter counts
        - Variables from variables.tf with descriptions and default values
        - Submodules information
        - Version details and release information
    """
    logger.info(f"Searching for specific AWS-IA modules with query: '{query}'")

    tasks = []

    # Create tasks for fetching module information
    for module_info in SPECIFIC_MODULES:
        tasks.append(get_specific_module_info(module_info))

    # Run all tasks concurrently
    module_results = await asyncio.gather(*tasks)

    # Filter out None results (modules not found)
    module_results = [result for result in module_results if result is not None]

    # If query is provided, filter results
    if query and query.strip():
        query_terms = query.lower().split()
        filtered_results = []

        for result in module_results:
            # Check if any query term is in the module name, description, readme, or variables
            matches = False

            # Build search text from module details and variables
            search_text = (
                f'{result.name} {result.description} {result.readme_content or ""}'.lower()
            )

            # Add variables information to search text if available
            if result.variables:
                for var in result.variables:
                    var_text = f'{var.name} {var.type or ""} {var.description or ""}'
                    search_text += f' {var_text.lower()}'

            # Add variables.tf content to search text if available
            if result.variables_content:
                search_text += f' {result.variables_content.lower()}'

            # Add outputs information to search text if available
            if result.outputs:
                for output in result.outputs:
                    output_text = f'{output.name} {output.description or ""}'
                    search_text += f' {output_text.lower()}'

            for term in query_terms:
                if term in search_text:
                    matches = True
                    break

            if matches:
                filtered_results.append(result)

        logger.info(
            f"Found {len(filtered_results)} modules matching query '{query}' out of {len(module_results)} total modules"
        )
        return filtered_results
    else:
        logger.info(f'Returning all {len(module_results)} specific modules (no query filter)')
        return module_results
