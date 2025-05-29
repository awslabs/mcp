"""Implementation of the list_registries tool."""

from botocore.client import BaseClient
from loguru import logger
from typing import Dict, Optional


async def list_registries_impl(
    schemas_client: BaseClient,
    registry_name_prefix: Optional[str] = None,
    scope: Optional[str] = None,
    limit: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict:
    """Lists the registries in your account.

    Args:
        schemas_client: Boto3 schemas client instance
        registry_name_prefix: Limits results to registry names starting with this prefix
        scope: Can be 'Local' or 'AWS' to limit responses
        limit: Maximum number of results to return (0-100)
        next_token: Token from previous operation for pagination

    Returns:
        Dict containing registries list and next token

    Raises:
        Exception: If there's an error listing registries
    """
    try:
        params = {}
        if limit is not None:
            params['Limit'] = limit
        if next_token is not None:
            params['NextToken'] = next_token
        if scope is not None:
            params['Scope'] = scope
        if registry_name_prefix is not None:
            params['RegistryNamePrefix'] = registry_name_prefix

        response = schemas_client.list_registries(**params)
        return {
            'Registries': response.get('Registries', []),
            'NextToken': response.get('NextToken'),
        }
    except Exception as e:
        logger.error(f'Error listing registries: {str(e)}')
        raise
