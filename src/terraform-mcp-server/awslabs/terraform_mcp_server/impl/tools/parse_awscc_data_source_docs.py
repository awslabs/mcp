"""Implementation of AWSCC data source documentation parser tool."""

import re
import requests
import sys
import time
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple

from ...models import ProviderDocsResult

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

# Simple in-memory cache
_GITHUB_DOC_CACHE = {}


async def parse_awscc_data_source_docs_impl(
    url: str, resource_type: str, attribute: Optional[str] = None
) -> ProviderDocsResult:
    """Parse AWSCC data source documentation from a URL.

    This tool parses the Terraform AWSCC provider data source documentation from a URL
    and returns a structured representation of the documentation.

    Parameters:
        url: URL to the data source documentation
        resource_type: AWSCC resource type (e.g., 'awscc_lambda_function')
        attribute: Optional specific attribute to search for

    Returns:
        A ProviderDocsResult object containing the parsed documentation
    """
    start_time = time.time()
    correlation_id = f'parse-{int(start_time * 1000)}'
    logger.info(f"[{correlation_id}] Parsing AWSCC data source documentation for '{resource_type}' from {url}")

    # Check cache first
    cache_key = f'{url}_{resource_type}'
    if cache_key in _GITHUB_DOC_CACHE:
        logger.info(f"[{correlation_id}] Using cached documentation for '{resource_type}'")
        return _GITHUB_DOC_CACHE[cache_key]

    try:
        # Fetch the markdown content from the URL
        logger.debug(f'[{correlation_id}] Fetching from URL: {url}')
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            logger.warning(f'[{correlation_id}] URL request failed: HTTP {response.status_code}')
            return ProviderDocsResult(
                resource_name=resource_type,
                url=url,
                description=f"Failed to fetch documentation for {resource_type}: HTTP {response.status_code}",
                example_snippets=None,
                arguments=None,
                schema={'required': [], 'optional': [], 'read_only': [], 'nested': {}},
                kind='data_source',
            )

        markdown_content = response.text
        content_length = len(markdown_content)
        logger.debug(f'[{correlation_id}] Received markdown content: {content_length} bytes')

        if content_length > 0:
            preview_length = min(200, content_length)
            logger.debug(f'[{correlation_id}] Markdown preview: {markdown_content[:preview_length]}...')

        # Parse the markdown content
        result = parse_data_source_markdown(markdown_content, resource_type, url, correlation_id, attribute)

        # Cache the result
        _GITHUB_DOC_CACHE[cache_key] = result

        parse_time = time.time() - start_time
        logger.info(f'[{correlation_id}] Documentation parsed in {parse_time:.2f} seconds')
        return result

    except requests.exceptions.Timeout as e:
        logger.exception(f'[{correlation_id}] Timeout error fetching from URL: {str(e)}')
        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=f"Timeout error fetching documentation for {resource_type}: {str(e)}",
            example_snippets=None,
            arguments=None,
            schema={'required': [], 'optional': [], 'read_only': [], 'nested': {}},
            kind='data_source',
        )
    except requests.exceptions.RequestException as e:
        logger.exception(f'[{correlation_id}] Request error fetching from URL: {str(e)}')
        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=f"Request error fetching documentation for {resource_type}: {str(e)}",
            example_snippets=None,
            arguments=None,
            schema={'required': [], 'optional': [], 'read_only': [], 'nested': {}},
            kind='data_source',
        )
    except Exception as e:
        logger.exception(f'[{correlation_id}] Unexpected error parsing documentation')
        logger.error(f'[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}')
        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=f"Error parsing documentation for {resource_type}: {type(e).__name__}: {str(e)}",
            example_snippets=None,
            arguments=None,
            schema={'required': [], 'optional': [], 'read_only': [], 'nested': {}},
            kind='data_source',
        )


