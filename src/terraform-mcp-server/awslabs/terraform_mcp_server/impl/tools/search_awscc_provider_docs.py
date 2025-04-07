"""Implementation of AWSCC provider documentation search tool."""

import os
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from ...models import ProviderDocsResult
from loguru import logger
from typing import Dict, List, Optional, Tuple


# Path to the static markdown file
STATIC_RESOURCES_PATH = (
    Path(__file__).parent.parent.parent / 'static' / 'AWSCC_PROVIDER_RESOURCES.md'
)

# Base URL for AWSCC provider documentation
AWSCC_DOCS_BASE_URL = 'https://registry.terraform.io/providers/hashicorp/awscc/latest/docs'


async def search_awscc_provider_docs_impl(
    resource_type: str, attribute: Optional[str] = None
) -> List[ProviderDocsResult]:
    """Search AWSCC provider documentation for resources and attributes.

    This tool searches the Terraform AWSCC provider documentation for information about
    specific resource types and their attributes.

    Parameters:
        resource_type: AWSCC resource type (e.g., 'awscc_s3_bucket', 'awscc_lambda_function')
        attribute: Optional specific attribute to search for

    Returns:
        A list of matching documentation entries with details
    """
    logger.info(f"Searching AWSCC provider docs for '{resource_type}'")
    search_term = resource_type.lower()

    try:
        # Step 1: Find the resource URL from the static resources file or by direct URL construction
        resource_url = find_resource_url(search_term)
        
        if not resource_url:
            logger.warning(f"Resource '{search_term}' not found in static resources file")
            # Construct a URL based on the resource name pattern
            if search_term.startswith('awscc_'):
                # Extract the service and resource name from the resource type
                parts = search_term[6:].split('_', 1)  # Remove 'awscc_' prefix
                if len(parts) > 1:
                    service, resource_name = parts
                else:
                    service = parts[0]
                    resource_name = parts[0]
                
                # Check if this is likely a data source
                is_data_source = 'data' in search_term.lower()
                
                # Construct the URL
                if is_data_source:
                    resource_url = f"{AWSCC_DOCS_BASE_URL}/data-sources/{service}_{resource_name}"
                else:
                    resource_url = f"{AWSCC_DOCS_BASE_URL}/resources/{service}_{resource_name}"
            else:
                # If no 'awscc_' prefix, assume it's a resource name and add the prefix
                resource_url = f"{AWSCC_DOCS_BASE_URL}/resources/{search_term}"
        
        # Step 2: Fetch and parse the documentation page
        resource_info = fetch_resource_documentation(resource_url, search_term, attribute)
        
        if resource_info:
            return [resource_info]
        else:
            # Return a "not found" result
            return [
                ProviderDocsResult(
                    resource_name='Not found',
                    url=f"{AWSCC_DOCS_BASE_URL}/resources",
                    description=f"No documentation found for resource type '{resource_type}'.",
                    example_snippet=None,
                )
            ]
            
    except Exception as e:
        logger.error(f'Error searching AWSCC provider docs: {e}')
        return [
            ProviderDocsResult(
                resource_name='Error',
                url='',
                description=f'Failed to search AWSCC provider documentation: {str(e)}',
                example_snippet=None,
            )
        ]


def find_resource_url(resource_type: str) -> Optional[str]:
    """Find the URL for a specific resource type in the static resources file.
    
    Args:
        resource_type: The resource type to search for (e.g., 'awscc_s3_bucket')
        
    Returns:
        The URL for the resource documentation, or None if not found
    """
    if not STATIC_RESOURCES_PATH.exists():
        logger.warning(f"Static resources file not found at {STATIC_RESOURCES_PATH}")
        return None
    
    try:
        # Read the static file in chunks to handle large files
        pattern = re.compile(rf'\[({re.escape(resource_type)})\]\(([^)]+)\)')
        
        with open(STATIC_RESOURCES_PATH, 'r') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    return match.group(2)  # Return the URL
        
        return None
    except Exception as e:
        logger.error(f"Error reading static resources file: {e}")
        return None


