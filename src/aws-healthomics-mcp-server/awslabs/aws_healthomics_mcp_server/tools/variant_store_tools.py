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

"""Variant store tools for the AWS HealthOmics MCP server."""

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


async def list_aho_variant_stores(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of variant stores to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics variant stores.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of variant stores to return
        next_token: Token for pagination from a previous response

    Returns:
        Dictionary containing variant stores list and pagination info

    Raises:
        Exception: If there's an error listing variant stores
    """
    try:
        client = get_omics_client()

        params = {'maxResults': max_results}

        if next_token:
            params['nextToken'] = next_token

        response = client.list_variant_stores(**params)

        return {
            'variantStores': response.get('variantStores', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('variantStores', [])),
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to list variant stores: {error_code} - {error_message}')

        raise Exception(f'Failed to list variant stores: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error listing variant stores: {str(e)}')
        raise Exception(f'Failed to list variant stores: {str(e)}')


async def get_aho_variant_store(
    ctx: Context,
    variant_store_id: str = Field(
        ...,
        description='ID of the variant store to retrieve',
    ),
) -> Dict[str, Any]:
    """Get detailed information about a specific variant store.

    Args:
        ctx: MCP context for error reporting
        variant_store_id: ID of the variant store

    Returns:
        Dictionary containing variant store details

    Raises:
        Exception: If there's an error retrieving variant store information
    """
    try:
        client = get_omics_client()

        response = client.get_variant_store(name=variant_store_id)

        return {
            'variantStore': {
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
            }
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to get variant store: {error_code} - {error_message}')

        raise Exception(f'Failed to get variant store: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting variant store: {str(e)}')
        raise Exception(f'Failed to get variant store: {str(e)}')


async def search_aho_variants(
    ctx: Context,
    variant_store_id: str = Field(
        ...,
        description='ID of the variant store to search',
    ),
    gene: Optional[str] = Field(
        None,
        description='Gene name to search for variants (e.g., BRCA1)',
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
    variant_type: Optional[str] = Field(
        None,
        description='Type of variant (e.g., SNV, INDEL, CNV)',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of variants to return',
        ge=1,
        le=1000,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
) -> Dict[str, Any]:
    """Search for variants in a HealthOmics variant store.

    Args:
        ctx: MCP context for error reporting
        variant_store_id: ID of the variant store
        gene: Gene name to search for
        chromosome: Chromosome to search
        start_position: Start position for range search
        end_position: End position for range search
        variant_type: Type of variant to search for
        max_results: Maximum number of variants to return
        next_token: Token for pagination

    Returns:
        Dictionary containing search results

    Raises:
        Exception: If there's an error searching variants
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

        if variant_type:
            filter_criteria['variantType'] = {'eq': variant_type.upper()}

        params = {'variantStoreId': variant_store_id, 'maxResults': max_results}

        if filter_criteria:
            params['filter'] = filter_criteria

        if next_token:
            params['nextToken'] = next_token

        response = client.search_variants(**params)

        return {
            'variants': response.get('variants', []),
            'nextToken': response.get('nextToken'),
            'totalCount': len(response.get('variants', [])),
            'variantStoreId': variant_store_id,
            'searchCriteria': {
                'gene': gene,
                'chromosome': chromosome,
                'startPosition': start_position,
                'endPosition': end_position,
                'variantType': variant_type,
            },
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to search variants: {error_code} - {error_message}')

        raise Exception(f'Failed to search variants: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error searching variants: {str(e)}')
        raise Exception(f'Failed to search variants: {str(e)}')


async def count_aho_variants(
    ctx: Context,
    variant_store_id: str = Field(
        ...,
        description='ID of the variant store to count variants in',
    ),
    gene: Optional[str] = Field(
        None,
        description='Gene name to count variants for',
    ),
    chromosome: Optional[str] = Field(
        None,
        description='Chromosome to count variants on',
    ),
    variant_type: Optional[str] = Field(
        None,
        description='Type of variant to count',
    ),
) -> Dict[str, Any]:
    """Count variants in a HealthOmics variant store with optional filters.

    Args:
        ctx: MCP context for error reporting
        variant_store_id: ID of the variant store
        gene: Gene name to filter by
        chromosome: Chromosome to filter by
        variant_type: Type of variant to filter by

    Returns:
        Dictionary containing variant count information

    Raises:
        Exception: If there's an error counting variants
    """
    try:
        # Use search with a large max_results to get an accurate count
        # In practice, this might need to be implemented differently
        # depending on the actual HealthOmics API capabilities

        search_result = await search_aho_variants(
            ctx=ctx,
            variant_store_id=variant_store_id,
            gene=gene,
            chromosome=chromosome,
            variant_type=variant_type,
            max_results=1000,  # Use large number for counting
        )

        # If there's a nextToken, we need to continue searching to get accurate count
        total_count = len(search_result['variants'])
        has_more = 'nextToken' in search_result and search_result['nextToken']

        return {
            'variantCount': total_count,
            'hasMoreResults': has_more,
            'variantStoreId': variant_store_id,
            'countCriteria': {'gene': gene, 'chromosome': chromosome, 'variantType': variant_type},
            'note': 'Count may be partial if hasMoreResults is true',
        }

    except Exception as e:
        logger.error(f'Unexpected error counting variants: {str(e)}')
        raise Exception(f'Failed to count variants: {str(e)}')


async def start_aho_variant_import_job(
    ctx: Context,
    variant_store_id: str = Field(
        ...,
        description='ID of the variant store to import into',
    ),
    role_arn: str = Field(
        ...,
        description='ARN of the IAM role to use for the import',
    ),
    items: List[Dict[str, Any]] = Field(
        ...,
        description='List of VCF files to import from S3',
    ),
    run_left_normalization: bool = Field(
        False,
        description='Whether to run left normalization on variants',
    ),
    client_token: Optional[str] = Field(
        None,
        description='Client token for idempotency',
    ),
) -> Dict[str, Any]:
    """Start a variant import job from S3 VCF files.

    Args:
        ctx: MCP context for error reporting
        variant_store_id: ID of the variant store
        role_arn: ARN of the IAM role for the import
        items: List of VCF file configurations
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
            'variantStoreId': variant_store_id,
            'roleArn': role_arn,
            'items': items,
            'runLeftNormalization': run_left_normalization,
        }

        if client_token:
            params['clientToken'] = client_token

        response = client.start_variant_import_job(**params)

        return {
            'id': response.get('id'),
            'variantStoreId': response.get('variantStoreId'),
            'roleArn': response.get('roleArn'),
            'status': response.get('status'),
            'creationTime': response.get('creationTime'),
            'runLeftNormalization': run_left_normalization,
            'items': items,
        }

    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        logger.error(f'Failed to start variant import job: {error_code} - {error_message}')

        raise Exception(f'Failed to start variant import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error starting variant import job: {str(e)}')
        raise Exception(f'Failed to start variant import job: {str(e)}')


async def get_aho_variant_import_job(
    ctx: Context,
    variant_import_job_id: str = Field(
        ...,
        description='ID of the variant import job',
    ),
) -> Dict[str, Any]:
    """Get the status and details of a variant import job.

    Args:
        ctx: MCP context for error reporting
        variant_import_job_id: ID of the variant import job

    Returns:
        Dictionary containing import job status and details

    Raises:
        Exception: If there's an error retrieving import job status
    """
    try:
        client = get_omics_client()

        response = client.get_variant_import_job(id=variant_import_job_id)

        return {
            'id': response.get('id'),
            'variantStoreId': response.get('variantStoreId'),
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

        logger.error(f'Failed to get variant import job: {error_code} - {error_message}')

        raise Exception(f'Failed to get variant import job: {error_code} - {error_message}')
    except Exception as e:
        logger.error(f'Unexpected error getting variant import job: {str(e)}')
        raise Exception(f'Failed to get variant import job: {str(e)}')
