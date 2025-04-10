"""Implementation of AWSCC provider documentation search tool."""

import os
import re
import sys
import time
import traceback
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import markdown
from ...models import ProviderDocsResult
from loguru import logger
from typing import Dict, List, Optional, Tuple, Any

# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {"sink": sys.stderr, "backtrace": True, "diagnose": True, 
         "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"}
    ]
)

# Path to the static markdown file
STATIC_RESOURCES_PATH = (
    Path(__file__).parent.parent.parent / 'static' / 'AWSCC_PROVIDER_RESOURCES.md'
)

# Base URLs for AWSCC provider documentation
AWSCC_DOCS_BASE_URL = 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs'
GITHUB_RAW_BASE_URL = 'https://raw.githubusercontent.com/hashicorp/terraform-provider-awscc/main/docs'

# Simple in-memory cache
_GITHUB_DOC_CACHE = {}


def resource_to_github_path(resource_type: str, correlation_id: str = "", doc_kind: str = "resource") -> Tuple[str, str]:
    """Convert AWSCC resource type to GitHub documentation file path.
    
    Args:
        resource_type: The resource type (e.g., 'awscc_s3_bucket')
        correlation_id: Identifier for tracking this request in logs
        doc_kind: Type of document to search for - 'resource', 'data_source', or 'both' (default: 'resource')
        
    Returns:
        A tuple of (path, url) for the GitHub documentation file
    """
    # Remove the 'awscc_' prefix if present
    if resource_type.startswith('awscc_'):
        resource_name = resource_type[6:]
        logger.debug(f"[{correlation_id}] Removed 'awscc_' prefix: {resource_name}")
    else:
        resource_name = resource_type
        logger.debug(f"[{correlation_id}] No 'awscc_' prefix to remove: {resource_name}")
    
    # Determine document type based on doc_kind parameter
    if doc_kind == "data_source":
        doc_path = 'data-sources'  # data sources directory
    elif doc_kind == "resource":
        doc_path = 'resources'  # resources directory
    else:
        # For "both" or any other value, determine based on name pattern
        # Data sources typically have 'data' in the name or follow other patterns
        is_data_source = 'data' in resource_type.lower()
        doc_path = 'data-sources' if is_data_source else 'resources'
    
    # Create the file path for the markdown documentation
    file_path = f"{doc_path}/{resource_name}.md"
    logger.debug(f"[{correlation_id}] Constructed GitHub file path: {file_path}")
    
    # Create the full URL to the raw GitHub content
    github_url = f"{GITHUB_RAW_BASE_URL}/{file_path}"
    logger.debug(f"[{correlation_id}] GitHub raw URL: {github_url}")
    
    return file_path, github_url


