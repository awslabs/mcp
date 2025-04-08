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

"""Lambda layer documentation parser module."""

import httpx
import logging
import json
import os
import time
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any

# Set up logging
logger = logging.getLogger(__name__)

class LambdaLayerParser:
    """Parser for Lambda layer documentation from AWS docs."""
    
    # Cache file path
    CACHE_FILE = os.path.join(os.path.dirname(__file__), "lambda_layer_docs_cache.json")
    # Cache TTL in seconds (1 day)
    CACHE_TTL = 86400
    
    # Documentation URLs
    GENERIC_LAYER_URL = "https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda-readme.html"
    PYTHON_LAYER_URL = "https://docs.aws.amazon.com/cdk/api/v2/docs/@aws-cdk_aws-lambda-python-alpha.PythonLayerVersion.html"
    
    # Search patterns to directly find sections when headers aren't working
    LAYER_SECTION_PATTERNS = ["layers", "layer version", "layerversion"]
    
    @classmethod
    async def fetch_page(cls, url: str) -> Optional[str]:
        """Fetch a page from AWS documentation."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Failed to fetch {url}: HTTP {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    @classmethod
    def extract_section(cls, html: str, section_id: str = None, section_title: str = None) -> Optional[str]:
        """Extract a section from HTML content by ID or title."""
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        section_header = None
        
        # Try to find by ID first
        if section_id:
            section_header = soup.find(id=section_id)
            if not section_header:
                # If ID not found directly, try to find the closest header
                for tag in ['h1', 'h2', 'h3', 'h4']:
                    section_header = soup.find(tag, id=section_id)
                    if section_header:
                        break
        
        # If not found by ID, try to find by title
        if not section_header and section_title:
            for tag in ['h1', 'h2', 'h3', 'h4']:
                section_header = soup.find(tag, string=section_title)
                if section_header:
                    break
        
        if not section_header:
            logger.warning(f"Section not found: id={section_id}, title={section_title}")
            return None
        
        # Extract content until the next header of same or higher level
        try:
            # Check if section_header.name is a header tag (h1, h2, etc.)
            if not section_header.name or not section_header.name[0] == 'h' or len(section_header.name) < 2:
                # If it's not a header tag, just return the section and its siblings
                logger.warning(f"Section header is not a header tag: {section_header.name}")
                content = [str(section_header)]
                current = section_header.next_sibling
                # Get the next 10 elements as a fallback
                for _ in range(10):
                    if current and current.name:
                        content.append(str(current))
                    if current:
                        current = current.next_sibling
                    else:
                        break
                return ''.join(content)
            
            header_level = int(section_header.name[1])
            content = []
            current = section_header
            
            # Include the header itself
            content.append(str(section_header))
            
            # Get all siblings until next header of same or higher level
            current = current.next_sibling
            while current:
                if current.name and current.name[0] == 'h' and len(current.name) > 1 and int(current.name[1]) <= header_level:
                    break
                if current.name:  # Skip empty NavigableString objects
                    content.append(str(current))
                current = current.next_sibling
            
            return ''.join(content)
        except (IndexError, ValueError) as e:
            # Handle any parsing exceptions
            logger.warning(f"Error parsing section header: {str(e)}")
            # Return just the section header as fallback
            return str(section_header)
    
    @classmethod
    def extract_code_examples(cls, html_section: str) -> List[Dict[str, str]]:
        """Extract code examples from an HTML section."""
        if not html_section:
            return []
            
        soup = BeautifulSoup(html_section, 'html.parser')
        code_blocks = soup.find_all('pre')
        
        examples = []
        for block in code_blocks:
            # Try to determine the language
            language = "typescript"  # Default
            if block.get('class'):
                classes = block.get('class')
                if 'python' in ' '.join(classes).lower():
                    language = "python"
                elif 'javascript' in ' '.join(classes).lower():
                    language = "javascript"
            
            # Get the code content
            code = block.get_text()
            
            examples.append({
                "language": language,
                "code": code
            })
        
        return examples
    
    @classmethod
    def extract_directory_structure(cls, html_section: str) -> Optional[str]:
        """Extract directory structure information from HTML section."""
        if not html_section:
            return None
            
        soup = BeautifulSoup(html_section, 'html.parser')
        
        # Look for pre blocks that might contain directory structure
        pre_blocks = soup.find_all('pre')
        for block in pre_blocks:
            text = block.get_text()
            if '/' in text and (
                'directory' in text.lower() or 
                'structure' in text.lower() or
                'layer' in text.lower()
            ):
                return text
        
        # Look for paragraphs that might describe directory structure
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text()
            if ('directory' in text.lower() and 'structure' in text.lower()) or 'layer' in text.lower():
                return text
                
        return None
    
    @classmethod
    def extract_constructor_props(cls, html_section: str) -> Dict[str, Dict[str, str]]:
        """Extract constructor properties from HTML section."""
        if not html_section:
            return {}
            
        soup = BeautifulSoup(html_section, 'html.parser')
        props = {}
        
        # Look for tables that might contain props
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 2:
                    prop_name = cells[0].get_text().strip()
                    prop_desc = cells[1].get_text().strip()
                    props[prop_name] = {
                        "description": prop_desc
                    }
        
        return props
    
    @classmethod
    def save_to_cache(cls, data: Dict[str, Any]) -> None:
        """Save data to cache file."""
        try:
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            with open(cls.CACHE_FILE, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    @classmethod
    def load_from_cache(cls) -> Optional[Dict[str, Any]]:
        """Load data from cache file if it exists and is not expired."""
        try:
            if not os.path.exists(cls.CACHE_FILE):
                return None
                
            with open(cls.CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            if time.time() - cache_data["timestamp"] > cls.CACHE_TTL:
                logger.info("Cache expired")
                return None
                
            return cache_data["data"]
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
            return None
    
    @classmethod
    def find_layer_content(cls, html: str) -> Optional[str]:
        """Find Lambda layer content using multiple strategies."""
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Strategy 1: Find section by id
        section = soup.find(id="layers")
        if section:
            # If we found an anchor, get its parent and look for the actual content
            if section.name == 'a':
                parent = section.parent
                if parent and parent.name.startswith('h'):
                    # We found a header, extract all content until the next header of same or higher level
                    content = []
                    content.append(str(parent))
                    
                    header_level = int(parent.name[1])
                    sibling = parent.next_sibling
                    
                    while sibling:
                        if sibling.name and sibling.name.startswith('h') and int(sibling.name[1]) <= header_level:
                            break
                        if sibling.name:
                            content.append(str(sibling))
                        sibling = sibling.next_sibling
                    
                    return ''.join(content)
        
        # Strategy 2: Look for headers containing layer keywords
        for tag in ['h1', 'h2', 'h3', 'h4']:
            headers = soup.find_all(tag)
            for header in headers:
                text = header.get_text().lower()
                if any(pattern in text for pattern in cls.LAYER_SECTION_PATTERNS):
                    # Found a relevant header, extract all content until the next header of same or higher level
                    content = []
                    content.append(str(header))
                    
                    header_level = int(header.name[1])
                    sibling = header.next_sibling
                    
                    while sibling:
                        if sibling.name and sibling.name.startswith('h') and int(sibling.name[1]) <= header_level:
                            break
                        if sibling.name:
                            content.append(str(sibling))
                        sibling = sibling.next_sibling
                    
                    return ''.join(content)
        
        # Strategy 3: Look for content div with class="api" or class="props"
        content_divs = soup.find_all('div', class_=["api", "props"])
        if content_divs:
            return ''.join(str(div) for div in content_divs)
        
        # Strategy 4: Look for table with class containing 'cdk'
        tables = soup.find_all('table')
        for table in tables:
            if table.get('class') and any('cdk' in cls for cls in table.get('class')):
                return str(table)
        
        return None
    
    @classmethod
    def find_python_layer_content(cls, html: str) -> Optional[str]:
        """Find Python layer content specifically."""
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Strategy 1: Look for class definition section
        class_div = soup.find('div', class_="classDef")
        if class_div:
            return str(class_div)
            
        # Strategy 2: Look for h2 or h3 with "PythonLayerVersion" in text
        for tag in ['h1', 'h2', 'h3', 'h4']:
            headers = soup.find_all(tag)
            for header in headers:
                if "PythonLayerVersion" in header.get_text():
                    # Found the header, get all content up to the next header
                    content = []
                    content.append(str(header))
                    
                    sibling = header.next_sibling
                    while sibling:
                        if sibling.name and sibling.name.startswith('h') and sibling.name <= header.name:
                            break
                        if sibling.name:
                            content.append(str(sibling))
                        sibling = sibling.next_sibling
                    
                    return ''.join(content)
        
        # Strategy 3: Just get the full page body as fallback
        body = soup.find('body')
        if body:
            return str(body)
            
        return None
    
    @classmethod
    async def fetch_lambda_layer_docs(cls) -> Dict[str, Any]:
        """Fetch Lambda layer documentation from AWS docs."""
        # Try to load from cache first
        cached_data = cls.load_from_cache()
        if cached_data and False:  # Temporarily disable cache to test
            logger.info("Using cached Lambda layer documentation")
            return cached_data
            
        # Fetch the pages
        generic_html = await cls.fetch_page(cls.GENERIC_LAYER_URL)
        python_html = await cls.fetch_page(cls.PYTHON_LAYER_URL)
        
        # Extract relevant sections using our specialized finders
        generic_layers_section = cls.find_layer_content(generic_html)
        python_layer_section = cls.find_python_layer_content(python_html)
        
        # Extract code examples
        generic_examples = cls.extract_code_examples(generic_layers_section)
        python_examples = cls.extract_code_examples(python_layer_section)
        
        # Extract directory structure
        generic_dir_structure = cls.extract_directory_structure(generic_layers_section)
        python_dir_structure = cls.extract_directory_structure(python_layer_section)
        
        # Extract constructor props
        generic_props = cls.extract_constructor_props(generic_layers_section)
        python_props = cls.extract_constructor_props(python_layer_section)
        
        # Compile the results
        result = {
            "generic_layers": {
                "html": generic_layers_section,
                "examples": generic_examples,
                "directory_structure": generic_dir_structure,
                "props": generic_props,
                "url": cls.GENERIC_LAYER_URL
            },
            "python_layers": {
                "html": python_layer_section,
                "examples": python_examples,
                "directory_structure": python_dir_structure,
                "props": python_props,
                "url": cls.PYTHON_LAYER_URL
            }
        }
        
        # Save to cache
        cls.save_to_cache(result)
        
        return result
