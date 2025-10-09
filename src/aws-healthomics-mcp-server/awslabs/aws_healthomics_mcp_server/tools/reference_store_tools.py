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

"""Reference store tools for the AWS HealthOmics MCP server."""

import botocore.exceptions
from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


async def list_aho_reference_stores(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of reference stores to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics reference stores.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of reference stores to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing reference stores list and pagination info

    Raises:
        Exception: If there's an error listing reference stores
    """
    try:
        client = get_omics_client()

        params = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        response = client.list_reference_stores(**params)

        return {
            'referenceStores': response.get('referenceStores', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('referenceStores', [])),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list reference stores: {error_code} - {error_message}')

        raise Exception(f'Failed to list reference stores: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing reference stores: {str(e)}')
        raise Exception(f'Failed to list reference stores: {str(e)}')


async def get_aho_reference_store(
    ctx: Context,
    reference_store_id: str = Field(
        ...,
        description='ID of the reference store to retrieve',
    ),
) -> Dict[str, Any]:
    """Get detailed information about a specific reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: ID of the reference store

    Returns:
        Dictionary containing reference store details

    Raises:
        Exception: If there's an error retrieving reference store information
    """
    try:
        client = get_omics_client()

        response = client.get_reference_store(id=reference_store_id)

        return {
            'referenceStore': {
                'id': response.get('id'),
                'arn': response.get('arn'),
                'name': response.get('name'),
                'description': response.get('description'),
                'sseConfig': response.get('sseConfig'),
                'creationTime': response.get('creationTime'),
                'status': response.get('status'),
                'statusMessage': response.get('statusMessage'),
            }
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get reference store: {error_code} - {error_message}')

        raise Exception(f'Failed to get reference store: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting reference store: {str(e)}')
        raise Exception(f'Failed to get reference store: {str(e)}')


async def list_aho_references(
    ctx: Context,
    reference_store_id: str = Field(
        ...,
        description='ID of the reference store to list references from',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of references to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List references in a HealthOmics reference store.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: ID of the reference store
        max_results: Maximum number of references to return
        next_token: Token for pagination

    Returns:
        Dictionary containing references list and pagination info

    Raises:
        Exception: If there's an error listing references
    """
    try:
        client = get_omics_client()

        params = {'referenceStoreId': reference_store_id, 'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        response = client.list_references(**params)

        return {
            'references': response.get('references', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('references', [])),
            'referenceStoreId': reference_store_id,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list references: {error_code} - {error_message}')

        raise Exception(f'Failed to list references: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing references: {str(e)}')
        raise Exception(f'Failed to list references: {str(e)}')


async def get_aho_reference(
    ctx: Context,
    reference_store_id: str = Field(
        ...,
        description='ID of the reference store',
    ),
    reference_id: str = Field(
        ...,
        description='ID of the reference to retrieve',
    ),
) -> Dict[str, Any]:
    """Get detailed metadata for a specific reference.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: ID of the reference store
        reference_id: ID of the reference

    Returns:
        Dictionary containing reference metadata

    Raises:
        Exception: If there's an error retrieving reference metadata
    """
    try:
        client = get_omics_client()

        response = client.get_reference_metadata(
            referenceStoreId=reference_store_id, id=reference_id
        )

        return {
            'reference': {
                'id': response.get('id'),
                'arn': response.get('arn'),
                'referenceStoreId': response.get('referenceStoreId'),
                'md5': response.get('md5'),
                'status': response.get('status'),
                'name': response.get('name'),
                'description': response.get('description'),
                'creationTime': response.get('creationTime'),
                'updateTime': response.get('updateTime'),
                'files': response.get('files'),
            },
            'referenceStoreId': reference_store_id,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get reference metadata: {error_code} - {error_message}')

        raise Exception(f'Failed to get reference metadata: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting reference metadata: {str(e)}')
        raise Exception(f'Failed to get reference metadata: {str(e)}')


async def start_aho_reference_import_job(
    ctx: Context,
    reference_store_id: str = Field(
        ...,
        description='ID of the reference store to import into',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM role to use for the import',
    ),
    sources: list = Field(
        ...,
        description='List of reference source files to import from S3',
    ),
    client_token: Optional[str] = Field(
        None,
        description='Client token for idempotency',
    ),
) -> Dict[str, Any]:
    """Start a reference import job from S3 sources.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: ID of the reference store
        role_arn: ARN of the IAM role for the import
        sources: List of reference source file configurations
        client_token: Client token for idempotency

    Returns:
        Dictionary containing import job information

    Raises:
        Exception: If there's an error starting the import job
    """
    try:
        client = get_omics_client()

        params = {'referenceStoreId': reference_store_id, 'roleArn': role_arn, 'sources': sources}

        if client_token:
            params['clientToken'] = client_token

        response = client.start_reference_import_job(**params)

        return {
            'id': response.get('id'),
            'referenceStoreId': response.get('referenceStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'creationTime': response.get('creationTime'),
            'sources': sources,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to start reference import job: {error_code} - {error_message}')

        raise Exception(f'Failed to start reference import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error starting reference import job: {str(e)}')
        raise Exception(f'Failed to start reference import job: {str(e)}')


async def get_aho_reference_import_job(
    ctx: Context,
    reference_store_id: str = Field(
        ...,
        description='ID of the reference store',
    ),
    import_job_id: str = Field(
        ...,
        description='ID of the import job',
    ),
) -> Dict[str, Any]:
    """Get the status and details of a reference import job.

    Args:
        ctx: MCP context for error reporting
        reference_store_id: ID of the reference store
        import_job_id: ID of the import job

    Returns:
        Dictionary containing import job status and details

    Raises:
        Exception: If there's an error retrieving import job status
    """
    try:
        client = get_omics_client()

        response = client.get_reference_import_job(
            referenceStoreId=reference_store_id, id=import_job_id
        )

        return {
            'id': response.get('id'),
            'referenceStoreId': response.get('referenceStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'statusMessage': response.get('statusMessage'),
            'creationTime': response.get('creationTime'),
            'completionTime': response.get('completionTime'),
            'sources': response.get('sources', []),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get reference import job: {error_code} - {error_message}')

        raise Exception(f'Failed to get reference import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting reference import job: {str(e)}')
        raise Exception(f'Failed to get reference import job: {str(e)}')
