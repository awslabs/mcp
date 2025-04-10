"""Implementation of AWS provider documentation search tool."""

import re
import requests
import sys
import time
import traceback
from ...models import ProviderDocsResult
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
    Path(__file__).parent.parent.parent / 'static' / 'AWS_PROVIDER_RESOURCES.md'
)

# Base URLs for AWS provider documentation
AWS_DOCS_BASE_URL = 'https://registry.terraform.io/providers/hashicorp/aws/latest/docs'
GITHUB_RAW_BASE_URL = (
    'https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs'
)

# Simple in-memory cache
_GITHUB_DOC_CACHE = {}


def resource_to_github_path(
    resource_type: str, correlation_id: str = '', doc_kind: str = 'resource'
) -> Tuple[str, str]:
    """Convert AWS resource type to GitHub documentation file path.

    Args:
        resource_type: The resource type (e.g., 'aws_s3_bucket')
        correlation_id: Identifier for tracking this request in logs
        doc_kind: Type of document to search for - 'resource', 'data_source', or 'both' (default: 'resource')

    Returns:
        A tuple of (path, url) for the GitHub documentation file
    """
    # Remove the 'aws_' prefix if present
    if resource_type.startswith('aws_'):
        resource_name = resource_type[4:]
        logger.debug(f"[{correlation_id}] Removed 'aws_' prefix: {resource_name}")
    else:
        resource_name = resource_type
        logger.debug(f"[{correlation_id}] No 'aws_' prefix to remove: {resource_name}")

    # Determine document type based on doc_kind parameter
    if doc_kind == 'data_source':
        doc_type = 'd'  # data sources
    elif doc_kind == 'resource':
        doc_type = 'r'  # resources
    else:
        # For "both" or any other value, determine based on name pattern
        # Data sources typically have 'data' in the name or follow other patterns
        is_data_source = 'data' in resource_type.lower()
        doc_type = 'd' if is_data_source else 'r'

    # Create the file path for the markdown documentation
    file_path = f'{doc_type}/{resource_name}.html.markdown'
    logger.debug(f'[{correlation_id}] Constructed GitHub file path: {file_path}')

    # Create the full URL to the raw GitHub content
    github_url = f'{GITHUB_RAW_BASE_URL}/{file_path}'
    logger.debug(f'[{correlation_id}] GitHub raw URL: {github_url}')

    return file_path, github_url


