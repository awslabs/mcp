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

"""Genomics search orchestrator that coordinates searches across multiple storage systems."""

import asyncio
import secrets
import time
from awslabs.aws_healthomics_mcp_server.consts import (
    BUFFER_EFFICIENCY_HIGH_THRESHOLD,
    BUFFER_EFFICIENCY_LOW_THRESHOLD,
    COMPLEXITY_MULTIPLIER_ASSOCIATED_FILES,
    COMPLEXITY_MULTIPLIER_BUFFER_OVERFLOW,
    COMPLEXITY_MULTIPLIER_FILE_TYPE_FILTER,
    COMPLEXITY_MULTIPLIER_HIGH_EFFICIENCY,
    COMPLEXITY_MULTIPLIER_LOW_EFFICIENCY,
    CURSOR_PAGINATION_BUFFER_THRESHOLD,
    CURSOR_PAGINATION_PAGE_THRESHOLD,
    MAX_SEARCH_RESULTS_LIMIT,
    S3_CACHE_CLEANUP_PROBABILITY,
)
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileSearchRequest,
    GenomicsFileSearchResponse,
    GlobalContinuationToken,
    PaginationCacheEntry,
    PaginationMetrics,
    SearchConfig,
    StoragePaginationRequest,
    StoragePaginationResponse,
)
from awslabs.aws_healthomics_mcp_server.search.file_association_engine import FileAssociationEngine
from awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine import (
    HealthOmicsSearchEngine,
)
from awslabs.aws_healthomics_mcp_server.search.json_response_builder import JsonResponseBuilder
from awslabs.aws_healthomics_mcp_server.search.result_ranker import ResultRanker
from awslabs.aws_healthomics_mcp_server.search.s3_search_engine import S3SearchEngine
from awslabs.aws_healthomics_mcp_server.search.scoring_engine import ScoringEngine
from awslabs.aws_healthomics_mcp_server.utils.search_config import get_genomics_search_config
from loguru import logger

# Import here to avoid circular imports
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple


if TYPE_CHECKING:
    from awslabs.aws_healthomics_mcp_server.search.s3_search_engine import S3SearchEngine