def fetch_github_documentation(resource_type: str, correlation_id: str = "", doc_kind: str = "resource") -> Optional[Dict[str, Any]]:
    """Fetch documentation from GitHub for a specific resource type.
    
    Args:
        resource_type: The resource type (e.g., 'awscc_s3_bucket')
        correlation_id: Identifier for tracking this request in logs
        doc_kind: Type of document to search for - 'resource', 'data_source', or 'both' (default: 'resource')
        
    Returns:
        Dictionary with markdown content and metadata, or None if not found
    """
    start_time = time.time()
    logger.info(f"[{correlation_id}] Fetching documentation from GitHub for '{resource_type}'")
    
    # Create a cache key that includes both resource_type and doc_kind
    cache_key = f"{resource_type}_{doc_kind}"
    
    # Check cache first
    if cache_key in _GITHUB_DOC_CACHE:
        logger.info(f"[{correlation_id}] Using cached documentation for '{resource_type}' (kind: {doc_kind})")
        return _GITHUB_DOC_CACHE[cache_key]
    
    try:
        # Convert resource type to GitHub path and URL
        _, github_url = resource_to_github_path(resource_type, correlation_id, doc_kind)
        
        # Fetch the markdown content from GitHub
        logger.debug(f"[{correlation_id}] Fetching from GitHub: {github_url}")
        response = requests.get(github_url, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"[{correlation_id}] GitHub request failed: HTTP {response.status_code}")
            return None
        
        markdown_content = response.text
        content_length = len(markdown_content)
        logger.debug(f"[{correlation_id}] Received markdown content: {content_length} bytes")
        
        if content_length > 0:
            preview_length = min(200, content_length)
            logger.debug(f"[{correlation_id}] Markdown preview: {markdown_content[:preview_length]}...")
        
        # Parse the markdown content
        result = parse_markdown_documentation(markdown_content, resource_type, github_url, correlation_id, doc_kind)
        
        # Cache the result with the composite key
        _GITHUB_DOC_CACHE[cache_key] = result
        
        fetch_time = time.time() - start_time
        logger.info(f"[{correlation_id}] GitHub documentation fetched in {fetch_time:.2f} seconds")
        return result
        
    except requests.exceptions.Timeout as e:
        logger.exception(f"[{correlation_id}] Timeout error fetching from GitHub: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        logger.exception(f"[{correlation_id}] Request error fetching from GitHub: {str(e)}")
        return None
    except Exception as e:
        logger.exception(f"[{correlation_id}] Unexpected error fetching from GitHub")
        logger.error(f"[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}")
        return None


def parse_markdown_documentation(
    content: str, 
    resource_type: str, 
    url: str, 
    correlation_id: str = "",
    doc_kind: str = "resource",
    attribute: Optional[str] = None
) -> Dict[str, Any]:
    """Parse markdown documentation content for a resource.
    
    Args:
        content: The markdown content
        resource_type: The resource type
        url: The source URL for this documentation
        correlation_id: Identifier for tracking this request in logs
        doc_kind: Type of document - 'resource' or 'data_source'
        attribute: Optional attribute to look for
        
    Returns:
        Dictionary with parsed documentation details
    """
    start_time = time.time()
    logger.debug(f"[{correlation_id}] Parsing markdown documentation for '{resource_type}'")
    
    try:
        # Extract description: First paragraph after page title or from the description section
        description = ""
        example_snippets = []
        attribute_info = None
        schema_content = None
        
        # New structured schema organization
        schema_sections = {
            "required": [],
            "optional": [],
            "read_only": [],
            "nested": {}  # Will contain parent_name -> {required: [], optional: [], read_only: []}
        }
        
        # Try to find the description from the frontmatter
        desc_match = re.search(r'description: \|-\s*(.*?)(?=---|\Z)', content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            logger.debug(f"[{correlation_id}] Found description in frontmatter: '{description[:100]}...'")

        # Find resource title
        resource_title = ""
        title_match = re.search(r'page_title: "(.*?)"', content)
        if title_match:
            resource_title = title_match.group(1)
            logger.debug(f"[{correlation_id}] Found page title: '{resource_title}'")
        else:
            # Fallback to the first heading
            heading_match = re.search(r'# ([^\n]+)', content)
            if heading_match:
                resource_title = heading_match.group(1).strip()
                logger.debug(f"[{correlation_id}] Found heading title: '{resource_title}'")
            else:
                resource_title = resource_type
                logger.debug(f"[{correlation_id}] Using resource type as title: '{resource_title}'")
        
        # If no description from frontmatter, try to extract it from the main content
        if not description:
            # Look for the first paragraph after the first heading that's not part of a code block
            paragraphs = re.finditer(r'^(?!#)([^\n]+)$', content, re.MULTILINE)
            for match in paragraphs:
                potential_desc = match.group(1).strip()
                if potential_desc and not potential_desc.startswith('---'):
                    description = potential_desc
                    logger.debug(f"[{correlation_id}] Using first paragraph as description: '{description[:100]}...'")
                    break
            
            if not description:
                description = f"Documentation for {resource_type}"
                logger.debug(f"[{correlation_id}] No description found, using default")
            
        # Find example snippets
        example_section_match = re.search(r'## Example Usage\s*(?:###[^#]+)?([\s\S]*?)(?=\n## |\Z)', content, re.DOTALL)
        logger.debug(f"[{correlation_id}] example_section_match content: {example_section_match.group()}")
        
        if example_section_match:
            example_section = example_section_match.group(1).strip()
            logger.debug(f"[{correlation_id}] Found Example Usage section ({len(example_section)} chars)")
            
            # Look for sub-examples (### headings under Example Usage)
            sub_examples = re.finditer(r'### ([^\n]+)\s*([\s\S]*?)(?=\n### |\n## |\Z)', example_section, re.DOTALL)
            found_sub_examples = False
            
            for sub_example in sub_examples:
                found_sub_examples = True
                title = sub_example.group(1).strip()
                content_block = sub_example.group(2).strip()
                
                # Find code blocks in this sub-example
                code_match = re.search(r'```(?:terraform|hcl)?([^`]*?)```', content_block, re.DOTALL)
                if code_match:
                    code_snippet = code_match.group(1).strip()
                    example_snippets.append({
                        "title": title,
                        "code": code_snippet
                    })
                    logger.debug(f"[{correlation_id}] Found example '{title}' with {len(code_snippet)} chars")
            
            # If no sub-examples with headers, look for direct code blocks
            if not found_sub_examples:
                code_blocks = re.finditer(r'```(?:terraform|hcl)?([^`]*?)```', example_section, re.DOTALL)
                for code_match in code_blocks:
                    code_snippet = code_match.group(1).strip()
                    example_snippets.append({
                        "title": "Example Usage",
                        "code": code_snippet
                    })
                    logger.debug(f"[{correlation_id}] Found direct example with {len(code_snippet)} chars")
        else:
            logger.debug(f"[{correlation_id}] No Example Usage section found")
            
            # Fallback: Look for any code block that contains the resource type
            code_block_pattern = re.compile(r'```(?:terraform|hcl)?([^`]*?)```', re.DOTALL)
            for code_match in code_block_pattern.finditer(content):
                code_content = code_match.group(1).strip()
                if resource_type in code_content and ('resource' in code_content or 'data' in code_content):
                    example_snippets.append({
                        "title": "Example Usage",
                        "code": code_content
                    })
                    logger.debug(f"[{correlation_id}] Found resource-specific code example ({len(code_content)} chars)")
                    break
        
        if example_snippets:
            logger.debug(f"[{correlation_id}] Total examples found: {len(example_snippets)}")
        else:
            logger.debug(f"[{correlation_id}] No example snippets found")
        
        # Extract Schema section
        schema_match = re.search(r'## Schema\s*([\s\S]*?)(?=\n##|\Z)', content, re.DOTALL)
        if schema_match:
            schema_section = schema_match.group(1).strip()
            schema_content = schema_section
            logger.debug(f"[{correlation_id}] Found Schema section ({len(schema_section)} chars)")
            
            # Parse different schema sections (Required, Optional, Read-Only)
            section_types = ["Required", "Optional", "Read-Only"]
            
            # Process each section type
            for section_type in section_types:
                section_match = re.search(rf'### {section_type}\s*([\s\S]*?)(?=\n### |\n##|\Z)', schema_section, re.DOTALL)
                if section_match:
                    section_content = section_match.group(1).strip()
                    logger.debug(f"[{correlation_id}] Found {section_type} schema section ({len(section_content)} chars)")
                    section_key = section_type.lower().replace('-', '_')
                    
                    # Parse the list items in this section
                    # Format is typically:
                    # - `parameter_name` (Type) Description text...
                    items = re.finditer(r'-\s+`([^`]+)`(?:\s+\(([^)]+)\))?\s*(.*?)(?=\n-|\n\n|\Z)', section_content, re.DOTALL)
                    
                    for item in items:
                        name = item.group(1).strip()
                        type_info = item.group(2).strip() if item.group(2) else ""
                        desc = item.group(3).strip() if item.group(3) else ""
                        
                        # Combine type info and description
                        full_desc = f"{desc}"
                        if type_info:
                            full_desc = f"Type: {type_info}. {full_desc}"
                        
                        # Add metadata about requirement level
                        if section_type == "Required":
                            full_desc = f"{full_desc} (Required field)"
                        elif section_type == "Optional":
                            full_desc = f"{full_desc} (Optional field)"
                        elif section_type == "Read-Only":
                            full_desc = f"{full_desc} (Read-only field)"
                        
                        schema_item = {
                            "name": name,
                            "description": full_desc,
                            "section": section_key
                        }
                        
                        # Add to appropriate section
                        schema_sections[section_key].append(schema_item)
                        logger.debug(f"[{correlation_id}] Added schema item '{name}' to {section_key} section")
            
            # Parse nested schemas
            nested_schemas = re.finditer(r'<a id="nestedatt--([^"]+)"></a>[\s\n]*### Nested Schema for `([^`]+)`\s*([\s\S]*?)(?=<a id|\n##|\Z)', schema_section, re.DOTALL)
            
            for nested_schema in nested_schemas:
                anchor_id = nested_schema.group(1)
                parent_name = nested_schema.group(2)
                nested_content = nested_schema.group(3).strip()
                
                logger.debug(f"[{correlation_id}] Found nested schema for '{parent_name}'")
                
                # Initialize the nested schema structure for this parent
                if parent_name not in schema_sections["nested"]:
                    schema_sections["nested"][parent_name] = {
                        "required": [],
                        "optional": [],
                        "read_only": []
                    }
                
                # Look for sections in the nested schema
                for section_type in section_types:
                    nested_section_match = re.search(rf'{section_type}:\s*\n([\s\S]*?)(?=\n\w+:|\Z)', nested_content, re.DOTALL)
                    if nested_section_match:
                        nested_section = nested_section_match.group(1).strip()
                        section_key = section_type.lower().replace('-', '_')
                        
                        # Items are typically listed with bullet points
                        nested_items = re.finditer(r'-\s+`([^`]+)`(?:\s+\(([^)]+)\))?\s*(.*?)(?=\n-|\n\n|\Z)', nested_section, re.DOTALL)
                        
                        for item in nested_items:
                            name = item.group(1).strip()
                            type_info = item.group(2).strip() if item.group(2) else ""
                            desc = item.group(3).strip() if item.group(3) else ""
                            
                            # Create fully qualified name for nested field
                            full_name = f"{parent_name}.{name}"
                            
                            # Combine type info and description for nested field
                            full_desc = f"{desc}"
                            if type_info:
                                full_desc = f"Type: {type_info}. {full_desc}"
                            
                            # Add metadata about requirement level and parent
                            if section_type == "Required":
                                full_desc = f"{full_desc} (Required nested field in '{parent_name}')"
                            elif section_type == "Optional":
                                full_desc = f"{full_desc} (Optional nested field in '{parent_name}')"
                            elif section_type == "Read-Only":
                                full_desc = f"{full_desc} (Read-only nested field in '{parent_name}')" 
                            
                            nested_item = {
                                "name": name,
                                "qualified_name": full_name,
                                "description": full_desc,
                                "section": section_key,
                                "parent": parent_name
                            }
                            
                            # Add to the appropriate nested section
                            schema_sections["nested"][parent_name][section_key].append(nested_item)
                            logger.debug(f"[{correlation_id}] Added nested schema item '{name}' to {parent_name}.{section_key}")
            
            # Debug log the schema structure
            logger.debug(f"[{correlation_id}] Schema structure summary:")
            logger.debug(f"[{correlation_id}] - Required items: {len(schema_sections['required'])}")
            logger.debug(f"[{correlation_id}] - Optional items: {len(schema_sections['optional'])}")
            logger.debug(f"[{correlation_id}] - Read-only items: {len(schema_sections['read_only'])}")
            logger.debug(f"[{correlation_id}] - Nested schemas: {len(schema_sections['nested'])}")
            
            for parent_name, nested_schema in schema_sections["nested"].items():
                logger.debug(f"[{correlation_id}]   - {parent_name}:")
                logger.debug(f"[{correlation_id}]     - Required: {len(nested_schema['required'])}")
                logger.debug(f"[{correlation_id}]     - Optional: {len(nested_schema['optional'])}")
                logger.debug(f"[{correlation_id}]     - Read-only: {len(nested_schema['read_only'])}")
            
            # If attribute is specified, look for information about it in the schema
            if attribute:
                # Build a flattened view for attribute search, including qualified name mapping
                flat_schema_map = {}
                
                # Add top-level attributes
                for section_key in ["required", "optional", "read_only"]:
                    for item in schema_sections[section_key]:
                        flat_schema_map[item["name"]] = item
                
                # Add nested attributes with their qualified names
                for parent_name, nested_schema in schema_sections["nested"].items():
                    for section_key in ["required", "optional", "read_only"]:
                        for item in nested_schema[section_key]:
                            qual_name = f"{parent_name}.{item['name']}"
                            flat_schema_map[qual_name] = item
                            # Also add by just the attribute name for easier matching
                            if item["name"] not in flat_schema_map:
                                flat_schema_map[item["name"]] = item
                
                # Search for the attribute
                if attribute in flat_schema_map:
                    item = flat_schema_map[attribute]
                    if "parent" in item:
                        attribute_info = f"The '{attribute}' attribute: {item['description']} (found in nested schema '{item['parent']}')"
                    else:
                        attribute_info = f"The '{attribute}' attribute: {item['description']}"
                    logger.debug(f"[{correlation_id}] Found attribute info: '{attribute_info[:100]}...'")
                else:
                    # Try to match the attribute name as part of a nested attribute
                    for qual_name, item in flat_schema_map.items():
                        if qual_name.endswith(f".{attribute}"):
                            attribute_info = f"The '{attribute}' attribute: {item['description']} (found as part of '{qual_name}')"
                            logger.debug(f"[{correlation_id}] Found attribute as nested field: '{attribute_info[:100]}...'")
                            break
                    
                    if not attribute_info and attribute in content:
                        attribute_info = f"The '{attribute}' attribute is mentioned in the documentation."
                        logger.debug(f"[{correlation_id}] Attribute mentioned but details not found")
        else:
            logger.debug(f"[{correlation_id}] No Schema section found")
            
            # If attribute is specified but no schema found, try to find in content
            if attribute:
                attribute_pattern = re.compile(rf'`{re.escape(attribute)}`\s*(?:\([^)]+\))?\s*([^\n]+)', re.DOTALL)
                attribute_match = attribute_pattern.search(content)
                
                if attribute_match:
                    attribute_info = f"The '{attribute}' attribute: {attribute_match.group(1).strip()}"
                    logger.debug(f"[{correlation_id}] Found attribute mention: '{attribute_info[:100]}...'")
                elif attribute in content:
                    attribute_info = f"The '{attribute}' attribute is mentioned in the documentation."
                    logger.debug(f"[{correlation_id}] Attribute mentioned but details not found")
        
        # Return the parsed information
        parse_time = time.time() - start_time
        logger.debug(f"[{correlation_id}] Markdown parsing completed in {parse_time:.2f} seconds")
        
        return {
            'title': resource_title,
            'description': description,
            'example_snippets': example_snippets if example_snippets else None,
            'attribute_info': attribute_info,
            'schema_sections': schema_sections,  # New structured schema
            'schema_content': schema_content,
            'url': url,
            'kind': doc_kind
        }
    
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error parsing markdown content")
        logger.error(f"[{correlation_id}] Error type: {type(e).__name__}, message: {str(e)}")
        
        # Return partial info if available
        return {
            'title': f"AWSCC {resource_type}",
            'description': f"Documentation for AWSCC {resource_type} (Error parsing details: {str(e)})",
            'example_snippets': None,
            'attribute_info': None,
            'schema_sections': {
                "required": [],
                "optional": [],
                "read_only": [],
                "nested": {}
            },
            'schema_content': None,
            'url': url,
            'kind': doc_kind
        }


async def search_awscc_provider_docs_impl(
    resource_type: str, attribute: Optional[str] = None, kind: str = "both"
) -> List[ProviderDocsResult]:
    """Search AWSCC provider documentation for resources and attributes.

    This tool searches the Terraform AWSCC provider documentation for information about
    specific resource types and their attributes.

    Parameters:
        resource_type: AWSCC resource type (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        attribute: Optional specific attribute to search for
        kind: Type of documentation to search - 'resource', 'data_source', or 'both' (default)

    Returns:
        A list of matching documentation entries with details
    """
    start_time = time.time()
    correlation_id = f"search-{int(start_time*1000)}"
    logger.info(f"[{correlation_id}] Starting AWSCC provider docs search for '{resource_type}'")
    
    if attribute:
        logger.info(f"[{correlation_id}] Also searching for attribute '{attribute}'")
        
    search_term = resource_type.lower()
    
    try:
        # Try fetching from GitHub
        logger.info(f"[{correlation_id}] Fetching from GitHub")
        
        results = []
        
        # If kind is "both", try both resource and data source paths
        if kind == "both":
            logger.info(f"[{correlation_id}] Searching for both resources and data sources")
            
            # First try as a resource
            github_result = fetch_github_documentation(search_term, correlation_id, "resource")
            if github_result:
                logger.info(f"[{correlation_id}] Found documentation as a resource")
                # Create result object
                description = github_result['description']
                if attribute and github_result.get('attribute_info'):
                    description += f" {github_result['attribute_info']}"
                
                # Use schema_sections directly instead of flattening
                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=github_result['url'],
                    description=description,
                    example_snippets=github_result.get('example_snippets'),
                    schema=github_result.get('schema_sections'),  # Pass schema_sections directly
                    kind="resource",
                )
                results.append(result)
            
            # Then try as a data source
            data_result = fetch_github_documentation(search_term, correlation_id, "data_source")
            if data_result:
                logger.info(f"[{correlation_id}] Found documentation as a data source")
                # Create result object
                description = data_result['description']
                if attribute and data_result.get('attribute_info'):
                    description += f" {data_result['attribute_info']}"
                
                # Use schema_sections directly instead of flattening
                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=data_result['url'],
                    description=description,
                    example_snippets=data_result.get('example_snippets'),
                    schema=data_result.get('schema_sections'),  # Pass schema_sections directly
                    kind="data_source",
                )
                results.append(result)
            
            if results:
                logger.info(f"[{correlation_id}] Found {len(results)} documentation entries")
                for result in results:
                    if hasattr(result, 'schema') and result.schema:
                        logger.debug(f"[{correlation_id}] Schema structure for {result.resource_name} ({result.kind}):")
                        if isinstance(result.schema, dict):
                            for section, items in result.schema.items():
                                if section != 'nested':
                                    logger.debug(f"[{correlation_id}]   - {section}: {len(items)} items")
                                else:
                                    logger.debug(f"[{correlation_id}]   - nested: {len(items)} parent objects")
                
                end_time = time.time()
                logger.info(f"[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (GitHub source)")
                return results
        else:
            # Search for either resource or data source based on kind parameter
            github_result = fetch_github_documentation(search_term, correlation_id, kind)
            if github_result:
                logger.info(f"[{correlation_id}] Successfully found GitHub documentation")
                
                # Create result object
                description = github_result['description']
                if attribute and github_result.get('attribute_info'):
                    description += f" {github_result['attribute_info']}"
                
                # Use schema_sections directly instead of flattening
                result = ProviderDocsResult(
                    resource_name=resource_type,
                    url=github_result['url'],
                    description=description,
                    example_snippets=github_result.get('example_snippets'),
                    schema=github_result.get('schema_sections'),  # Pass schema_sections directly
                    kind=kind,
                )
                
                end_time = time.time()
                logger.info(f"[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (GitHub source)")
                return [result]
        
        # If GitHub approach fails, return a "not found" result
        logger.warning(f"[{correlation_id}] Documentation not found on GitHub for '{search_term}'")
        
        # Return a "not found" result
        logger.warning(f"[{correlation_id}] No resource documentation found")
        end_time = time.time()
        logger.info(f"[{correlation_id}] Search completed in {end_time - start_time:.2f} seconds (no results)")
        return [
            ProviderDocsResult(
                resource_name='Not found',
                url=f"{AWSCC_DOCS_BASE_URL}/resources",
                description=f"No documentation found for resource type '{resource_type}'.",
                example_snippets=None,
                schema=None,
            )
        ]
    
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error searching AWSCC provider docs")
        logger.error(f"[{correlation_id}] Exception details: {type(e).__name__}: {str(e)}")
        logger.debug(f"[{correlation_id}] Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        
        end_time = time.time()
        logger.info(f"[{correlation_id}] Search failed in {end_time - start_time:.2f} seconds")
        
        return [
            ProviderDocsResult(
                resource_name='Error',
                url='',
                description=f'Failed to search AWSCC provider documentation: {type(e).__name__}: {str(e)}',
                example_snippets=None,
                schema=None,
            )
        ]
