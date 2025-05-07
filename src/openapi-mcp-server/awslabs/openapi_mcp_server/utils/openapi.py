"""Utilities for working with OpenAPI specifications."""

import httpx
import json
from awslabs.openapi_mcp_server import get_caller_info, logger
from pathlib import Path
from typing import Any, Dict


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
    caller_info = get_caller_info()

    if not url and not path:
        logger.error(f'Neither URL nor path provided (called from {caller_info})')
        raise ValueError('Either url or path must be provided')

    # Load from URL
    if url:
        logger.info(f'Fetching OpenAPI spec from URL: {url}')
        try:
            response = httpx.get(url)
            response.raise_for_status()
            return response.json()
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
                    return json.loads(content)
                except json.JSONDecodeError:
                    # If it's not JSON, try to parse as YAML
                    try:
                        import yaml

                        return yaml.safe_load(content)
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
        except Exception as e:
            logger.error(f'Failed to load OpenAPI spec from file: {path} - Error: {e}')
            raise

    # This should not happen, but just in case
    raise ValueError('Either url or path must be provided')