class GenomicsSearchOrchestrator:
    """Orchestrates genomics file searches across multiple storage systems."""

    def __init__(self, config: SearchConfig, s3_engine: Optional['S3SearchEngine'] = None):
        """Initialize the search orchestrator.

        Args:
            config: Search configuration containing settings for all storage systems
            s3_engine: Optional pre-configured S3SearchEngine (for testing)
        """
        self.config = config

        # Use provided S3 engine (for testing) or create from environment with validation
        if s3_engine is not None:
            self.s3_engine = s3_engine
        else:
            try:
                self.s3_engine = S3SearchEngine.from_environment()
            except ValueError as e:
                logger.warning(
                    f'S3SearchEngine initialization failed: {e}. S3 search will be disabled.'
                )
                self.s3_engine = None

        self.healthomics_engine = HealthOmicsSearchEngine(config)
        self.association_engine = FileAssociationEngine()
        self.scoring_engine = ScoringEngine()
        self.result_ranker = ResultRanker()
        self.json_builder = JsonResponseBuilder()

    @classmethod
    def from_environment(cls) -> 'GenomicsSearchOrchestrator':
        """Create a GenomicsSearchOrchestrator using configuration from environment variables.

        Returns:
            GenomicsSearchOrchestrator instance configured from environment

        Raises:
            ValueError: If configuration is invalid
        """
        config = get_genomics_search_config()
        return cls(config)

    async def search(self, request: GenomicsFileSearchRequest) -> GenomicsFileSearchResponse:
        """Coordinate searches across multiple storage systems and return ranked results.

        Args:
            request: Search request containing search parameters

        Returns:
            GenomicsFileSearchResponse with ranked results and metadata

        Raises:
            ValueError: If search parameters are invalid
            Exception: If search operations fail
        """
        start_time = time.time()
        logger.info(f'Starting genomics file search with parameters: {request}')

        try:
            # Validate search request
            self._validate_search_request(request)

            # Execute parallel searches across storage systems
            all_files = await self._execute_parallel_searches(request)
            logger.info(f'Found {len(all_files)} total files across all storage systems')

            # Deduplicate results based on file paths
            deduplicated_files = self._deduplicate_files(all_files)
            logger.info(f'After deduplication: {len(deduplicated_files)} unique files')

            # Extract HealthOmics associated files and add them to the file list
            all_files_with_associations = self._extract_healthomics_associations(
                deduplicated_files
            )
            logger.info(
                f'After extracting HealthOmics associations: {len(all_files_with_associations)} total files'
            )

            # Apply file associations and grouping
            file_groups = self.association_engine.find_associations(all_files_with_associations)
            logger.info(f'Created {len(file_groups)} file groups with associations')

            # Score results
            scored_results = await self._score_results(
                file_groups,
                request.file_type,
                request.search_terms,
                request.include_associated_files,
            )

            # Rank results by relevance score
            ranked_results = self.result_ranker.rank_results(scored_results)

            # Apply result limits and pagination
            limited_results = self.result_ranker.apply_pagination(
                ranked_results, request.max_results, request.offset
            )

            # Get ranking statistics
            ranking_stats = self.result_ranker.get_ranking_statistics(ranked_results)

            # Build comprehensive JSON response
            search_duration_ms = int((time.time() - start_time) * 1000)
            storage_systems_searched = self._get_searched_storage_systems()

            pagination_info = {
                'offset': request.offset,
                'limit': request.max_results,
                'total_available': len(ranked_results),
                'has_more': (request.offset + len(limited_results)) < len(ranked_results),
                'next_offset': request.offset + len(limited_results)
                if (request.offset + len(limited_results)) < len(ranked_results)
                else None,
                'continuation_token': request.continuation_token,  # Pass through for now
            }

            response_dict = self.json_builder.build_search_response(
                results=limited_results,
                total_found=len(scored_results),
                search_duration_ms=search_duration_ms,
                storage_systems_searched=storage_systems_searched,
                search_statistics=ranking_stats,
                pagination_info=pagination_info,
            )

            # Create GenomicsFileSearchResponse object for compatibility
            response = GenomicsFileSearchResponse(
                results=response_dict['results'],
                total_found=response_dict['total_found'],
                search_duration_ms=response_dict['search_duration_ms'],
                storage_systems_searched=response_dict['storage_systems_searched'],
                enhanced_response=response_dict,
            )

            logger.info(
                f'Search completed in {search_duration_ms}ms, returning {len(limited_results)} results'
            )
            return response

        except Exception as e:
            search_duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f'Search failed after {search_duration_ms}ms: {e}')
            raise

    async def search_paginated(
        self, request: GenomicsFileSearchRequest
    ) -> GenomicsFileSearchResponse:
        """Coordinate paginated searches across multiple storage systems with ranking-aware pagination.

        This method implements:
        1. Multi-storage pagination coordination with buffer management
        2. Ranking-aware pagination to maintain consistent results across pages
        3. Global continuation token management across all storage systems
        4. Result ranking with pagination edge cases and score thresholds

        Args:
            request: Search request containing search parameters and pagination settings

        Returns:
            GenomicsFileSearchResponse with paginated results and continuation tokens

        Raises:
            ValueError: If search parameters are invalid
            Exception: If search operations fail
        """
        from awslabs.aws_healthomics_mcp_server.models import (
            GlobalContinuationToken,
            StoragePaginationRequest,
        )

        start_time = time.time()
        logger.info(f'Starting paginated genomics file search with parameters: {request}')

        try:
            # Validate search request
            self._validate_search_request(request)

            # Parse global continuation token
            global_token = GlobalContinuationToken()
            if request.continuation_token:
                try:
                    global_token = GlobalContinuationToken.decode(request.continuation_token)
                except ValueError as e:
                    logger.warning(f'Invalid continuation token, starting fresh search: {e}')
                    global_token = GlobalContinuationToken()

            # Create pagination metrics if enabled
            metrics = None
            if self.config.enable_pagination_metrics:
                metrics = self._create_pagination_metrics(global_token.page_number, start_time)

            # Check pagination cache
            cache_key = self._create_pagination_cache_key(request, global_token.page_number)
            cached_state = self._get_cached_pagination_state(cache_key)

            # Optimize buffer size based on request and historical metrics
            optimized_buffer_size = self._optimize_buffer_size(
                request, cached_state.metrics if cached_state else None
            )

            # Create storage pagination request with optimized buffer size
            storage_pagination_request = StoragePaginationRequest(
                max_results=optimized_buffer_size,
                continuation_token=request.continuation_token,
                buffer_size=optimized_buffer_size,
            )

            # Execute parallel paginated searches across storage systems
            (
                all_files,
                next_global_token,
                total_scanned,
            ) = await self._execute_parallel_paginated_searches(
                request, storage_pagination_request, global_token
            )
            logger.info(
                f'Found {len(all_files)} total files across all storage systems (scanned {total_scanned})'
            )

            # Deduplicate results based on file paths
            deduplicated_files = self._deduplicate_files(all_files)
            logger.info(f'After deduplication: {len(deduplicated_files)} unique files')

            # Extract HealthOmics associated files and add them to the file list
            all_files_with_associations = self._extract_healthomics_associations(
                deduplicated_files
            )
            logger.info(
                f'After extracting HealthOmics associations: {len(all_files_with_associations)} total files'
            )

            # Apply file associations and grouping
            file_groups = self.association_engine.find_associations(all_files_with_associations)
            logger.info(f'Created {len(file_groups)} file groups with associations')

            # Score results
            scored_results = await self._score_results(
                file_groups,
                request.file_type,
                request.search_terms,
                request.include_associated_files,
            )

            # Rank results by relevance score with pagination awareness
            ranked_results = self.result_ranker.rank_results(scored_results)

            # Apply score threshold filtering if we have a continuation token
            if global_token.last_score_threshold is not None:
                ranked_results = [
                    result
                    for result in ranked_results
                    if result.relevance_score <= global_token.last_score_threshold
                ]
                logger.debug(
                    f'Applied score threshold {global_token.last_score_threshold}: {len(ranked_results)} results remain'
                )

            # Apply result limits for this page
            limited_results = ranked_results[: request.max_results]

            # Determine if there are more results and set score threshold
            has_more_results = len(ranked_results) > request.max_results or (
                next_global_token and next_global_token.has_more_pages()
            )

            # Update score threshold for next page
            if has_more_results and limited_results:
                last_score = limited_results[-1].relevance_score
                if next_global_token:
                    next_global_token.last_score_threshold = last_score
                    next_global_token.total_results_seen = global_token.total_results_seen + len(
                        limited_results
                    )

            # Get ranking statistics
            ranking_stats = self.result_ranker.get_ranking_statistics(ranked_results)

            # Build comprehensive JSON response
            search_duration_ms = int((time.time() - start_time) * 1000)
            storage_systems_searched = self._get_searched_storage_systems()

            # Create next continuation token
            next_continuation_token = None
            if has_more_results and next_global_token:
                next_continuation_token = next_global_token.encode()

            # Update metrics if enabled
            if self.config.enable_pagination_metrics and metrics:
                metrics.total_results_fetched = len(limited_results)
                metrics.total_objects_scanned = total_scanned
                metrics.search_duration_ms = search_duration_ms
                if len(all_files) > optimized_buffer_size:
                    metrics.buffer_overflows = 1

            # Cache pagination state for future requests
            if self.config.pagination_cache_ttl_seconds > 0:
                from awslabs.aws_healthomics_mcp_server.models import PaginationCacheEntry

                cache_entry = PaginationCacheEntry(
                    search_key=cache_key,
                    page_number=global_token.page_number + 1,
                    score_threshold=global_token.last_score_threshold,
                    storage_tokens=next_global_token.s3_tokens if next_global_token else {},
                    metrics=metrics,
                )
                self._cache_pagination_state(cache_key, cache_entry)

            # Clean up expired cache entries periodically (reduced frequency due to size-based cleanup)
            if (
                secrets.randbelow(100) == 0
            ):  # Probability defined by PAGINATION_CACHE_CLEANUP_PROBABILITY
                try:
                    self.cleanup_expired_pagination_cache()
                except Exception as e:
                    logger.debug(f'Pagination cache cleanup failed: {e}')

            pagination_info = {
                'offset': request.offset,
                'limit': request.max_results,
                'total_available': len(ranked_results),
                'has_more': has_more_results,
                'next_offset': None,  # Not applicable for storage-level pagination
                'continuation_token': next_continuation_token,
                'storage_level_pagination': True,
                'buffer_size': optimized_buffer_size,
                'original_buffer_size': request.pagination_buffer_size,
                'total_scanned': total_scanned,
                'page_number': global_token.page_number + 1,
                'cursor_pagination_available': self._should_use_cursor_pagination(
                    request, global_token
                ),
                'metrics': metrics.to_dict()
                if metrics and self.config.enable_pagination_metrics
                else None,
            }

            response_dict = self.json_builder.build_search_response(
                results=limited_results,
                total_found=len(scored_results),
                search_duration_ms=search_duration_ms,
                storage_systems_searched=storage_systems_searched,
                search_statistics=ranking_stats,
                pagination_info=pagination_info,
            )

            # Create GenomicsFileSearchResponse object for compatibility
            response = GenomicsFileSearchResponse(
                results=response_dict['results'],
                total_found=response_dict['total_found'],
                search_duration_ms=response_dict['search_duration_ms'],
                storage_systems_searched=response_dict['storage_systems_searched'],
                enhanced_response=response_dict,
            )

            logger.info(
                f'Paginated search completed in {search_duration_ms}ms, returning {len(limited_results)} results, '
                f'has_more: {has_more_results}'
            )
            return response

        except Exception as e:
            search_duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f'Paginated search failed after {search_duration_ms}ms: {e}')
            raise

    def _validate_search_request(self, request: GenomicsFileSearchRequest) -> None:
        """Validate the search request parameters.

        Args:
            request: Search request to validate

        Raises:
            ValueError: If request parameters are invalid
        """
        if request.max_results <= 0:
            raise ValueError('max_results must be greater than 0')

        if request.max_results > MAX_SEARCH_RESULTS_LIMIT:
            raise ValueError(f'max_results cannot exceed {MAX_SEARCH_RESULTS_LIMIT}')

        # Validate file_type if provided
        if request.file_type:
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileType

            try:
                GenomicsFileType(request.file_type.lower())
            except ValueError:
                valid_types = [ft.value for ft in GenomicsFileType]
                raise ValueError(
                    f"Invalid file_type '{request.file_type}'. Valid types: {valid_types}"
                )

        logger.debug(f'Search request validation passed: {request}')

    async def _execute_parallel_searches(
        self, request: GenomicsFileSearchRequest
    ) -> List[GenomicsFile]:
        """Execute searches across all configured storage systems in parallel.

        Args:
            request: Search request containing search parameters

        Returns:
            Combined list of GenomicsFile objects from all storage systems
        """
        search_tasks = []

        # Add S3 search task if bucket paths are configured and S3 engine is available
        if self.config.s3_bucket_paths and self.s3_engine is not None:
            logger.info(f'Adding S3 search task for {len(self.config.s3_bucket_paths)} buckets')
            s3_task = self._search_s3_with_timeout(request)
            search_tasks.append(('s3', s3_task))

        # Add HealthOmics search tasks if enabled
        if self.config.enable_healthomics_search:
            logger.info('Adding HealthOmics search tasks')
            sequence_task = self._search_healthomics_sequences_with_timeout(request)
            reference_task = self._search_healthomics_references_with_timeout(request)
            search_tasks.append(('healthomics_sequences', sequence_task))
            search_tasks.append(('healthomics_references', reference_task))

        if not search_tasks:
            logger.warning('No storage systems configured for search')
            return []

        # Execute all search tasks concurrently
        logger.info(f'Executing {len(search_tasks)} parallel search tasks')
        results = await asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True)

        # Collect results and handle exceptions
        all_files = []
        for i, result in enumerate(results):
            storage_system, _ = search_tasks[i]
            if isinstance(result, Exception):
                logger.error(f'Error in {storage_system} search: {result}')
                # Continue with other results rather than failing completely
            elif isinstance(result, list):
                logger.info(f'{storage_system} search returned {len(result)} files')
                all_files.extend(result)
            else:
                logger.warning(f'Unexpected result type from {storage_system}: {type(result)}')

        # Periodically clean up expired cache entries (reduced frequency due to size-based cleanup)
        if (
            secrets.randbelow(100 // S3_CACHE_CLEANUP_PROBABILITY) == 0
            and self.s3_engine is not None
        ):  # Probability defined by S3_CACHE_CLEANUP_PROBABILITY
            try:
                self.s3_engine.cleanup_expired_cache_entries()
            except Exception as e:
                logger.debug(f'Cache cleanup failed: {e}')

        return all_files

    async def _execute_parallel_paginated_searches(
        self,
        request: GenomicsFileSearchRequest,
        storage_pagination_request: 'StoragePaginationRequest',
        global_token: 'GlobalContinuationToken',
    ) -> Tuple[List[GenomicsFile], Optional['GlobalContinuationToken'], int]:
        """Execute paginated searches across all configured storage systems in parallel.

        Args:
            request: Search request containing search parameters
            storage_pagination_request: Storage-level pagination parameters
            global_token: Global continuation token with per-storage state

        Returns:
            Tuple of (combined_files, next_global_token, total_scanned)
        """
        from awslabs.aws_healthomics_mcp_server.models import GlobalContinuationToken

        search_tasks = []
        total_scanned = 0
        next_global_token = GlobalContinuationToken(
            s3_tokens=global_token.s3_tokens.copy(),
            healthomics_sequence_token=global_token.healthomics_sequence_token,
            healthomics_reference_token=global_token.healthomics_reference_token,
            page_number=global_token.page_number,
            total_results_seen=global_token.total_results_seen,
        )

        # Add S3 paginated search task if bucket paths are configured and S3 engine is available
        if self.config.s3_bucket_paths and self.s3_engine is not None:
            logger.info(
                f'Adding S3 paginated search task for {len(self.config.s3_bucket_paths)} buckets'
            )
            s3_task = self._search_s3_paginated_with_timeout(request, storage_pagination_request)
            search_tasks.append(('s3', s3_task))

        # Add HealthOmics paginated search tasks if enabled
        if self.config.enable_healthomics_search:
            logger.info('Adding HealthOmics paginated search tasks')
            sequence_task = self._search_healthomics_sequences_paginated_with_timeout(
                request, storage_pagination_request
            )
            reference_task = self._search_healthomics_references_paginated_with_timeout(
                request, storage_pagination_request
            )
            search_tasks.append(('healthomics_sequences', sequence_task))
            search_tasks.append(('healthomics_references', reference_task))

        if not search_tasks:
            logger.warning('No storage systems configured for paginated search')
            return [], None, 0

        # Execute all search tasks concurrently
        logger.info(f'Executing {len(search_tasks)} parallel paginated search tasks')
        results = await asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True)

        # Collect results and handle exceptions
        all_files = []
        has_more_results = False

        for i, result in enumerate(results):
            storage_system, _ = search_tasks[i]
            if isinstance(result, Exception):
                logger.error(f'Error in {storage_system} paginated search: {result}')
                # Continue with other results rather than failing completely
            else:
                # Assume result is a valid storage response object
                try:
                    # Type guard: access attributes safely
                    results_list = getattr(result, 'results', [])
                    total_scanned_count = getattr(result, 'total_scanned', 0)
                    has_more = getattr(result, 'has_more_results', False)
                    next_token = getattr(result, 'next_continuation_token', None)

                    logger.info(
                        f'{storage_system} paginated search returned {len(results_list)} files'
                    )
                    all_files.extend(results_list)
                    total_scanned += total_scanned_count

                    # Update continuation tokens based on storage system
                    if has_more and next_token:
                        has_more_results = True

                        if storage_system == 's3':
                            # Parse S3 continuation tokens from the response
                            try:
                                response_token = GlobalContinuationToken.decode(next_token)
                                next_global_token.s3_tokens.update(response_token.s3_tokens)
                            except ValueError:
                                logger.warning(
                                    f'Failed to parse S3 continuation token from {storage_system}'
                                )
                        elif storage_system == 'healthomics_sequences':
                            try:
                                response_token = GlobalContinuationToken.decode(next_token)
                                next_global_token.healthomics_sequence_token = (
                                    response_token.healthomics_sequence_token
                                )
                            except ValueError:
                                logger.warning(
                                    f'Failed to parse sequence store continuation token from {storage_system}'
                                )
                        elif storage_system == 'healthomics_references':
                            try:
                                response_token = GlobalContinuationToken.decode(next_token)
                                next_global_token.healthomics_reference_token = (
                                    response_token.healthomics_reference_token
                                )
                            except ValueError:
                                logger.warning(
                                    f'Failed to parse reference store continuation token from {storage_system}'
                                )
                except AttributeError as e:
                    logger.warning(
                        f'Unexpected result type from {storage_system}: {type(result)} - {e}'
                    )

        # Return next token only if there are more results
        final_next_token = next_global_token if has_more_results else None

        return all_files, final_next_token, total_scanned

    async def _search_s3_with_timeout(
        self, request: GenomicsFileSearchRequest
    ) -> List[GenomicsFile]:
        """Execute S3 search with timeout protection.

        Args:
            request: Search request

        Returns:
            List of GenomicsFile objects from S3 search
        """
        if self.s3_engine is None:
            logger.warning('S3 search engine not available, skipping S3 search')
            return []

        try:
            return await asyncio.wait_for(
                self.s3_engine.search_buckets(
                    self.config.s3_bucket_paths, request.file_type, request.search_terms
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f'S3 search timed out after {self.config.search_timeout_seconds} seconds')
            return []
        except Exception as e:
            logger.error(f'S3 search failed: {e}')
            return []

    async def _search_healthomics_sequences_with_timeout(
        self, request: GenomicsFileSearchRequest
    ) -> List[GenomicsFile]:
        """Execute HealthOmics sequence store search with timeout protection.

        Args:
            request: Search request

        Returns:
            List of GenomicsFile objects from HealthOmics sequence stores
        """
        try:
            return await asyncio.wait_for(
                self.healthomics_engine.search_sequence_stores(
                    request.file_type, request.search_terms
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f'HealthOmics sequence store search timed out after {self.config.search_timeout_seconds} seconds'
            )
            return []
        except Exception as e:
            logger.error(f'HealthOmics sequence store search failed: {e}')
            return []

    async def _search_healthomics_references_with_timeout(
        self, request: GenomicsFileSearchRequest
    ) -> List[GenomicsFile]:
        """Execute HealthOmics reference store search with timeout protection.

        Args:
            request: Search request

        Returns:
            List of GenomicsFile objects from HealthOmics reference stores
        """
        try:
            return await asyncio.wait_for(
                self.healthomics_engine.search_reference_stores(
                    request.file_type, request.search_terms
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f'HealthOmics reference store search timed out after {self.config.search_timeout_seconds} seconds'
            )
            return []
        except Exception as e:
            logger.error(f'HealthOmics reference store search failed: {e}')
            return []

    async def _search_s3_paginated_with_timeout(
        self,
        request: GenomicsFileSearchRequest,
        storage_pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Execute S3 paginated search with timeout protection.

        Args:
            request: Search request
            storage_pagination_request: Storage-level pagination parameters

        Returns:
            StoragePaginationResponse from S3 search
        """
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationResponse

        if self.s3_engine is None:
            logger.warning('S3 search engine not available, skipping S3 paginated search')
            return StoragePaginationResponse(results=[], has_more_results=False)

        try:
            return await asyncio.wait_for(
                self.s3_engine.search_buckets_paginated(
                    self.config.s3_bucket_paths,
                    request.file_type,
                    request.search_terms,
                    storage_pagination_request,
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f'S3 paginated search timed out after {self.config.search_timeout_seconds} seconds'
            )
            return StoragePaginationResponse(results=[], has_more_results=False)
        except Exception as e:
            logger.error(f'S3 paginated search failed: {e}')
            return StoragePaginationResponse(results=[], has_more_results=False)

    async def _search_healthomics_sequences_paginated_with_timeout(
        self,
        request: GenomicsFileSearchRequest,
        storage_pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Execute HealthOmics sequence store paginated search with timeout protection.

        Args:
            request: Search request
            storage_pagination_request: Storage-level pagination parameters

        Returns:
            StoragePaginationResponse from HealthOmics sequence stores
        """
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationResponse

        try:
            return await asyncio.wait_for(
                self.healthomics_engine.search_sequence_stores_paginated(
                    request.file_type, request.search_terms, storage_pagination_request
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f'HealthOmics sequence store paginated search timed out after {self.config.search_timeout_seconds} seconds'
            )
            return StoragePaginationResponse(results=[], has_more_results=False)
        except Exception as e:
            logger.error(f'HealthOmics sequence store paginated search failed: {e}')
            return StoragePaginationResponse(results=[], has_more_results=False)

    async def _search_healthomics_references_paginated_with_timeout(
        self,
        request: GenomicsFileSearchRequest,
        storage_pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Execute HealthOmics reference store paginated search with timeout protection.

        Args:
            request: Search request
            storage_pagination_request: Storage-level pagination parameters

        Returns:
            StoragePaginationResponse from HealthOmics reference stores
        """
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationResponse

        try:
            return await asyncio.wait_for(
                self.healthomics_engine.search_reference_stores_paginated(
                    request.file_type, request.search_terms, storage_pagination_request
                ),
                timeout=self.config.search_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f'HealthOmics reference store paginated search timed out after {self.config.search_timeout_seconds} seconds'
            )
            return StoragePaginationResponse(results=[], has_more_results=False)
        except Exception as e:
            logger.error(f'HealthOmics reference store paginated search failed: {e}')
            return StoragePaginationResponse(results=[], has_more_results=False)

    def _deduplicate_files(self, files: List[GenomicsFile]) -> List[GenomicsFile]:
        """Remove duplicate files based on their paths.

        Args:
            files: List of GenomicsFile objects that may contain duplicates

        Returns:
            List of unique GenomicsFile objects
        """
        seen_paths: Set[str] = set()
        unique_files = []

        for file in files:
            if file.path not in seen_paths:
                seen_paths.add(file.path)
                unique_files.append(file)
            else:
                logger.debug(f'Removing duplicate file: {file.path}')

        return unique_files

    async def _score_results(
        self,
        file_groups: List,
        file_type_filter: Optional[str],
        search_terms: List[str],
        include_associated_files: bool = True,
    ) -> List[GenomicsFileResult]:
        """Score file groups and create GenomicsFileResult objects.

        Args:
            file_groups: List of FileGroup objects with associated files
            file_type_filter: Optional file type filter from search request
            search_terms: List of search terms for scoring
            include_associated_files: Whether to include associated files in results

        Returns:
            List of GenomicsFileResult objects with calculated relevance scores
        """
        scored_results = []

        for file_group in file_groups:
            # Calculate score for the primary file considering its associations
            score, reasons = self.scoring_engine.calculate_score(
                file_group.primary_file,
                search_terms,
                file_type_filter,
                file_group.associated_files,
            )

            # Create GenomicsFileResult
            result = GenomicsFileResult(
                primary_file=file_group.primary_file,
                associated_files=file_group.associated_files if include_associated_files else [],
                relevance_score=score,
                match_reasons=reasons,
            )

            scored_results.append(result)

        logger.info(f'Scored {len(scored_results)} results')
        return scored_results

    def _get_searched_storage_systems(self) -> List[str]:
        """Get the list of storage systems that were searched.

        Returns:
            List of storage system names that were included in the search
        """
        systems = []

        if self.config.s3_bucket_paths and self.s3_engine is not None:
            systems.append('s3')

        if self.config.enable_healthomics_search:
            systems.extend(['healthomics_sequence_stores', 'healthomics_reference_stores'])

        return systems

    def _extract_healthomics_associations(self, files: List[GenomicsFile]) -> List[GenomicsFile]:
        """Extract associated files from HealthOmics files and add them to the file list.

        Args:
            files: List of GenomicsFile objects

        Returns:
            List of GenomicsFile objects including associated files
        """
        all_files = []

        for file in files:
            all_files.append(file)

            # Check if this is a HealthOmics reference file with index information
            index_info = file.metadata.get('_healthomics_index_info')
            if index_info is not None:
                logger.debug(f'Creating associated index file for {file.path}')

                # Import here to avoid circular imports
                from awslabs.aws_healthomics_mcp_server.models import (
                    GenomicsFile,
                    GenomicsFileType,
                )
                from datetime import datetime

                # Create the index file
                index_file = GenomicsFile(
                    path=index_info['index_uri'],
                    file_type=GenomicsFileType.FAI,
                    size_bytes=index_info['index_size'],
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='reference_store',
                    metadata={
                        'store_id': index_info['store_id'],
                        'store_name': index_info['store_name'],
                        'reference_id': index_info['reference_id'],
                        'reference_name': index_info['reference_name'],
                        'status': index_info['status'],
                        'md5': index_info['md5'],
                        'omics_uri': index_info['index_uri'],
                        'is_index_file': True,
                        'primary_file_uri': file.path,
                    },
                )

                all_files.append(index_file)

        return all_files

    def _create_pagination_cache_key(
        self, request: GenomicsFileSearchRequest, page_number: int
    ) -> str:
        """Create a cache key for pagination state.

        Args:
            request: Search request
            page_number: Current page number

        Returns:
            Cache key string for pagination state
        """
        import hashlib
        import json

        key_data = {
            'file_type': request.file_type or '',
            'search_terms': sorted(request.search_terms),
            'include_associated_files': request.include_associated_files,
            'page_number': page_number,
            'buffer_size': request.pagination_buffer_size,
            's3_buckets': sorted(self.config.s3_bucket_paths),
            'enable_healthomics': self.config.enable_healthomics_search,
        }

        key_str = json.dumps(key_data, separators=(',', ':'))
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    def _get_cached_pagination_state(self, cache_key: str) -> Optional['PaginationCacheEntry']:
        """Get cached pagination state if available and not expired.

        Args:
            cache_key: Cache key for the pagination state

        Returns:
            Cached pagination entry if available and valid, None otherwise
        """
        if not hasattr(self, '_pagination_cache'):
            self._pagination_cache = {}

        if cache_key in self._pagination_cache:
            cached_entry = self._pagination_cache[cache_key]
            if not cached_entry.is_expired(self.config.pagination_cache_ttl_seconds):
                logger.debug(f'Pagination cache hit for key: {cache_key}')
                return cached_entry
            else:
                # Remove expired entry
                del self._pagination_cache[cache_key]
                logger.debug(f'Pagination cache expired for key: {cache_key}')

        return None

    def _cache_pagination_state(self, cache_key: str, entry: 'PaginationCacheEntry') -> None:
        """Cache pagination state.

        Args:
            cache_key: Cache key for the pagination state
            entry: Pagination cache entry to store
        """
        if self.config.pagination_cache_ttl_seconds > 0:
            if not hasattr(self, '_pagination_cache'):
                self._pagination_cache = {}

            # Check if we need to clean up before adding
            if len(self._pagination_cache) >= self.config.max_pagination_cache_size:
                self._cleanup_pagination_cache_by_size()

            entry.update_timestamp()
            self._pagination_cache[cache_key] = entry
            logger.debug(f'Cached pagination state for key: {cache_key}')

    def _optimize_buffer_size(
        self, request: GenomicsFileSearchRequest, metrics: Optional['PaginationMetrics'] = None
    ) -> int:
        """Optimize buffer size based on request parameters and historical metrics.

        Args:
            request: Search request
            metrics: Optional historical pagination metrics

        Returns:
            Optimized buffer size
        """
        base_buffer_size = request.pagination_buffer_size

        # Adjust based on search complexity
        complexity_multiplier = 1.0

        # More search terms = higher complexity
        if request.search_terms:
            complexity_multiplier += len(request.search_terms) * 0.1

        # File type filtering reduces complexity
        if request.file_type:
            complexity_multiplier *= COMPLEXITY_MULTIPLIER_FILE_TYPE_FILTER

        # Associated files increase complexity
        if request.include_associated_files:
            complexity_multiplier *= COMPLEXITY_MULTIPLIER_ASSOCIATED_FILES

        # Adjust based on historical metrics
        if metrics:
            # If we had buffer overflows, increase buffer size
            if metrics.buffer_overflows > 0:
                complexity_multiplier *= COMPLEXITY_MULTIPLIER_BUFFER_OVERFLOW

            # If efficiency was low, increase buffer size
            efficiency_ratio = metrics.total_results_fetched / max(
                metrics.total_objects_scanned, 1
            )
            if efficiency_ratio < BUFFER_EFFICIENCY_LOW_THRESHOLD:
                complexity_multiplier *= COMPLEXITY_MULTIPLIER_LOW_EFFICIENCY
            elif efficiency_ratio > BUFFER_EFFICIENCY_HIGH_THRESHOLD:
                complexity_multiplier *= COMPLEXITY_MULTIPLIER_HIGH_EFFICIENCY

        optimized_size = int(base_buffer_size * complexity_multiplier)

        # Apply bounds
        optimized_size = max(self.config.min_pagination_buffer_size, optimized_size)
        optimized_size = min(self.config.max_pagination_buffer_size, optimized_size)

        if optimized_size != base_buffer_size:
            logger.debug(
                f'Optimized buffer size from {base_buffer_size} to {optimized_size} '
                f'(complexity: {complexity_multiplier:.2f})'
            )

        return optimized_size

    def _create_pagination_metrics(
        self, page_number: int, start_time: float
    ) -> 'PaginationMetrics':
        """Create pagination metrics for performance monitoring.

        Args:
            page_number: Current page number
            start_time: Search start time

        Returns:
            PaginationMetrics object
        """
        import time
        from awslabs.aws_healthomics_mcp_server.models import PaginationMetrics

        return PaginationMetrics(
            page_number=page_number, search_duration_ms=int((time.time() - start_time) * 1000)
        )

    def _should_use_cursor_pagination(
        self, request: GenomicsFileSearchRequest, global_token: 'GlobalContinuationToken'
    ) -> bool:
        """Determine if cursor-based pagination should be used for very large datasets.

        Args:
            request: Search request
            global_token: Global continuation token

        Returns:
            True if cursor-based pagination should be used
        """
        # Use cursor pagination for large buffer sizes or high page numbers
        return self.config.enable_cursor_based_pagination and (
            request.pagination_buffer_size > CURSOR_PAGINATION_BUFFER_THRESHOLD
            or global_token.page_number > CURSOR_PAGINATION_PAGE_THRESHOLD
        )

    def _cleanup_pagination_cache_by_size(self) -> None:
        """Clean up pagination cache when it exceeds max size, prioritizing expired entries first.

        Strategy:
        1. First: Remove all expired entries (regardless of age)
        2. Then: If still over size limit, remove oldest non-expired entries
        """
        if not hasattr(self, '_pagination_cache'):
            return

        if len(self._pagination_cache) < self.config.max_pagination_cache_size:
            return

        target_size = int(
            self.config.max_pagination_cache_size * self.config.cache_cleanup_keep_ratio
        )

        # Separate expired and valid entries
        expired_items = []
        valid_items = []

        for key, entry in self._pagination_cache.items():
            if entry.is_expired(self.config.pagination_cache_ttl_seconds):
                expired_items.append((key, entry))
            else:
                valid_items.append((key, entry))

        # Phase 1: Remove all expired items first
        expired_count = len(expired_items)
        for key, _ in expired_items:
            del self._pagination_cache[key]

        # Phase 2: If still over target size, remove oldest valid items
        remaining_count = len(self._pagination_cache)
        additional_removals = 0

        if remaining_count > target_size:
            # Sort valid items by timestamp (oldest first)
            valid_items.sort(key=lambda x: x[1].timestamp)
            additional_to_remove = remaining_count - target_size

            for i in range(min(additional_to_remove, len(valid_items))):
                key, _ = valid_items[i]
                if key in self._pagination_cache:  # Double-check key still exists
                    del self._pagination_cache[key]
                    additional_removals += 1

        total_removed = expired_count + additional_removals
        if total_removed > 0:
            logger.debug(
                f'Smart pagination cache cleanup: removed {expired_count} expired + {additional_removals} oldest valid = {total_removed} total entries, {len(self._pagination_cache)} remaining'
            )

    def cleanup_expired_pagination_cache(self) -> None:
        """Clean up expired pagination cache entries to prevent memory leaks."""
        if not hasattr(self, '_pagination_cache'):
            return

        expired_keys = []
        for cache_key, cached_entry in self._pagination_cache.items():
            if cached_entry.is_expired(self.config.pagination_cache_ttl_seconds):
                expired_keys.append(cache_key)

        for key in expired_keys:
            del self._pagination_cache[key]

        if expired_keys:
            logger.debug(f'Cleaned up {len(expired_keys)} expired pagination cache entries')

    def get_pagination_cache_stats(self) -> Dict[str, Any]:
        """Get pagination cache statistics for monitoring.

        Returns:
            Dictionary with pagination cache statistics
        """
        if not hasattr(self, '_pagination_cache'):
            return {'total_entries': 0, 'valid_entries': 0}

        valid_entries = sum(
            1
            for entry in self._pagination_cache.values()
            if not entry.is_expired(self.config.pagination_cache_ttl_seconds)
        )

        return {
            'total_entries': len(self._pagination_cache),
            'valid_entries': valid_entries,
            'ttl_seconds': self.config.pagination_cache_ttl_seconds,
            'max_cache_size': self.config.max_pagination_cache_size,
            'cache_utilization': len(self._pagination_cache)
            / self.config.max_pagination_cache_size,
            'config': {
                'enable_cursor_pagination': self.config.enable_cursor_based_pagination,
                'max_buffer_size': self.config.max_pagination_buffer_size,
                'min_buffer_size': self.config.min_pagination_buffer_size,
                'enable_metrics': self.config.enable_pagination_metrics,
                'cache_cleanup_keep_ratio': self.config.cache_cleanup_keep_ratio,
            },
        }
