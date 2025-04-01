"""AWS Solutions Constructs patterns parser module."""

import httpx
import logging
import re
import urllib.parse
from awslabs.cdk_mcp_server.core import search_utils
from datetime import datetime, timedelta
from typing import Any, Dict, List


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GITHUB_API_URL = 'https://api.github.com'
GITHUB_RAW_CONTENT_URL = 'https://raw.githubusercontent.com'
REPO_OWNER = 'awslabs'
REPO_NAME = 'aws-solutions-constructs'
PATTERNS_PATH = 'source/patterns/@aws-solutions-constructs'
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours

# Cache for pattern list and pattern details
_pattern_list_cache = {'timestamp': None, 'data': []}
_pattern_details_cache = {}


async def fetch_pattern_list() -> List[str]:
    """Fetch the list of available AWS Solutions Constructs patterns.

    Returns:
        List of pattern names (e.g., ['aws-lambda-dynamodb', 'aws-apigateway-lambda', ...])
    """
    global _pattern_list_cache
    
    # Initialize cache if it's None
    if _pattern_list_cache is None:
        _pattern_list_cache = {'timestamp': None, 'data': []}
        
    # Check cache first
    if (
        _pattern_list_cache['timestamp'] is not None
        and _pattern_list_cache['data'] is not None
        and datetime.now() - _pattern_list_cache['timestamp'] < CACHE_TTL
    ):
        return _pattern_list_cache['data']

    # Fetch from GitHub API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{PATTERNS_PATH}',
            headers={'Accept': 'application/vnd.github.v3+json'},
        )

        if response.status_code != 200:
            return []

        content = response.json()

        # Filter for directories that are actual patterns (exclude core, resources, etc.)
        patterns = [
            item['name']
            for item in content
            if item['type'] == 'dir' and item['name'].startswith('aws-')
        ]

        # Update cache
        _pattern_list_cache['timestamp'] = datetime.now()
        _pattern_list_cache['data'] = patterns

        return patterns


async def get_pattern_info(pattern_name: str) -> Dict[str, Any]:
    """Get metadata information about a specific pattern.

    This function returns only metadata about the pattern, not the full documentation.
    For complete documentation, use the resource URI: aws-solutions-constructs://{pattern_name}

    Args:
        pattern_name: Name of the pattern (e.g., 'aws-lambda-dynamodb')

    Returns:
        Dictionary with pattern metadata
    """
    global _pattern_details_cache

    try:
        logger.info(f'Fetching pattern info for {pattern_name}')

        # Decode the pattern name if it's URL-encoded
        pattern_name = urllib.parse.unquote(pattern_name)

        # Check cache first
        if (
            _pattern_details_cache is not None
            and pattern_name in _pattern_details_cache
            and datetime.now() - _pattern_details_cache[pattern_name]['timestamp'] < CACHE_TTL
        ):
            logger.info(f'Using cached info for {pattern_name}')
            return _pattern_details_cache[pattern_name]['data']

        # Fetch README.md content
        async with httpx.AsyncClient() as client:
            readme_url = f'{GITHUB_RAW_CONTENT_URL}/{REPO_OWNER}/{REPO_NAME}/main/{PATTERNS_PATH}/{pattern_name}/README.md'
            logger.info(f'Fetching README from {readme_url}')
            response = await client.get(readme_url)

            if response.status_code != 200:
                logger.warning(
                    f'Failed to fetch README for {pattern_name}: HTTP {response.status_code}'
                )
                return {
                    'error': f'Pattern {pattern_name} not found or README.md not available',
                    'status_code': response.status_code,
                }

            readme_content = response.text

        # Extract only metadata
        services = extract_services_from_pattern_name(pattern_name)
        description = extract_description(readme_content)
        use_cases = extract_use_cases(readme_content)

        # Create pattern info with only metadata
        pattern_info = {
            'pattern_name': pattern_name,
            'services': services,
            'description': description,
            'use_cases': use_cases,
            'documentation_uri': f'aws-solutions-constructs://{pattern_name}',
        }

        # Update cache
        if _pattern_details_cache is None:
            _pattern_details_cache = {}
            
        _pattern_details_cache[pattern_name] = {'timestamp': datetime.now(), 'data': pattern_info}

        return pattern_info
    except Exception as e:
        logger.error(f'Error processing pattern {pattern_name}: {str(e)}')
        return {
            'error': f'Error processing pattern {pattern_name}: {str(e)}',
            'pattern_name': pattern_name,
        }


