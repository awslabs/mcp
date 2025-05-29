"""Implementation of the search_schema tool."""

from botocore.client import BaseClient
from loguru import logger
from typing import Dict, Optional


async def search_schema_impl(
    schemas_client: BaseClient,
    keywords: str,
    registry_name: str,
    limit: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict:
    """Search for schemas in a registry using keywords.

    Args:
        schemas_client: Boto3 schemas client instance
        keywords: Keywords to search for
        registry_name: Registry name to search in (e.g., "aws.events")
        limit: Maximum number of results to return (0-100)
        next_token: Token from previous operation for pagination

    Returns:
        Dict containing schemas list and next token

    Raises:
        Exception: If there's an error searching schemas
    """
    try:
        params = {'Keywords': keywords, 'RegistryName': registry_name}
        if limit is not None:
            params['Limit'] = str(limit)
        if next_token is not None:
            params['NextToken'] = next_token

        response = schemas_client.search_schemas(**params)
        return {
            'Schemas': response.get('Schemas', []),
            'NextToken': response.get('NextToken'),
        }
    except Exception as e:
        logger.error(f'Error searching schemas: {str(e)}')
        raise
