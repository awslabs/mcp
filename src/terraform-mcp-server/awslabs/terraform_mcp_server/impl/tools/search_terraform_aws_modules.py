"""Implementation of Terraform module search tool."""

import asyncio
import re
import requests
import time
import traceback
from terraform_mcp_server.models import ModuleSearchResult, SubmoduleInfo
from functools import lru_cache
from loguru import logger
from typing import Any, Dict, List, Optional


def clean_description(description: str) -> str:
    """Remove emoji characters from description strings.

    Args:
        description: The module description text

    Returns:
        Cleaned description without emojis
    """
    # This regex pattern targets common emoji Unicode ranges
    emoji_pattern = re.compile(
        '['
        '\U0001f1e0-\U0001f1ff'  # flags (iOS)
        '\U0001f300-\U0001f5ff'  # symbols & pictographs
        '\U0001f600-\U0001f64f'  # emoticons
        '\U0001f680-\U0001f6ff'  # transport & map symbols
        '\U0001f700-\U0001f77f'  # alchemical symbols
        '\U0001f780-\U0001f7ff'  # Geometric Shapes
        '\U0001f800-\U0001f8ff'  # Supplemental Arrows-C
        '\U0001f900-\U0001f9ff'  # Supplemental Symbols and Pictographs
        '\U0001fa00-\U0001fa6f'  # Chess Symbols
        '\U0001fa70-\U0001faff'  # Symbols and Pictographs Extended-A
        '\U00002702-\U000027b0'  # Dingbats
        ']+',
        flags=re.UNICODE,
    )

    # Clean the description
    return emoji_pattern.sub(r'', description).strip()


# Add a simple cache for GitHub API responses
@lru_cache(maxsize=100)
def cached_github_request(url: str) -> Dict:
    """Cache GitHub API responses to reduce API calls.

    Args:
        url: GitHub API URL

    Returns:
        Cached response or new response
    """
    logger.debug(f'Cache miss for: {url}')
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None


async def get_github_release_details(owner: str, repo: str) -> Dict[str, Any]:
    """Fetch detailed release information from GitHub API.

    Args:
        owner: The GitHub repository owner
        repo: The GitHub repository name

    Returns:
        Dictionary containing version details and cleaned version string
    """
    logger.info(f'Fetching GitHub release details for {owner}/{repo}')

    # Try to get the latest release first
    release_url = f'https://api.github.com/repos/{owner}/{repo}/releases/latest'
    logger.debug(f'Making request to GitHub releases API: {release_url}')

    try:
        response = requests.get(release_url)
        logger.debug(f'GitHub releases API response code: {response.status_code}')

        if response.status_code == 200:
            release_data = response.json()
            logger.info(f'Found latest GitHub release: {release_data.get("tag_name")}')

            # Extract just the requested fields (tag name and publish date)
            version_details = {
                'tag_name': release_data.get('tag_name'),
                'published_at': release_data.get('published_at'),
            }

            # Use clean version for the module result
            clean_version = release_data.get('tag_name', '')
            if clean_version.startswith('v'):
                clean_version = clean_version[1:]

            logger.debug(f'Extracted version: {clean_version}')

            return {'details': version_details, 'version': clean_version}
    except Exception as ex:
        logger.error(f'Error fetching GitHub release details: {ex}')
        logger.debug(f'Stack trace: {traceback.format_exc()}')

    # Fallback to tags if no releases found
    tags_url = f'https://api.github.com/repos/{owner}/{repo}/tags'
    logger.debug(f'No releases found, trying tags: {tags_url}')

    try:
        response = requests.get(tags_url)
        logger.debug(f'GitHub tags API response code: {response.status_code}')

        if response.status_code == 200 and response.json():
            tags_data = response.json()
            if tags_data:
                latest_tag = tags_data[0]  # Tags are typically sorted newest first
                logger.info(f'Found latest GitHub tag: {latest_tag.get("name")}')

                version_details = {
                    'tag_name': latest_tag.get('name'),
                    'published_at': None,  # Tags don't have publish dates in GitHub API
                }

                # Use clean version for the module result
                clean_version = latest_tag.get('name', '')
                if clean_version.startswith('v'):
                    clean_version = clean_version[1:]

                logger.debug(f'Extracted version from tag: {clean_version}')

                return {'details': version_details, 'version': clean_version}
    except Exception as ex:
        logger.error(f'Error fetching GitHub tags: {ex}')
        logger.debug(f'Stack trace: {traceback.format_exc()}')

    # Return empty details if nothing was found
    logger.warning('No GitHub release or tag information found')
    return {'details': {}, 'version': ''}