def fetch_resource_documentation(
    url: str, resource_type: str, attribute: Optional[str] = None
) -> Optional[ProviderDocsResult]:
    """Fetch and parse the documentation for a specific resource.
    
    Args:
        url: The URL of the resource documentation
        resource_type: The resource type (e.g., 'awscc_s3_bucket')
        attribute: Optional attribute to search for
        
    Returns:
        A ProviderDocsResult object with the resource documentation
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch documentation from {url}: {response.status_code}")
            return None
        
        html = response.text
                
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract the description
        description = ""
        main_content = soup.select_one('div.docs-content')
        if main_content:
            # Try to find the first paragraph that's not part of a code block
            for p in main_content.select('p'):
                if p.parent.name != 'pre' and p.parent.get('class') != 'highlight':
                    description = p.get_text(strip=True)
                    break
        
        if not description:
            # Fallback: use the title or h1 content
            title = soup.select_one('title')
            if title:
                description = f"Documentation for {title.get_text(strip=True)}"
            else:
                h1 = soup.select_one('h1')
                if h1:
                    description = f"Documentation for {h1.get_text(strip=True)}"
                else:
                    description = f"Documentation for {resource_type}"
        
        # If attribute is specified, try to find information about it
        if attribute:
            attribute_info = find_attribute_info(soup, attribute)
            if attribute_info:
                description += f" {attribute_info}"
        
        # Extract an example snippet
        example_snippet = extract_example_snippet(soup, resource_type)
        
        return ProviderDocsResult(
            resource_name=resource_type,
            url=url,
            description=description,
            example_snippet=example_snippet,
        )
    
    except requests.RequestException as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing documentation from {url}: {e}")
        return None


def find_attribute_info(soup: BeautifulSoup, attribute: str) -> Optional[str]:
    """Find information about a specific attribute in the documentation.
    
    Args:
        soup: BeautifulSoup object of the documentation page
        attribute: The attribute to search for
        
    Returns:
        A string with information about the attribute, or None if not found
    """
    # Look for attribute in argument reference section
    arg_reference = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 
                             'argument reference' in tag.get_text(strip=True).lower())
    
    if arg_reference:
        # Look for the attribute in the following content
        current = arg_reference.next_sibling
        while current and (current.name != 'h2' and current.name != 'h3'):
            if current.name == 'ul':
                for li in current.find_all('li'):
                    text = li.get_text(strip=True)
                    if attribute in text:
                        return f"Information about the '{attribute}' attribute: {text}"
            elif current.name == 'p' and attribute in current.get_text(strip=True):
                return f"Information about the '{attribute}' attribute: {current.get_text(strip=True)}"
            current = current.next_sibling
    
    # If not found in argument reference, look for it in any code block or table
    code_blocks = soup.find_all('code')
    for block in code_blocks:
        if attribute in block.get_text(strip=True):
            parent = block.parent
            if parent and parent.name == 'pre':
                return f"The '{attribute}' attribute is used in example code."
    
    # Look in tables
    tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                if attribute in cell.get_text(strip=True):
                    return f"The '{attribute}' attribute is mentioned in the documentation tables."
    
    return f"No specific information found for the '{attribute}' attribute."


def extract_example_snippet(soup: BeautifulSoup, resource_type: str) -> Optional[str]:
    """Extract an example code snippet from the documentation.
    
    Args:
        soup: BeautifulSoup object of the documentation page
        resource_type: The resource type to look for in examples
        
    Returns:
        A string with an example snippet, or None if not found
    """
    # Look for code blocks that contain the resource type
    pre_blocks = soup.find_all('pre')
    for pre in pre_blocks:
        code = pre.get_text(strip=True)
        if resource_type in code and 'resource' in code:
            # Clean up the code snippet
            return pre.get_text()
    
    # If no specific example found, look for any Terraform code block
    for pre in pre_blocks:
        code = pre.get_text(strip=True)
        if 'resource' in code and '{' in code and '}' in code:
            return pre.get_text()
    
    return None