def fetch_github_documentation(
    resource_type: str, correlation_id: str = '', doc_kind: str = 'resource'
) -> Optional[Dict[str, Any]]:
    """Fetch documentation from GitHub for a specific resource type.

    Args:
        resource_type: The resource type (e.g., 'aws_s3_bucket')
        correlation_id: Identifier for tracking this request in logs
        doc_kind: Type of document to search for - 'resource', 'data_source', or 'both' (default: 'resource')

    Returns:
        Dictionary with markdown content and metadata, or None if not found
    """
    start_time = time.time()
    logger.info(f"[{correlation_id}] Fetching documentation from GitHub for '{resource_type}'")

    # Create a cache key that includes both resource_type and doc_kind
    cache_key = f'{resource_type}_{doc_kind}'

    # Check cache first
    if cache_key in _GITHUB_DOC_CACHE:
        logger.info(
            f"[{correlation_id}] Using cached documentation for '{resource_type}' (kind: {doc_kind})"
        )
        return _GITHUB_DOC_CACHE[cache_key]

    try:
        # Convert resource type to GitHub path and URL
        _, github_url = resource_to_github_path(resource_type, correlation_id, doc_kind)

        # Fetch the markdown content from GitHub
        logger.debug(f'[{correlation_id}] Fetching from GitHub: {github_url}')
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
            logger.debug(
                f'[{correlation_id}] Markdown preview: {markdown_content[:preview_length]}...'
            )

        # Parse the markdown content
        result = parse_markdown_documentation(
            markdown_content, resource_type, github_url, correlation_id
        )

        # Cache the result with the composite key
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
    resource_type: str,
    url: str,
    correlation_id: str = '',
    attribute: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse markdown documentation content for a resource.

    Args:
        content: The markdown content
        resource_type: The resource type
        url: The source URL for this documentation
        correlation_id: Identifier for tracking this request in logs
        attribute: Optional attribute to look for

    Returns:
        Dictionary with parsed documentation details
    """
    start_time = time.time()
    logger.debug(f"[{correlation_id}] Parsing markdown documentation for '{resource_type}'")

    try:
        # Extract description: First paragraph after page title
        description = ''
        attribute_info = None

        # Find the title (typically the first heading)
        title_match = re.search(r'^#\s+(.*?)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            logger.debug(f"[{correlation_id}] Found title: '{title}'")
        else:
            title = f'AWS {resource_type}'
            logger.debug(f"[{correlation_id}] No title found, using default: '{title}'")

        # Find the main resource description section (all content after resource title before next heading)
        resource_heading_pattern = re.compile(
            rf'# Resource: {re.escape(resource_type)}\s*(.*?)(?=\n##|\Z)', re.DOTALL
        )
        resource_match = resource_heading_pattern.search(content)

        if resource_match:
            # Extract the description text and clean it up
            description = resource_match.group(1).strip()
            logger.debug(
                f"[{correlation_id}] Found resource description section: '{description[:100]}...'"
            )
        else:
            # Fall back to the first non-heading paragraph if resource section not found
            desc_match = re.search(r'^(?!#)(.+?)$', content, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
                logger.debug(
                    f"[{correlation_id}] Using fallback description: '{description[:100]}...'"
                )
            else:
                description = f'Documentation for AWS {resource_type}'
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

                # Find code blocks in this subsection - improved pattern to match terraform code blocks
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

            # Fallback: Look for any code block that contains the resource type
            code_block_pattern = re.compile(r'```(?:terraform|hcl)?\s*(.*?)\n```', re.DOTALL)
            for code_match in code_block_pattern.finditer(content):
                code_content = code_match.group(1).strip()
                if resource_type in code_content and 'resource' in code_content:
                    example_snippets.append({'title': 'Example Usage', 'code': code_content})
                    logger.debug(
                        f'[{correlation_id}] Found resource-specific code example via fallback ({len(code_content)} chars)'
                    )
                    break

        if example_snippets:
            logger.debug(f'[{correlation_id}] Found {len(example_snippets)} example snippets')
        else:
            logger.debug(f'[{correlation_id}] No example snippets found')

        # Find attribute information if specified
        if attribute:
            logger.debug(f"[{correlation_id}] Looking for info about attribute '{attribute}'")

            # Look in argument reference section
            arg_ref_match = re.search(
                r'## Argument Reference\s+(.*?)(?=##|\Z)', content, re.DOTALL
            )
            if arg_ref_match:
                arg_ref_content = arg_ref_match.group(1)

                # Pattern to match attributes with formatting: `attribute` - Description
                # Also handles indentation and multiline descriptions
                attr_pattern = re.compile(
                    rf'[*-]\s+[`"]?{re.escape(attribute)}[`"]?\s*-\s*(.*?)(?=\n\s*[*-]|\n##|\Z)',
                    re.DOTALL,
                )
                attr_match = attr_pattern.search(arg_ref_content)

                if attr_match:
                    # Clean up the attribute description - remove excessive whitespace and newlines
                    attribute_info = re.sub(r'\s+', ' ', attr_match.group(1).strip())
                    logger.debug(
                        f"[{correlation_id}] Found attribute info: '{attribute_info[:100]}...'"
                    )
                else:
                    # Try alternative format where attribute might be alone on a line
                    alt_pattern = re.compile(
                        rf'[*-]\s+[`"]?{re.escape(attribute)}[`"]?[^-\n]*\n\s+(.*?)(?=\n\s*[*-]|\n##|\Z)',
                        re.DOTALL,
                    )
                    alt_match = alt_pattern.search(arg_ref_content)

                    if alt_match:
                        attribute_info = re.sub(r'\s+', ' ', alt_match.group(1).strip())
                        logger.debug(
                            f"[{correlation_id}] Found attribute info with alternative pattern: '{attribute_info[:100]}...'"
                        )
                    # Fall back to searching for just the attribute name in the section
                    elif attribute in arg_ref_content:
                        attribute_info = f"The '{attribute}' attribute is mentioned in the argument reference section."
                        logger.debug(
                            f'[{correlation_id}] Attribute mentioned but details not found'
                        )

            # If not found in argument reference, check attribute reference section
            if not attribute_info:
                attr_ref_match = re.search(
                    r'## Attribute Reference\s+(.*?)(?=##|\Z)', content, re.DOTALL
                )
                if attr_ref_match:
                    # Apply the same patterns to the attribute reference section
                    attr_content = attr_ref_match.group(1)
                    attr_pattern = re.compile(
                        rf'[*-]\s+[`"]?{re.escape(attribute)}[`"]?\s*-\s*(.*?)(?=\n\s*[*-]|\n##|\Z)',
                        re.DOTALL,
                    )
                    attr_match = attr_pattern.search(attr_content)

                    if attr_match:
                        attribute_info = re.sub(r'\s+', ' ', attr_match.group(1).strip())
                        logger.debug(
                            f"[{correlation_id}] Found attribute info in attribute reference section: '{attribute_info[:100]}...'"
                        )
                    elif attribute in attr_content:
                        attribute_info = f"The '{attribute}' attribute is mentioned in the attribute reference section."
                        logger.debug(
                            f'[{correlation_id}] Attribute mentioned in attribute reference section but details not found'
                        )

        # Extract Arguments Reference section
        arguments = []
        arg_ref_match = re.search(r'## Argument Reference\n([\s\S]*?)(?=\n## |\Z)', content)
        if arg_ref_match:
            arg_section = arg_ref_match.group(1).strip()
            logger.debug(
                f'[{correlation_id}] Found Argument Reference section ({len(arg_section)} chars)'
            )

            # Parse arguments - typically in list format with bullet points
            arg_matches = re.finditer(
                r'[*-]\s+[`"]?([^`":\n]+)[`"]?(?:[`":\s-]+)?(.*?)(?=\n[*-]|\n\n|\Z)',
                arg_section,
                re.DOTALL,
            )
            arg_list = list(arg_matches)
            logger.debug(
                f'[{correlation_id}] Found {len(arg_list)} arguments in Argument Reference section'
            )

            for match in arg_list:
                arg_name = match.group(1).strip()
                arg_desc = match.group(2).strip() if match.group(2) else 'No description available'
                arguments.append({'name': arg_name, 'description': arg_desc})
                logger.debug(
                    f"[{correlation_id}] Added argument '{arg_name}': '{arg_desc[:50]}...' (truncated)"
                )

            arguments = arguments if arguments else None
        else:
            logger.debug(f'[{correlation_id}] No Argument Reference section found')

        # Extract Attributes Reference section
        attributes = []
        attr_ref_match = re.search(r'## Attribute Reference\n([\s\S]*?)(?=\n## |\Z)', content)
        if attr_ref_match:
            attr_section = attr_ref_match.group(1).strip()
            logger.debug(
                f'[{correlation_id}] Found Attribute Reference section ({len(attr_section)} chars)'
            )

            # Parse attributes - similar format to arguments
            attr_matches = re.finditer(
                r'[*-]\s+[`"]?([^`":\n]+)[`"]?(?:[`":\s-]+)?(.*?)(?=\n[*-]|\n\n|\Z)',
                attr_section,
                re.DOTALL,
            )
            attr_list = list(attr_matches)
            logger.debug(
                f'[{correlation_id}] Found {len(attr_list)} attributes in Attribute Reference section'
            )

            for match in attr_list:
                attr_name = match.group(1).strip()
                attr_desc = (
                    match.group(2).strip() if match.group(2) else 'No description available'
                )
                attributes.append({'name': attr_name, 'description': attr_desc})
                logger.debug(
                    f"[{correlation_id}] Added attribute '{attr_name}': '{attr_desc[:50]}...' (truncated)"
                )

            attributes = attributes if attributes else None
        else:
            logger.debug(f'[{correlation_id}] No Attribute Reference section found')

        # Return the parsed information
        parse_time = time.time() - start_time
        logger.debug(f'[{correlation_id}] Markdown parsing completed in {parse_time:.2f} seconds')

        return {
            'title': title,
            'description': description,
            'example_snippets': example_snippets,
            'attribute_info': attribute_info,
            'url': url,
            'arguments': arguments,
            'attributes': attributes,
        }

    except Exception as e:
        logger.exception(f'[{correlation_id}] Error parsing markdown content')
        logger.error(f'[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}')

        # Return partial info if available
        return {
            'title': f'AWS {resource_type}',
            'description': f'Documentation for AWS {resource_type} (Error parsing details: {str(e)})',
            'example_snippets': None,
            'attribute_info': None,
            'url': url,
            'arguments': None,
            'attributes': None,
        }


async def search_aws_provider_docs_impl(
    resource_type: str, attribute: Optional[str] = None, kind: str = 'both'
) -> List[ProviderDocsResult]:
    """Search AWS provider documentation for resources and attributes.

    This tool searches the Terraform AWS provider documentation for information about
    specific resource types and their attributes. It retrieves comprehensive details including
    descriptions, example code snippets, argument references, and attribute references.

    The implementation fetches documentation directly from the official Terraform AWS provider
    GitHub repository to ensure the most up-to-date information. Results are cached for
    improved performance on subsequent queries.

    Use the 'kind' parameter to specify if you are looking for information about provider 
    resources, data sources, or both. The tool will automatically handle prefixes - you can 
    search for either 'aws_s3_bucket' or 's3_bucket'.

    Examples:
        - To get documentation for an S3 bucket resource:
          search_aws_provider_docs_impl(resource_type='aws_s3_bucket')
        
        - To find information about a specific attribute:
          search_aws_provider_docs_impl(resource_type='aws_lambda_function', attribute='runtime')
        
        - To search only for data sources:
          search_aws_provider_docs_impl(resource_type='aws_ami', kind='data_source')
        
        - To search only for resources:
          search_aws_provider_docs_impl(resource_type='aws_instance', kind='resource')

    Parameters:
        resource_type: AWS resource type (e.g., 'aws_s3_bucket', 'aws_lambda_function')
        attribute: Optional specific attribute to search for
        kind: Type of documentation to search - 'resource', 'data_source', or 'both' (default)

    Returns:
        A list of matching documentation entries with details including:
        - Resource name and description
        - Example code snippets
        - Arguments with descriptions
        - Attributes with descriptions
        - URL to the official documentation
    """
    start_time = time.time()
    correlation_id = f'search-{int(start_time * 1000)}'
    logger.info(f"[{correlation_id}] Starting AWS provider docs search for '{resource_type}'")

    if attribute:
        logger.info(f"[{correlation_id}] Also searching for attribute '{attribute}'")

    search_term = resource_type.lower()

    try:
        # Try fetching from GitHub
        logger.info(f'[{correlation_id}] Fetching from GitHub')

        results = []

        # If kind is "both", try both resource and data source paths
        if kind == 'both':
            logger.info(f'[{correlation_id}] Searching for both resources and data sources')

            # First try as a resource
            github_result = fetch_github_documentation(search_term, correlation_id, 'resource')
            if github_result:
                logger.info(f'[{correlation_id}] Found documentation as a resource')
                # Create result object
                description = github_result['description']
                if attribute and github_result.get('attribute_info'):
                    description += f' {github_result["attribute_info"]}'

                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=github_result['url'],
                    description=description,
                    example_snippets=github_result.get('example_snippets'),
                    arguments=github_result.get('arguments'),
                    attributes=github_result.get('attributes'),
                    kind='resource',
                )
                results.append(result)

            # Then try as a data source
            data_result = fetch_github_documentation(search_term, correlation_id, 'data_source')
            if data_result:
                logger.info(f'[{correlation_id}] Found documentation as a data source')
                # Create result object
                description = data_result['description']
                if attribute and data_result.get('attribute_info'):
                    description += f' {data_result["attribute_info"]}'

                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=data_result['url'],
                    description=description,
                    example_snippets=data_result.get('example_snippets'),
                    arguments=data_result.get('arguments'),
                    attributes=data_result.get('attributes'),
                    kind='data_source',
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
            # Search for either resource or data source based on kind parameter
            github_result = fetch_github_documentation(search_term, correlation_id, kind)
            if github_result:
                logger.info(f'[{correlation_id}] Successfully found GitHub documentation')

                # Create result object
                description = github_result['description']
                if attribute and github_result.get('attribute_info'):
                    description += f' {github_result["attribute_info"]}'

                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=github_result['url'],
                    description=description,
                    example_snippets=github_result.get('example_snippets'),
                    arguments=github_result.get('arguments'),
                    attributes=github_result.get('attributes'),
                    kind=kind,
                )

                end_time = time.time()
                logger.info(
                    f'[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (GitHub source)'
                )
                return [result]

        # If GitHub approach fails, return a "not found" result
        logger.warning(f"[{correlation_id}] Documentation not found on GitHub for '{search_term}'")

        # Return a "not found" result
        logger.warning(f'[{correlation_id}] No resource documentation found')
        end_time = time.time()
        logger.info(
            f'[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (no results)'
        )
        return [
            ProviderDocsResult(
                resource_name='Not found',
                url=f'{AWS_DOCS_BASE_URL}/resources',
                description=f"No documentation found for resource type '{resource_type}'.",
                example_snippets=None,
                arguments=None,
                attributes=None,
            )
        ]

    except Exception as e:
        logger.exception(f'[{correlation_id}] Error searching AWS provider docs')
        logger.error(f'[{correlation_id}] Exception details: {type(e).__name__}: {str(e)}')
        logger.debug(
            f'[{correlation_id}] Traceback: {"".join(traceback.format_tb(e.__traceback__))}'
        )

        end_time = time.time()
        logger.info(f'[{correlation_id}] Search failed in {end_time - start_time:.2f} seconds')

        return [
            ProviderDocsResult(
                resource_name='Error',
                url='',
                description=f'Failed to search AWS provider documentation: {type(e).__name__}: {str(e)}',
                example_snippets=None,
                arguments=None,
                attributes=None,
            )
        ]
