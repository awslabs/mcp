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

"""Genomics file search tool for the AWS HealthOmics MCP server."""

from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFileSearchRequest,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator import (
    GenomicsSearchOrchestrator,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional


async def search_genomics_files(
    ctx: Context,
    file_type: Optional[str] = Field(
        None,
        description='Optional file type filter. Valid types: fastq, fasta, fna, bam, cram, sam, vcf, gvcf, bcf, bed, gff, bai, crai, fai, dict, tbi, csi, bwa_amb, bwa_ann, bwa_bwt, bwa_pac, bwa_sa',
    ),
    search_terms: List[str] = Field(
        default_factory=list,
        description='List of search terms to match against file paths, tags and metadata. If empty, returns all files of the specified file type.',
    ),
    max_results: int = Field(
        100,
        description='Maximum number of results to return (1-10000)',
        ge=1,
        le=10000,
    ),
    include_associated_files: bool = Field(
        True,
        description='Whether to include associated files (e.g., BAM index files, FASTQ pairs) in the results',
    ),
    offset: int = Field(
        0,
        description='Number of results to skip for pagination (0-based offset), ignored if enable_storage_pagination is true',
        ge=0,
    ),
    continuation_token: Optional[str] = Field(
        None,
        description='Continuation token from previous search response for paginated results',
    ),
    enable_storage_pagination: bool = Field(
        False,
        description='Enable efficient storage-level pagination for large datasets (recommended for >1000 results)',
    ),
    pagination_buffer_size: int = Field(
        500,
        description='Buffer size for storage-level pagination (100-50000). Larger values improve ranking accuracy but use more memory.',
        ge=100,
        le=50000,
    ),
) -> Dict[str, Any]:
    """Search for genomics files across S3 buckets, HealthOmics sequence stores, and reference stores.

    This tool provides intelligent search capabilities with pattern matching, file association detection,
    and ranked results based on relevance scoring. It can find genomics files across multiple storage
    locations and automatically group related files together.

    Args:
        ctx: MCP context for error reporting
        file_type: Optional file type filter (e.g., 'fastq', 'bam', 'vcf')
        search_terms: List of search terms to match against file paths and tags
        max_results: Maximum number of results to return (default: 100, max: 10000)
        include_associated_files: Whether to include associated files in results (default: True)
        offset: Number of results to skip for pagination (0-based offset, default: 0), allows arbitray page skippig, ignored of enable_storage_pagination is true
        continuation_token: Continuation token from previous search response for paginated results
        enable_storage_pagination: Enable efficient storage-level pagination for large datasets
        pagination_buffer_size: Buffer size for storage-level pagination (affects ranking accuracy)

    Returns:
        Comprehensive dictionary containing:

        **Core Results:**
        - results: List of file result objects, each containing:
          - primary_file: Main genomics file with full metadata (path, file_type, size_bytes,
            size_human_readable, storage_class, last_modified, tags, source_system, metadata, file_info)
          - associated_files: List of related files (index files, paired reads, etc.) with same metadata structure
          - file_group: Summary of the file group (total_files, total_size_bytes, has_associations, association_types)
          - relevance_score: Numerical relevance score (0.0-1.0)
          - match_reasons: List of reasons why this file matched the search
          - ranking_info: Score breakdown and match quality assessment

        **Search Metadata:**
        - total_found: Total number of files found before pagination
        - returned_count: Number of results actually returned
        - search_duration_ms: Time taken for the search in milliseconds
        - storage_systems_searched: List of storage systems that were searched

        **Performance & Analytics:**
        - performance_metrics: Search efficiency statistics including results_per_second and truncation_ratio
        - search_statistics: Optional detailed search metrics if available
        - pagination: Pagination information including:
          - has_more: Boolean indicating if more results are available
          - next_offset: Offset value to use for the next page
          - continuation_token: Token to use for the next page (if applicable)
          - current_page: Current page number (if applicable)

        **Content Analysis:**
        - metadata: Analysis of the result set including:
          - file_type_distribution: Count of each file type found
          - source_system_distribution: Count of files from each storage system
          - association_summary: Statistics about file associations and groupings

    Raises:
        ValueError: If search parameters are invalid
        Exception: If search operations fail
    """
    try:
        logger.info(
            f'Starting genomics file search: file_type={file_type}, '
            f'search_terms={search_terms}, max_results={max_results}, '
            f'include_associated_files={include_associated_files}, '
            f'offset={offset}, continuation_token={continuation_token is not None}, '
            f'enable_storage_pagination={enable_storage_pagination}, '
            f'pagination_buffer_size={pagination_buffer_size}'
        )

        # Validate file_type parameter if provided
        if file_type:
            try:
                GenomicsFileType(file_type.lower())
            except ValueError:
                valid_types = [ft.value for ft in GenomicsFileType]
                error_message = (
                    f"Invalid file_type '{file_type}'. Valid types are: {', '.join(valid_types)}"
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        # Create search request
        search_request = GenomicsFileSearchRequest(
            file_type=file_type.lower() if file_type else None,
            search_terms=search_terms,
            max_results=max_results,
            include_associated_files=include_associated_files,
            offset=offset,
            continuation_token=continuation_token,
            enable_storage_pagination=enable_storage_pagination,
            pagination_buffer_size=pagination_buffer_size,
        )

        # Initialize search orchestrator from environment configuration
        try:
            orchestrator = GenomicsSearchOrchestrator.from_environment()
        except ValueError as e:
            error_message = f'Configuration error: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise

        # Execute the search - use paginated search if enabled
        try:
            if enable_storage_pagination:
                response = await orchestrator.search_paginated(search_request)
            else:
                response = await orchestrator.search(search_request)
        except Exception as e:
            error_message = f'Search execution failed: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            raise

        # Use the enhanced response if available, otherwise fall back to basic structure
        if hasattr(response, 'enhanced_response') and response.enhanced_response:
            result_dict = response.enhanced_response
        else:
            # Fallback to basic structure for compatibility
            result_dict = {
                'results': response.results,
                'total_found': response.total_found,
                'search_duration_ms': response.search_duration_ms,
                'storage_systems_searched': response.storage_systems_searched,
            }

        logger.info(
            f'Search completed successfully: found {response.total_found} files, '
            f'returning {len(response.results)} results in {response.search_duration_ms}ms'
        )

        return result_dict

    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        error_message = f'Unexpected error during genomics file search: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise Exception(error_message) from e


# Additional helper function for getting file type information
async def get_supported_file_types(ctx: Context) -> Dict[str, Any]:
    """Get information about supported genomics file types.

    Args:
        ctx: MCP context for error reporting

    Returns:
        Dictionary containing information about supported file types and their descriptions
    """
    try:
        file_type_info = {
            'sequence_files': {
                'fastq': 'FASTQ sequence files (raw sequencing reads)',
                'fasta': 'FASTA sequence files (reference sequences)',
                'fna': 'FASTA nucleic acid files (alternative extension)',
            },
            'alignment_files': {
                'bam': 'Binary Alignment Map files (compressed SAM)',
                'cram': 'Compressed Reference-oriented Alignment Map files',
                'sam': 'Sequence Alignment Map files (text format)',
            },
            'variant_files': {
                'vcf': 'Variant Call Format files',
                'gvcf': 'Genomic Variant Call Format files',
                'bcf': 'Binary Variant Call Format files',
            },
            'annotation_files': {
                'bed': 'Browser Extensible Data format files',
                'gff': 'General Feature Format files',
            },
            'index_files': {
                'bai': 'BAM index files',
                'crai': 'CRAM index files',
                'fai': 'FASTA index files',
                'dict': 'FASTA dictionary files',
                'tbi': 'Tabix index files (for VCF/GFF)',
                'csi': 'Coordinate-sorted index files',
            },
            'bwa_index_files': {
                'bwa_amb': 'BWA index ambiguous nucleotides file',
                'bwa_ann': 'BWA index annotations file',
                'bwa_bwt': 'BWA index Burrows-Wheeler transform file',
                'bwa_pac': 'BWA index packed sequence file',
                'bwa_sa': 'BWA index suffix array file',
            },
        }

        # Get all valid file types for validation
        all_types = []
        for category in file_type_info.values():
            all_types.extend(category.keys())

        return {
            'supported_file_types': file_type_info,
            'all_valid_types': sorted(all_types),
            'total_types_supported': len(all_types),
        }

    except Exception as e:
        error_message = f'Error retrieving supported file types: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise
