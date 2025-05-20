"""GitHub API utilities for AWS Lambda MCP Server."""

import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def fetch_github_content(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Fetch content from GitHub API.
    
    Args:
        url: GitHub API URL
        headers: Optional additional headers
    
    Returns:
        Dict: GitHub API response
    """
    default_headers = {"Accept": "application/vnd.github.v3+json"}
    if headers:
        default_headers.update(headers)
    
    try:
        logger.info(f"Fetching GitHub content from {url}")
        response = requests.get(url, headers=default_headers, timeout=30)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching GitHub content: {str(e)}")
        raise ValueError(f"Failed to fetch GitHub content: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding GitHub response: {str(e)}")
        raise ValueError(f"Failed to decode GitHub response: {str(e)}")