async def get_pattern_raw(pattern_name: str) -> Dict[str, Any]:
    """Get raw README.md content for a specific pattern.

    Args:
        pattern_name: Name of the pattern (e.g., 'aws-lambda-dynamodb')

    Returns:
        Dictionary with raw pattern documentation
    """
    try:
        logger.info(f'Fetching raw pattern info for {pattern_name}')

        # Decode the pattern name if it's URL-encoded
        pattern_name = urllib.parse.unquote(pattern_name)

        # Fetch README.md content
        async with httpx.AsyncClient() as client:
            readme_url = f'{GITHUB_RAW_CONTENT_URL}/{REPO_OWNER}/{REPO_NAME}/main/{PATTERNS_PATH}/{pattern_name}/README.md'
            logger.info(f'Fetching README from {readme_url}')
            response = await client.get(readme_url)

            if response.status_code != 200:
                logger.warning(
                    f'Failed to fetch README for {pattern_name}: HTTP {response.status_code}'
                )
                return {
                    'error': f'Pattern {pattern_name} not found or README.md not available',
                    'status_code': response.status_code,
                }

            readme_content = response.text

            # Extract services from pattern name
            services = extract_services_from_pattern_name(pattern_name)

            return {
                'status': 'success',
                'pattern_name': pattern_name,
                'services': services,
                'content': readme_content,
                'message': f'Retrieved pattern documentation for {pattern_name}',
            }
    except Exception as e:
        logger.error(f'Error fetching raw pattern {pattern_name}: {str(e)}')
        return {
            'status': 'error',
            'pattern_name': pattern_name,
            'error': f'Error fetching pattern documentation: {str(e)}',
        }


def parse_readme_content(pattern_name: str, content: str) -> Dict[str, Any]:
    """Parse README.md content to extract pattern information.

    Args:
        pattern_name: Name of the pattern
        content: README.md content

    Returns:
        Dictionary with parsed pattern information
    """
    result = {
        'pattern_name': pattern_name,
        'services': extract_services_from_pattern_name(pattern_name),
        'description': extract_description(content),
        'props': extract_props(content),
        'props_markdown': extract_props_markdown(content),
        'properties': extract_properties(content),
        'default_settings': extract_default_settings(content),
        'code_example': extract_code_example(content),
        'use_cases': extract_use_cases(content),
    }

    return result


def extract_props_markdown(content: str) -> str:
    """Extract the Pattern Construct Props section as markdown from README.md content.

    Args:
        content: README.md content

    Returns:
        Markdown string containing the Pattern Construct Props section
    """
    # Look for the Pattern Construct Props section
    props_section_match = re.search(
        r'## Pattern Construct Props(.*?)(?=##|\Z)', content, re.DOTALL
    )
    if not props_section_match:
        # Try alternative section names
        props_section_match = re.search(r'## Construct Props(.*?)(?=##|\Z)', content, re.DOTALL)
        if not props_section_match:
            props_section_match = re.search(r'## Props(.*?)(?=##|\Z)', content, re.DOTALL)
            if not props_section_match:
                return 'No props section found'

    # Return the entire section as markdown
    return props_section_match.group(1).strip()


def extract_services_from_pattern_name(pattern_name: str) -> List[str]:
    """Extract AWS service names from the pattern name.

    Args:
        pattern_name: Name of the pattern (e.g., 'aws-lambda-dynamodb')

    Returns:
        List of service names (e.g., ['Lambda', 'DynamoDB'])
    """
    # Remove 'aws-' prefix and split by '-'
    parts = pattern_name[4:].split('-')

    # Map to proper service names
    service_mapping = {
        'lambda': 'Lambda',
        'dynamodb': 'DynamoDB',
        'apigateway': 'API Gateway',
        's3': 'S3',
        'sqs': 'SQS',
        'sns': 'SNS',
        'eventbridge': 'EventBridge',
        'kinesisfirehose': 'Kinesis Firehose',
        'kinesisstreams': 'Kinesis Streams',
        'cloudfront': 'CloudFront',
        'alb': 'Application Load Balancer',
        'fargate': 'Fargate',
        'iot': 'IoT Core',
        'elasticsearch': 'Elasticsearch',
        'opensearch': 'OpenSearch',
        'secretsmanager': 'Secrets Manager',
        'sagemakerendpoint': 'SageMaker Endpoint',
        'stepfunctions': 'Step Functions',
        'wafwebacl': 'WAF Web ACL',
        'cognito': 'Cognito',
        'appsync': 'AppSync',
        'kendra': 'Kendra',
        'elasticachememcached': 'ElastiCache Memcached',
        'ssmstringparameter': 'SSM String Parameter',
        'mediastore': 'MediaStore',
        'gluejob': 'Glue Job',
        'pipes': 'EventBridge Pipes',
        'oai': 'Origin Access Identity',
        'route53': 'Route 53',
        'openapigateway': 'API Gateway (OpenAPI)',
        'apigatewayv2websocket': 'API Gateway v2 WebSocket',
    }

    return [service_mapping.get(part, part.capitalize()) for part in parts]


