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

"""S3 search engine for genomics files."""

import asyncio
import hashlib
import time
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_S3_PAGE_SIZE
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
    SearchConfig,
    StoragePaginationRequest,
    StoragePaginationResponse,
    build_s3_uri,
    create_genomics_file_from_s3_object,
)
from awslabs.aws_healthomics_mcp_server.search.file_type_detector import FileTypeDetector
from awslabs.aws_healthomics_mcp_server.search.pattern_matcher import PatternMatcher
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import parse_s3_path
from awslabs.aws_healthomics_mcp_server.utils.search_config import (
    get_genomics_search_config,
    validate_bucket_access_permissions,
)
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple


class S3SearchEngine:
    """Search engine for genomics files in S3 buckets."""

    def __init__(self, config: SearchConfig, _internal: bool = False):
        """Initialize the S3 search engine.

        Args:
            config: Search configuration containing S3 bucket paths and other settings
            _internal: Internal flag to prevent direct instantiation. Use from_environment() instead.

        Raises:
            RuntimeError: If called directly without _internal=True
        """
        if not _internal:
            raise RuntimeError(
                'S3SearchEngine should not be instantiated directly. '
                'Use S3SearchEngine.from_environment() to ensure proper bucket access validation, '
                'or S3SearchEngine._create_for_testing() for tests.'
            )

        self.config = config
        self.session = get_aws_session()
        self.s3_client = self.session.client('s3')
        self.file_type_detector = FileTypeDetector()
        self.pattern_matcher = PatternMatcher()

        # Caching for optimization
        self._tag_cache = {}  # Cache for object tags
        self._result_cache = {}  # Cache for search results

        logger.info(
            f'S3SearchEngine initialized with tag search: {config.enable_s3_tag_search}, '
            f'tag batch size: {config.max_tag_retrieval_batch_size}, '
            f'result cache TTL: {config.result_cache_ttl_seconds}s, '
            f'tag cache TTL: {config.tag_cache_ttl_seconds}s'
        )

    @classmethod
    def from_environment(cls) -> 'S3SearchEngine':
        """Create an S3SearchEngine using configuration from environment variables.

        Returns:
            S3SearchEngine instance configured from environment

        Raises:
            ValueError: If configuration is invalid or no S3 buckets are accessible
        """
        config = get_genomics_search_config()

        # Validate bucket access during initialization (only if configured buckets exist)
        if config.s3_bucket_paths:
            try:
                accessible_buckets = validate_bucket_access_permissions()
                # Update config to only include accessible buckets
                original_count = len(config.s3_bucket_paths)
                config.s3_bucket_paths = accessible_buckets

                if len(accessible_buckets) < original_count:
                    logger.warning(
                        f'Only {len(accessible_buckets)} of {original_count} configured buckets are accessible'
                    )
                else:
                    logger.info(f'All {len(accessible_buckets)} configured buckets are accessible')

            except ValueError as e:
                logger.error(f'S3 bucket access validation failed: {e}')
                raise ValueError(f'Cannot create S3SearchEngine: {e}') from e
        else:
            logger.info(
                'No configured S3 bucket paths. S3SearchEngine created for adhoc bucket searches.'
            )

        return cls(config, _internal=True)

    @classmethod
    def _create_for_testing(cls, config: SearchConfig) -> 'S3SearchEngine':
        """Create an S3SearchEngine for testing purposes without bucket validation.

        This method bypasses bucket access validation and should only be used in tests.

        Args:
            config: Search configuration containing S3 bucket paths and other settings

        Returns:
            S3SearchEngine instance configured for testing
        """
        return cls(config, _internal=True)

    async def search_buckets(
        self, bucket_paths: List[str], file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search for genomics files across multiple S3 bucket paths with result caching.

        Args:
            bucket_paths: List of S3 bucket paths to search
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects matching the search criteria

        Raises:
            ValueError: If bucket paths are invalid
            ClientError: If S3 access fails
        """
        if not bucket_paths:
            logger.warning('No S3 bucket paths provided for search')
            return []

        # Check result cache first
        cache_key = self._create_search_cache_key(bucket_paths, file_type, search_terms)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            logger.info(f'Returning cached search results for {len(bucket_paths)} bucket paths')
            return cached_result

        all_files = []

        # Create tasks for concurrent bucket searches
        tasks = []
        for bucket_path in bucket_paths:
            task = self._search_single_bucket_path_optimized(bucket_path, file_type, search_terms)
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
                logger.error(f'Error searching bucket path {bucket_paths[i]}: {result}')
            elif isinstance(result, list):
                all_files.extend(result)
            else:
                logger.warning(f'Unexpected result type from bucket path: {type(result)}')

        # Cache the results
        self._cache_search_result(cache_key, all_files)

        return all_files

    async def search_buckets_paginated(
        self,
        bucket_paths: List[str],
        file_type: Optional[str],
        search_terms: List[str],
        pagination_request: 'StoragePaginationRequest',
    ) -> 'StoragePaginationResponse':
        """Search for genomics files across multiple S3 bucket paths with storage-level pagination.

        This method implements efficient pagination by:
        1. Using native S3 continuation tokens for each bucket
        2. Implementing buffer-based result fetching for global ranking
        3. Handling parallel bucket searches with individual pagination state

        Args:
            bucket_paths: List of S3 bucket paths to search
            file_type: Optional file type filter
            search_terms: List of search terms to match against
            pagination_request: Pagination parameters and continuation tokens

        Returns:
            StoragePaginationResponse with paginated results and continuation tokens

        Raises:
            ValueError: If bucket paths are invalid
            ClientError: If S3 access fails
        """
        from awslabs.aws_healthomics_mcp_server.models import (
            GlobalContinuationToken,
            StoragePaginationResponse,
        )

        if not bucket_paths:
            logger.warning('No S3 bucket paths provided for paginated search')
            return StoragePaginationResponse(results=[], has_more_results=False)

        # Parse continuation token to get per-bucket tokens
        global_token = GlobalContinuationToken()
        if pagination_request.continuation_token:
            try:
                global_token = GlobalContinuationToken.decode(
                    pagination_request.continuation_token
                )
            except ValueError as e:
                logger.warning(f'Invalid continuation token, starting fresh search: {e}')
                global_token = GlobalContinuationToken()

        all_files = []
        total_scanned = 0
        bucket_tokens = {}
        has_more_results = False
        buffer_overflow = False

        # Create tasks for concurrent paginated bucket searches
        tasks = []
        for bucket_path in bucket_paths:
            bucket_token = global_token.s3_tokens.get(bucket_path)
            task = self._search_single_bucket_path_paginated(
                bucket_path, file_type, search_terms, bucket_token, pagination_request.buffer_size
            )
            tasks.append((bucket_path, task))

        # Execute searches concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)

        async def bounded_search(bucket_path_task):
            bucket_path, task = bucket_path_task
            async with semaphore:
                return bucket_path, await task

        results = await asyncio.gather(
            *[bounded_search(task_tuple) for task_tuple in tasks], return_exceptions=True
        )

        # Collect results and handle exceptions
        for result in results:
            if isinstance(result, Exception):
                logger.error(f'Error in paginated bucket search: {result}')
                continue
            elif isinstance(result, tuple) and len(result) == 2:
                bucket_path, bucket_result = result
            else:
                logger.warning(f'Unexpected result type in paginated search: {type(result)}')
                continue
            bucket_files, next_token, scanned_count = bucket_result

            all_files.extend(bucket_files)
            total_scanned += scanned_count

            # Store continuation token for this bucket
            if next_token:
                bucket_tokens[bucket_path] = next_token
                has_more_results = True

        # Check if we exceeded the buffer size (indicates potential ranking issues)
        if len(all_files) > pagination_request.buffer_size:
            buffer_overflow = True
            logger.warning(
                f'Buffer overflow: got {len(all_files)} results, buffer size {pagination_request.buffer_size}'
            )

        # Create next continuation token
        next_continuation_token = None
        if has_more_results:
            next_global_token = GlobalContinuationToken(
                s3_tokens=bucket_tokens,
                healthomics_sequence_token=global_token.healthomics_sequence_token,
                healthomics_reference_token=global_token.healthomics_reference_token,
                page_number=global_token.page_number + 1,
                total_results_seen=global_token.total_results_seen + len(all_files),
            )
            next_continuation_token = next_global_token.encode()

        logger.info(
            f'S3 paginated search completed: {len(all_files)} results, '
            f'{total_scanned} objects scanned, has_more: {has_more_results}'
        )

        return StoragePaginationResponse(
            results=all_files,
            next_continuation_token=next_continuation_token,
            has_more_results=has_more_results,
            total_scanned=total_scanned,
            buffer_overflow=buffer_overflow,
        )

    async def _search_single_bucket_path_optimized(
        self, bucket_path: str, file_type: Optional[str], search_terms: List[str]
    ) -> List[GenomicsFile]:
        """Search a single S3 bucket path for genomics files using optimized strategy.

        This method implements smart filtering to minimize S3 API calls:
        1. List all objects (single API call per page of objects)
        2. Filter by file type and path patterns (no additional S3 calls)
        3. Only retrieve tags for objects that need tag-based matching (batch calls)

        Args:
            bucket_path: S3 bucket path (e.g., 's3://bucket-name/prefix/')
            file_type: Optional file type filter
            search_terms: List of search terms to match against

        Returns:
            List of GenomicsFile objects found in this bucket path
        """
        try:
            bucket_name, prefix = parse_s3_path(bucket_path)

            # Validate bucket access
            await self._validate_bucket_access(bucket_name)

            # Phase 1: Get all objects (minimal S3 calls)
            objects = await self._list_s3_objects(bucket_name, prefix)
            logger.debug(f'Listed {len(objects)} objects in {bucket_path}')

            # Phase 2: Filter by file type and path patterns (no S3 calls)
            path_matched_objects = []
            objects_needing_tags = []

            for obj in objects:
                key = obj['Key']

                # File type filtering
                detected_file_type = self.file_type_detector.detect_file_type(key)
                if not detected_file_type:
                    continue

                if not self._matches_file_type_filter(detected_file_type, file_type):
                    continue

                # Path-based search term matching
                if search_terms:
                    # Use centralized URI construction for pattern matching
                    s3_path = build_s3_uri(bucket_name, key)
                    path_score, _ = self.pattern_matcher.match_file_path(s3_path, search_terms)
                    if path_score > 0:
                        # Path matched, no need for tags
                        path_matched_objects.append((obj, {}, detected_file_type))
                        continue
                    elif self.config.enable_s3_tag_search:
                        # Need to check tags
                        objects_needing_tags.append((obj, detected_file_type))
                    # If path doesn't match and tag search is disabled, skip
                else:
                    # No search terms, include all type-matched files
                    path_matched_objects.append((obj, {}, detected_file_type))

            logger.debug(
                f'After path filtering: {len(path_matched_objects)} path matches, '
                f'{len(objects_needing_tags)} objects need tag checking'
            )

            # Phase 3: Batch retrieve tags only for objects that need them
            tag_matched_objects = []
            if objects_needing_tags and self.config.enable_s3_tag_search:
                object_keys = [obj[0]['Key'] for obj in objects_needing_tags]
                tag_map = await self._get_tags_for_objects_batch(bucket_name, object_keys)

                for obj, detected_file_type in objects_needing_tags:
                    key = obj['Key']
                    tags = tag_map.get(key, {})

                    # Check tag-based matching
                    if search_terms:
                        tag_score, _ = self.pattern_matcher.match_tags(tags, search_terms)
                        if tag_score > 0:
                            tag_matched_objects.append((obj, tags, detected_file_type))

            # Phase 4: Convert to GenomicsFile objects
            all_matched_objects = path_matched_objects + tag_matched_objects
            genomics_files = []

            for obj, tags, detected_file_type in all_matched_objects:
                genomics_file = self._create_genomics_file_from_object(
                    obj, bucket_name, tags, detected_file_type
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.info(
                f'Found {len(genomics_files)} files in {bucket_path} '
                f'({len(path_matched_objects)} path matches, {len(tag_matched_objects)} tag matches)'
            )
            return genomics_files

        except Exception as e:
            logger.error(f'Error searching bucket path {bucket_path}: {e}')
            raise

    async def _search_single_bucket_path_paginated(
        self,
        bucket_path: str,
        file_type: Optional[str],
        search_terms: List[str],
        continuation_token: Optional[str] = None,
        max_results: int = DEFAULT_S3_PAGE_SIZE,
    ) -> Tuple[List[GenomicsFile], Optional[str], int]:
        """Search a single S3 bucket path with pagination support.

        This method implements efficient pagination by:
        1. Using native S3 continuation tokens for object listing
        2. Filtering during object listing to minimize API calls
        3. Implementing buffer-based result fetching for ranking

        Args:
            bucket_path: S3 bucket path (e.g., 's3://bucket-name/prefix/')
            file_type: Optional file type filter
            search_terms: List of search terms to match against
            continuation_token: S3 continuation token for this bucket
            max_results: Maximum number of results to return

        Returns:
            Tuple of (genomics_files, next_continuation_token, objects_scanned)
        """
        try:
            bucket_name, prefix = parse_s3_path(bucket_path)

            # Validate bucket access
            await self._validate_bucket_access(bucket_name)

            # Phase 1: Get objects with pagination
            objects, next_token, total_scanned = await self._list_s3_objects_paginated(
                bucket_name, prefix, continuation_token, max_results
            )
            logger.debug(
                f'Listed {len(objects)} objects in {bucket_path} (scanned {total_scanned})'
            )

            # Phase 2: Filter by file type and path patterns (no S3 calls)
            path_matched_objects = []
            objects_needing_tags = []

            for obj in objects:
                key = obj['Key']

                # File type filtering
                detected_file_type = self.file_type_detector.detect_file_type(key)
                if not detected_file_type:
                    continue

                if not self._matches_file_type_filter(detected_file_type, file_type):
                    continue

                # Path-based search term matching
                if search_terms:
                    # Use centralized URI construction for pattern matching
                    s3_path = build_s3_uri(bucket_name, key)
                    path_score, _ = self.pattern_matcher.match_file_path(s3_path, search_terms)
                    if path_score > 0:
                        # Path matched, no need for tags
                        path_matched_objects.append((obj, {}, detected_file_type))
                        continue
                    elif self.config.enable_s3_tag_search:
                        # Need to check tags
                        objects_needing_tags.append((obj, detected_file_type))
                    # If path doesn't match and tag search is disabled, skip
                else:
                    # No search terms, include all type-matched files
                    path_matched_objects.append((obj, {}, detected_file_type))

            logger.debug(
                f'After path filtering: {len(path_matched_objects)} path matches, '
                f'{len(objects_needing_tags)} objects need tag checking'
            )

            # Phase 3: Batch retrieve tags only for objects that need them
            tag_matched_objects = []
            if objects_needing_tags and self.config.enable_s3_tag_search:
                object_keys = [obj[0]['Key'] for obj in objects_needing_tags]
                tag_map = await self._get_tags_for_objects_batch(bucket_name, object_keys)

                for obj, detected_file_type in objects_needing_tags:
                    key = obj['Key']
                    tags = tag_map.get(key, {})

                    # Check tag-based matching
                    if search_terms:
                        tag_score, _ = self.pattern_matcher.match_tags(tags, search_terms)
                        if tag_score > 0:
                            tag_matched_objects.append((obj, tags, detected_file_type))

            # Phase 4: Convert to GenomicsFile objects
            all_matched_objects = path_matched_objects + tag_matched_objects
            genomics_files = []

            for obj, tags, detected_file_type in all_matched_objects:
                genomics_file = self._create_genomics_file_from_object(
                    obj, bucket_name, tags, detected_file_type
                )
                if genomics_file:
                    genomics_files.append(genomics_file)

            logger.debug(
                f'Found {len(genomics_files)} files in {bucket_path} '
                f'({len(path_matched_objects)} path matches, {len(tag_matched_objects)} tag matches)'
            )

            return genomics_files, next_token, total_scanned

        except Exception as e:
            logger.error(f'Error in paginated search of bucket path {bucket_path}: {e}')
            raise

    async def _validate_bucket_access(self, bucket_name: str) -> None:
        """Validate that we have access to the specified S3 bucket.

        Args:
            bucket_name: Name of the S3 bucket

        Raises:
            ClientError: If bucket access validation fails
        """
        try:
            # Use head_bucket to check if bucket exists and we have access
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.s3_client.head_bucket(Bucket=bucket_name)
            )
            logger.debug(f'Validated access to bucket: {bucket_name}')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ClientError(
                    {
                        'Error': {
                            'Code': 'NoSuchBucket',
                            'Message': f'Bucket {bucket_name} does not exist',
                        }
                    },
                    'HeadBucket',
                )
            elif error_code == '403':
                raise ClientError(
                    {
                        'Error': {
                            'Code': 'AccessDenied',
                            'Message': f'Access denied to bucket {bucket_name}',
                        }
                    },
                    'HeadBucket',
                )
            else:
                raise

    async def _list_s3_objects(self, bucket_name: str, prefix: str) -> List[Dict[str, Any]]:
        """List objects in an S3 bucket with the given prefix.

        Args:
            bucket_name: Name of the S3 bucket
            prefix: Object key prefix to filter by

        Returns:
            List of S3 object dictionaries
        """
        objects = []
        continuation_token = None

        while True:
            try:
                # Prepare list_objects_v2 parameters
                params = {
                    'Bucket': bucket_name,
                    'Prefix': prefix,
                    'MaxKeys': DEFAULT_S3_PAGE_SIZE,
                }

                if continuation_token:
                    params['ContinuationToken'] = continuation_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.s3_client.list_objects_v2(**params)
                )

                # Add objects from this page
                if 'Contents' in response:
                    objects.extend(response['Contents'])

                # Check if there are more pages
                if response.get('IsTruncated', False):
                    continuation_token = response.get('NextContinuationToken')
                else:
                    break

            except ClientError as e:
                logger.error(
                    f'Error listing objects in bucket {bucket_name} with prefix {prefix}: {e}'
                )
                raise

        logger.debug(f'Listed {len(objects)} objects in s3://{bucket_name}/{prefix}')
        return objects

    async def _list_s3_objects_paginated(
        self,
        bucket_name: str,
        prefix: str,
        continuation_token: Optional[str] = None,
        max_results: int = DEFAULT_S3_PAGE_SIZE,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """List objects in an S3 bucket with pagination support.

        Args:
            bucket_name: Name of the S3 bucket
            prefix: Object key prefix to filter by
            continuation_token: S3 continuation token from previous request
            max_results: Maximum number of objects to return

        Returns:
            Tuple of (objects, next_continuation_token, total_objects_scanned)
        """
        objects = []
        total_scanned = 0
        current_token = continuation_token

        try:
            while len(objects) < max_results:
                # Calculate how many more objects we need
                remaining_needed = max_results - len(objects)
                page_size = min(DEFAULT_S3_PAGE_SIZE, remaining_needed)

                # Prepare list_objects_v2 parameters
                params = {
                    'Bucket': bucket_name,
                    'Prefix': prefix,
                    'MaxKeys': page_size,
                }

                if current_token:
                    params['ContinuationToken'] = current_token

                # Execute the list operation asynchronously
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.s3_client.list_objects_v2(**params)
                )

                # Add objects from this page
                page_objects = response.get('Contents', [])
                objects.extend(page_objects)
                total_scanned += len(page_objects)

                # Check if there are more pages
                if response.get('IsTruncated', False):
                    current_token = response.get('NextContinuationToken')

                    # If we have enough objects, return with the continuation token
                    if len(objects) >= max_results:
                        break
                else:
                    # No more pages available
                    current_token = None
                    break

        except ClientError as e:
            logger.error(
                f'Error listing objects in bucket {bucket_name} with prefix {prefix}: {e}'
            )
            raise

        # Trim to exact max_results if we got more
        if len(objects) > max_results:
            objects = objects[:max_results]

        logger.debug(
            f'Listed {len(objects)} objects in s3://{bucket_name}/{prefix} '
            f'(scanned {total_scanned}, next_token: {bool(current_token)})'
        )

        return objects, current_token, total_scanned

    def _create_genomics_file_from_object(
        self,
        s3_object: Dict[str, Any],
        bucket_name: str,
        tags: Dict[str, str],
        detected_file_type: GenomicsFileType,
    ) -> GenomicsFile:
        """Create a GenomicsFile object from S3 object metadata.

        Args:
            s3_object: S3 object dictionary from list_objects_v2
            bucket_name: Name of the S3 bucket
            tags: Object tags (already retrieved)
            detected_file_type: Already detected file type

        Returns:
            GenomicsFile object
        """
        # Use centralized utility function - no manual URI construction needed
        return create_genomics_file_from_s3_object(
            bucket=bucket_name,
            s3_object=s3_object,
            file_type=detected_file_type,
            tags=tags,
            source_system='s3',
            metadata={
                'etag': s3_object.get('ETag', '').strip('"'),
            },
        )

    async def _get_object_tags_cached(self, bucket_name: str, key: str) -> Dict[str, str]:
        """Get tags for an S3 object with caching.

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key

        Returns:
            Dictionary of object tags
        """
        cache_key = f'{bucket_name}/{key}'

        # Check cache first
        if cache_key in self._tag_cache:
            cached_entry = self._tag_cache[cache_key]
            if time.time() - cached_entry['timestamp'] < self.config.tag_cache_ttl_seconds:
                return cached_entry['tags']
            else:
                # Remove expired entry
                del self._tag_cache[cache_key]

        # Retrieve from S3 and cache
        tags = await self._get_object_tags(bucket_name, key)

        # Check if we need to clean up before adding
        if len(self._tag_cache) >= self.config.max_tag_cache_size:
            self._cleanup_cache_by_size(
                self._tag_cache,
                self.config.max_tag_cache_size,
                self.config.cache_cleanup_keep_ratio,
            )

        self._tag_cache[cache_key] = {'tags': tags, 'timestamp': time.time()}

        return tags

    async def _get_object_tags(self, bucket_name: str, key: str) -> Dict[str, str]:
        """Get tags for an S3 object.

        Args:
            bucket_name: Name of the S3 bucket
            key: Object key

        Returns:
            Dictionary of object tags
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.s3_client.get_object_tagging(Bucket=bucket_name, Key=key)
            )

            # Convert tag list to dictionary
            tags = {}
            for tag in response.get('TagSet', []):
                tags[tag['Key']] = tag['Value']

            return tags

        except ClientError as e:
            # If we can't get tags (e.g., no permission), return empty dict
            logger.debug(f'Could not get tags for s3://{bucket_name}/{key}: {e}')
            return {}

    async def _get_tags_for_objects_batch(
        self, bucket_name: str, object_keys: List[str]
    ) -> Dict[str, Dict[str, str]]:
        """Retrieve tags for multiple objects efficiently using batching and caching.

        Args:
            bucket_name: Name of the S3 bucket
            object_keys: List of object keys to get tags for

        Returns:
            Dictionary mapping object keys to their tags
        """
        if not object_keys:
            return {}

        # Check cache for existing entries
        tag_map = {}
        keys_to_fetch = []

        for key in object_keys:
            cache_key = f'{bucket_name}/{key}'
            if cache_key in self._tag_cache:
                cached_entry = self._tag_cache[cache_key]
                if time.time() - cached_entry['timestamp'] < self.config.tag_cache_ttl_seconds:
                    tag_map[key] = cached_entry['tags']
                    continue
                else:
                    # Remove expired entry
                    del self._tag_cache[cache_key]

            keys_to_fetch.append(key)

        if not keys_to_fetch:
            logger.debug(f'All {len(object_keys)} object tags found in cache')
            return tag_map

        logger.debug(
            f'Fetching tags for {len(keys_to_fetch)} objects (batch size limit: {self.config.max_tag_retrieval_batch_size})'
        )

        # Process in batches to avoid overwhelming the API
        batch_size = min(self.config.max_tag_retrieval_batch_size, len(keys_to_fetch))
        semaphore = asyncio.Semaphore(10)  # Limit concurrent tag retrievals

        async def get_single_tag(key: str) -> Tuple[str, Dict[str, str]]:
            async with semaphore:
                tags = await self._get_object_tags_cached(bucket_name, key)
                return key, tags

        # Process keys in batches
        for i in range(0, len(keys_to_fetch), batch_size):
            batch_keys = keys_to_fetch[i : i + batch_size]

            # Execute batch in parallel
            tasks = [get_single_tag(key) for key in batch_keys]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f'Failed to get tags in batch: {result}')
                elif isinstance(result, tuple) and len(result) == 2:
                    key, tags = result
                    tag_map[key] = tags
                else:
                    logger.warning(f'Unexpected result type in tag batch: {type(result)}')

        logger.debug(f'Retrieved tags for {len(tag_map)} objects total')
        return tag_map

    def _matches_file_type_filter(
        self, detected_file_type: GenomicsFileType, file_type_filter: Optional[str]
    ) -> bool:
        """Check if a detected file type matches the file type filter.

        Args:
            detected_file_type: The detected file type
            file_type_filter: Optional file type filter

        Returns:
            True if the file type matches the filter or no filter is specified
        """
        if not file_type_filter:
            return True

        # Include the requested file type
        if detected_file_type.value == file_type_filter:
            return True

        # Also include index files that might be associated with the requested type
        if self._is_related_index_file(detected_file_type, file_type_filter):
            return True

        return False

    def _create_search_cache_key(
        self, bucket_paths: List[str], file_type: Optional[str], search_terms: List[str]
    ) -> str:
        """Create a cache key for search results.

        Args:
            bucket_paths: List of S3 bucket paths
            file_type: Optional file type filter
            search_terms: List of search terms

        Returns:
            Cache key string
        """
        # Create a deterministic cache key from search parameters
        key_data = {
            'bucket_paths': sorted(bucket_paths),  # Sort for consistency
            'file_type': file_type or '',
            'search_terms': sorted(search_terms),  # Sort for consistency
        }

        # Create hash of the key data
        key_str = str(key_data)
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[List[GenomicsFile]]:
        """Get cached search result if available and not expired.

        Args:
            cache_key: Cache key for the search

        Returns:
            Cached result if available and valid, None otherwise
        """
        if cache_key in self._result_cache:
            cached_entry = self._result_cache[cache_key]
            if time.time() - cached_entry['timestamp'] < self.config.result_cache_ttl_seconds:
                logger.debug(f'Cache hit for search key: {cache_key}')
                return cached_entry['results']
            else:
                # Remove expired entry
                del self._result_cache[cache_key]
                logger.debug(f'Cache expired for search key: {cache_key}')

        return None

    def _cache_search_result(self, cache_key: str, results: List[GenomicsFile]) -> None:
        """Cache search results.

        Args:
            cache_key: Cache key for the search
            results: Search results to cache
        """
        if self.config.result_cache_ttl_seconds > 0:  # Only cache if TTL > 0
            # Check if we need to clean up before adding
            if len(self._result_cache) >= self.config.max_result_cache_size:
                self._cleanup_cache_by_size(
                    self._result_cache,
                    self.config.max_result_cache_size,
                    self.config.cache_cleanup_keep_ratio,
                )

            self._result_cache[cache_key] = {'results': results, 'timestamp': time.time()}
            logger.debug(f'Cached {len(results)} results for search key: {cache_key}')

    def _matches_search_terms(
        self, s3_path: str, tags: Dict[str, str], search_terms: List[str]
    ) -> bool:
        """Check if a file matches the search terms.

        Args:
            s3_path: Full S3 path of the file
            tags: Dictionary of object tags
            search_terms: List of search terms to match against

        Returns:
            True if the file matches the search terms, False otherwise
        """
        if not search_terms:
            return True

        # Use pattern matcher to check if any search term matches the path or tags
        # Check path match
        path_score, _ = self.pattern_matcher.match_file_path(s3_path, search_terms)
        if path_score > 0:
            return True

        # Check tag matches
        tag_score, _ = self.pattern_matcher.match_tags(tags, search_terms)
        if tag_score > 0:
            return True

        return False

    def _is_related_index_file(
        self, detected_file_type: GenomicsFileType, requested_file_type: str
    ) -> bool:
        """Check if a detected file type is a related index file for the requested file type.

        Args:
            detected_file_type: The detected file type of the current file
            requested_file_type: The file type being searched for

        Returns:
            True if the detected file type is a related index file
        """
        # Define relationships between primary file types and their index files
        index_relationships = {
            'bam': [GenomicsFileType.BAI],
            'cram': [GenomicsFileType.CRAI],
            'fasta': [
                GenomicsFileType.FAI,
                GenomicsFileType.DICT,
                GenomicsFileType.BWA_AMB,
                GenomicsFileType.BWA_ANN,
                GenomicsFileType.BWA_BWT,
                GenomicsFileType.BWA_PAC,
                GenomicsFileType.BWA_SA,
            ],
            'fa': [GenomicsFileType.FAI, GenomicsFileType.DICT],
            'fna': [GenomicsFileType.FAI, GenomicsFileType.DICT],
            'vcf': [GenomicsFileType.TBI, GenomicsFileType.CSI],
            'gvcf': [GenomicsFileType.TBI, GenomicsFileType.CSI],
            'bcf': [GenomicsFileType.CSI],
        }

        related_indexes = index_relationships.get(requested_file_type, [])
        return detected_file_type in related_indexes

    def _cleanup_cache_by_size(self, cache_dict: Dict, max_size: int, keep_ratio: float) -> None:
        """Clean up cache when it exceeds max size, prioritizing expired entries first.

        Strategy:
        1. First: Remove all expired entries (regardless of age)
        2. Then: If still over size limit, remove oldest non-expired entries

        Args:
            cache_dict: Cache dictionary to clean up
            max_size: Maximum allowed cache size
            keep_ratio: Ratio of entries to keep (e.g., 0.8 = keep 80%)
        """
        if len(cache_dict) < max_size:
            return

        current_time = time.time()
        target_size = int(max_size * keep_ratio)

        # Determine TTL based on cache type (check if it's tag cache or result cache)
        # We can identify this by checking if entries have 'tags' key (tag cache) or 'results' key (result cache)
        sample_entry = next(iter(cache_dict.values())) if cache_dict else None
        if sample_entry and 'tags' in sample_entry:
            ttl_seconds = self.config.tag_cache_ttl_seconds
            cache_type = 'tag'
        else:
            ttl_seconds = self.config.result_cache_ttl_seconds
            cache_type = 'result'

        # Separate expired and valid entries
        expired_items = []
        valid_items = []

        for key, entry in cache_dict.items():
            if current_time - entry['timestamp'] >= ttl_seconds:
                expired_items.append((key, entry))
            else:
                valid_items.append((key, entry))

        # Phase 1: Remove all expired items first
        expired_count = len(expired_items)
        for key, _ in expired_items:
            del cache_dict[key]

        # Phase 2: If still over target size, remove oldest valid items
        remaining_count = len(cache_dict)
        additional_removals = 0

        if remaining_count > target_size:
            # Sort valid items by timestamp (oldest first)
            valid_items.sort(key=lambda x: x[1]['timestamp'])
            additional_to_remove = remaining_count - target_size

            for i in range(min(additional_to_remove, len(valid_items))):
                key, _ = valid_items[i]
                if key in cache_dict:  # Double-check key still exists
                    del cache_dict[key]
                    additional_removals += 1

        total_removed = expired_count + additional_removals
        if total_removed > 0:
            logger.debug(
                f'Smart {cache_type} cache cleanup: removed {expired_count} expired + {additional_removals} oldest valid = {total_removed} total entries, {len(cache_dict)} remaining'
            )

    def cleanup_expired_cache_entries(self) -> None:
        """Clean up expired cache entries to prevent memory leaks."""
        current_time = time.time()

        # Clean up tag cache
        expired_tag_keys = []
        for cache_key, cached_entry in self._tag_cache.items():
            if current_time - cached_entry['timestamp'] >= self.config.tag_cache_ttl_seconds:
                expired_tag_keys.append(cache_key)

        for key in expired_tag_keys:
            del self._tag_cache[key]

        # Clean up result cache
        expired_result_keys = []
        for cache_key, cached_entry in self._result_cache.items():
            if current_time - cached_entry['timestamp'] >= self.config.result_cache_ttl_seconds:
                expired_result_keys.append(cache_key)

        for key in expired_result_keys:
            del self._result_cache[key]

        if expired_tag_keys or expired_result_keys:
            logger.debug(
                f'Cleaned up {len(expired_tag_keys)} expired tag cache entries and '
                f'{len(expired_result_keys)} expired result cache entries'
            )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        current_time = time.time()

        # Count valid entries
        valid_tag_entries = sum(
            1
            for entry in self._tag_cache.values()
            if current_time - entry['timestamp'] < self.config.tag_cache_ttl_seconds
        )

        valid_result_entries = sum(
            1
            for entry in self._result_cache.values()
            if current_time - entry['timestamp'] < self.config.result_cache_ttl_seconds
        )

        return {
            'tag_cache': {
                'total_entries': len(self._tag_cache),
                'valid_entries': valid_tag_entries,
                'ttl_seconds': self.config.tag_cache_ttl_seconds,
                'max_cache_size': self.config.max_tag_cache_size,
                'cache_utilization': len(self._tag_cache) / self.config.max_tag_cache_size,
            },
            'result_cache': {
                'total_entries': len(self._result_cache),
                'valid_entries': valid_result_entries,
                'ttl_seconds': self.config.result_cache_ttl_seconds,
                'max_cache_size': self.config.max_result_cache_size,
                'cache_utilization': len(self._result_cache) / self.config.max_result_cache_size,
            },
            'config': {
                'enable_s3_tag_search': self.config.enable_s3_tag_search,
                'max_tag_batch_size': self.config.max_tag_retrieval_batch_size,
                'cache_cleanup_keep_ratio': self.config.cache_cleanup_keep_ratio,
            },
        }
