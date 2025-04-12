"""Implementation of AWSCC provider documentation search tool."""

import re
import requests
import sys
import time
import traceback
from ...models import TerraformAWSCCProviderDocsResult
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from typing import Literal, cast

# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {
            'sink': sys.stderr,
            'backtrace': True,
            'diagnose': True,
            'format': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        }
    ]
)

# Path to the static markdown file
STATIC_RESOURCES_PATH = (
    Path(__file__).parent.parent.parent / 'static' / 'AWSCC_PROVIDER_RESOURCES.md'
)

# Base URLs for AWSCC provider documentation
AWSCC_DOCS_BASE_URL = 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs'
GITHUB_RAW_BASE_URL = (
    'https://raw.githubusercontent.com/hashicorp/terraform-provider-awscc/main/docs'
)

# Simple in-memory cache
_GITHUB_DOC_CACHE = {}


def resource_to_github_path(
    asset_name: str, asset_type: str = 'resource', correlation_id: str = ''
) -> Tuple[str, str]:
    """Convert AWSCC resource type to GitHub documentation file path.

    Args:
        asset_name: The name of the asset to search (e.g., 'awscc_s3_bucket')
        asset_type: Type of asset to search for - 'resource' or 'data_source'
        correlation_id: Identifier for tracking this request in logs

    Returns:
        A tuple of (path, url) for the GitHub documentation file
    """
    # Remove the 'awscc_' prefix if present
    if asset_name.startswith('awscc_'):
        resource_name = asset_name[6:]
        logger.trace(f"[{correlation_id}] Removed 'awscc_' prefix: {resource_name}")
    else:
        resource_name = asset_name
        logger.trace(f"[{correlation_id}] No 'awscc_' prefix to remove: {resource_name}")

    # Determine document type based on asset_type parameter
    if asset_type == 'data_source':
        doc_type = 'data-sources'  # data sources
    elif asset_type == 'resource':
        doc_type = 'resources'  # resources
    else:
        # For "both" or any other value, determine based on name pattern
        # Data sources typically have 'data' in the name or follow other patterns
        is_data_source = 'data' in asset_name.lower()
        doc_type = 'data-sources' if is_data_source else 'resources'

    # Create the file path for the markdown documentation
    file_path = f'{doc_type}/{resource_name}.md'
    logger.trace(f'[{correlation_id}] Constructed GitHub file path: {file_path}')

    # Create the full URL to the raw GitHub content
    github_url = f'{GITHUB_RAW_BASE_URL}/{file_path}'
    logger.trace(f'[{correlation_id}] GitHub raw URL: {github_url}')

    return file_path, github_url


def fetch_github_documentation(
    asset_name: str, asset_type: str, cache_enabled: bool, correlation_id: str = ''
) -> Optional[Dict[str, Any]]:
    """Fetch documentation from GitHub for a specific resource type.

    Args:
        asset_name: The asset name (e.g., 'awscc_s3_bucket')
        asset_type: Either 'resource' or 'data_source'
        cache_enabled: Whether local cache is enabled or not
        correlation_id: Identifier for tracking this request in logs

    Returns:
        Dictionary with markdown content and metadata, or None if not found
    """
    start_time = time.time()
    logger.info(f"[{correlation_id}] Fetching documentation from GitHub for '{asset_name}'")

    # Create a cache key that includes both asset_name and asset_type
    cache_key = f'{asset_name}_{asset_type}'

    # Check cache first
    if cache_enabled:
        if cache_key in _GITHUB_DOC_CACHE:
            logger.info(
                f"[{correlation_id}] Using cached documentation for '{asset_name}' (asset_type: {asset_type})"
            )
            return _GITHUB_DOC_CACHE[cache_key]

    try:
        # Convert resource type to GitHub path and URL
        _, github_url = resource_to_github_path(asset_name, asset_type, correlation_id)

        # Fetch the markdown content from GitHub
        logger.info(f'[{correlation_id}] Fetching from GitHub: {github_url}')
        response = requests.get(github_url, timeout=10)

        if response.status_code != 200:
            logger.warning(
                f'[{correlation_id}] GitHub request failed: HTTP {response.status_code}'
            )
            return None

        markdown_content = response.text
        content_length = len(markdown_content)
        logger.debug(f'[{correlation_id}] Received markdown content: {content_length} bytes')

        if content_length > 0:
            preview_length = min(200, content_length)
            logger.trace(
                f'[{correlation_id}] Markdown preview: {markdown_content[:preview_length]}...'
            )

        # Parse the markdown content
        result = parse_markdown_documentation(
            markdown_content, asset_name, github_url, correlation_id
        )

        # Cache the result with the composite key
        if cache_enabled:
            _GITHUB_DOC_CACHE[cache_key] = result

        fetch_time = time.time() - start_time
        logger.info(f'[{correlation_id}] GitHub documentation fetched in {fetch_time:.2f} seconds')
        return result

    except requests.exceptions.Timeout as e:
        logger.exception(f'[{correlation_id}] Timeout error fetching from GitHub: {str(e)}')
        return None
    except requests.exceptions.RequestException as e:
        logger.exception(f'[{correlation_id}] Request error fetching from GitHub: {str(e)}')
        return None
    except Exception as e:
        logger.exception(f'[{correlation_id}] Unexpected error fetching from GitHub')
        logger.error(f'[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}')
        return None


def parse_markdown_documentation(
    content: str,
    asset_name: str,
    url: str,
    correlation_id: str = '',
) -> Dict[str, Any]:
    """Parse markdown documentation content for a resource.

    Args:
        content: The markdown content
        asset_name: The asset name
        url: The source URL for this documentation
        correlation_id: Identifier for tracking this request in logs

    Returns:
        Dictionary with parsed documentation details
    """
    start_time = time.time()
    logger.debug(f"[{correlation_id}] Parsing markdown documentation for '{asset_name}'")

    try:
        # Find the title (typically the first heading)
        title_match = re.search(r'^#\s+(.*?)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            logger.debug(f"[{correlation_id}] Found title: '{title}'")
        else:
            title = f'AWS {asset_name}'
            logger.debug(f"[{correlation_id}] No title found, using default: '{title}'")

        # Find the main resource description section (all content after resource title before next heading)
        description = ''
        resource_heading_pattern = re.compile(
            rf'# {re.escape(asset_name)}\s+\(Resource\)\s*(.*?)(?=\n#|\Z)', re.DOTALL
        )
        resource_match = resource_heading_pattern.search(content)

        if resource_match:
            # Extract the description text and clean it up
            description = resource_match.group(1).strip()
            logger.debug(
                f"[{correlation_id}] Found resource description section: '{description[:100]}...'"
            )
        else:
            # Fall back to the description found on the starting markdown table of each github markdown page
            desc_match = re.search(r'description:\s*\|-\n(.*?)\n---', content, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
                logger.debug(
                    f"[{correlation_id}] Using fallback description: '{description[:100]}...'"
                )
            else:
                description = f'Documentation for AWSCC {asset_name}'
                logger.debug(f'[{correlation_id}] No description found, using default')

        # Find all example snippets
        example_snippets = []

        # First try to extract from the Example Usage section
        example_section_match = re.search(r'## Example Usage\n([\s\S]*?)(?=\n## |\Z)', content)

        if example_section_match:
            # logger.debug(f"example_section_match: {example_section_match.group()}")
            example_section = example_section_match.group(1).strip()
            logger.debug(
                f'[{correlation_id}] Found Example Usage section ({len(example_section)} chars)'
            )

            # Find all subheadings in the Example Usage section with a more robust pattern
            subheading_list = list(
                re.finditer(r'### (.*?)[\r\n]+(.*?)(?=###|\Z)', example_section, re.DOTALL)
            )
            logger.debug(
                f'[{correlation_id}] Found {len(subheading_list)} subheadings in Example Usage section'
            )
            subheading_found = False

            # Check if there are any subheadings
            for match in subheading_list:
                # logger.info(f"subheading match: {match.group()}")
                subheading_found = True
                title = match.group(1).strip()
                subcontent = match.group(2).strip()

                logger.debug(
                    f"[{correlation_id}] Found subheading '{title}' with {len(subcontent)} chars content"
                )

                # Find code blocks in this subsection - pattern to match terraform code blocks
                code_match = re.search(r'```(?:terraform|hcl)?\s*(.*?)```', subcontent, re.DOTALL)
                if code_match:
                    code_snippet = code_match.group(1).strip()
                    example_snippets.append({'title': title, 'code': code_snippet})
                    logger.debug(
                        f"[{correlation_id}] Added example snippet for '{title}' ({len(code_snippet)} chars)"
                    )

            # If no subheadings were found, look for direct code blocks under Example Usage
            if not subheading_found:
                logger.debug(
                    f'[{correlation_id}] No subheadings found, looking for direct code blocks'
                )
                # Improved pattern for code blocks
                code_blocks = re.finditer(
                    r'```(?:terraform|hcl)?\s*(.*?)```', example_section, re.DOTALL
                )
                code_found = False

                for code_match in code_blocks:
                    code_found = True
                    code_snippet = code_match.group(1).strip()
                    example_snippets.append({'title': 'Example Usage', 'code': code_snippet})
                    logger.debug(
                        f'[{correlation_id}] Added direct example snippet ({len(code_snippet)} chars)'
                    )

                if not code_found:
                    logger.debug(
                        f'[{correlation_id}] No code blocks found in Example Usage section'
                    )
        else:
            logger.debug(f'[{correlation_id}] No Example Usage section found')

        if example_snippets:
            logger.info(f'[{correlation_id}] Found {len(example_snippets)} example snippets')
        else:
            logger.debug(f'[{correlation_id}] No example snippets found')

        # Extract Schema section
        schema_arguments = []
        schema_section_match = re.search(r'## Schema\n([\s\S]*?)(?=\n## |\Z)', content)
        if schema_section_match:
            schema_section = schema_section_match.group(1).strip()
            logger.debug(f'[{correlation_id}] Found Schema section ({len(schema_section)} chars)')

            # DO NOT Look for schema arguments directly under the main Schema section
            # args_under_main_section_match = re.search(r'(.*?)(?=\n###|\n##|$)', schema_section, re.DOTALL)
            # if args_under_main_section_match:
            #     args_under_main_section = args_under_main_section_match.group(1).strip()
            #     logger.debug(
            #         f'[{correlation_id}] Found arguments directly under the Schema section ({len(args_under_main_section)} chars)'
            #     )

            #     # Find arguments in this subsection
            #     arg_matches = re.finditer(
            #         r'-\s+`([^`]+)`\s+(.*?)(?=\n-\s+`|$)',
            #         args_under_main_section,
            #         re.DOTALL,
            #     )
            #     arg_list = list(arg_matches)
            #     logger.debug(
            #         f'[{correlation_id}] Found {len(arg_list)} arguments directly under the Argument Reference section'
            #     )

            #     for match in arg_list:
            #         arg_name = match.group(1).strip()
            #         arg_desc = match.group(2).strip() if match.group(2) else None
            #         # Do not add arguments that do not have a description
            #         if arg_name is not None and arg_desc is not None:
            #             schema_arguments.append({'name': arg_name, 'description': arg_desc, 'schema_section': "main"})
            #         logger.debug(
            #             f"[{correlation_id}] Added argument '{arg_name}': '{arg_desc[:50]}...' (truncated)"
            #         )

            # Now, Find all subheadings in the Argument Reference section with a more robust pattern
            subheading_list = list(
                re.finditer(r'### (.*?)[\r\n]+(.*?)(?=###|\Z)', schema_section, re.DOTALL)
            )
            logger.debug(
                f'[{correlation_id}] Found {len(subheading_list)} subheadings in Argument Reference section'
            )
            subheading_found = False

            # Check if there are any subheadings
            for match in subheading_list:
                subheading_found = True
                title = match.group(1).strip()
                subcontent = match.group(2).strip()
                logger.debug(
                    f"[{correlation_id}] Found subheading '{title}' with {len(subcontent)} chars content"
                )

                # Find arguments in this subsection
                arg_matches = re.finditer(
                    r'-\s+`([^`]+)`\s+(.*?)(?=\n-\s+`|$)',
                    subcontent,
                    re.DOTALL,
                )
                arg_list = list(arg_matches)
                logger.debug(
                    f'[{correlation_id}] Found {len(arg_list)} arguments in subheading {title}'
                )

                for match in arg_list:
                    arg_name = match.group(1).strip()
                    arg_desc = match.group(2).strip() if match.group(2) else None
                    # Do not add arguments that do not have a description
                    if arg_name is not None and arg_desc is not None:
                        schema_arguments.append({'name': arg_name, 'description': arg_desc, 'argument_section': title})
                    else:
                        logger.debug(
                            f"[{correlation_id}] Added argument '{arg_name}': '{arg_desc[:50] if arg_desc else 'No description found'}...' (truncated)"
                        )

            schema_arguments = schema_arguments if schema_arguments else None
            if schema_arguments:
                logger.info(
                    f'[{correlation_id}] Found {len(schema_arguments)} arguments across all sections'
                )
        else:
            logger.debug(f'[{correlation_id}] No Schema section found')

        # Return the parsed information
        parse_time = time.time() - start_time
        logger.debug(f'[{correlation_id}] Markdown parsing completed in {parse_time:.2f} seconds')

        return {
            'title': title,
            'description': description,
            'example_snippets': example_snippets if example_snippets else None,
            'url': url,
            'schema_arguments': schema_arguments,
        }

    except Exception as e:
        logger.exception(f'[{correlation_id}] Error parsing markdown content')
        logger.error(f'[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}')

        # Return partial info if available
        return {
            'title': f'AWSCC {asset_name}',
            'description': f'Documentation for AWSCC {asset_name} (Error parsing details: {str(e)})',
            'url': url,
            'example_snippets': None,
            'schema_arguments': None,
        }


async def search_awscc_provider_docs_impl(
    asset_name: str, asset_type: str = 'resource', cache_enabled: bool = False
) -> List[TerraformAWSCCProviderDocsResult]:
    """Search AWSCC provider documentation for resources and data sources.

    This tool searches the Terraform AWSCC provider documentation for information about
    specific assets, which can either be resources or data sources. It retrieves comprehensive details including
    descriptions, example code snippets, and schema information.

    The AWSCC provider is based on the AWS Cloud Control API and provides a more consistent interface to AWS resources compared to the standard AWS provider.

    The implementation fetches documentation directly from the official Terraform AWSCC provider
    GitHub repository to ensure the most up-to-date information. Results are cached for
    improved performance on subsequent queries.

    The tool retrieves comprehensive details including descriptions, example code snippets,
    and schema information (required, optional, and read-only attributes). It also handles
    nested schema structures for complex attributes.

    The tool will automatically handle prefixes - you can search for either 'awscc_s3_bucket' or 's3_bucket'.

    Examples:
        - To get documentation for an S3 bucket resource:
          search_awscc_provider_docs_impl(resource_type='awscc_s3_bucket')

        - To find information about a specific attribute:
          search_awscc_provider_docs_impl(resource_type='awscc_lambda_function', attribute='code')

        - Without the prefix:
          search_awscc_provider_docs_impl(resource_type='ec2_instance')

    Parameters:
        asset_name: Name of the AWSCC Provider resource or data source to look for (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        asset_type: Type of documentation to search - 'resource' (default), 'data_source', or 'both'. Some resources and data sources share the same name

    Returns:
        A list of matching documentation entries with details including:
        - Resource name and description
        - URL to the official documentation
        - Example code snippets
        - Schema information (required, optional, read-only, and nested structures attributes)
    """
    start_time = time.time()
    correlation_id = f'search-{int(start_time * 1000)}'
    logger.info(f"[{correlation_id}] Starting AWSCC provider docs search for '{asset_name}'")

    search_term = asset_name.lower()

    try:
        # Try fetching from GitHub
        logger.info(f'[{correlation_id}] Fetching from GitHub')

        results = []

        # If asset_type is "both", try both resource and data source paths
        if asset_type == 'both':
            logger.info(f'[{correlation_id}] Searching for both resources and data sources')

            # First try as a resource
            github_result = fetch_github_documentation(
                search_term, 'resource', cache_enabled, correlation_id
            )
            if github_result:
                logger.info(f'[{correlation_id}] Found documentation as a resource')
                # Create result object
                description = github_result['description']

                result = TerraformAWSCCProviderDocsResult(
                    asset_name=asset_name,
                    asset_type='resource',
                    description=description,
                    url=github_result['url'],
                    example_usage=github_result.get('example_snippets'),
                    schema_arguments=github_result.get('schema_arguments'),
                )
                results.append(result)

            # Then try as a data source
            data_result = fetch_github_documentation(
                search_term, 'data_source', cache_enabled, correlation_id
            )
            if data_result:
                logger.info(f'[{correlation_id}] Found documentation as a data source')
                # Create result object
                description = data_result['description']

                result = TerraformAWSCCProviderDocsResult(
                    asset_name=asset_name,
                    asset_type='data_source',
                    description=description,
                    url=data_result['url'],
                    example_usage=data_result.get('example_snippets'),
                    schema_arguments=data_result.get('schema_arguments'),
                )
                results.append(result)

            if results:
                logger.info(f'[{correlation_id}] Found {len(results)} documentation entries')
                end_time = time.time()
                logger.info(
                    f'[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (GitHub source)'
                )
                return results
        else:
            # Search for either resource or data source based on asset_type parameter
            github_result = fetch_github_documentation(
                search_term, asset_type, cache_enabled, correlation_id
            )
            if github_result:
                logger.info(f'[{correlation_id}] Successfully found GitHub documentation')

                # Create result object
                description = github_result['description']
                result = TerraformAWSCCProviderDocsResult(
                    asset_name=asset_name,
                    asset_type=cast(Literal['both', 'resource', 'data_source'], asset_type),
                    description=description,
                    url=github_result['url'],
                    example_usage=github_result.get('example_snippets'),
                    schema_arguments=github_result.get('schema_arguments'),
                )

                end_time = time.time()
                logger.info(
                    f'[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (GitHub source)'
                )
                return [result]

        # If GitHub approach fails, return a "not found" result
        logger.warning(f"[{correlation_id}] Documentation not found on GitHub for '{search_term}'")

        # Return a "not found" result
        logger.warning(f'[{correlation_id}] No documentation found for asset {asset_name}')
        end_time = time.time()
        logger.info(
            f'[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (no results)'
        )
        return [
            TerraformAWSCCProviderDocsResult(
                asset_name='Not found',
                asset_type=cast(Literal['both', 'resource', 'data_source'], asset_type),
                description=f"No documentation found for resource type '{asset_name}'.",
                url=None,
                example_usage=None,
                schema_arguments=None,
            )
        ]

    except Exception as e:
        logger.exception(f'[{correlation_id}] Error searching AWSCC provider docs')
        logger.error(f'[{correlation_id}] Exception details: {type(e).__name__}: {str(e)}')
        logger.debug(
            f'[{correlation_id}] Traceback: {"".join(traceback.format_tb(e.__traceback__))}'
        )

        end_time = time.time()
        logger.info(f'[{correlation_id}] Search failed in {end_time - start_time:.2f} seconds')

        return [
            TerraformAWSCCProviderDocsResult(
                asset_name='Error',
                asset_type=cast(Literal['both', 'resource', 'data_source'], asset_type),
                description=f'Failed to search AWSCC provider documentation: {type(e).__name__}: {str(e)}',
                url=None,
                example_usage=None,
                schema_arguments=None,
            )
        ]
