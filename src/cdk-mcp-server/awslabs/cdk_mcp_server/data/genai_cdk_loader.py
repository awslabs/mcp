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

"""GitHub-based GenAI CDK constructs content loader."""

import httpx
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Constants
GITHUB_API_URL = 'https://api.github.com'
GITHUB_RAW_CONTENT_URL = 'https://raw.githubusercontent.com'
REPO_OWNER = 'awslabs'
REPO_NAME = 'generative-ai-cdk-constructs'
BASE_PATH = 'src/cdk-lib'
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours

# Simple caches
_readme_cache = {}  # Cache for README.md content, keyed by path
_sections_cache = {}  # Cache for extracted sections, keyed by path
_constructs_cache = {}  # Cache for constructs list
_last_constructs_fetch = None  # Last time constructs were fetched


async def fetch_readme(construct_type: str, construct_name: Optional[str] = None) -> Dict[str, Any]:
    """Fetch README.md content directly from GitHub.
    
    Args:
        construct_type: Top-level directory (e.g., 'bedrock')
        construct_name: Optional subdirectory (e.g., 'agents')
        
    Returns:
        Dictionary with README content and metadata
    """
    # Build the path
    path_parts = [construct_type]
    if construct_name:
        path_parts.append(construct_name)
    
    path = "/".join(path_parts)
    cache_key = f"{construct_type}/{construct_name}" if construct_name else construct_type
    
    # Check cache first
    if cache_key in _readme_cache and datetime.now() - _readme_cache[cache_key]['timestamp'] < CACHE_TTL:
        logger.debug(f"Using cached README for {path}")
        return _readme_cache[cache_key]['data']
    
    # Fetch from GitHub
    readme_url = f'{GITHUB_RAW_CONTENT_URL}/{REPO_OWNER}/{REPO_NAME}/main/{BASE_PATH}/{path}/README.md'
    logger.info(f"Fetching README from {readme_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(readme_url)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch README for {path}: HTTP {response.status_code}")
                return {
                    'error': f'Failed to fetch README for {path}: HTTP {response.status_code}',
                    'status_code': response.status_code,
                }
            
            content = response.text
            
            # Update cache
            result = {
                'content': content,
                'path': path,
                'url': readme_url,
                'status': 'success',
            }
            
            _readme_cache[cache_key] = {
                'timestamp': datetime.now(),
                'data': result,
            }
            
            return result
    except Exception as e:
        logger.error(f"Error fetching README for {path}: {str(e)}")
        return {
            'error': f'Error fetching README: {str(e)}',
            'status': 'error',
        }


def extract_sections(content: str) -> Dict[str, str]:
    """Extract sections from README.md content based on level 2 headings (##) only.
    
    Returns a dictionary mapping section names to their content.
    Uses URL encoding for section names to handle special characters.
    """
    # Find all level 2 headings (## Heading)
    headings = re.finditer(r'^##\s+(.+?)$', content, re.MULTILINE)
    
    sections = {}
    section_starts = []
    
    # Import here to avoid circular imports
    import urllib.parse
    
    # Collect all level 2 headings with their positions
    for match in headings:
        heading_text = match.group(1).strip()
        # Store URL-safe version for proper matching later
        section_starts.append((match.start(), heading_text))
    
    # Sort by position
    section_starts.sort()
    
    # Extract content between headings
    for i, (start_pos, heading) in enumerate(section_starts):
        # Find the end of this section (start of next level 2 heading or end of file)
        end_pos = section_starts[i+1][0] if i < len(section_starts) - 1 else len(content)
        
        # Extract the section content including the heading
        section_content = content[start_pos:end_pos].strip()
        
        # Use the heading text as the key
        sections[heading] = section_content
    
    return sections


async def get_section(construct_type: str, construct_name: str, section_name: str) -> Dict[str, Any]:
    """Get a specific section from a README.md file.
    
    Args:
        construct_type: Top-level directory (e.g., 'bedrock')
        construct_name: Subdirectory (e.g., 'agents')
        section_name: Name of the section to extract
        
    Returns:
        Dictionary with section content and metadata
    """
    # Build cache key
    path = f"{construct_type}/{construct_name}"
    cache_key = path
    
    # Check if sections are already cached
    if cache_key in _sections_cache and datetime.now() - _sections_cache[cache_key]['timestamp'] < CACHE_TTL:
        sections = _sections_cache[cache_key]['data']
        
        # Find the section (case-insensitive)
        for heading, content in sections.items():
            if heading.lower() == section_name.lower():
                return {
                    'content': content,
                    'section': heading,
                    'path': path,
                    'status': 'success',
                }
        
        # Section not found in cache
        return {
            'error': f"Section '{section_name}' not found in {path}",
            'status': 'not_found',
        }
    
    # Fetch the README
    readme_result = await fetch_readme(construct_type, construct_name)
    
    if 'error' in readme_result:
        return readme_result
    
    # Extract sections
    sections = extract_sections(readme_result['content'])
    
    # Cache the sections
    _sections_cache[cache_key] = {
        'timestamp': datetime.now(),
        'data': sections,
    }
    
    # Find the section using URL decoding and case-insensitive comparison
    import urllib.parse
    decoded_section_name = urllib.parse.unquote(section_name)
    logger.info(f"Looking for section '{decoded_section_name}' in {path}")
    logger.info(f"Available sections: {', '.join(sections.keys())}")
    
    # First try direct match after decoding
    for heading, content in sections.items():
        if heading.lower() == decoded_section_name.lower():
            return {
                'content': content,
                'section': heading,
                'path': path,
                'status': 'success',
            }
    
    # Section not found
    logger.warning(f"Section '{section_name}' not found in {path}")
    return {
        'error': f"Section '{section_name}' not found in {path}",
        'status': 'not_found',
    }