def parse_data_source_markdown(
    content: str,
    resource_type: str,
    url: str,
    correlation_id: str = '',
    attribute: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse markdown documentation content for a data source.

    Args:
        content: The markdown content
        resource_type: The resource type
        url: The source URL for this documentation
        correlation_id: Identifier for tracking this request in logs
        attribute: Optional attribute to look for

    Returns:
        A ProviderDocsResult object with parsed documentation details
    """
    start_time = time.time()
    logger.debug(f"[{correlation_id}] Parsing data source markdown documentation for '{resource_type}'")

    try:
        # Extract description from frontmatter
        description = ''
        example_snippets = []
        attribute_info = None
        arguments = {}
        
        # New structured schema organization
        schema_sections = {
            'required': [],
            'optional': [],
            'read_only': [],
            'nested': {},  # Will contain parent_name -> {required: [], optional: [], read_only: []}
        }

        # Try to find the description from the frontmatter
        desc_match = re.search(r'description: \|-\s*(.*?)(?=---|\Z)', content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            logger.debug(f"[{correlation_id}] Found description in frontmatter: '{description[:100]}...'")
        else:
            # Fallback to the first paragraph after the heading
            heading_match = re.search(r'# ([^\n]+).*?\n\n([^\n#]+)', content, re.DOTALL)
            if heading_match:
                description = heading_match.group(2).strip()
                logger.debug(f"[{correlation_id}] Found description after heading: '{description[:100]}...'")
            else:
                description = f'Data Source schema for {resource_type}'
                logger.debug(f'[{correlation_id}] Using default description')
        
        # Extract example snippets
        example_match = re.search(r'## Example Usage\s*([\s\S]*?)(?=\n##|\Z)', content, re.DOTALL)
        if example_match:
            example_content = example_match.group(1).strip()
            logger.debug(f'[{correlation_id}] Found Example Usage section ({len(example_content)} chars)')
            
            # Extract code blocks
            code_blocks = re.finditer(r'```(?:terraform|hcl)?\s*([\s\S]*?)```', example_content, re.DOTALL)
            for i, block in enumerate(code_blocks):
                code = block.group(1).strip()
                if code:
                    example_snippets.append({
                        'title': f'Example {i+1}',
                        'code': code,
                        'language': 'terraform'
                    })
                    logger.debug(f'[{correlation_id}] Added example snippet {i+1} ({len(code)} chars)')

        # Extract schema section
        schema_match = re.search(r'## Schema\s*([\s\S]*?)(?=\n##|\Z)', content, re.DOTALL)
        if schema_match:
            schema_section = schema_match.group(1).strip()
            logger.debug(f'[{correlation_id}] Found Schema section ({len(schema_section)} chars)')
            
            # Extract Required section
            required_match = re.search(r'### Required\s*([\s\S]*?)(?=\n###|\Z)', schema_section, re.DOTALL)
            if required_match:
                required_content = required_match.group(1).strip()
                logger.debug(f'[{correlation_id}] Found Required section ({len(required_content)} chars)')
                
                # Parse required attributes
                required_items = re.finditer(
                    r'-\s+`([^`]+)`\s*\(([^)]+)\)\s*([\s\S]*?)(?=\n-|\Z)',
                    required_content,
                    re.DOTALL
                )
                
                for item in required_items:
                    name = item.group(1).strip()
                    type_info = item.group(2).strip() if item.group(2) else ''
                    desc = item.group(3).strip() if item.group(3) else ''
                    
                    # Combine type info and description
                    full_desc = f'{desc}'
                    if type_info:
                        full_desc = f'Type: {type_info}. {full_desc}'
                    
                    # Add metadata about requirement level
                    full_desc = f'{full_desc} (Required field)'
                    
                    schema_item = {
                        'name': name,
                        'description': full_desc,
                        'section': 'required',
                    }
                    
                    # Add to required section
                    schema_sections['required'].append(schema_item)
                    logger.debug(f"[{correlation_id}] Added required attribute '{name}'")
            
            # Extract Read-Only section
            read_only_match = re.search(r'### Read-Only\s*([\s\S]*?)(?=\n###|\Z)', schema_section, re.DOTALL)
            if read_only_match:
                read_only_content = read_only_match.group(1).strip()
                logger.debug(f'[{correlation_id}] Found Read-Only section ({len(read_only_content)} chars)')
                
                # Parse read-only attributes
                read_only_items = re.finditer(
                    r'-\s+`([^`]+)`\s*\(([^)]+)\)\s*([\s\S]*?)(?=\n-|\Z)',
                    read_only_content,
                    re.DOTALL
                )
                
                for item in read_only_items:
                    name = item.group(1).strip()
                    type_info = item.group(2).strip() if item.group(2) else ''
                    desc = item.group(3).strip() if item.group(3) else ''
                    
                    # Check if this is a nested attribute
                    is_nested = '(see [below for nested schema]' in desc
                    
                    # Combine type info and description
                    full_desc = f'{desc}'
                    if type_info:
                        full_desc = f'Type: {type_info}. {full_desc}'
                    
                    # Add metadata about requirement level
                    full_desc = f'{full_desc} (Read-only field)'
                    
                    schema_item = {
                        'name': name,
                        'description': full_desc,
                        'section': 'read_only',
                    }
                    
                    # Add to read_only section
                    schema_sections['read_only'].append(schema_item)
                    logger.debug(f"[{correlation_id}] Added read-only attribute '{name}'")
            
            # Extract Optional section (if any)
            optional_match = re.search(r'### Optional\s*([\s\S]*?)(?=\n###|\Z)', schema_section, re.DOTALL)
            if optional_match:
                optional_content = optional_match.group(1).strip()
                logger.debug(f'[{correlation_id}] Found Optional section ({len(optional_content)} chars)')
                
                # Parse optional attributes
                optional_items = re.finditer(
                    r'-\s+`([^`]+)`\s*\(([^)]+)\)\s*([\s\S]*?)(?=\n-|\Z)',
                    optional_content,
                    re.DOTALL
                )
                
                for item in optional_items:
                    name = item.group(1).strip()
                    type_info = item.group(2).strip() if item.group(2) else ''
                    desc = item.group(3).strip() if item.group(3) else ''
                    
                    # Combine type info and description
                    full_desc = f'{desc}'
                    if type_info:
                        full_desc = f'Type: {type_info}. {full_desc}'
                    
                    # Add metadata about requirement level
                    full_desc = f'{full_desc} (Optional field)'
                    
                    schema_item = {
                        'name': name,
                        'description': full_desc,
                        'section': 'optional',
                    }
                    
                    # Add to optional section
                    schema_sections['optional'].append(schema_item)
                    logger.debug(f"[{correlation_id}] Added optional attribute '{name}'")
            
            # Extract nested schemas
            nested_schemas = re.finditer(
                r'<a id="nestedatt--([^"]+)"></a>\s*### Nested Schema for `([^`]+)`\s*([\s\S]*?)(?=<a id|\n##|\Z)',
                content,
                re.DOTALL
            )
            
            for nested_schema in nested_schemas:
                try:
                    anchor_id = nested_schema.group(1)
                    parent_name = nested_schema.group(2)
                    nested_content = nested_schema.group(3).strip()
                    
                    logger.debug(f"[{correlation_id}] Found nested schema for '{parent_name}'")
                    
                    # Initialize the nested schema structure for this parent
                    if parent_name not in schema_sections['nested']:
                        schema_sections['nested'][parent_name] = {
                            'required': [],
                            'optional': [],
                            'read_only': [],
                        }
                    
                    # For data sources, most nested attributes are read-only
                    # Parse the nested attributes
                    nested_items = re.finditer(
                        r'-\s+`([^`]+)`\s*\(([^)]+)\)\s*([\s\S]*?)(?=\n-|\Z)',
                        nested_content,
                        re.DOTALL
                    )
                    
                    for item in nested_items:
                        name = item.group(1).strip()
                        type_info = item.group(2).strip() if item.group(2) else ''
                        desc = item.group(3).strip() if item.group(3) else ''
                        
                        # Create fully qualified name for nested field
                        full_name = f'{parent_name}.{name}'
                        
                        # Combine type info and description
                        full_desc = f'{desc}'
                        if type_info:
                            full_desc = f'Type: {type_info}. {full_desc}'
                        
                        # Add metadata about parent and requirement level
                        full_desc = f"{full_desc} (Read-only nested field in '{parent_name}')"
                        
                        nested_item = {
                            'name': name,
                            'qualified_name': full_name,
                            'description': full_desc,
                            'section': 'read_only',
                            'parent': parent_name,
                        }
                        
                        # Add to nested read_only section
                        schema_sections['nested'][parent_name]['read_only'].append(nested_item)
                        logger.debug(f"[{correlation_id}] Added nested read-only attribute '{name}' to {parent_name}")
                except Exception as e:
                    logger.warning(f"[{correlation_id}] Error processing nested schema: {str(e)}")
                    continue
        
        # If attribute is specified, look for information about it in the schema
        if attribute:
            # Build a flattened view for attribute search, including qualified name mapping
            flat_schema_map = {}

            # Add top-level attributes
            for section_key in ['required', 'optional', 'read_only']:
                for item in schema_sections[section_key]:
                    flat_schema_map[item['name']] = item

            # Add nested attributes with their qualified names
            for parent_name, nested_schema in schema_sections['nested'].items():
                for section_key in ['required', 'optional', 'read_only']:
                    for item in nested_schema[section_key]:
                        qual_name = f'{parent_name}.{item["name"]}'
                        flat_schema_map[qual_name] = item
                        # Also add by just the attribute name for easier matching
                        if item['name'] not in flat_schema_map:
                            flat_schema_map[item['name']] = item

            # Search for the attribute
            if attribute in flat_schema_map:
                item = flat_schema_map[attribute]
                if 'parent' in item:
                    attribute_info = f"The '{attribute}' attribute: {item['description']} (found in nested schema '{item['parent']}')"
                else:
                    attribute_info = f"The '{attribute}' attribute: {item['description']}"
                logger.debug(
                    f"[{correlation_id}] Found attribute info: '{attribute_info[:100]}...'"
                )
            else:
                # Try to match the attribute name as part of a nested attribute
                for qual_name, item in flat_schema_map.items():
                    if qual_name.endswith(f'.{attribute}'):
                        attribute_info = f"The '{attribute}' attribute: {item['description']} (found as part of '{qual_name}')"
                        logger.debug(
                            f"[{correlation_id}] Found attribute as nested field: '{attribute_info[:100]}...'"
                        )
                        break

                if not attribute_info and attribute in content:
                    attribute_info = (
                        f"The '{attribute}' attribute is mentioned in the documentation."
                    )
                    logger.debug(
                        f'[{correlation_id}] Attribute mentioned but details not found'
                    )

        # Return the parsed information as a ProviderDocsResult
        parse_time = time.time() - start_time
        logger.debug(f'[{correlation_id}] Markdown parsing completed in {parse_time:.2f} seconds')

        # If attribute info was found, append it to the description
        if attribute_info:
            description = f"{description}\n\n{attribute_info}"

        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=description,
            example_snippets=example_snippets if example_snippets else None,
            arguments=arguments if arguments else None,
            schema=schema_sections,
            kind='data_source',
        )

    except Exception as e:
        logger.exception(f'[{correlation_id}] Error parsing markdown content')
        logger.error(f'[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}')
        
        # Include detailed error information
        error_detail = f"Error type: {type(e).__name__}, message: {str(e)}"
        
        # Return partial info with error details
        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=f"Documentation for AWSCC {resource_type} data source (Error parsing details: {error_detail})",
            example_snippets=None,
            arguments=None,
            schema={'required': [], 'optional': [], 'read_only': [], 'nested': {}},
            kind='data_source',
        )
