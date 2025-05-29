"""Implementation of the describe_schema tool."""

from botocore.client import BaseClient
from loguru import logger
from typing import Dict, Optional


async def describe_schema_impl(
    schemas_client: BaseClient,
    registry_name: str,
    schema_name: str,
    schema_version: Optional[str] = None,
) -> Dict:
    """Retrieve the schema definition for the specified schema version.

    Args:
        schemas_client: Boto3 schemas client instance
        registry_name: Registry name (e.g., "aws.events")
        schema_name: Name of the schema to retrieve
        schema_version: Version number of the schema

    Returns:
        Dict containing schema details including content and metadata

    Raises:
        Exception: If there's an error describing the schema
    """
    try:
        params = {'RegistryName': registry_name, 'SchemaName': schema_name}
        if schema_version is not None:
            params['SchemaVersion'] = schema_version

        response = schemas_client.describe_schema(**params)
        return {
            'SchemaName': response.get('SchemaName'),
            'SchemaArn': response.get('SchemaArn'),
            'SchemaVersion': response.get('SchemaVersion'),
            'Content': response.get('Content'),
            'LastModified': response.get('LastModified'),
        }
    except Exception as e:
        logger.error(f'Error describing schema: {str(e)}')
        raise