async def list_sections(construct_type: str, construct_name: str) -> Dict[str, Any]:
    """List available sections in a README.md file.
    
    Args:
        construct_type: Top-level directory (e.g., 'bedrock')
        construct_name: Subdirectory (e.g., 'agents')
        
    Returns:
        Dictionary with list of sections and metadata
    """
    # Build cache key
    path = f"{construct_type}/{construct_name}"
    cache_key = path
    
    # Check if sections are already cached
    if cache_key in _sections_cache and datetime.now() - _sections_cache[cache_key]['timestamp'] < CACHE_TTL:
        sections = _sections_cache[cache_key]['data']
        return {
            'sections': list(sections.keys()),
            'path': path,
            'status': 'success',
        }
    
    # Fetch the README
    readme_result = await fetch_readme(construct_type, construct_name)
    
    if 'error' in readme_result:
        return readme_result
    
    # Extract sections
    sections = extract_sections(readme_result['content'])
    
    # Cache the sections
    _sections_cache[cache_key] = {
        'timestamp': datetime.now(),
        'data': sections,
    }
    
    return {
        'sections': list(sections.keys()),
        'path': path,
        'status': 'success',
    }


async def get_construct_overview(construct_type: str) -> Dict[str, Any]:
    """Get overview documentation for a construct type.
    
    Args:
        construct_type: Top-level directory (e.g., 'bedrock')
        
    Returns:
        Dictionary with README content for the construct type
    """
    return await fetch_readme(construct_type)


