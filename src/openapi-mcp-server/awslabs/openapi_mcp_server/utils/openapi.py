# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for working with OpenAPI specifications."""

import httpx
import json
import tempfile
import time
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.cache_provider import cached
from awslabs.openapi_mcp_server.utils.openapi_validator import validate_openapi_spec
from pathlib import Path
from typing import Any, Dict, Optional


def extract_api_name_from_spec(spec: Dict[str, Any]) -> Optional[str]:
    """Extract the API name from an OpenAPI specification.

    Args:
        spec: The OpenAPI specification dictionary

    Returns:
        Optional[str]: The API name extracted from the specification, or None if not found

    """
    if not spec or not isinstance(spec, dict):
        logger.warning('Invalid OpenAPI spec format')
        return None

    # Extract from info.title
    if 'info' in spec and isinstance(spec['info'], dict) and 'title' in spec['info']:
        return spec['info']['title']

    logger.debug('No API name found in OpenAPI spec')
    return None


# Import yaml conditionally to avoid errors if it's not installed
try:
    import yaml
except ImportError:
    yaml = None  # type: Optional[Any]


# Try to import prance, but don't fail if it's not installed
try:
    from prance import ResolvingParser

    PRANCE_AVAILABLE = True
except ImportError:
    PRANCE_AVAILABLE = False
    logger.warning('Prance library not found. Reference resolution will be limited.')


@cached(ttl_seconds=3600)  # Cache OpenAPI specs for 1 hour
def load_openapi_spec(url: str = '', path: str = '') -> Dict[str, Any]:
    """Load an OpenAPI specification from a URL or file path.

    If prance is available, it will be used to resolve references in the OpenAPI spec.
    Otherwise, falls back to basic JSON/YAML parsing.

    Args:
        url: URL to the OpenAPI specification
        path: Path to the OpenAPI specification file

    Returns:
        Dict[str, Any]: The parsed OpenAPI specification

    Raises:
        ValueError: If neither url nor path are provided
        FileNotFoundError: If the file at path does not exist
        httpx.HTTPError: If there's an HTTP error when fetching the spec
        httpx.TimeoutException: If there's a timeout when fetching the spec

    """
    if not url and not path:
        logger.error('Neither URL nor path provided')
        raise ValueError('Either url or path must be provided')

    # Load from URL
    if url:
        logger.info(f'Fetching OpenAPI spec from URL: {url}')
        last_exception = None

        # Use retry logic for network resilience
        for attempt in range(3):
            try:
                response = httpx.get(url, timeout=10.0)
                response.raise_for_status()

                if PRANCE_AVAILABLE:
                    logger.info('Using prance for reference resolution')
                    # Use prance for reference resolution if available
                    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_file.write(response.content)

                    try:
                        parser = ResolvingParser(temp_path)
                        spec = parser.specification

                        # Clean up the temporary file
                        Path(temp_path).unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning(
                            f'Failed to parse with prance: {e}. Falling back to basic parsing.'
                        )
                        # Clean up the temporary file
                        Path(temp_path).unlink(missing_ok=True)
                        # Fall back to basic parsing
                        spec = response.json()
                else:
                    # Basic parsing without reference resolution
                    spec = response.json()

                # Validate the spec
                if validate_openapi_spec(spec):
                    return spec
                else:
                    logger.error('Invalid OpenAPI specification')
                    raise ValueError('Invalid OpenAPI specification')

            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_exception = e
                if attempt < 2:  # Don't log on the last attempt
                    logger.warning(f'Attempt {attempt + 1} failed: {e}. Retrying...')
                    time.sleep(1 * (2**attempt))  # Exponential backoff
                else:
                    # Re-raise the exception on the last attempt
                    logger.error(f'All retry attempts failed: {e}')
                    raise

        # This will only be reached if all retries fail and no exception is raised
        if last_exception:
            raise last_exception
        else:
            raise httpx.HTTPError('All retry attempts failed')

    # Load from file
    if path:
        spec_path = Path(path)
        if not spec_path.exists():
            logger.error(f'OpenAPI spec file not found: {path}')
            raise FileNotFoundError(f'File not found: {path}')

        logger.info(f'Loading OpenAPI spec from file: {path}')
        try:
            if PRANCE_AVAILABLE:
                logger.info('Using prance for reference resolution')
                # Use prance for reference resolution if available
                try:
                    parser = ResolvingParser(path)
                    spec = parser.specification
                except Exception as e:
                    logger.warning(
                        f'Failed to parse with prance: {e}. Falling back to basic parsing.'
                    )
                    # Fall back to basic parsing
                    with open(spec_path, 'r') as f:
                        content = f.read()
                        try:
                            spec = json.loads(content)
                        except json.JSONDecodeError as json_err:
                            # If it's not JSON, try to parse as YAML
                            try:
                                import yaml

                                spec = yaml.safe_load(content)
                            except ImportError:
                                logger.error('YAML parsing requires pyyaml to be installed')
                                raise ImportError(
                                    "Required dependency 'pyyaml' not installed. Install it with: pip install pyyaml"
                                ) from json_err
                            except Exception as yaml_err:
                                logger.error(f'Failed to parse YAML: {yaml_err}')
                                raise ValueError(f'Invalid YAML: {yaml_err}') from yaml_err
            else:
                # Basic parsing without reference resolution
                with open(spec_path, 'r') as f:
                    content = f.read()
                    try:
                        spec = json.loads(content)
                    except json.JSONDecodeError as json_err:
                        # If it's not JSON, try to parse as YAML
                        try:
                            import yaml

                            spec = yaml.safe_load(content)
                        except ImportError:
                            logger.error('YAML parsing requires pyyaml to be installed')
                            raise ImportError(
                                "Required dependency 'pyyaml' not installed. Install it with: pip install pyyaml"
                            ) from json_err
                        except Exception as yaml_err:
                            logger.error(f'Failed to parse YAML: {yaml_err}')
                            raise ValueError(f'Invalid YAML: {yaml_err}') from yaml_err

            # Validate the spec
            if validate_openapi_spec(spec):
                return spec
            else:
                raise ValueError('Invalid OpenAPI specification')

        except Exception as e:
            logger.error(f'Failed to load OpenAPI spec from file: {path} - Error: {e}')
            raise