async def get_submodules(owner: str, repo: str, branch: str = 'master') -> List[SubmoduleInfo]:
    """Fetch submodules from a module's GitHub repository.

    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        branch: Branch name (default: master)

    Returns:
        List of SubmoduleInfo objects
    """
    logger.info(f'Checking for submodules in {owner}/{repo} ({branch} branch)')
    submodules = []

    # Check if modules directory exists
    modules_url = f'https://api.github.com/repos/{owner}/{repo}/contents/modules?ref={branch}'
    logger.debug(f'Checking for modules directory: {modules_url}')

    try:
        # Get list of directories in /modules
        start_time = time.time()
        response = requests.get(
            modules_url,
            headers={'Accept': 'application/vnd.github.v3+json'},
            timeout=3.0,  # Add timeout
        )
        logger.debug(f'GitHub API request took {time.time() - start_time:.2f} seconds')

        if response.status_code == 404:
            logger.debug(f'No modules directory found in {branch} branch')
            return []

        if response.status_code == 403:
            logger.warning(f'GitHub API rate limit reached, status: {response.status_code}')
            # Return empty list but don't fail completely
            return []

        if response.status_code != 200:
            logger.warning(f'Failed to get modules directory: status {response.status_code}')
            return []

        modules_list = response.json()
        if not isinstance(modules_list, list):
            logger.warning('Unexpected API response format for modules listing')
            return []

        # Filter for directories only
        submodule_dirs = [item for item in modules_list if item.get('type') == 'dir']
        logger.info(f'Found {len(submodule_dirs)} potential submodules')

        # Process submodules with concurrency limits
        # Only process up to 5 submodules to avoid timeouts
        max_submodules = min(len(submodule_dirs), 5)
        logger.info(f'Processing {max_submodules} out of {len(submodule_dirs)} submodules')

        # Process each submodule
        for i, submodule in enumerate(submodule_dirs[:max_submodules]):
            name = submodule.get('name')
            path = submodule.get('path', f'modules/{name}')

            # Create basic submodule info
            submodule_info = SubmoduleInfo(
                name=name,
                path=path,
            )

            # Add a slight delay between API requests to avoid rate limiting
            if i > 0:
                await asyncio.sleep(0.2)  # 200ms delay between requests

            # Try to get README content
            readme_url = (
                f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/README.md'
            )
            logger.debug(f'Fetching README for submodule {name}: {readme_url}')

            try:
                start_time = time.time()
                readme_response = requests.get(readme_url, timeout=2.0)  # Add timeout
                logger.debug(f'README fetch took {time.time() - start_time:.2f} seconds')

                if readme_response.status_code == 200:
                    readme_content = readme_response.text
                    # Truncate if too long
                    if len(readme_content) > 8000:
                        readme_content = (
                            readme_content[:8000] + '...\n[README truncated due to length]'
                        )

                    # Extract description from first paragraph if available
                    description = extract_description_from_readme(readme_content)
                    if description:
                        submodule_info.description = description

                    submodule_info.readme_content = readme_content
                    logger.debug(
                        f'Found README for submodule {name} ({len(readme_content)} chars)'
                    )
                else:
                    logger.debug(
                        f'No README found for submodule {name}, status: {readme_response.status_code}'
                    )
                    # Try lowercase readme.md as fallback
                    lowercase_readme_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/readme.md'
                    logger.debug(f'Trying lowercase readme.md: {lowercase_readme_url}')

                    lowercase_response = requests.get(lowercase_readme_url, timeout=2.0)
                    if lowercase_response.status_code == 200:
                        readme_content = lowercase_response.text
                        if len(readme_content) > 8000:
                            readme_content = (
                                readme_content[:8000] + '...\n[README truncated due to length]'
                            )

                        description = extract_description_from_readme(readme_content)
                        if description:
                            submodule_info.description = description

                        submodule_info.readme_content = readme_content
                        logger.debug(
                            f'Found lowercase readme.md for {name} ({len(readme_content)} chars)'
                        )
            except Exception as ex:
                logger.error(f'Error fetching README for submodule {name}: {ex}')

            # Add the submodule to our result list
            submodules.append(submodule_info)

        if len(submodule_dirs) > max_submodules:
            logger.warning(
                f'Only processed {max_submodules} out of {len(submodule_dirs)} submodules to avoid timeouts'
            )

        return submodules

    except Exception as e:
        logger.error(f'Error fetching submodules: {e}')
        logger.debug(f'Stack trace: {traceback.format_exc()}')
        return []


def extract_description_from_readme(readme_content: str) -> Optional[str]:
    """Extract a short description from the README content.

    Args:
        readme_content: The README markdown content

    Returns:
        Short description or None if not found
    """
    if not readme_content:
        return None

    # Try to find the first paragraph after any headings
    lines = readme_content.split('\n')
    paragraph_text = []

    for line in lines:
        # Skip headings, horizontal rules and blank lines
        if line.startswith('#') or line.startswith('---') or not line.strip():
            # If we already found a paragraph, return it
            if paragraph_text:
                break
            continue

        # Found text content, add to paragraph
        paragraph_text.append(line)

        # If this line ends a paragraph, break
        if not line.endswith('\\') and len(paragraph_text) > 0:
            break

    if paragraph_text:
        description = ' '.join(paragraph_text).strip()
        # Limit to 200 chars max
        if len(description) > 200:
            description = description[:197] + '...'
        return description

    return None