async def fetch_bedrock_subdirectories() -> List[Dict[str, Any]]:
    """Fetch subdirectories specifically for the bedrock directory.
    
    Returns:
        List of subdirectory information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{BASE_PATH}/bedrock',
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch bedrock subdirectories: HTTP {response.status_code}")
                return []
            
            contents = response.json()
            
            # Filter directories only
            subdirs = []
            for item in contents:
                if item['type'] == 'dir':
                    subdir_name = item['name']
                    
                    # Get README for this subdirectory if available
                    readme_result = await fetch_readme('bedrock', subdir_name)
                    
                    # Default values
                    title = subdir_name
                    description = f'Bedrock {subdir_name.capitalize()} constructs'
                    
                    # Extract better title/description if README exists
                    if 'error' not in readme_result:
                        readme_content = readme_result['content']
                        
                        # Use a safer approach to extract title - find first # heading
                        lines = readme_content.split('\n')
                        for line in lines:
                            if line.startswith('# '):
                                title = line.replace('# ', '').strip()
                                break
                        
                        # Extract description from content after first heading and before next heading
                        # or stability banner
                        description_text = ""
                        capture_description = False
                        for line in lines:
                            if line.startswith('# '):
                                capture_description = True
                                continue
                            if capture_description and (line.startswith('#') or line.startswith('<!--BEGIN')):
                                break
                            if capture_description and line.strip():
                                description_text += line.strip() + " "
                        
                        if description_text:
                            # Clean up and truncate description
                            description_text = description_text.strip()
                            # Take first sentence or up to 150 chars
                            description = description_text.split('.')[0][:150]
                            if len(description) < len(description_text):
                                description += "..."
                    
                    subdirs.append({
                        'name': title,
                        'path': f"bedrock/{subdir_name}",
                        'url': item['html_url'],
                        'description': description
                    })
            
            return subdirs
    except Exception as e:
        logger.error(f"Error fetching bedrock subdirectories: {str(e)}")
        return []


async def fetch_repo_structure() -> Dict[str, Any]:
    """Fetch repository structure from GitHub API.
    
    Returns:
        Dictionary with repository structure information
    """
    global _constructs_cache, _last_constructs_fetch
    
    # Check if we've fetched recently
    if _last_constructs_fetch and datetime.now() - _last_constructs_fetch < CACHE_TTL:
        logger.debug("Using cached repo structure")
        return _constructs_cache
    
    try:
        # Fetch top-level directories
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{BASE_PATH}',
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch repo structure: HTTP {response.status_code}")
                return {'error': 'Failed to fetch repository structure'}
            
            contents = response.json()
            
            # Filter directories only
            directories = [item for item in contents if item['type'] == 'dir']
            
            # For each directory, get its README.md if available
            construct_types = {}
            for dir_info in directories:
                dir_name = dir_info['name']
                
                # Initialize default values first
                title = dir_name
                description = f'AWS {dir_name.capitalize()} constructs'
                
                # Then fetch and potentially override with better data
                readme_result = await fetch_readme(dir_name)
                if 'error' not in readme_result:
                    # Try to extract title and description from README content using markdown parsing
                    readme_content = readme_result['content']
                    
                    # Use a safer approach to extract title - find first # heading
                    lines = readme_content.split('\n')
                    for line in lines:
                        if line.startswith('# '):
                            title = line.replace('# ', '').strip()
                            break
                    
                    # Extract description from content after first heading and before next heading
                    # or stability banner
                    import urllib.parse
                    description_text = ""
                    capture_description = False
                    for line in lines:
                        if line.startswith('# '):
                            capture_description = True
                            continue
                        if capture_description and (line.startswith('#') or line.startswith('<!--BEGIN')):
                            break
                        if capture_description and line.strip():
                            description_text += line.strip() + " "
                    
                    if description_text:
                        # Clean up and truncate description
                        description_text = description_text.strip()
                        # Take first sentence or up to 150 chars
                        description = description_text.split('.')[0][:150]
                        if len(description) < len(description_text):
                            description += "..."
                
                # Store in construct types
                construct_types[dir_name] = {
                    'name': title,
                    'description': description,
                    'path': dir_info['path'],
                    'url': dir_info['html_url'],
                }
            
            # Special case for bedrock: fetch its subdirectories
            if 'bedrock' in construct_types:
                bedrock_subdirs = await fetch_bedrock_subdirectories()
                if bedrock_subdirs:
                    construct_types['bedrock']['subdirectories'] = bedrock_subdirs
            
            # Update cache
            _constructs_cache = {'construct_types': construct_types}
            _last_constructs_fetch = datetime.now()
            
            return _constructs_cache
    except Exception as e:
        logger.error(f"Error fetching repo structure: {str(e)}")
        return {'error': f'Error fetching repository structure: {str(e)}'}


async def list_available_constructs(construct_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available constructs from GitHub.
    
    Args:
        construct_type: Optional construct type to filter by
        
    Returns:
        List of constructs with name, type, and description
    """
    # Get repository structure
    repo_structure = await fetch_repo_structure()
    
    if 'error' in repo_structure:
        logger.error(f"Error in list_available_constructs: {repo_structure['error']}")
        return []
    
    construct_types = repo_structure.get('construct_types', {})
    
    # Get available types
    available_types = list(construct_types.keys())
    
    # If construct type is provided, filter by it
    if construct_type:
        if construct_type not in available_types:
            logger.warning(f"Construct type '{construct_type}' not found. Available types: {', '.join(available_types)}")
            return []
        filter_types = [construct_type]
    else:
        filter_types = available_types
    
    # Prepare result list
    constructs = []
    
    # For each construct type
    for ct in filter_types:
        # Get README for this construct type
        readme_result = await fetch_readme(ct)
        
        if 'error' in readme_result:
            continue
        
        # Extract sections from README
        sections = extract_sections(readme_result['content'])
        
        # Add construct types as top-level constructs
        constructs.append({
            'name': ct.capitalize(),
            'type': ct,
            'description': construct_types[ct]['description'],
        })
        
        # Add sections as constructs
        for section_name in sections:
            # Build a construct name from section
            name_parts = [part.capitalize() for part in section_name.split()]
            if len(name_parts) > 1:
                construct_name = f"{name_parts[0]}{''.join(name_parts[1:])}"
            else:
                construct_name = name_parts[0]
                
            # Build description from the first line of the section
            section_content = sections[section_name]
            first_line = section_content.split('\n')[0].strip('# ')
            description = first_line
            
            # Add to constructs list
            constructs.append({
                'name': construct_name,
                'type': ct,
                'description': description,
            })
        
        # Add bedrock subdirectories as constructs
        if ct == 'bedrock' and 'subdirectories' in construct_types[ct]:
            for subdir in construct_types[ct]['subdirectories']:
                # Add the subdirectory as a construct
                subdir_name = subdir['name']
                constructs.append({
                    'name': f"{subdir_name}",
                    'type': 'bedrock',
                    'description': subdir['description'],
                })
                
                # Also fetch README for this subdirectory to extract sections
                subdir_raw_name = subdir['path'].split('/')[-1]  # Get the raw name from path
                subdir_readme = await fetch_readme('bedrock', subdir_raw_name)
                if 'error' not in subdir_readme:
                    subdir_sections = extract_sections(subdir_readme['content'])
                    
                    # Add sections from subdirectory README
                    for section_name in subdir_sections:
                        # Similar logic to build construct name and description
                        name_parts = [part.capitalize() for part in section_name.split()]
                        if len(name_parts) > 1:
                            section_construct_name = f"{name_parts[0]}{''.join(name_parts[1:])}"
                        else:
                            section_construct_name = name_parts[0]
                        
                        section_content = subdir_sections[section_name]
                        first_line = section_content.split('\n')[0].strip('# ')
                        description = first_line
                        
                        # Add to constructs list with special naming to indicate subdirectory
                        constructs.append({
                            'name': f"{subdir_name}{section_construct_name}",
                            'type': 'bedrock',
                            'description': description,
                        })
            
    return constructs
