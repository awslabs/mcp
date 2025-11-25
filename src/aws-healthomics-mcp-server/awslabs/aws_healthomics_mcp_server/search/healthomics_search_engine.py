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

"""HealthOmics search engine for genomics files in sequence and reference stores."""

import asyncio
from awslabs.aws_healthomics_mcp_server.consts import (
    HEALTHOMICS_RATE_LIMIT_DELAY,
    HEALTHOMICS_STATUS_ACTIVE,
    HEALTHOMICS_STORAGE_CLASS_MANAGED,
)
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
    SearchConfig,
    StoragePaginationRequest,
    StoragePaginationResponse,
)
from awslabs.aws_healthomics_mcp_server.search.file_type_detector import FileTypeDetector
from awslabs.aws_healthomics_mcp_server.search.pattern_matcher import PatternMatcher
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


class HealthOmicsSearchEngine:
    """Search engine for genomics files in HealthOmics sequence and reference stores."""

    def __init__(self, config: SearchConfig):
        """Initialize the HealthOmics search engine.

        Args:
            config: Search configuration containing settings
        """
        self.config = config
        self.omics_client = get_omics_client()
        self.file_type_detector = FileTypeDetector()
        self.pattern_matcher = PatternMatcher()

    async def search_sequence_stores(
        self, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files in HealthOmics sequence stores.

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ClientError: If HealthOmics API access fails
        """
        try:
            logger.info('Starting search in HealthOmics sequence stores')

            # List all sequence stores
            sequence_stores = await self._list_sequence_stores()
            logger.info(f'Found {len(sequence_stores)} sequence stores')

            all_files = []

            # Create tasks for concurrent store searches
            tasks = []
            for store in sequence_stores:
                store_id = store['id']
                task = self._search_single_sequence_store(store_id, store, file_type, search_terms)
                tasks.append(task)

            # Execute searches concurrently with semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

            async def bounded_search(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[bounded_search(task) for task in tasks], return_exceptions=True
            )

            # Collect results and handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    store_id = sequence_stores[i]['id']
                    logger.error(f'Error searching sequence store {store_id}: {result}')
                elif isinstance(result, list):
                    all_files.extend(result)
                else:
                    logger.warning(f'Unexpected result type from sequence store: {type(result)}')

            logger.info(f'Found {len(all_files)} files in sequence stores')
            return all_files

        except Exception as e:
            logger.error(f'Error searching HealthOmics sequence stores: {e}')
            raise

    async def search_sequence_stores_paginated(
        self,
        file_type: Optional[str],
        search_terms: List[str],
        pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Search for genomics files in HealthOmics sequence stores with pagination.

        This method implements efficient pagination by:
        1. Using native HealthOmics nextToken for ListReadSets API
        2. Implementing efficient API batching to reach result limits
        3. Adding rate limiting and retry logic for API pagination

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against
            pagination_request: Pagination parameters and continuation tokens

        Returns:
            StoragePaginationResponse with paginated results and continuation tokens

        Raises:
            ClientError: If HealthOmics API access fails
        """
        from awslabs.aws_healthomics_mcp_server.models import (
            GlobalContinuationToken,
            StoragePaginationResponse,
        )

        try:
            logger.info('Starting paginated search in HealthOmics sequence stores')

            # Parse continuation token
            global_token = GlobalContinuationToken()
            if pagination_request.continuation_token:
                try:
                    global_token = GlobalContinuationToken.decode(
                        pagination_request.continuation_token
                    )
                except ValueError as e:
                    logger.warning(f'Invalid continuation token, starting fresh search: {e}')
                    global_token = GlobalContinuationToken()

            # List all sequence stores (this is typically a small list, so no pagination needed)
            sequence_stores = await self._list_sequence_stores()
            logger.info(f'Found {len(sequence_stores)} sequence stores')

            all_files = []
            total_scanned = 0
            has_more_results = False
            next_sequence_token = global_token.healthomics_sequence_token

            # Search sequence stores with pagination
            for store in sequence_stores:
                store_id = store['id']

                # Search this store with pagination
                (
                    store_files,
                    store_next_token,
                    store_scanned,
                ) = await self._search_single_sequence_store_paginated(
                    store_id,
                    store,
                    file_type,
                    search_terms,
                    next_sequence_token,
                    pagination_request.buffer_size,
                )

                all_files.extend(store_files)
                total_scanned += store_scanned

                # Update continuation token
                if store_next_token:
                    next_sequence_token = store_next_token
                    has_more_results = True
                    break  # Stop at first store with more results to maintain order
                else:
                    next_sequence_token = None

                # Check if we have enough results
                if len(all_files) >= pagination_request.max_results:
                    break

            # Create next continuation token
            next_continuation_token = None
            if has_more_results:
                next_global_token = GlobalContinuationToken(
                    s3_tokens=global_token.s3_tokens,
                    healthomics_sequence_token=next_sequence_token,
                    healthomics_reference_token=global_token.healthomics_reference_token,
                    page_number=global_token.page_number + 1,
                    total_results_seen=global_token.total_results_seen + len(all_files),
                )
                next_continuation_token = next_global_token.encode()

            logger.info(
                f'HealthOmics sequence stores paginated search completed: {len(all_files)} results, '
                f'{total_scanned} read sets scanned, has_more: {has_more_results}'
            )

            return StoragePaginationResponse(
                results=all_files,
                next_continuation_token=next_continuation_token,
                has_more_results=has_more_results,
                total_scanned=total_scanned,
                buffer_overflow=len(all_files) > pagination_request.buffer_size,
            )

        except Exception as e:
            logger.error(f'Error in paginated search of HealthOmics sequence stores: {e}')
            raise

    async def search_reference_stores(
        self, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files in HealthOmics reference stores.

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ClientError: If HealthOmics API access fails
        """
        try:
            logger.info('Starting search in HealthOmics reference stores')

            # List all reference stores
            reference_stores = await self._list_reference_stores()
            logger.info(f'Found {len(reference_stores)} reference stores')

            all_files = []

            # Create tasks for concurrent store searches
            tasks = []
            for store in reference_stores:
                store_id = store['id']
                task = self._search_single_reference_store(
                    store_id, store, file_type, search_terms
                )
                tasks.append(task)

            # Execute searches concurrently with semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

            async def bounded_search(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[bounded_search(task) for task in tasks], return_exceptions=True
            )

            # Collect results and handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    store_id = reference_stores[i]['id']
                    logger.error(f'Error searching reference store {store_id}: {result}')
                elif isinstance(result, list):
                    all_files.extend(result)
                else:
                    logger.warning(f'Unexpected result type from reference store: {type(result)}')

            logger.info(f'Found {len(all_files)} files in reference stores')
            return all_files

        except Exception as e:
            logger.error(f'Error searching HealthOmics reference stores: {e}')
            raise

    async def search_reference_stores_paginated(
        self,
        file_type: Optional[str],
        search_terms: List[str],
        pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Search for genomics files in HealthOmics reference stores with pagination.

        This method implements efficient pagination by:
        1. Using native HealthOmics nextToken for ListReferences API
        2. Implementing efficient API batching to reach result limits
        3. Adding rate limiting and retry logic for API pagination

        Args:
            file_type: Optional file type filter
            search_terms: List of search terms to match against
            pagination_request: Pagination parameters and continuation tokens

        Returns:
            StoragePaginationResponse with paginated results and continuation tokens

        Raises:
            ClientError: If HealthOmics API access fails
        """
        from awslabs.aws_healthomics_mcp_server.models import (
            GlobalContinuationToken,
            StoragePaginationResponse,
        )

        try:
            logger.info('Starting paginated search in HealthOmics reference stores')

            # Parse continuation token
            global_token = GlobalContinuationToken()
            if pagination_request.continuation_token:
                try:
                    global_token = GlobalContinuationToken.decode(
                        pagination_request.continuation_token
                    )
                except ValueError as e:
                    logger.warning(f'Invalid continuation token, starting fresh search: {e}')
                    global_token = GlobalContinuationToken()

            # List all reference stores (this is typically a small list, so no pagination needed)
            reference_stores = await self._list_reference_stores()
            logger.info(f'Found {len(reference_stores)} reference stores')

            all_files = []
            total_scanned = 0
            has_more_results = False
            next_reference_token = global_token.healthomics_reference_token

            # Search reference stores with pagination
            for store in reference_stores:
                store_id = store['id']

                # Search this store with pagination
                (
                    store_files,
                    store_next_token,
                    store_scanned,
                ) = await self._search_single_reference_store_paginated(
                    store_id,
                    store,
                    file_type,
                    search_terms,
                    next_reference_token,
                    pagination_request.buffer_size,
                )

                all_files.extend(store_files)
                total_scanned += store_scanned

                # Update continuation token
                if store_next_token:
                    next_reference_token = store_next_token
                    has_more_results = True
                    break  # Stop at first store with more results to maintain order
                else:
                    next_reference_token = None

                # Check if we have enough results
                if len(all_files) >= pagination_request.max_results:
                    break

            # Create next continuation token
            next_continuation_token = None
            if has_more_results:
                next_global_token = GlobalContinuationToken(
                    s3_tokens=global_token.s3_tokens,
                    healthomics_sequence_token=global_token.healthomics_sequence_token,
                    healthomics_reference_token=next_reference_token,
                    page_number=global_token.page_number + 1,
                    total_results_seen=global_token.total_results_seen + len(all_files),
                )
                next_continuation_token = next_global_token.encode()

            logger.info(
                f'HealthOmics reference stores paginated search completed: {len(all_files)} results, '
                f'{total_scanned} references scanned, has_more: {has_more_results}'
            )

            return StoragePaginationResponse(
                results=all_files,
                next_continuation_token=next_continuation_token,
                has_more_results=has_more_results,
                total_scanned=total_scanned,
                buffer_overflow=len(all_files) > pagination_request.buffer_size,
            )

        except Exception as e:
            logger.error(f'Error in paginated search of HealthOmics reference stores: {e}')
            raise

    async def _list_sequence_stores(self) -> List[Dict[str, Any]]:
        """List all HealthOmics sequence stores.

        Returns:
            List of sequence store dictionaries

        Raises:
            ClientError: If API call fails
        """
        stores = []
        next_token = None

        while True:
            try:
                # Prepare list_sequence_stores parameters
                params = {'maxResults': 100}  # AWS maximum for this API
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_sequence_stores(**params)
                )

                # Add stores from this page
                if 'sequenceStores' in response:
                    stores.extend(response['sequenceStores'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing sequence stores: {e}')
                raise

        logger.debug(f'Listed {len(stores)} sequence stores')
        return stores

    async def _list_reference_stores(self) -> List[Dict[str, Any]]:
        """List all HealthOmics reference stores.

        Returns:
            List of reference store dictionaries

        Raises:
            ClientError: If API call fails
        """
        stores = []
        next_token = None

        while True:
            try:
                # Prepare list_reference_stores parameters
                params = {'maxResults': 100}  # AWS maximum for this API
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_reference_stores(**params)
                )

                # Add stores from this page
                if 'referenceStores' in response:
                    stores.extend(response['referenceStores'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing reference stores: {e}')
                raise

        logger.debug(f'Listed {len(stores)} reference stores')
        return stores

    async def _search_single_sequence_store(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> List[GenomicsFile]:
        """Search a single HealthOmics sequence store for genomics files.

        Args:
            store_id: ID of the sequence store
            store_info: Store information from list_sequence_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this store
        """
        try:
            logger.debug(f'Searching sequence store {store_id}')

            # List read sets in the sequence store
            read_sets = await self._list_read_sets(store_id)
            logger.debug(f'Found {len(read_sets)} read sets in store {store_id}')

            genomics_files = []
            for read_set in read_sets:
                genomics_file = await self._convert_read_set_to_genomics_file(
                    read_set, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in sequence store {store_id}'
            )
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching sequence store {store_id}: {e}')
            raise

    async def _search_single_reference_store(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> List[GenomicsFile]:
        """Search a single HealthOmics reference store for genomics files.

        Args:
            store_id: ID of the reference store
            store_info: Store information from list_reference_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this store
        """
        try:
            logger.debug(f'Searching reference store {store_id}')

            # List references in the reference store with server-side filtering
            references = await self._list_references(store_id, search_terms)
            logger.debug(f'Found {len(references)} references in store {store_id}')

            genomics_files = []
            for reference in references:
                genomics_file = await self._convert_reference_to_genomics_file(
                    reference, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in reference store {store_id}'
            )
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching reference store {store_id}: {e}')
            raise

    async def _list_read_sets(self, sequence_store_id: str) -> List[Dict[str, Any]]:
        """List read sets in a HealthOmics sequence store.

        Args:
            sequence_store_id: ID of the sequence store

        Returns:
            List of read set dictionaries

        Raises:
            ClientError: If API call fails
        """
        read_sets = []
        next_token = None

        while True:
            try:
                # Prepare list_read_sets parameters
                params = {
                    'sequenceStoreId': sequence_store_id,
                    'maxResults': 100,  # AWS maximum for this API
                }
                if next_token:
                    params['nextToken'] = next_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_read_sets(**params)
                )

                # Add read sets from this page
                if 'readSets' in response:
                    read_sets.extend(response['readSets'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(f'Error listing read sets in sequence store {sequence_store_id}: {e}')
                raise

        return read_sets

    async def _list_read_sets_paginated(
        self, sequence_store_id: str, next_token: Optional[str] = None, max_results: int = 100
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """List read sets in a HealthOmics sequence store with pagination.

        Args:
            sequence_store_id: ID of the sequence store
            next_token: Continuation token from previous request
            max_results: Maximum number of read sets to return

        Returns:
            Tuple of (read_sets, next_continuation_token, total_read_sets_scanned)

        Raises:
            ClientError: If API call fails
        """
        read_sets = []
        total_scanned = 0
        current_token = next_token

        try:
            while len(read_sets) < max_results:
                # Calculate how many more read sets we need
                remaining_needed = max_results - len(read_sets)
                page_size = min(100, remaining_needed)  # AWS maximum is 100 for this API

                # Prepare list_read_sets parameters
                params = {
                    'sequenceStoreId': sequence_store_id,
                    'maxResults': page_size,
                }
                if current_token:
                    params['nextToken'] = current_token

                # Execute the list operation asynchronously with rate limiting
                await asyncio.sleep(
                    HEALTHOMICS_RATE_LIMIT_DELAY
                )  # Rate limiting: 10 requests per second
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_read_sets(**params)
                )

                # Add read sets from this page
                page_read_sets = response.get('readSets', [])
                read_sets.extend(page_read_sets)
                total_scanned += len(page_read_sets)

                # Check if there are more pages
                if response.get('nextToken'):
                    current_token = response.get('nextToken')

                    # If we have enough read sets, return with the continuation token
                    if len(read_sets) >= max_results:
                        break
                else:
                    # No more pages available
                    current_token = None
                    break

        except ClientError as e:
            logger.error(f'Error listing read sets in sequence store {sequence_store_id}: {e}')
            raise

        # Trim to exact max_results if we got more
        if len(read_sets) > max_results:
            read_sets = read_sets[:max_results]

        logger.debug(
            f'Listed {len(read_sets)} read sets in sequence store {sequence_store_id} '
            f'(scanned {total_scanned}, next_token: {bool(current_token)})'
        )

        return read_sets, current_token, total_scanned

    async def _search_single_sequence_store_paginated(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
        continuation_token: Optional[str] = None,
        max_results: int = 100,
    ) -> Tuple[List[GenomicsFile], Optional[str], int]:
        """Search a single HealthOmics sequence store with pagination support.

        Args:
            store_id: ID of the sequence store
            store_info: Store information from list_sequence_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against
            continuation_token: HealthOmics continuation token for this store
            max_results: Maximum number of results to return

        Returns:
            Tuple of (genomics_files, next_continuation_token, read_sets_scanned)
        """
        try:
            logger.debug(f'Searching sequence store {store_id} with pagination')

            # List read sets in the sequence store with pagination
            read_sets, next_token, total_scanned = await self._list_read_sets_paginated(
                store_id, continuation_token, max_results
            )
            logger.debug(
                f'Found {len(read_sets)} read sets in store {store_id} (scanned {total_scanned})'
            )

            genomics_files = []
            for read_set in read_sets:
                genomics_file = await self._convert_read_set_to_genomics_file(
                    read_set, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in sequence store {store_id}'
            )
            return genomics_files, next_token, total_scanned

        except Exception as e:
            logger.error(f'Error in paginated search of sequence store {store_id}: {e}')
            raise

    async def _list_references(
        self, reference_store_id: str, search_terms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List references in a HealthOmics reference store.

        Args:
            reference_store_id: ID of the reference store
            search_terms: Optional list of search terms to filter by name on the server side

        Returns:
            List of reference dictionaries

        Raises:
            ClientError: If API call fails
        """
        references = []

        # If we have search terms, try server-side filtering for each term
        # This is more efficient than retrieving all references and filtering client-side
        if search_terms:
            logger.debug(
                f'Searching reference store {reference_store_id} with terms: {search_terms}'
            )

            # First, try exact matches for each search term using server-side filtering
            for search_term in search_terms:
                logger.debug(f'Trying server-side exact match for: {search_term}')
                term_references = await self._list_references_with_filter(
                    reference_store_id, search_term
                )
                logger.debug(
                    f'Server-side filter for "{search_term}" returned {len(term_references)} references'
                )
                references.extend(term_references)

            # If no results from server-side filtering, fall back to getting all references
            # This handles cases where the server-side filter requires exact matches
            if not references:
                logger.info(
                    f'No server-side matches found for {search_terms}, falling back to client-side filtering'
                )
                references = await self._list_references_with_filter(reference_store_id, None)
                logger.debug(
                    f'Retrieved {len(references)} total references for client-side filtering'
                )
            else:
                logger.debug(f'Server-side filtering found {len(references)} references')

            # Remove duplicates based on reference ID
            seen_ids = set()
            unique_references = []
            for ref in references:
                ref_id = ref.get('id')
                if ref_id and ref_id not in seen_ids:
                    seen_ids.add(ref_id)
                    unique_references.append(ref)

            logger.debug(f'After deduplication: {len(unique_references)} unique references')
            return unique_references
        else:
            # No search terms, get all references
            logger.debug(
                f'No search terms provided, retrieving all references from store {reference_store_id}'
            )
            return await self._list_references_with_filter(reference_store_id, None)

    async def _list_references_with_filter(
        self, reference_store_id: str, name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List references in a HealthOmics reference store with optional name filter.

        Args:
            reference_store_id: ID of the reference store
            name_filter: Optional name filter to apply server-side

        Returns:
            List of reference dictionaries

        Raises:
            ClientError: If API call fails
        """
        references = []
        next_token = None

        while True:
            try:
                # Prepare list_references parameters
                params = {
                    'referenceStoreId': reference_store_id,
                    'maxResults': 100,  # AWS maximum for this API
                }
                if next_token:
                    params['nextToken'] = next_token

                # Add server-side name filter if provided
                if name_filter:
                    params['filter'] = {'name': name_filter}
                    logger.debug(f'Applying server-side name filter: {name_filter}')

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_references(**params)
                )

                # Add references from this page
                if 'references' in response:
                    references.extend(response['references'])

                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break

            except ClientError as e:
                logger.error(
                    f'Error listing references in reference store {reference_store_id}: {e}'
                )
                raise

        return references

    async def _list_references_with_filter_paginated(
        self,
        reference_store_id: str,
        name_filter: Optional[str] = None,
        next_token: Optional[str] = None,
        max_results: int = 100,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """List references in a HealthOmics reference store with pagination and optional name filter.

        Args:
            reference_store_id: ID of the reference store
            name_filter: Optional name filter to apply server-side
            next_token: Continuation token from previous request
            max_results: Maximum number of references to return

        Returns:
            Tuple of (references, next_continuation_token, total_references_scanned)

        Raises:
            ClientError: If API call fails
        """
        references = []
        total_scanned = 0
        current_token = next_token

        try:
            while len(references) < max_results:
                # Calculate how many more references we need
                remaining_needed = max_results - len(references)
                page_size = min(100, remaining_needed)  # AWS maximum is 100 for this API

                # Prepare list_references parameters
                params = {
                    'referenceStoreId': reference_store_id,
                    'maxResults': page_size,
                }
                if current_token:
                    params['nextToken'] = current_token

                # Add server-side name filter if provided
                if name_filter:
                    params['filter'] = {'name': name_filter}
                    logger.debug(f'Applying server-side name filter: {name_filter}')

                # Execute the list operation asynchronously with rate limiting
                await asyncio.sleep(
                    HEALTHOMICS_RATE_LIMIT_DELAY
                )  # Rate limiting: 10 requests per second
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.omics_client.list_references(**params)
                )

                # Add references from this page
                page_references = response.get('references', [])
                references.extend(page_references)
                total_scanned += len(page_references)

                # Check if there are more pages
                if response.get('nextToken'):
                    current_token = response.get('nextToken')

                    # If we have enough references, return with the continuation token
                    if len(references) >= max_results:
                        break
                else:
                    # No more pages available
                    current_token = None
                    break

        except ClientError as e:
            logger.error(f'Error listing references in reference store {reference_store_id}: {e}')
            raise

        # Trim to exact max_results if we got more
        if len(references) > max_results:
            references = references[:max_results]

        logger.debug(
            f'Listed {len(references)} references in reference store {reference_store_id} '
            f'(scanned {total_scanned}, next_token: {bool(current_token)})'
        )

        return references, current_token, total_scanned

    async def _search_single_reference_store_paginated(
        self,
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
        continuation_token: Optional[str] = None,
        max_results: int = 100,
    ) -> Tuple[List[GenomicsFile], Optional[str], int]:
        """Search a single HealthOmics reference store with pagination support.

        Args:
            store_id: ID of the reference store
            store_info: Store information from list_reference_stores
            file_type_filter: Optional file type filter
            search_terms: List of search terms to match against
            continuation_token: HealthOmics continuation token for this store
            max_results: Maximum number of results to return

        Returns:
            Tuple of (genomics_files, next_continuation_token, references_scanned)
        """
        try:
            logger.debug(f'Searching reference store {store_id} with pagination')

            # List references in the reference store with server-side filtering and pagination
            references = []
            next_token = continuation_token
            total_scanned = 0

            if search_terms:
                # Try server-side filtering for each search term
                for search_term in search_terms:
                    (
                        term_references,
                        term_next_token,
                        term_scanned,
                    ) = await self._list_references_with_filter_paginated(
                        store_id, search_term, next_token, max_results
                    )
                    references.extend(term_references)
                    total_scanned += term_scanned

                    if term_next_token:
                        next_token = term_next_token
                        break  # Stop at first term with more results
                    else:
                        next_token = None

                    # Check if we have enough results
                    if len(references) >= max_results:
                        break

                # If no server-side matches, fall back to getting all references
                if not references and not next_token:
                    logger.info(
                        f'No server-side matches for {search_terms}, falling back to client-side filtering'
                    )
                    (
                        references,
                        next_token,
                        fallback_scanned,
                    ) = await self._list_references_with_filter_paginated(
                        store_id, None, continuation_token, max_results
                    )
                    total_scanned += fallback_scanned

                # Remove duplicates based on reference ID
                seen_ids = set()
                unique_references = []
                for ref in references:
                    ref_id = ref.get('id')
                    if ref_id and ref_id not in seen_ids:
                        seen_ids.add(ref_id)
                        unique_references.append(ref)
                references = unique_references
            else:
                # No search terms, get all references
                (
                    references,
                    next_token,
                    total_scanned,
                ) = await self._list_references_with_filter_paginated(
                    store_id, None, continuation_token, max_results
                )

            logger.debug(
                f'Found {len(references)} references in store {store_id} (scanned {total_scanned})'
            )

            genomics_files = []
            for reference in references:
                genomics_file = await self._convert_reference_to_genomics_file(
                    reference, store_id, store_info, file_type_filter, search_terms
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} matching files in reference store {store_id}'
            )
            return genomics_files, next_token, total_scanned

        except Exception as e:
            logger.error(f'Error in paginated search of reference store {store_id}: {e}')
            raise

    async def _get_read_set_metadata(self, store_id: str, read_set_id: str) -> Dict[str, Any]:
        """Get detailed metadata for a read set using get-read-set-metadata API.

        Args:
            store_id: ID of the sequence store
            read_set_id: ID of the read set

        Returns:
            Dictionary containing detailed read set metadata

        Raises:
            ClientError: If API call fails
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.omics_client.get_read_set_metadata(
                    sequenceStoreId=store_id, id=read_set_id
                ),
            )
            return response
        except ClientError as e:
            logger.warning(f'Failed to get detailed metadata for read set {read_set_id}: {e}')
            return {}

    async def _get_read_set_tags(self, read_set_arn: str) -> Dict[str, str]:
        """Get tags for a read set using list-tags-for-resource API.

        Args:
            read_set_arn: ARN of the read set

        Returns:
            Dictionary of tag key-value pairs

        Raises:
            ClientError: If API call fails
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.omics_client.list_tags_for_resource(resourceArn=read_set_arn),
            )
            return response.get('tags', {})
        except ClientError as e:
            logger.debug(f'Failed to get tags for read set {read_set_arn}: {e}')
            return {}

    async def _convert_read_set_to_genomics_file(
        self,
        read_set: Dict[str, Any],
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> Optional[GenomicsFile]:
        """Convert a HealthOmics read set to a GenomicsFile if it matches search criteria.

        Args:
            read_set: Read set dictionary from list_read_sets
            store_id: ID of the sequence store
            store_info: Store information
            file_type_filter: Optional file type to filter by
            search_terms: List of search terms to match against

        Returns:
            GenomicsFile object if the read set matches criteria, None otherwise
        """
        try:
            read_set_id = read_set['id']
            read_set_name = read_set.get('name', read_set_id)

            # Get enhanced metadata for better file information
            enhanced_metadata = await self._get_read_set_metadata(store_id, read_set_id)

            # Use enhanced metadata if available, otherwise fall back to list response
            file_format = enhanced_metadata.get('fileType', read_set.get('fileType', 'FASTQ'))
            actual_size = 0
            files_info = enhanced_metadata.get('files', {})

            # Calculate actual file size from files information
            if 'source1' in files_info and 'contentLength' in files_info['source1']:
                actual_size = files_info['source1']['contentLength']

            # Determine file type based on read set type from HealthOmics metadata
            if file_format.upper() == 'FASTQ':
                detected_file_type = GenomicsFileType.FASTQ
            elif file_format.upper() == 'BAM':
                detected_file_type = GenomicsFileType.BAM
            elif file_format.upper() == 'CRAM':
                detected_file_type = GenomicsFileType.CRAM
            elif file_format.upper() == 'UBAM':
                detected_file_type = GenomicsFileType.BAM  # uBAM is still BAM format
            else:
                # Try to detect from name if available
                detected_file_type = self.file_type_detector.detect_file_type(read_set_name)
                if not detected_file_type:
                    # Use the actual file type from HealthOmics if detection fails
                    logger.warning(
                        f'Unknown file type {file_format} for read set {read_set_id}, using FASTQ as fallback'
                    )
                    detected_file_type = GenomicsFileType.FASTQ

            # Apply file type filter if specified
            if file_type_filter and detected_file_type.value != file_type_filter:
                return None

            # Filter out read sets that are not in ACTIVE status
            read_set_status = enhanced_metadata.get('status', read_set.get('status', ''))
            if read_set_status != HEALTHOMICS_STATUS_ACTIVE:
                logger.debug(f'Skipping read set {read_set_id} with status: {read_set_status}')
                return None

            # Get tags for the read set
            read_set_arn = enhanced_metadata.get(
                'arn',
                f'arn:{self._get_partition()}:omics:{self._get_region()}:{self._get_account_id()}:sequenceStore/{store_id}/readSet/{read_set_id}',
            )
            tags = await self._get_read_set_tags(read_set_arn)

            # Create metadata for pattern matching - include sequence store info
            metadata = {
                'name': read_set_name,
                'description': enhanced_metadata.get(
                    'description', read_set.get('description', '')
                ),
                'subject_id': enhanced_metadata.get('subjectId', read_set.get('subjectId', '')),
                'sample_id': enhanced_metadata.get('sampleId', read_set.get('sampleId', '')),
                'reference_arn': enhanced_metadata.get(
                    'referenceArn', read_set.get('referenceArn', '')
                ),
                'store_name': store_info.get('name', ''),
                'store_description': store_info.get('description', ''),
            }

            # Check if read set matches search terms (including tags as fallback)
            if search_terms:
                # First check metadata fields
                metadata_match = self._matches_search_terms_metadata(
                    read_set_name, metadata, search_terms
                )

                # If no metadata match and tags are available, check tags
                if not metadata_match and tags:
                    tag_score, _ = self.pattern_matcher.match_tags(tags, search_terms)
                    if tag_score == 0:
                        return None
                elif not metadata_match:
                    return None

            # Generate proper HealthOmics URI for read set data
            # Format: omics://account_id.storage.region.amazonaws.com/sequence_store_id/readSet/read_set_id/source1
            account_id = self._get_account_id()
            region = self._get_region()
            omics_uri = f'omics://{account_id}.storage.{region}.amazonaws.com/{store_id}/readSet/{read_set_id}/source1'

            # Create GenomicsFile object with enhanced metadata
            genomics_file = GenomicsFile(
                path=omics_uri,
                file_type=detected_file_type,
                size_bytes=actual_size,  # Use actual file size from enhanced metadata
                storage_class=HEALTHOMICS_STORAGE_CLASS_MANAGED,  # HealthOmics manages storage internally
                last_modified=enhanced_metadata.get(
                    'creationTime', read_set.get('creationTime', datetime.now())
                ),
                tags=tags,  # Include actual tags from HealthOmics
                source_system='sequence_store',
                metadata={
                    'store_id': store_id,
                    'store_name': store_info.get('name', ''),
                    'store_description': store_info.get('description', ''),
                    'read_set_id': read_set_id,
                    'read_set_name': read_set_name,
                    'subject_id': enhanced_metadata.get(
                        'subjectId', read_set.get('subjectId', '')
                    ),
                    'sample_id': enhanced_metadata.get('sampleId', read_set.get('sampleId', '')),
                    'reference_arn': enhanced_metadata.get(
                        'referenceArn', read_set.get('referenceArn', '')
                    ),
                    'status': enhanced_metadata.get('status', read_set.get('status', '')),
                    'sequence_information': enhanced_metadata.get(
                        'sequenceInformation', read_set.get('sequenceInformation', {})
                    ),
                    'files': files_info,  # Include detailed file information
                    'omics_uri': omics_uri,  # Store the clean URI for reference
                    's3_access_uri': files_info.get('source1', {})
                    .get('s3Access', {})
                    .get('s3Uri', ''),  # Include S3 URI if available
                    'account_id': account_id,  # Store for association engine
                    'region': region,  # Store for association engine
                },
            )

            # Store multi-source information for the file association engine
            if len([k for k in files_info.keys() if k.startswith('source')]) > 1:
                genomics_file.metadata['_healthomics_multi_source_info'] = {
                    'store_id': store_id,
                    'read_set_id': read_set_id,
                    'account_id': account_id,
                    'region': region,
                    'files': files_info,
                    'file_type': detected_file_type,
                    'tags': tags,
                    'metadata_base': {
                        'store_id': store_id,
                        'store_name': store_info.get('name', ''),
                        'store_description': store_info.get('description', ''),
                        'read_set_id': read_set_id,
                        'read_set_name': read_set_name,
                        'subject_id': enhanced_metadata.get(
                            'subjectId', read_set.get('subjectId', '')
                        ),
                        'sample_id': enhanced_metadata.get(
                            'sampleId', read_set.get('sampleId', '')
                        ),
                        'reference_arn': enhanced_metadata.get(
                            'referenceArn', read_set.get('referenceArn', '')
                        ),
                        'status': enhanced_metadata.get('status', read_set.get('status', '')),
                        'sequence_information': enhanced_metadata.get(
                            'sequenceInformation', read_set.get('sequenceInformation', {})
                        ),
                    },
                    'creation_time': enhanced_metadata.get(
                        'creationTime', read_set.get('creationTime', datetime.now())
                    ),
                    'storage_class': 'STANDARD',
                }

            return genomics_file

        except Exception as e:
            logger.error(
                f'Error converting read set {read_set.get("id", "unknown")} to GenomicsFile: {e}'
            )
            return None

    async def _get_reference_tags(self, reference_arn: str) -> Dict[str, str]:
        """Get tags for a reference using list-tags-for-resource API.

        Args:
            reference_arn: ARN of the reference

        Returns:
            Dictionary of tag key-value pairs

        Raises:
            ClientError: If API call fails
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.omics_client.list_tags_for_resource(resourceArn=reference_arn),
            )
            return response.get('tags', {})
        except ClientError as e:
            logger.debug(f'Failed to get tags for reference {reference_arn}: {e}')
            return {}

    async def _convert_reference_to_genomics_file(
        self,
        reference: Dict[str, Any],
        store_id: str,
        store_info: Dict[str, Any],
        file_type_filter: Optional[str],
        search_terms: List[str],
    ) -> Optional[GenomicsFile]:
        """Convert a HealthOmics reference to a GenomicsFile if it matches search criteria.

        Args:
            reference: Reference dictionary from list_references
            store_id: ID of the reference store
            store_info: Store information
            file_type_filter: Optional file type to filter by
            search_terms: List of search terms to match against

        Returns:
            GenomicsFile object if the reference matches criteria, None otherwise
        """
        try:
            reference_id = reference['id']
            reference_name = reference.get('name', reference_id)

            # References are typically FASTA files
            detected_file_type = GenomicsFileType.FASTA

            # Apply file type filter if specified
            if file_type_filter and detected_file_type.value != file_type_filter:
                return None

            # Filter out references that are not in ACTIVE status
            reference_status = reference.get('status', '')
            if reference_status != HEALTHOMICS_STATUS_ACTIVE:
                logger.debug(f'Skipping reference {reference_id} with status: {reference_status}')
                return None

            # Get tags for the reference
            reference_arn = reference.get(
                'arn',
                f'arn:{self._get_partition()}:omics:{self._get_region()}:{self._get_account_id()}:referenceStore/{store_id}/reference/{reference_id}',
            )
            tags = await self._get_reference_tags(reference_arn)

            # Create metadata for pattern matching - include reference store info
            metadata = {
                'name': reference_name,
                'description': reference.get('description', ''),
                'store_name': store_info.get('name', ''),
                'store_description': store_info.get('description', ''),
            }

            # Check if reference matches search terms (including tags as fallback)
            if search_terms:
                # First check metadata fields
                metadata_match = self._matches_search_terms_metadata(
                    reference_name, metadata, search_terms
                )

                # If no metadata match and tags are available, check tags
                if not metadata_match and tags:
                    tag_score, _ = self.pattern_matcher.match_tags(tags, search_terms)
                    if tag_score == 0:
                        logger.debug(
                            f'Reference "{reference_name}" did not match search terms {search_terms} in metadata or tags'
                        )
                        return None
                elif not metadata_match:
                    logger.debug(
                        f'Reference "{reference_name}" did not match search terms {search_terms} in client-side filtering'
                    )
                    return None
                else:
                    logger.debug(
                        f'Reference "{reference_name}" matched search terms {search_terms} in client-side filtering'
                    )

            # Generate proper HealthOmics URI for reference data
            # Format: omics://account_id.storage.region.amazonaws.com/reference_store_id/reference/reference_id/source
            account_id = self._get_account_id()
            region = self._get_region()
            omics_uri = f'omics://{account_id}.storage.{region}.amazonaws.com/{store_id}/reference/{reference_id}/source'

            # Get file size information
            source_size = 0
            index_size = 0

            # Check if files information is available in the reference response
            if 'files' in reference:
                files_info = reference['files']
                if 'source' in files_info and 'contentLength' in files_info['source']:
                    source_size = files_info['source']['contentLength']
                if 'index' in files_info and 'contentLength' in files_info['index']:
                    index_size = files_info['index']['contentLength']
            else:
                # Files information not available in ListReferences response
                # Call GetReferenceMetadata to get file size information
                try:
                    logger.debug(
                        f'Getting metadata for reference {reference_id} to retrieve file sizes'
                    )
                    loop = asyncio.get_event_loop()
                    metadata_response = await loop.run_in_executor(
                        None,
                        lambda: self.omics_client.get_reference_metadata(
                            referenceStoreId=store_id, id=reference_id
                        ),
                    )

                    if 'files' in metadata_response:
                        files_info = metadata_response['files']
                        if 'source' in files_info and 'contentLength' in files_info['source']:
                            source_size = files_info['source']['contentLength']
                        if 'index' in files_info and 'contentLength' in files_info['index']:
                            index_size = files_info['index']['contentLength']
                        logger.debug(
                            f'Retrieved file sizes: source={source_size}, index={index_size}'
                        )
                except Exception as e:
                    logger.warning(f'Failed to get reference metadata for {reference_id}: {e}')
                    # Continue with 0 sizes if metadata call fails

            # Create GenomicsFile object
            genomics_file = GenomicsFile(
                path=omics_uri,
                file_type=detected_file_type,
                size_bytes=source_size,
                storage_class='STANDARD',  # HealthOmics manages storage internally
                last_modified=reference.get('creationTime', datetime.now()),
                tags=tags,  # Include actual tags from HealthOmics
                source_system='reference_store',
                metadata={
                    'store_id': store_id,
                    'store_name': store_info.get('name', ''),
                    'store_description': store_info.get('description', ''),
                    'reference_id': reference_id,
                    'reference_name': reference_name,
                    'status': reference.get('status', ''),
                    'md5': reference.get('md5', ''),
                    'omics_uri': omics_uri,  # Store the clean URI for reference
                    'index_uri': f'omics://{account_id}.storage.{region}.amazonaws.com/{store_id}/reference/{reference_id}/index',
                },
            )

            # Store index file information for the file association engine to use
            genomics_file.metadata['_healthomics_index_info'] = {
                'index_uri': f'omics://{account_id}.storage.{region}.amazonaws.com/{store_id}/reference/{reference_id}/index',
                'index_size': index_size,
                'store_id': store_id,
                'store_name': store_info.get('name', ''),
                'reference_id': reference_id,
                'reference_name': reference_name,
                'status': reference.get('status', ''),
                'md5': reference.get('md5', ''),
            }

            return genomics_file

        except Exception as e:
            logger.error(
                f'Error converting reference {reference.get("id", "unknown")} to GenomicsFile: {e}'
            )
            return None

    def _matches_search_terms_metadata(
        self, name: str, metadata: Dict[str, Any], search_terms: List[str]
    ) -> bool:
        """Check if a HealthOmics resource matches the search terms based on name and metadata.

        Args:
            name: Resource name
            metadata: Resource metadata dictionary
            search_terms: List of search terms to match against

        Returns:
            True if the resource matches the search terms, False otherwise
        """
        if not search_terms:
            return True

        logger.debug(f'Checking if name "{name}" matches search terms {search_terms}')

        # Check name match
        name_score, reasons = self.pattern_matcher.calculate_match_score(name, search_terms)
        if name_score > 0:
            logger.debug(f'Name match found: score={name_score}, reasons={reasons}')
            return True

        # Check metadata values
        for key, value in metadata.items():
            if isinstance(value, str) and value:
                value_score, value_reasons = self.pattern_matcher.calculate_match_score(
                    value, search_terms
                )
                if value_score > 0:
                    logger.debug(
                        f'Metadata match found: key={key}, value={value}, score={value_score}, reasons={value_reasons}'
                    )
                    return True

        logger.debug(f'No match found for name "{name}" with search terms {search_terms}')
        return False

    def _get_region(self) -> str:
        """Get the current AWS region.

        Returns:
            AWS region string
        """
        # Import here to avoid circular imports
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_region

        return get_region()

    def _get_account_id(self) -> str:
        """Get the current AWS account ID.

        Returns:
            AWS account ID string
        """
        # Import here to avoid circular imports
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_account_id

        return get_account_id()

    def _get_partition(self) -> str:
        """Get the current AWS partition.

        Returns:
            AWS partition string (e.g., 'aws', 'aws-cn', 'aws-us-gov')
        """
        # Import here to avoid circular imports
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_partition

        return get_partition()
