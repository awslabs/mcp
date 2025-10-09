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

"""Annotation store tools for the AWS HealthOmics MCP server."""

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
from typing import Any, Dict, List, Optional


async def list_aho_annotation_stores(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of annotation stores to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics annotation stores.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of annotation stores to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing annotation stores list and pagination info

    Raises:
        Exception: If there's an error listing annotation stores
    """
    try:
        client = get_omics_client()

        params = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        response = client.list_annotation_stores(**params)

        return {
            'annotationStores': response.get('annotationStores', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('annotationStores', [])),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list annotation stores: {error_code} - {error_message}')

        raise Exception(f'Failed to list annotation stores: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing annotation stores: {str(e)}')
        raise Exception(f'Failed to list annotation stores: {str(e)}')


async def get_aho_annotation_store(
    ctx: Context,
    annotation_store_id: str = Field(
        ...,
        description='ID of the annotation store to retrieve',
    ),
) -> Dict[str, Any]:
    """Get detailed information about a specific annotation store.

    Args:
        ctx: MCP context for error reporting
        annotation_store_id: ID of the annotation store

    Returns:
        Dictionary containing annotation store details

    Raises:
        Exception: If there's an error retrieving annotation store information
    """
    try:
        client = get_omics_client()

        response = client.get_annotation_store(name=annotation_store_id)

        return {
            'annotationStore': {
                'id': response.get('id'),
                'reference': response.get('reference'),
                'status': response.get('status'),
                'statusMessage': response.get('statusMessage'),
                'storeArn': response.get('storeArn'),
                'name': response.get('name'),
                'description': response.get('description'),
                'sseConfig': response.get('sseConfig'),
                'creationTime': response.get('creationTime'),
                'updateTime': response.get('updateTime'),
                'tags': response.get('tags', {}),
                'storeFormat': response.get('storeFormat'),
                'storeOptions': response.get('storeOptions'),
            }
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get annotation store: {error_code} - {error_message}')

        raise Exception(f'Failed to get annotation store: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting annotation store: {str(e)}')
        raise Exception(f'Failed to get annotation store: {str(e)}')


async def search_aho_annotations(
    ctx: Context,
    annotation_store_id: str = Field(
        ...,
        description='ID of the annotation store to search',
    ),
    gene: Optional[str] = Field(
        None,
        description='Gene name to search for annotations (e.g., BRCA1)',
    ),
    chromosome: Optional[str] = Field(
        None,
        description='Chromosome to search (e.g., chr1, 1)',
    ),
    start_position: Optional[int] = Field(
        None,
        description='Start position for genomic range search',
        ge=1,
    ),
    end_position: Optional[int] = Field(
        None,
        description='End position for genomic range search',
        ge=1,
    ),
    annotation_type: Optional[str] = Field(
        None,
        description='Type of annotation to search for',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of annotations to return',
        ge=1,
        le=1000,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """Search for annotations in a HealthOmics annotation store.

    Args:
        ctx: MCP context for error reporting
        annotation_store_id: ID of the annotation store
        gene: Gene name to search for
        chromosome: Chromosome to search
        start_position: Start position for range search
        end_position: End position for range search
        annotation_type: Type of annotation to search for
        max_results: Maximum number of annotations to return
        next_token: Token for pagination

    Returns:
        Dictionary containing search results

    Raises:
        Exception: If there's an error searching annotations
    """
    try:
        client = get_omics_client()

        # Build search criteria
        filter_criteria = {}

        if gene:
            filter_criteria['gene'] = {'eq': gene}

        if chromosome:
            # Normalize chromosome format
            if not chromosome.startswith('chr'):
                chromosome = f'chr{chromosome}'
            filter_criteria['contigName'] = {'eq': chromosome}

        if start_position is not None and end_position is not None:
            filter_criteria['start'] = {'gte': start_position}
            filter_criteria['end'] = {'lte': end_position}
        elif start_position is not None:
            filter_criteria['start'] = {'gte': start_position}
        elif end_position is not None:
            filter_criteria['end'] = {'lte': end_position}

        if annotation_type:
            filter_criteria['annotationType'] = {'eq': annotation_type}

        params = {'annotationStoreId': annotation_store_id, 'maxResults': max_results}

        if filter_criteria:
            params['filter'] = filter_criteria

        if next_token:
            params['nextToken'] = next_token

        response = client.search_annotations(**params)

        return {
            'annotations': response.get('annotations', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('annotations', [])),
            'annotationStoreId': annotation_store_id,
            'searchCriteria': {
                'gene': gene,
                'chromosome': chromosome,
                'startPosition': start_position,
                'endPosition': end_position,
                'annotationType': annotation_type,
            },
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to search annotations: {error_code} - {error_message}')

        raise Exception(f'Failed to search annotations: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error searching annotations: {str(e)}')
        raise Exception(f'Failed to search annotations: {str(e)}')


async def start_aho_annotation_import_job(
    ctx: Context,
    annotation_store_id: str = Field(
        ...,
        description='ID of the annotation store to import into',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM role to use for the import',
    ),
    items: List[Dict[str, Any]] = Field(
        ...,
        description='List of annotation files to import from S3',
    ),
    run_left_normalization: bool = Field(
        False,
        description='Whether to run left normalization on annotations',
    ),
    client_token: Optional[str] = Field(
        None,
        description='Client token for idempotency',
    ),
) -> Dict[str, Any]:
    """Start an annotation import job from S3 files.

    Args:
        ctx: MCP context for error reporting
        annotation_store_id: ID of the annotation store
        role_arn: ARN of the IAM role for the import
        items: List of annotation file configurations
        run_left_normalization: Whether to run left normalization
        client_token: Client token for idempotency

    Returns:
        Dictionary containing import job information

    Raises:
        Exception: If there's an error starting the import job
    """
    try:
        client = get_omics_client()

        params = {
            'annotationStoreId': annotation_store_id,
            'roleArn': role_arn,
            'items': items,
            'runLeftNormalization': run_left_normalization,
        }

        if client_token:
            params['clientToken'] = client_token

        response = client.start_annotation_import_job(**params)

        return {
            'id': response.get('id'),
            'annotationStoreId': response.get('annotationStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'creationTime': response.get('creationTime'),
            'runLeftNormalization': run_left_normalization,
            'items': items,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to start annotation import job: {error_code} - {error_message}')

        raise Exception(f'Failed to start annotation import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error starting annotation import job: {str(e)}')
        raise Exception(f'Failed to start annotation import job: {str(e)}')


async def get_aho_annotation_import_job(
    ctx: Context,
    annotation_import_job_id: str = Field(
        ...,
        description='ID of the annotation import job',
    ),
) -> Dict[str, Any]:
    """Get the status and details of an annotation import job.

    Args:
        ctx: MCP context for error reporting
        annotation_import_job_id: ID of the annotation import job

    Returns:
        Dictionary containing import job status and details

    Raises:
        Exception: If there's an error retrieving import job status
    """
    try:
        client = get_omics_client()

        response = client.get_annotation_import_job(id=annotation_import_job_id)

        return {
            'id': response.get('id'),
            'annotationStoreId': response.get('annotationStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'statusMessage': response.get('statusMessage'),
            'creationTime': response.get('creationTime'),
            'updateTime': response.get('updateTime'),
            'completionTime': response.get('completionTime'),
            'items': response.get('items', []),
            'runLeftNormalization': response.get('runLeftNormalization'),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get annotation import job: {error_code} - {error_message}')

        raise Exception(f'Failed to get annotation import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting annotation import job: {str(e)}')
        raise Exception(f'Failed to get annotation import job: {str(e)}')