async def get_module_details(namespace: str, name: str, provider: str = 'aws') -> Dict:
    """Fetch detailed information about a specific Terraform module.

    Args:
        namespace: The module namespace (e.g., terraform-aws-modules)
        name: The module name (e.g., s3-bucket)
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
            if 'github.com' in source_url:
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


async def search_terraform_aws_modules_impl(
    query: str, limit: int = 3
) -> List[ModuleSearchResult]:
    """Search for AWS Terraform modules in the Terraform Registry.

    This tool searches the Terraform Registry for AWS modules that match the query
    and returns information about them, including their README content and submodules
    when available. The search is performed one keyword at a time to find matching modules.

    Parameters:
        query: Search term for modules (e.g., "vpc", "ecs", "lambda")
        limit: Maximum number of results to return (default: 3)

    Returns:
        A list of matching modules with their details including README content and submodules
    """
    total_start_time = time.time()
    logger.info(f"Searching Terraform Registry for AWS modules matching '{query}'")

    # Split the query into individual keywords
    keywords = query.strip().split()
    logger.info(f'Split query into {len(keywords)} keywords: {keywords}')

    # Use the Terraform Registry API
    try:
        url = 'https://registry.terraform.io/v1/modules/search'
        all_modules = []

        # Search for each keyword separately
        for keyword in keywords:
            logger.info(f"Searching for keyword: '{keyword}'")
            params = {'q': f'{keyword} aws', 'namespace': 'terraform-aws-modules', 'limit': limit}

            api_start_time = time.time()
            response = requests.get(url, params=params, timeout=5.0)
            api_duration_ms = (time.time() - api_start_time) * 1000
            logger.info(f'API request for keyword "{keyword}" took {api_duration_ms:.2f}ms')

            response.raise_for_status()

            data = response.json()
            modules = data.get('modules', [])
            logger.info(f'Found {len(modules)} matching modules for keyword "{keyword}"')

            # Add modules to the combined list
            all_modules.extend(modules)

        # Remove duplicates based on module name and namespace
        unique_modules = {}
        for module in all_modules:
            key = f'{module.get("namespace", "")}/{module.get("name", "")}'
            if key not in unique_modules:
                unique_modules[key] = module

        # Convert back to list and limit results
        modules = list(unique_modules.values())[:limit]
        logger.info(
            f'After removing duplicates, found {len(modules)} unique modules, processing up to {limit}'
        )

        results = []

        for module in modules:
            module_start_time = time.time()
            namespace = module.get('namespace', '')
            name = module.get('name', '')
            logger.info(f'Processing module: {namespace}/{name}')

            # Get the description and clean it
            description = module.get('description', 'No description available')
            cleaned_description = clean_description(description)
            logger.debug(f'Original description: {description}')
            logger.debug(f'Cleaned description: {cleaned_description}')

            # Create the basic result with cleaned description
            result = ModuleSearchResult(
                name=name,
                namespace=namespace,
                provider='aws',
                version=module.get('latest_version', 'unknown'),
                url=f'https://registry.terraform.io/modules/{namespace}/{name}/aws',
                description=cleaned_description,
            )

            # Get detailed information including README
            try:
                logger.debug(f'Fetching detailed information for {namespace}/{name}')
                details_start_time = time.time()
                details = await get_module_details(namespace, name)
                details_duration_ms = (time.time() - details_start_time) * 1000
                logger.info(f'Module details fetch for {name} took {details_duration_ms:.2f}ms')

                if details:
                    # Update the version if we got a better one from the details
                    if 'latest_version' in details:
                        result.version = details['latest_version']
                        logger.debug(f'Updated version to: {result.version}')

                    # Add version details if available
                    if 'version_details' in details:
                        result.version_details = details['version_details']
                        logger.debug('Added version details')

                    # Get README content
                    if 'readme_content' in details and details['readme_content']:
                        result.readme_content = details['readme_content']
                        logger.debug(f'Added README content ({len(result.readme_content)} chars)')
                    else:
                        logger.debug('No README content available in module details')

                    # Get input and output counts if available
                    if 'root' in details and 'inputs' in details['root']:
                        result.input_count = len(details['root']['inputs'])
                        logger.debug(f'Found {result.input_count} inputs')

                    if 'root' in details and 'outputs' in details['root']:
                        result.output_count = len(details['root']['outputs'])
                        logger.debug(f'Found {result.output_count} outputs')

                    # Add submodules if available
                    if 'submodules' in details and details['submodules']:
                        submodules = [
                            SubmoduleInfo(**submodule_data)
                            for submodule_data in details['submodules']
                        ]
                        result.submodules = submodules
                        logger.debug(f'Added {len(submodules)} submodules')
            except Exception as e:
                logger.warning(f'Error fetching details for {name}: {e}')

            results.append(result)
            module_duration_ms = (time.time() - module_start_time) * 1000
            logger.info(f'Finished processing module {name} in {module_duration_ms:.2f}ms')

        total_duration_ms = (time.time() - total_start_time) * 1000
        logger.info(f'Total search operation completed in {total_duration_ms:.2f}ms')
        return results
    except Exception as e:
        logger.error(f'Error searching Terraform Registry: {e}')
        return [
            ModuleSearchResult(
                name='Error',
                namespace='error',
                url='',
                description=f'Failed to search modules: {str(e)}',
                version='',
            )
        ]
