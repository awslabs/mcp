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
import time
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileSearchRequest,
    GenomicsFileSearchResponse,
    SearchConfig,
)
from awslabs.aws_healthomics_mcp_server.search.file_association_engine import FileAssociationEngine
from awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine import (
    HealthOmicsSearchEngine,
)
from awslabs.aws_healthomics_mcp_server.search.json_response_builder import JsonResponseBuilder
from awslabs.aws_healthomics_mcp_server.search.result_ranker import ResultRanker
from awslabs.aws_healthomics_mcp_server.search.s3_search_engine import S3SearchEngine
from awslabs.aws_healthomics_mcp_server.search.scoring_engine import ScoringEngine
from awslabs.aws_healthomics_mcp_server.utils.config_utils import get_genomics_search_config
from loguru import logger
from typing import List, Set


class GenomicsSearchOrchestrator:
    """Orchestrates genomics file searches across multiple storage systems."""

    def __init__(self, config: SearchConfig):
        """Initialize the search orchestrator.

        Args:
            config: Search configuration containing settings for all storage systems
        """
        self.config = config
        self.s3_engine = S3SearchEngine(config)
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

            # Apply file associations and grouping
            file_groups = self.association_engine.find_associations(deduplicated_files)
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
                ranked_results, request.max_results
            )

            # Get ranking statistics
            ranking_stats = self.result_ranker.get_ranking_statistics(ranked_results)

            # Build comprehensive JSON response
            search_duration_ms = int((time.time() - start_time) * 1000)
            storage_systems_searched = self._get_searched_storage_systems()

            pagination_info = {
                'offset': 0,
                'limit': request.max_results,
                'total_available': len(ranked_results),
                'has_more': len(ranked_results) > request.max_results,
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
            )

            # Store the enhanced response for access by tools
            response.enhanced_response = response_dict

            logger.info(
                f'Search completed in {search_duration_ms}ms, returning {len(limited_results)} results'
            )
            return response

        except Exception as e:
            search_duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f'Search failed after {search_duration_ms}ms: {e}')
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

        if request.max_results > 10000:
            raise ValueError('max_results cannot exceed 10000')

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

        # Add S3 search task if bucket paths are configured
        if self.config.s3_bucket_paths:
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
            else:
                logger.info(f'{storage_system} search returned {len(result)} files')
                all_files.extend(result)

        return all_files

    async def _search_s3_with_timeout(
        self, request: GenomicsFileSearchRequest
    ) -> List[GenomicsFile]:
        """Execute S3 search with timeout protection.

        Args:
            request: Search request

        Returns:
            List of GenomicsFile objects from S3 search
        """
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
        file_type_filter: str,
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

        if self.config.s3_bucket_paths:
            systems.append('s3')

        if self.config.enable_healthomics_search:
            systems.extend(['healthomics_sequence_stores', 'healthomics_reference_stores'])

        return systems
