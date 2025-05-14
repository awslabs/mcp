"""Utilities for working with OpenAPI specifications."""

import httpx
import json
import time
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.cache_provider import cached
from awslabs.openapi_mcp_server.utils.openapi_validator import validate_openapi_spec
from pathlib import Path
from typing import Any, Dict


@cached(ttl_seconds=3600)  # Cache OpenAPI specs for 1 hour
def load_openapi_spec(url: str = '', path: str = '') -> Dict[str, Any]:
    """Load an OpenAPI specification from a URL or file path.

    Args:
        url: URL to the OpenAPI specification
        path: Path to the OpenAPI specification file

    Returns:
        Dict[str, Any]: The parsed OpenAPI specification

    Raises:
        ValueError: If neither url nor path are provided
        FileNotFoundError: If the file at path does not exist
    """
    if not url and not path:
        logger.error('Neither URL nor path provided')
        raise ValueError('Either url or path must be provided')

    # Load from URL
    if url:
        logger.info(f'Fetching OpenAPI spec from URL: {url}')
        try:
            # Use retry logic for network resilience
            for attempt in range(3):
                try:
                    response = httpx.get(url, timeout=10.0)
                    response.raise_for_status()
                    spec = response.json()

                    # Validate the spec
                    if validate_openapi_spec(spec):
                        return spec
                    else:
                        raise ValueError('Invalid OpenAPI specification')

                except (httpx.TimeoutException, httpx.HTTPError) as e:
                    if attempt < 2:  # Don't log on the last attempt
                        logger.warning(f'Attempt {attempt + 1} failed: {e}. Retrying...')
                        time.sleep(1 * (2**attempt))  # Exponential backoff
                    else:
                        raise

            # This will only be reached if all retries fail and no exception is raised
            raise httpx.HTTPError('All retry attempts failed')

        except Exception as e:
            logger.error(f'Failed to fetch OpenAPI spec from URL: {url} - Error: {e}')
            raise

    # Load from file
    if path:
        spec_path = Path(path)
        if not spec_path.exists():
            logger.error(f'OpenAPI spec file not found: {path}')
            raise FileNotFoundError(f'File not found: {path}')

        logger.info(f'Loading OpenAPI spec from file: {path}')
        try:
            with open(spec_path, 'r') as f:
                content = f.read()
                # Try to parse as JSON first
                try:
                    spec = json.loads(content)
                except json.JSONDecodeError:
                    # If it's not JSON, try to parse as YAML
                    try:
                        import yaml

                        spec = yaml.safe_load(content)
                    except ImportError:
                        logger.error('YAML parsing requires pyyaml to be installed')
                        raise ImportError(
                            "Required dependency 'pyyaml' not installed. Install it with: pip install pyyaml"
                        )
                    except Exception as e:
                        logger.error(
                            f'Failed to parse OpenAPI spec file as YAML: {path} - Error: {e}'
                        )
                        raise

                # Validate the spec
                if validate_openapi_spec(spec):
                    return spec
                else:
                    raise ValueError('Invalid OpenAPI specification')

        except Exception as e:
            logger.error(f'Failed to load OpenAPI spec from file: {path} - Error: {e}')
            raise

    # This should never be reached
    raise ValueError('Either url or path must be provided')