def extract_description(content: str) -> str:
    """Extract the pattern description from README.md content.

    Args:
        content: README.md content

    Returns:
        Pattern description
    """
    # First, try to find a dedicated Description section
    desc_section_match = re.search(r'## Description\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if desc_section_match:
        return desc_section_match.group(1).strip()

    # Next, try to find an Overview section
    overview_section_match = re.search(r'## Overview\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if overview_section_match:
        # Take the first paragraph of the overview
        overview = overview_section_match.group(1).strip()
        first_para_match = re.search(r'^(.*?)(?=\n\n|\Z)', overview, re.DOTALL)
        if first_para_match:
            return first_para_match.group(1).strip()
        return overview

    # Try to find the first paragraph after the title
    match = re.search(r'# [^\n]*\n\n(.*?)(?=\n\n|\n##|\Z)', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: Try to find any text before the first ## heading
    match = re.search(r'\n\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If all else fails, extract the title as a fallback
    title_match = re.search(r'# ([^\n]+)', content)
    if title_match:
        pattern_name = title_match.group(1).strip()
        return f'A pattern for integrating {pattern_name} services'

    return 'No description available'


def extract_props(content: str) -> Dict[str, Dict[str, Any]]:
    """Extract pattern construct props from README.md content.

    Args:
        content: README.md content

    Returns:
        Dictionary of props with their descriptions
    """
    props = {}

    # Look for the Pattern Construct Props section
    props_section_match = re.search(
        r'## Pattern Construct Props(.*?)(?=##|\Z)', content, re.DOTALL
    )
    if not props_section_match:
        # Try alternative section names
        props_section_match = re.search(r'## Construct Props(.*?)(?=##|\Z)', content, re.DOTALL)
        if not props_section_match:
            props_section_match = re.search(r'## Props(.*?)(?=##|\Z)', content, re.DOTALL)
            if not props_section_match:
                return props

    props_section = props_section_match.group(1)

    # First, try to find a markdown table with headers
    # Look for a table with a header row and a separator row
    table_match = re.search(
        r'\|([^|]*\|)+\s*\n\s*\|([-:]+\|)+\s*\n(.*?)(?=\n\s*\n|\Z)', props_section, re.DOTALL
    )

    if table_match:
        table_content = table_match.group(3)
        # Extract rows from the table
        rows = re.finditer(r'\|\s*(?:`([^`]+)`|([^|]+))\s*\|(.*?)\|', table_content)

        for row in rows:
            # The prop name could be in backticks or not
            prop_name = row.group(1) if row.group(1) else row.group(2).strip()
            prop_desc = row.group(3).strip()

            # Skip empty prop names or separator rows
            if not prop_name or prop_name.startswith('-') or all(c in '-:|' for c in prop_name):
                continue

            # Skip header rows
            if prop_name.lower() in ['name', 'property', 'parameter', 'prop']:
                continue

            # Determine if required
            required = (
                'required' in prop_desc.lower()
                and 'not required' not in prop_desc.lower()
                and 'optional' not in prop_desc.lower()
            )

            # Try to determine type
            type_match = re.search(r'([a-zA-Z0-9.]+(?:\.[a-zA-Z0-9]+)+)', prop_desc)
            prop_type = type_match.group(1) if type_match else 'unknown'

            # Look for default value
            default_match = re.search(
                r'Default(?:s)?\s*(?:is|:|to)?\s*[`"]?([^`"\n]+)[`"]?', prop_desc, re.IGNORECASE
            )
            default_value = default_match.group(1).strip() if default_match else None

            props[prop_name] = {
                'description': prop_desc,
                'required': required,
                'type': prop_type,
                'default': default_value,
            }

    # If no table found or no props extracted from table, try to find prop definitions in other formats
    if not props:
        # Look for definitions like "- `propName`: Description"
        prop_defs = re.finditer(
            r'[-*]\s*`([^`]+)`\s*:\s*(.*?)(?=\n[-*]|\n##|\Z)', props_section, re.DOTALL
        )

        for prop_def in prop_defs:
            prop_name = prop_def.group(1)
            prop_desc = prop_def.group(2).strip()

            # Determine if required
            required = (
                'required' in prop_desc.lower()
                and 'not required' not in prop_desc.lower()
                and 'optional' not in prop_desc.lower()
            )

            # Try to determine type
            type_match = re.search(r'([a-zA-Z0-9.]+(?:\.[a-zA-Z0-9]+)+)', prop_desc)
            prop_type = type_match.group(1) if type_match else 'unknown'

            # Look for default value
            default_match = re.search(
                r'Default(?:s)?\s*(?:is|:|to)?\s*[`"]?([^`"\n]+)[`"]?', prop_desc, re.IGNORECASE
            )
            default_value = default_match.group(1).strip() if default_match else None

            props[prop_name] = {
                'description': prop_desc,
                'required': required,
                'type': prop_type,
                'default': default_value,
            }

        # If still no props, try to find bullet points with prop descriptions
        if not props:
            # Look for bullet points with prop descriptions
            bullet_props = re.finditer(r'[-*]\s*(.*?)(?=\n[-*]|\n##|\Z)', props_section, re.DOTALL)

            for bullet_prop in bullet_props:
                bullet_text = bullet_prop.group(1).strip()

                # Try to extract prop name and description
                prop_match = re.search(r'^([a-zA-Z0-9_]+)\s*[-:]\s*(.*)', bullet_text)
                if prop_match:
                    prop_name = prop_match.group(1)
                    prop_desc = prop_match.group(2).strip()

                    # Determine if required
                    required = (
                        'required' in prop_desc.lower()
                        and 'not required' not in prop_desc.lower()
                        and 'optional' not in prop_desc.lower()
                    )

                    # Try to determine type
                    type_match = re.search(r'([a-zA-Z0-9.]+(?:\.[a-zA-Z0-9]+)+)', prop_desc)
                    prop_type = type_match.group(1) if type_match else 'unknown'

                    # Look for default value
                    default_match = re.search(
                        r'Default(?:s)?\s*(?:is|:|to)?\s*[`"]?([^`"\n]+)[`"]?',
                        prop_desc,
                        re.IGNORECASE,
                    )
                    default_value = default_match.group(1).strip() if default_match else None

                    props[prop_name] = {
                        'description': prop_desc,
                        'required': required,
                        'type': prop_type,
                        'default': default_value,
                    }

    return props


def extract_properties(content: str) -> Dict[str, Dict[str, Any]]:
    """Extract pattern properties from README.md content.

    Args:
        content: README.md content

    Returns:
        Dictionary of properties with their descriptions
    """
    properties = {}

    # Look for the Pattern Properties section
    props_section_match = re.search(r'## Pattern Properties(.*?)(?=##|\Z)', content, re.DOTALL)
    if not props_section_match:
        return properties

    props_section = props_section_match.group(1)

    # Extract properties from the section
    prop_matches = re.finditer(r'\|\s*`([^`]+)`\s*\|(.*?)\|', props_section)

    for match in prop_matches:
        prop_name = match.group(1)
        prop_desc = match.group(2).strip()

        # Try to determine type
        type_match = re.search(r'([a-zA-Z0-9.]+(?:\.[a-zA-Z0-9]+)+)', prop_desc)
        prop_type = type_match.group(1) if type_match else 'unknown'

        # Look for access method
        access_match = re.search(
            r'(?:access|get|retrieve)(?:ed)?\s+(?:via|using|with|by)?\s+`([^`]+)`',
            prop_desc,
            re.IGNORECASE,
        )
        access_method = access_match.group(1) if access_match else None

        properties[prop_name] = {
            'description': prop_desc,
            'type': prop_type,
            'access_method': access_method,
        }

    return properties


def extract_default_settings(content: str) -> List[str]:
    """Extract default settings from README.md content.

    Args:
        content: README.md content

    Returns:
        List of default settings
    """
    defaults = []

    # Look for the Default Settings section
    default_section_match = re.search(r'## Default Settings(.*?)(?=##|\Z)', content, re.DOTALL)
    if not default_section_match:
        return defaults

    default_section = default_section_match.group(1)

    # Extract bullet points - handle both * and - style bullets
    bullet_matches = re.finditer(
        r'(?:\*|\-)\s*(.*?)(?=\n(?:\*|\-)|\n##|\n$|\Z)', default_section, re.DOTALL
    )

    for match in bullet_matches:
        # Clean up any newlines or extra whitespace
        setting = re.sub(r'\s+', ' ', match.group(1).strip())
        defaults.append(setting)

    return defaults


def extract_code_example(content: str) -> str:
    """Extract a code example from README.md content.

    Args:
        content: README.md content

    Returns:
        Code example as a string
    """
    # First, look for TypeScript code blocks in the Architecture section
    architecture_section_match = re.search(r'## Architecture(.*?)(?=##|\Z)', content, re.DOTALL)
    if architecture_section_match:
        architecture_section = architecture_section_match.group(1)
        code_match = re.search(r'```typescript\n(.*?)\n```', architecture_section, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

    # Next, look for TypeScript code blocks in the entire content
    code_match = re.search(r'```typescript\n(.*?)\n```', content, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Try JavaScript code blocks
    code_match = re.search(r'```javascript\n(.*?)\n```', content, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Try Python code blocks
    code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Try without language specifier
    code_match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Look for code blocks with indentation (4 spaces)
    code_blocks = re.findall(r'(?:^|\n)( {4}[^\n]+(?:\n {4}[^\n]+)*)', content)
    if code_blocks:
        # Return the longest code block (most likely to be a complete example)
        longest_block = max(code_blocks, key=len)
        # Remove the 4-space indentation from each line
        return '\n'.join(line[4:] for line in longest_block.split('\n'))

    return 'No code example available'


def extract_use_cases(content: str) -> List[str]:
    """Extract use cases from README.md content.

    Args:
        content: README.md content

    Returns:
        List of use cases
    """
    use_cases = []

    # First, look for a dedicated Use Cases section
    use_cases_section_match = re.search(r'## Use Cases(.*?)(?=##|\Z)', content, re.DOTALL)
    if use_cases_section_match:
        use_cases_section = use_cases_section_match.group(1)

        # Extract bullet points
        bullet_matches = re.finditer(
            r'(?:\*|\-)\s*(.*?)(?=\n(?:\*|\-)|\n##|\n$|\Z)', use_cases_section, re.DOTALL
        )
        for match in bullet_matches:
            # Clean up any newlines or extra whitespace
            use_case = re.sub(r'\s+', ' ', match.group(1).strip())
            use_cases.append(use_case)

        if use_cases:
            return use_cases

    # If no dedicated section, look for the Overview section
    overview_match = re.search(r'## Overview(.*?)(?=##|\Z)', content, re.DOTALL)
    if overview_match:
        overview = overview_match.group(1)

        # Look for sentences that might indicate use cases
        sentences = re.split(r'(?<=[.!?])\s+', overview)
        for sentence in sentences:
            if any(
                keyword in sentence.lower()
                for keyword in [
                    'use',
                    'scenario',
                    'when',
                    'ideal',
                    'perfect',
                    'suitable',
                    'designed for',
                ]
            ):
                use_cases.append(sentence.strip())

    # Also check the main description for use case hints
    description = extract_description(content)
    if description != 'No description available':
        sentences = re.split(r'(?<=[.!?])\s+', description)
        for sentence in sentences:
            if any(
                keyword in sentence.lower()
                for keyword in [
                    'use',
                    'scenario',
                    'when',
                    'ideal',
                    'perfect',
                    'suitable',
                    'designed for',
                ]
            ):
                # Avoid duplicates
                if sentence.strip() not in use_cases:
                    use_cases.append(sentence.strip())

    # If we still couldn't find any, add a generic one based on the services
    if not use_cases:
        if description != 'No description available':
            use_cases.append(f'Implementing {description}')
        else:
            services = extract_services_from_pattern_name(content.split('\n')[0].strip('# '))
            use_cases.append(f'Integrating {" and ".join(services)}')

    return use_cases


async def search_patterns(services: List[str]) -> List[Dict[str, Any]]:
    """Search for patterns that use specific AWS services.

    Args:
        services: List of AWS service names to search for

    Returns:
        List of matching patterns with their information
    """
    try:
        logger.info(f'Searching for patterns with services: {services}')

        # Get all patterns
        all_patterns = await fetch_pattern_list()

        # Define functions to extract searchable text and name parts
        def get_text_fn(pattern_name: str) -> str:
            # Extract services from pattern name
            services = extract_services_from_pattern_name(pattern_name)
            return ' '.join(services).lower()

        def get_name_parts_fn(pattern_name: str) -> List[str]:
            return extract_services_from_pattern_name(pattern_name)

        # Use common search utility
        scored_patterns = search_utils.search_items_with_terms(
            all_patterns, services, get_text_fn, get_name_parts_fn
        )

        # Fetch full pattern info for matched patterns
        matching_patterns = []
        for scored_pattern in scored_patterns:
            pattern_name = scored_pattern['item']
            pattern_info = await get_pattern_info(pattern_name)

            # Add matched terms to the result
            pattern_info['matched_services'] = scored_pattern['matched_terms']

            # Remove verbose use_cases field
            if 'use_cases' in pattern_info:
                del pattern_info['use_cases']

            matching_patterns.append(pattern_info)

        logger.info(f'Found {len(matching_patterns)} matching patterns')
        return matching_patterns
    except Exception as e:
        logger.error(f'Error searching patterns: {str(e)}')
        return []


async def get_all_patterns_info() -> List[Dict[str, Any]]:
    """Get information about all available patterns.

    Returns:
        List of pattern information dictionaries
    """
    try:
        logger.info('Fetching information for all patterns')

        patterns = await fetch_pattern_list()
        result = []

        for pattern in patterns:
            try:
                pattern_info = await get_pattern_info(pattern)
                result.append(pattern_info)
            except Exception as e:
                logger.error(f'Error fetching info for pattern {pattern}: {str(e)}')
                # Add a minimal error entry so we don't lose the pattern in the list
                result.append(
                    {
                        'pattern_name': pattern,
                        'error': f'Failed to fetch pattern info: {str(e)}',
                        'services': extract_services_from_pattern_name(pattern),
                    }
                )

        logger.info(f'Fetched information for {len(result)} patterns')
        return result
    except Exception as e:
        logger.error(f'Error fetching all patterns info: {str(e)}')
        return []
