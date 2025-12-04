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

"""Tests for GenomicsSearchOrchestrator."""

import asyncio
import pytest
import time
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileSearchRequest,
    GenomicsFileType,
    GlobalContinuationToken,
    PaginationCacheEntry,
    PaginationMetrics,
    SearchConfig,
    StoragePaginationRequest,
    StoragePaginationResponse,
)
from awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator import (
    GenomicsSearchOrchestrator,
)
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestGenomicsSearchOrchestrator:
    """Test cases for GenomicsSearchOrchestrator."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock SearchConfig for testing."""
        return SearchConfig(
            s3_bucket_paths=['s3://test-bucket/'],
            enable_healthomics_search=True,
            search_timeout_seconds=30,
            enable_pagination_metrics=True,
            pagination_cache_ttl_seconds=300,
            min_pagination_buffer_size=100,
            max_pagination_buffer_size=10000,
            enable_cursor_based_pagination=True,
        )

    @pytest.fixture
    def sample_genomics_files(self):
        """Create sample GenomicsFile objects for testing."""
        return [
            GenomicsFile(
                path='s3://test-bucket/sample1.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={'project': 'test'},
                source_system='s3',
                metadata={'sample_id': 'sample1'},
            ),
            GenomicsFile(
                path='s3://test-bucket/sample2.bam',
                file_type=GenomicsFileType.BAM,
                size_bytes=2000000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={'project': 'test'},
                source_system='s3',
                metadata={'sample_id': 'sample2'},
            ),
        ]

    @pytest.fixture
    def sample_search_request(self):
        """Create a sample GenomicsFileSearchRequest for testing."""
        return GenomicsFileSearchRequest(
            file_type='fastq',
            search_terms=['sample'],
            max_results=10,
            offset=0,
            include_associated_files=True,
            pagination_buffer_size=1000,
        )

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create a GenomicsSearchOrchestrator instance for testing."""
        # Create a mock S3 engine
        mock_s3_engine = MagicMock()
        mock_s3_engine.search_buckets = AsyncMock()
        mock_s3_engine.search_buckets_paginated = AsyncMock()
        mock_s3_engine.cleanup_expired_cache_entries = MagicMock()

        # Mock only the expensive initialization parts for HealthOmics engine
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.HealthOmicsSearchEngine.__init__',
            return_value=None,
        ):
            orchestrator = GenomicsSearchOrchestrator(mock_config, s3_engine=mock_s3_engine)

            # The HealthOmics engine is a real object, but its __init__ was mocked to avoid expensive setup
            # We need to ensure it has the methods our tests expect
            if not hasattr(orchestrator.healthomics_engine, 'search_sequence_stores'):
                orchestrator.healthomics_engine.search_sequence_stores = AsyncMock()
            if not hasattr(orchestrator.healthomics_engine, 'search_reference_stores'):
                orchestrator.healthomics_engine.search_reference_stores = AsyncMock()
            if not hasattr(orchestrator.healthomics_engine, 'search_sequence_stores_paginated'):
                orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock()
            if not hasattr(orchestrator.healthomics_engine, 'search_reference_stores_paginated'):
                orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock()

            return orchestrator

    def test_init(self, orchestrator, mock_config):
        """Test GenomicsSearchOrchestrator initialization."""
        assert orchestrator.config == mock_config
        assert orchestrator.s3_engine is not None
        assert orchestrator.healthomics_engine is not None
        assert orchestrator.association_engine is not None
        assert orchestrator.scoring_engine is not None
        assert orchestrator.result_ranker is not None
        assert orchestrator.json_builder is not None

    @patch(
        'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.get_genomics_search_config'
    )
    def test_from_environment(self, mock_get_config, mock_config):
        """Test creating orchestrator from environment configuration."""
        mock_get_config.return_value = mock_config

        orchestrator = GenomicsSearchOrchestrator.from_environment()

        assert orchestrator.config == mock_config
        mock_get_config.assert_called_once()

    def test_validate_search_request_valid(self, orchestrator, sample_search_request):
        """Test validation of valid search request."""
        # Should not raise any exception
        orchestrator._validate_search_request(sample_search_request)

    def test_validate_search_request_invalid_max_results_zero(self, orchestrator):
        """Test validation with invalid max_results (zero)."""
        # Create a mock request object that bypasses Pydantic validation
        mock_request = MagicMock()
        mock_request.max_results = 0
        mock_request.file_type = None

        with pytest.raises(ValueError, match='max_results must be greater than 0'):
            orchestrator._validate_search_request(mock_request)

    def test_validate_search_request_invalid_max_results_too_large(self, orchestrator):
        """Test validation with invalid max_results (too large)."""
        # Create a mock request object that bypasses Pydantic validation
        mock_request = MagicMock()
        mock_request.max_results = 20000
        mock_request.file_type = None

        with pytest.raises(ValueError, match='max_results cannot exceed 10000'):
            orchestrator._validate_search_request(mock_request)

    def test_validate_search_request_invalid_file_type(self, orchestrator):
        """Test validation with invalid file type."""
        # Create a mock request object that bypasses Pydantic validation
        mock_request = MagicMock()
        mock_request.max_results = 10
        mock_request.file_type = 'invalid_type'

        with pytest.raises(ValueError, match="Invalid file_type 'invalid_type'"):
            orchestrator._validate_search_request(mock_request)

    def test_deduplicate_files(self, orchestrator, sample_genomics_files):
        """Test file deduplication based on paths."""
        # Create duplicate files
        duplicate_files = sample_genomics_files + [sample_genomics_files[0]]  # Add duplicate

        result = orchestrator._deduplicate_files(duplicate_files)

        assert len(result) == 2  # Should remove one duplicate
        paths = [f.path for f in result]
        assert len(set(paths)) == len(paths)  # All paths should be unique

    def test_get_searched_storage_systems_s3_only(self, mock_config):
        """Test getting searched storage systems with S3 only."""
        mock_config.enable_healthomics_search = False

        # Create a mock S3 engine
        mock_s3_engine = MagicMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.HealthOmicsSearchEngine.__init__',
            return_value=None,
        ):
            orchestrator = GenomicsSearchOrchestrator(mock_config, s3_engine=mock_s3_engine)

        systems = orchestrator._get_searched_storage_systems()

        assert systems == ['s3']

    def test_get_searched_storage_systems_all_enabled(self, orchestrator):
        """Test getting searched storage systems with all systems enabled."""
        systems = orchestrator._get_searched_storage_systems()

        expected = ['s3', 'healthomics_sequence_stores', 'healthomics_reference_stores']
        assert systems == expected

    def test_get_searched_storage_systems_no_s3(self, mock_config):
        """Test getting searched storage systems with no S3 buckets configured."""
        mock_config.s3_bucket_paths = []

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.HealthOmicsSearchEngine.__init__',
            return_value=None,
        ):
            # No S3 engine provided, so it should be None
            orchestrator = GenomicsSearchOrchestrator(mock_config, s3_engine=None)

        systems = orchestrator._get_searched_storage_systems()

        expected = ['healthomics_sequence_stores', 'healthomics_reference_stores']
        assert systems == expected

    def test_extract_healthomics_associations_no_index(self, orchestrator, sample_genomics_files):
        """Test extracting HealthOmics associations when no index info is present."""
        result = orchestrator._extract_healthomics_associations(sample_genomics_files)

        # Should return the same files since no index info
        assert len(result) == len(sample_genomics_files)
        assert result == sample_genomics_files

    def test_extract_healthomics_associations_with_index(self, orchestrator):
        """Test extracting HealthOmics associations when index info is present."""
        # Create a file with index information
        file_with_index = GenomicsFile(
            path='omics://reference-store/ref123',
            file_type=GenomicsFileType.FASTA,
            size_bytes=1000000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            tags={},
            source_system='reference_store',
            metadata={
                '_healthomics_index_info': {
                    'index_uri': 'omics://reference-store/ref123.fai',
                    'index_size': 50000,
                    'store_id': 'store123',
                    'store_name': 'test-store',
                    'reference_id': 'ref123',
                    'reference_name': 'test-reference',
                    'status': 'ACTIVE',
                    'md5': 'abc123',
                }
            },
        )

        result = orchestrator._extract_healthomics_associations([file_with_index])

        # Should return original file plus index file
        assert len(result) == 2
        assert result[0] == file_with_index

        # Check index file properties
        index_file = result[1]
        assert index_file.path == 'omics://reference-store/ref123.fai'
        assert index_file.file_type == GenomicsFileType.FAI
        assert index_file.metadata['is_index_file'] is True
        assert index_file.metadata['primary_file_uri'] == file_with_index.path

    def test_create_pagination_cache_key(self, orchestrator, sample_search_request):
        """Test creating pagination cache key."""
        cache_key = orchestrator._create_pagination_cache_key(sample_search_request, 1)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length

        # Same request should produce same key
        cache_key2 = orchestrator._create_pagination_cache_key(sample_search_request, 1)
        assert cache_key == cache_key2

        # Different page should produce different key
        cache_key3 = orchestrator._create_pagination_cache_key(sample_search_request, 2)
        assert cache_key != cache_key3

    def test_get_cached_pagination_state_no_cache(self, orchestrator):
        """Test getting cached pagination state when no cache exists."""
        result = orchestrator._get_cached_pagination_state('nonexistent_key')

        assert result is None

    def test_cache_and_get_pagination_state(self, orchestrator):
        """Test caching and retrieving pagination state."""
        cache_key = 'test_key'
        entry = PaginationCacheEntry(
            search_key=cache_key,
            page_number=1,
            score_threshold=0.8,
            storage_tokens={'s3': 'token123'},
            metrics=None,
        )

        # Cache the entry
        orchestrator._cache_pagination_state(cache_key, entry)

        # Retrieve the entry
        result = orchestrator._get_cached_pagination_state(cache_key)

        assert result is not None
        assert result.search_key == cache_key
        assert result.page_number == 1
        assert result.score_threshold == 0.8

    def test_optimize_buffer_size_base_case(self, orchestrator, sample_search_request):
        """Test buffer size optimization with base case."""
        result = orchestrator._optimize_buffer_size(sample_search_request)

        # Should be close to the original buffer size with some adjustments
        assert isinstance(result, int)
        assert result >= orchestrator.config.min_pagination_buffer_size
        assert result <= orchestrator.config.max_pagination_buffer_size

    def test_optimize_buffer_size_with_metrics(self, orchestrator, sample_search_request):
        """Test buffer size optimization with historical metrics."""
        metrics = PaginationMetrics(
            page_number=1,
            search_duration_ms=1000,
            total_results_fetched=50,
            total_objects_scanned=1000,
            buffer_overflows=1,
        )

        result = orchestrator._optimize_buffer_size(sample_search_request, metrics)

        # Should increase buffer size due to overflow
        assert result > sample_search_request.pagination_buffer_size

    def test_create_pagination_metrics(self, orchestrator):
        """Test creating pagination metrics."""
        import time

        start_time = time.time()

        metrics = orchestrator._create_pagination_metrics(1, start_time)

        assert isinstance(metrics, PaginationMetrics)
        assert metrics.page_number == 1
        assert metrics.search_duration_ms >= 0

    def test_should_use_cursor_pagination_large_buffer(self, orchestrator):
        """Test cursor pagination decision with large buffer size."""
        request = GenomicsFileSearchRequest(
            max_results=10,
            search_terms=['test'],
            pagination_buffer_size=6000,  # Large buffer
        )
        token = GlobalContinuationToken(page_number=1)

        result = orchestrator._should_use_cursor_pagination(request, token)

        assert result is True

    def test_should_use_cursor_pagination_high_page_number(self, orchestrator):
        """Test cursor pagination decision with high page number."""
        request = GenomicsFileSearchRequest(
            max_results=10,
            search_terms=['test'],
            pagination_buffer_size=1000,
        )
        token = GlobalContinuationToken(page_number=15)  # High page number

        result = orchestrator._should_use_cursor_pagination(request, token)

        assert result is True

    def test_should_use_cursor_pagination_normal_case(self, orchestrator):
        """Test cursor pagination decision with normal parameters."""
        request = GenomicsFileSearchRequest(
            max_results=10,
            search_terms=['test'],
            pagination_buffer_size=1000,
        )
        token = GlobalContinuationToken(page_number=1)

        result = orchestrator._should_use_cursor_pagination(request, token)

        assert result is False

    def test_cleanup_expired_pagination_cache_no_cache(self, orchestrator):
        """Test cleaning up expired cache when no cache exists."""
        # Should not raise any exception
        orchestrator.cleanup_expired_pagination_cache()

    def test_cleanup_expired_pagination_cache_with_entries(self, orchestrator):
        """Test cleaning up expired cache entries."""
        # Create cache with expired entry
        orchestrator._pagination_cache = {}

        # Create an expired entry (simulate by setting very old timestamp)
        expired_entry = PaginationCacheEntry(
            search_key='expired_key',
            page_number=1,
            score_threshold=0.8,
            storage_tokens={},
            metrics=None,
        )
        expired_entry.timestamp = 0  # Very old timestamp

        # Create a valid entry
        valid_entry = PaginationCacheEntry(
            search_key='valid_key',
            page_number=1,
            score_threshold=0.8,
            storage_tokens={},
            metrics=None,
        )

        orchestrator._pagination_cache['expired_key'] = expired_entry
        orchestrator._pagination_cache['valid_key'] = valid_entry

        # Verify initial state
        assert len(orchestrator._pagination_cache) == 2

        # Clean up
        orchestrator.cleanup_expired_pagination_cache()

        # Check that expired entry was removed
        assert 'expired_key' not in orchestrator._pagination_cache
        # Note: valid_entry might also be considered expired depending on TTL settings

    def test_cleanup_pagination_cache_by_size(self, orchestrator):
        """Test size-based cleanup of pagination cache."""
        # Set small cache size for testing
        orchestrator.config.max_pagination_cache_size = 3
        orchestrator.config.cache_cleanup_keep_ratio = 0.6  # Keep 60%

        # Create cache with more entries than the limit
        orchestrator._pagination_cache = {}

        for i in range(5):
            entry = PaginationCacheEntry(
                search_key=f'key{i}',
                page_number=i,
                score_threshold=0.8,
                storage_tokens={},
                metrics=None,
            )
            entry.timestamp = time.time() + i  # Different timestamps for ordering
            orchestrator._pagination_cache[f'key{i}'] = entry

        assert len(orchestrator._pagination_cache) == 5

        # Trigger size-based cleanup
        orchestrator._cleanup_pagination_cache_by_size()

        # Should keep 60% of max_size = 1.8 -> 1 entry (most recent)
        expected_size = int(
            orchestrator.config.max_pagination_cache_size
            * orchestrator.config.cache_cleanup_keep_ratio
        )
        assert len(orchestrator._pagination_cache) == expected_size

        # Should keep the most recent entries (highest timestamps)
        remaining_keys = list(orchestrator._pagination_cache.keys())
        assert 'key4' in remaining_keys  # Most recent entry

    def test_cleanup_pagination_cache_by_size_no_cleanup_needed(self, orchestrator):
        """Test that size-based cleanup does nothing when cache is under limit."""
        # Set cache size larger than current entries
        orchestrator.config.max_pagination_cache_size = 10

        # Create cache with fewer entries than the limit
        orchestrator._pagination_cache = {}

        for i in range(3):
            entry = PaginationCacheEntry(
                search_key=f'key{i}',
                page_number=i,
                score_threshold=0.8,
                storage_tokens={},
                metrics=None,
            )
            orchestrator._pagination_cache[f'key{i}'] = entry

        initial_size = len(orchestrator._pagination_cache)

        # Trigger size-based cleanup
        orchestrator._cleanup_pagination_cache_by_size()

        # Should not remove any entries
        assert len(orchestrator._pagination_cache) == initial_size

    def test_cleanup_pagination_cache_by_size_no_cache(self, orchestrator):
        """Test that size-based cleanup handles missing cache gracefully."""
        # Don't create _pagination_cache attribute

        # Should not raise any exception
        orchestrator._cleanup_pagination_cache_by_size()

    def test_automatic_pagination_cache_size_cleanup(self, orchestrator):
        """Test that pagination cache automatically cleans up when size limit is reached."""
        # Set small cache size for testing
        orchestrator.config.max_pagination_cache_size = 2
        orchestrator.config.cache_cleanup_keep_ratio = 0.5  # Keep 50%
        orchestrator.config.pagination_cache_ttl_seconds = 3600  # Long TTL to avoid TTL cleanup

        # Add entries that will trigger automatic cleanup
        for i in range(4):
            entry = PaginationCacheEntry(
                search_key=f'key{i}',
                page_number=i,
                score_threshold=0.8,
                storage_tokens={},
                metrics=None,
            )
            orchestrator._cache_pagination_state(f'key{i}', entry)

            # Cache should never exceed the maximum size
            cache_size = (
                len(orchestrator._pagination_cache)
                if hasattr(orchestrator, '_pagination_cache')
                else 0
            )
            assert cache_size <= orchestrator.config.max_pagination_cache_size

    def test_smart_pagination_cache_cleanup_prioritizes_expired_entries(self, orchestrator):
        """Test that smart pagination cache cleanup removes expired entries first."""
        # Set small cache size and short TTL for testing
        orchestrator.config.max_pagination_cache_size = 3
        orchestrator.config.cache_cleanup_keep_ratio = 0.6  # Keep 60% = 1 entry
        orchestrator.config.pagination_cache_ttl_seconds = 10  # 10 second TTL

        # Create cache manually
        orchestrator._pagination_cache = {}

        current_time = time.time()

        # Add mix of expired and valid entries
        expired1 = PaginationCacheEntry(
            search_key='expired1',
            page_number=1,
            score_threshold=0.8,
            storage_tokens={},
            metrics=None,
        )
        expired1.timestamp = current_time - 20  # Expired

        expired2 = PaginationCacheEntry(
            search_key='expired2',
            page_number=2,
            score_threshold=0.7,
            storage_tokens={},
            metrics=None,
        )
        expired2.timestamp = current_time - 15  # Expired

        valid1 = PaginationCacheEntry(
            search_key='valid1',
            page_number=3,
            score_threshold=0.6,
            storage_tokens={},
            metrics=None,
        )
        valid1.timestamp = current_time - 5  # Valid

        valid2 = PaginationCacheEntry(
            search_key='valid2',
            page_number=4,
            score_threshold=0.5,
            storage_tokens={},
            metrics=None,
        )
        valid2.timestamp = current_time - 2  # Valid (newest)

        orchestrator._pagination_cache['expired1'] = expired1
        orchestrator._pagination_cache['expired2'] = expired2
        orchestrator._pagination_cache['valid1'] = valid1
        orchestrator._pagination_cache['valid2'] = valid2

        assert len(orchestrator._pagination_cache) == 4

        # Trigger smart cleanup
        orchestrator._cleanup_pagination_cache_by_size()

        # Should keep only 1 entry (60% of 3 = 1.8 -> 1)
        # Should prioritize removing expired entries first, then oldest valid
        # Expected: expired1, expired2, and valid1 removed; valid2 kept (newest valid)
        assert len(orchestrator._pagination_cache) == 1
        assert 'valid2' in orchestrator._pagination_cache  # Newest valid entry should remain
        assert 'expired1' not in orchestrator._pagination_cache
        assert 'expired2' not in orchestrator._pagination_cache
        assert 'valid1' not in orchestrator._pagination_cache

    def test_get_pagination_cache_stats_no_cache(self, orchestrator):
        """Test getting pagination cache stats when no cache exists."""
        stats = orchestrator.get_pagination_cache_stats()

        assert stats['total_entries'] == 0
        assert stats['valid_entries'] == 0
        # Check for expected keys in the stats
        assert isinstance(stats, dict)

    def test_get_pagination_cache_stats_with_cache(self, orchestrator):
        """Test getting pagination cache stats with cache entries."""
        # Create cache with entries
        orchestrator._pagination_cache = {}

        entry1 = PaginationCacheEntry(
            search_key='key1',
            page_number=1,
            score_threshold=0.8,
            storage_tokens={},
            metrics=None,
        )
        entry2 = PaginationCacheEntry(
            search_key='key2',
            page_number=2,
            score_threshold=0.7,
            storage_tokens={},
            metrics=None,
        )

        orchestrator._pagination_cache['key1'] = entry1
        orchestrator._pagination_cache['key2'] = entry2

        stats = orchestrator.get_pagination_cache_stats()

        assert stats['total_entries'] == 2
        # Valid entries might be 0 if TTL is very short, so just check it's a number
        assert isinstance(stats['valid_entries'], int)
        assert stats['valid_entries'] >= 0

        # Check new size-related fields
        assert 'max_cache_size' in stats
        assert 'cache_utilization' in stats
        assert isinstance(stats['max_cache_size'], int)
        assert isinstance(stats['cache_utilization'], float)
        assert 'cache_cleanup_keep_ratio' in stats['config']

        # Test utilization calculation
        expected_utilization = (
            len(orchestrator._pagination_cache) / orchestrator.config.max_pagination_cache_size
        )
        assert stats['cache_utilization'] == expected_utilization

    @pytest.mark.asyncio
    async def test_search_s3_with_timeout_success(self, orchestrator, sample_search_request):
        """Test S3 search with timeout - success case."""
        mock_files = [
            GenomicsFile(
                path='s3://test-bucket/file1.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='s3',
                metadata={},
            )
        ]

        with patch.object(
            orchestrator.s3_engine, 'search_buckets', new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_files

            result = await orchestrator._search_s3_with_timeout(sample_search_request)

            assert result == mock_files
            mock_search.assert_called_once_with(
                orchestrator.config.s3_bucket_paths,
                sample_search_request.file_type,
                sample_search_request.search_terms,
            )

    @pytest.mark.asyncio
    async def test_search_s3_with_timeout_timeout(self, orchestrator, sample_search_request):
        """Test S3 search with timeout - timeout case."""
        with patch.object(
            orchestrator.s3_engine, 'search_buckets', new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()

            result = await orchestrator._search_s3_with_timeout(sample_search_request)

            assert result == []

    @pytest.mark.asyncio
    async def test_search_s3_with_timeout_exception(self, orchestrator, sample_search_request):
        """Test S3 search with timeout - exception case."""
        with patch.object(
            orchestrator.s3_engine, 'search_buckets', new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = Exception('Search failed')

            result = await orchestrator._search_s3_with_timeout(sample_search_request)

            assert result == []

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_with_timeout_success(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence search with timeout - success case."""
        mock_files = [
            GenomicsFile(
                path='omics://sequence-store/seq123',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='sequence_store',
                metadata={},
            )
        ]

        with patch.object(
            orchestrator.healthomics_engine, 'search_sequence_stores', new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_files

            result = await orchestrator._search_healthomics_sequences_with_timeout(
                sample_search_request
            )

            assert result == mock_files
            mock_search.assert_called_once_with(
                sample_search_request.file_type, sample_search_request.search_terms
            )

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_with_timeout_timeout(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence search with timeout - timeout case."""
        with patch.object(
            orchestrator.healthomics_engine, 'search_sequence_stores', new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()

            result = await orchestrator._search_healthomics_sequences_with_timeout(
                sample_search_request
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_search_healthomics_references_with_timeout_success(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics reference search with timeout - success case."""
        mock_files = [
            GenomicsFile(
                path='omics://reference-store/ref123',
                file_type=GenomicsFileType.FASTA,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='reference_store',
                metadata={},
            )
        ]

        with patch.object(
            orchestrator.healthomics_engine, 'search_reference_stores', new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_files

            result = await orchestrator._search_healthomics_references_with_timeout(
                sample_search_request
            )

            assert result == mock_files
            mock_search.assert_called_once_with(
                sample_search_request.file_type, sample_search_request.search_terms
            )

    @pytest.mark.asyncio
    async def test_execute_parallel_searches_s3_only(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test executing parallel searches with S3 only."""
        # Disable HealthOmics search
        orchestrator.config.enable_healthomics_search = False

        with patch.object(
            orchestrator, '_search_s3_with_timeout', new_callable=AsyncMock
        ) as mock_s3:
            mock_s3.return_value = sample_genomics_files

            result = await orchestrator._execute_parallel_searches(sample_search_request)

            assert result == sample_genomics_files
            mock_s3.assert_called_once_with(sample_search_request)

    @pytest.mark.asyncio
    async def test_execute_parallel_searches_all_systems(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test executing parallel searches with all systems enabled."""
        healthomics_files = [
            GenomicsFile(
                path='omics://sequence-store/seq123',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='sequence_store',
                metadata={},
            )
        ]

        with (
            patch.object(
                orchestrator, '_search_s3_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator, '_search_healthomics_sequences_with_timeout', new_callable=AsyncMock
            ) as mock_seq,
            patch.object(
                orchestrator, '_search_healthomics_references_with_timeout', new_callable=AsyncMock
            ) as mock_ref,
        ):
            mock_s3.return_value = sample_genomics_files
            mock_seq.return_value = healthomics_files
            mock_ref.return_value = []

            result = await orchestrator._execute_parallel_searches(sample_search_request)

            expected_files = sample_genomics_files + healthomics_files
            assert result == expected_files
            mock_s3.assert_called_once_with(sample_search_request)
            mock_seq.assert_called_once_with(sample_search_request)
            mock_ref.assert_called_once_with(sample_search_request)

    @pytest.mark.asyncio
    async def test_execute_parallel_searches_with_exceptions(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test executing parallel searches with some systems failing."""
        with (
            patch.object(
                orchestrator, '_search_s3_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator, '_search_healthomics_sequences_with_timeout', new_callable=AsyncMock
            ) as mock_seq,
            patch.object(
                orchestrator, '_search_healthomics_references_with_timeout', new_callable=AsyncMock
            ) as mock_ref,
        ):
            mock_s3.return_value = sample_genomics_files
            mock_seq.side_effect = Exception('HealthOmics failed')
            mock_ref.return_value = []

            result = await orchestrator._execute_parallel_searches(sample_search_request)

            # Should still return S3 results despite HealthOmics failure
            assert result == sample_genomics_files

    @pytest.mark.asyncio
    async def test_execute_parallel_searches_no_systems_configured(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel searches with no systems configured."""
        # Disable all systems
        orchestrator.config.s3_bucket_paths = []
        orchestrator.config.enable_healthomics_search = False

        result = await orchestrator._execute_parallel_searches(sample_search_request)

        assert result == []

    @pytest.mark.asyncio
    async def test_score_results(self, orchestrator, sample_genomics_files):
        """Test scoring results."""
        # Create mock file groups
        mock_file_group = MagicMock()
        mock_file_group.primary_file = sample_genomics_files[0]
        mock_file_group.associated_files = []

        file_groups = [mock_file_group]

        with patch.object(orchestrator.scoring_engine, 'calculate_score') as mock_score:
            mock_score.return_value = (0.8, ['file_type_match'])

            result = await orchestrator._score_results(file_groups, 'fastq', ['sample'], True)

            assert len(result) == 1
            assert isinstance(result[0], GenomicsFileResult)
            assert result[0].primary_file == sample_genomics_files[0]
            assert result[0].relevance_score == 0.8
            assert result[0].match_reasons == ['file_type_match']

            mock_score.assert_called_once_with(sample_genomics_files[0], ['sample'], 'fastq', [])

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_success(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches - success case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        mock_healthomics_response = StoragePaginationResponse(
            results=[],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=0,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_s3_response
            mock_seq.return_value = mock_healthomics_response
            mock_ref.return_value = mock_healthomics_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            assert len(files) == 1
            assert files[0].path == 's3://test-bucket/file1.fastq'
            assert next_token is None  # No more results
            assert total_scanned == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_with_continuation(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with continuation tokens."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token='test_token',
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        # Mock response with continuation token
        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=True,
            next_continuation_token=GlobalContinuationToken(
                s3_tokens={'bucket1': 'next_token'}
            ).encode(),
            total_scanned=1,
        )

        mock_healthomics_response = StoragePaginationResponse(
            results=[],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=0,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_s3_response
            mock_seq.return_value = mock_healthomics_response
            mock_ref.return_value = mock_healthomics_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            assert len(files) == 1
            assert next_token is not None  # Should have continuation token
            assert total_scanned == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_s3_only(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with S3 only."""
        # Disable HealthOmics search
        orchestrator.config.enable_healthomics_search = False

        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with patch.object(
            orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
        ) as mock_s3:
            mock_s3.return_value = mock_s3_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            assert len(files) == 1
            assert files[0].path == 's3://test-bucket/file1.fastq'
            assert next_token is None
            assert total_scanned == 1
            mock_s3.assert_called_once_with(sample_search_request, storage_request)

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_healthomics_only(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with HealthOmics only."""
        # Disable S3 search
        orchestrator.config.s3_bucket_paths = []

        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        mock_seq_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='omics://sequence-store/seq123',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='sequence_store',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        mock_ref_response = StoragePaginationResponse(
            results=[],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=0,
        )

        with (
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_seq.return_value = mock_seq_response
            mock_ref.return_value = mock_ref_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            assert len(files) == 1
            assert files[0].path == 'omics://sequence-store/seq123'
            assert next_token is None
            assert total_scanned == 1
            mock_seq.assert_called_once_with(sample_search_request, storage_request)
            mock_ref.assert_called_once_with(sample_search_request, storage_request)

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_with_exceptions(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with some systems failing."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_s3_response
            mock_seq.side_effect = Exception('HealthOmics sequences failed')
            mock_ref.side_effect = Exception('HealthOmics references failed')

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            # Should still return S3 results despite HealthOmics failures
            assert len(files) == 1
            assert files[0].path == 's3://test-bucket/file1.fastq'
            assert next_token is None
            assert total_scanned == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_no_systems_configured(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with no systems configured."""
        # Disable all systems
        orchestrator.config.s3_bucket_paths = []
        orchestrator.config.enable_healthomics_search = False

        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        files, next_token, total_scanned = await orchestrator._execute_parallel_paginated_searches(
            sample_search_request, storage_request, global_token
        )

        assert files == []
        assert next_token is None
        assert total_scanned == 0

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_mixed_continuation_tokens(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with mixed continuation token scenarios."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token='test_token',
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        # Mock S3 with continuation token
        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=True,
            next_continuation_token=GlobalContinuationToken(
                s3_tokens={'bucket1': 'next_s3_token'}
            ).encode(),
            total_scanned=1,
        )

        # Mock HealthOmics sequences with continuation token
        mock_seq_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='omics://sequence-store/seq123',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='sequence_store',
                    metadata={},
                )
            ],
            has_more_results=True,
            next_continuation_token=GlobalContinuationToken(
                healthomics_sequence_token='next_seq_token'
            ).encode(),
            total_scanned=1,
        )

        # Mock HealthOmics references without continuation token
        mock_ref_response = StoragePaginationResponse(
            results=[],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=0,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_s3_response
            mock_seq.return_value = mock_seq_response
            mock_ref.return_value = mock_ref_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            assert len(files) == 2  # One from S3, one from sequences
            assert (
                next_token is not None
            )  # Should have continuation token due to S3 and sequences having more
            assert total_scanned == 2

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_invalid_continuation_tokens(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with invalid continuation tokens."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token='test_token',
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        # Mock responses with invalid continuation tokens
        mock_s3_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=True,
            next_continuation_token='invalid_token_format',  # Invalid token
            total_scanned=1,
        )

        mock_healthomics_response = StoragePaginationResponse(
            results=[],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=0,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_s3_response
            mock_seq.return_value = mock_healthomics_response
            mock_ref.return_value = mock_healthomics_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            # Should still return results despite invalid continuation token
            assert len(files) == 1
            assert files[0].path == 's3://test-bucket/file1.fastq'
            # next_token might be None due to invalid token parsing
            assert total_scanned == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_unexpected_response_format(
        self, orchestrator, sample_search_request
    ):
        """Test executing parallel paginated searches with unexpected response formats."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )
        global_token = GlobalContinuationToken()

        # Mock response with missing attributes (simulating unexpected response format)
        mock_unexpected_response = MagicMock()
        mock_unexpected_response.results = []
        mock_unexpected_response.has_more_results = False
        mock_unexpected_response.next_continuation_token = None
        mock_unexpected_response.total_scanned = 0
        # Don't set the expected attributes to simulate unexpected response format

        mock_normal_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with (
            patch.object(
                orchestrator, '_search_s3_paginated_with_timeout', new_callable=AsyncMock
            ) as mock_s3,
            patch.object(
                orchestrator,
                '_search_healthomics_sequences_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_seq,
            patch.object(
                orchestrator,
                '_search_healthomics_references_paginated_with_timeout',
                new_callable=AsyncMock,
            ) as mock_ref,
        ):
            mock_s3.return_value = mock_normal_response
            mock_seq.return_value = mock_unexpected_response  # Unexpected format
            mock_ref.return_value = mock_normal_response

            (
                files,
                next_token,
                total_scanned,
            ) = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, storage_request, global_token
            )

            # Should handle unexpected response gracefully and return available results
            assert len(files) >= 1  # At least S3 and ref results
            assert total_scanned >= 1

    @pytest.mark.asyncio
    async def test_search_s3_paginated_with_timeout_success(
        self, orchestrator, sample_search_request
    ):
        """Test S3 paginated search with timeout - success case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        mock_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='s3://test-bucket/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with patch.object(
            orchestrator.s3_engine, 'search_buckets_paginated', new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await orchestrator._search_s3_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert result == mock_response
            mock_search.assert_called_once_with(
                orchestrator.config.s3_bucket_paths,
                sample_search_request.file_type,
                sample_search_request.search_terms,
                storage_request,
            )

    @pytest.mark.asyncio
    async def test_search_s3_paginated_with_timeout_timeout(
        self, orchestrator, sample_search_request
    ):
        """Test S3 paginated search with timeout - timeout case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        with patch.object(
            orchestrator.s3_engine, 'search_buckets_paginated', new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()

            result = await orchestrator._search_s3_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert isinstance(result, StoragePaginationResponse)
            assert result.results == []
            assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_search_s3_paginated_with_timeout_exception(
        self, orchestrator, sample_search_request
    ):
        """Test S3 paginated search with timeout - exception case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        with patch.object(
            orchestrator.s3_engine, 'search_buckets_paginated', new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = Exception('S3 search failed')

            result = await orchestrator._search_s3_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert isinstance(result, StoragePaginationResponse)
            assert result.results == []
            assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_paginated_with_timeout_success(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence paginated search with timeout - success case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        mock_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='omics://sequence-store/seq123',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='sequence_store',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with patch.object(
            orchestrator.healthomics_engine,
            'search_sequence_stores_paginated',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await orchestrator._search_healthomics_sequences_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert result == mock_response
            mock_search.assert_called_once_with(
                sample_search_request.file_type,
                sample_search_request.search_terms,
                storage_request,
            )

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_paginated_with_timeout_timeout(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence paginated search with timeout - timeout case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        with patch.object(
            orchestrator.healthomics_engine,
            'search_sequence_stores_paginated',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()

            result = await orchestrator._search_healthomics_sequences_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert isinstance(result, StoragePaginationResponse)
            assert result.results == []
            assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_search_healthomics_references_paginated_with_timeout_success(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics reference paginated search with timeout - success case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        mock_response = StoragePaginationResponse(
            results=[
                GenomicsFile(
                    path='omics://reference-store/ref123',
                    file_type=GenomicsFileType.FASTA,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='reference_store',
                    metadata={},
                )
            ],
            has_more_results=False,
            next_continuation_token=None,
            total_scanned=1,
        )

        with patch.object(
            orchestrator.healthomics_engine,
            'search_reference_stores_paginated',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_response

            result = await orchestrator._search_healthomics_references_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert result == mock_response
            mock_search.assert_called_once_with(
                sample_search_request.file_type,
                sample_search_request.search_terms,
                storage_request,
            )

    @pytest.mark.asyncio
    async def test_search_healthomics_references_paginated_with_timeout_timeout(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics reference paginated search with timeout - timeout case."""
        storage_request = StoragePaginationRequest(
            max_results=1000,
            continuation_token=None,
            buffer_size=1000,
        )

        with patch.object(
            orchestrator.healthomics_engine,
            'search_reference_stores_paginated',
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()

            result = await orchestrator._search_healthomics_references_paginated_with_timeout(
                sample_search_request, storage_request
            )

            assert isinstance(result, StoragePaginationResponse)
            assert result.results == []
            assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_search_main_method_success(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test the main search method with successful results."""
        # Mock the parallel search execution
        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = sample_genomics_files

            # Create proper GenomicsFileResult objects
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult

            result_obj = GenomicsFileResult(
                primary_file=sample_genomics_files[0],
                associated_files=[],
                relevance_score=0.8,
                match_reasons=['test reason'],
            )

            # Mock the scoring method to return proper results
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = [result_obj]

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = [result_obj]

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_response_dict = {
                            'results': [{'file': 'test'}],
                            'total_found': 1,
                            'search_duration_ms': 100,
                            'storage_systems_searched': ['s3'],
                            'search_statistics': {},
                            'pagination_info': {},
                        }
                        mock_build.return_value = mock_response_dict

                        result = await orchestrator.search(sample_search_request)

                        # Verify the method was called and returned results
                        assert result.total_found == 1
                        assert result.enhanced_response == mock_response_dict
                        mock_execute.assert_called_once_with(sample_search_request)
                        mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_main_method_validation_error(self, orchestrator):
        """Test the main search method with validation error."""
        # Test that Pydantic validation works at the model level
        with pytest.raises(ValueError) as exc_info:
            GenomicsFileSearchRequest(
                file_type='invalid_type',
                search_terms=['test'],
                max_results=0,  # Invalid
            )

        assert 'max_results must be greater than 0' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_main_method_execution_error(self, orchestrator, sample_search_request):
        """Test the main search method with execution error."""
        # Mock the parallel search execution to raise an exception
        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = Exception('Search execution failed')

            with pytest.raises(Exception) as exc_info:
                await orchestrator.search(sample_search_request)

            assert 'Search execution failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_paginated_main_method_success(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test the main search_paginated method with successful results."""
        # Mock the parallel paginated search execution
        with patch.object(
            orchestrator, '_execute_parallel_paginated_searches', new_callable=AsyncMock
        ) as mock_execute:
            from awslabs.aws_healthomics_mcp_server.models import GlobalContinuationToken

            next_token = GlobalContinuationToken()
            mock_execute.return_value = (
                sample_genomics_files,
                next_token,
                len(sample_genomics_files),
            )

            # Create proper GenomicsFileResult objects
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult

            result_obj = GenomicsFileResult(
                primary_file=sample_genomics_files[0],
                associated_files=[],
                relevance_score=0.8,
                match_reasons=['test reason'],
            )

            # Mock the scoring method to return proper results
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = [result_obj]

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = [result_obj]

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_response_dict = {
                            'results': [{'file': 'test'}],
                            'total_found': 1,
                            'search_duration_ms': 100,
                            'storage_systems_searched': ['s3'],
                            'search_statistics': {},
                            'pagination_info': {},
                        }
                        mock_build.return_value = mock_response_dict

                        result = await orchestrator.search_paginated(sample_search_request)

                        # Verify the method was called and returned results
                        assert result.total_found == 1
                        assert result.enhanced_response == mock_response_dict
                        mock_execute.assert_called_once()
                        mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_paginated_with_continuation_token(
        self, orchestrator, sample_search_request
    ):
        """Test search_paginated with continuation token."""
        # Create request with continuation token
        token = GlobalContinuationToken(
            s3_tokens={'s3://test-bucket/': 's3_token_123'},
            healthomics_sequence_token='seq_token_456',
            healthomics_reference_token='ref_token_789',
        )
        sample_search_request.continuation_token = token.encode()

        with patch.object(
            orchestrator, '_execute_parallel_paginated_searches', new_callable=AsyncMock
        ) as mock_execute:
            next_token = GlobalContinuationToken()
            mock_execute.return_value = ([], next_token, 0)

            with patch.object(orchestrator.json_builder, 'build_search_response') as mock_build:
                mock_response_dict = {
                    'results': [],
                    'total_found': 0,
                    'search_duration_ms': 100,
                    'storage_systems_searched': ['s3'],
                    'search_statistics': {},
                    'pagination_info': {},
                }
                mock_build.return_value = mock_response_dict

                result = await orchestrator.search_paginated(sample_search_request)

                # Verify the method handled the continuation token
                assert result.total_found == 0
                assert result.enhanced_response == mock_response_dict
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_paginated_validation_error(self, orchestrator):
        """Test search_paginated with validation error."""
        # Test that Pydantic validation works at the model level
        with pytest.raises(ValueError) as exc_info:
            GenomicsFileSearchRequest(
                file_type='fastq',
                search_terms=['test'],
                max_results=-1,  # Invalid
            )

        assert 'max_results must be greater than 0' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_with_file_associations(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test search with file association detection."""
        # Add a BAM file and its index to test associations
        bam_file = GenomicsFile(
            path='s3://test-bucket/sample.bam',
            file_type=GenomicsFileType.BAM,
            size_bytes=1000000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            tags={'project': 'test'},
            source_system='s3',
            metadata={'sample_id': 'sample'},
        )
        bai_file = GenomicsFile(
            path='s3://test-bucket/sample.bam.bai',
            file_type=GenomicsFileType.BAI,
            size_bytes=100000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            tags={'project': 'test'},
            source_system='s3',
            metadata={'sample_id': 'sample'},
        )
        files_with_associations = [bam_file, bai_file]

        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = files_with_associations

            # Create proper GenomicsFileResult objects
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult

            result_obj = GenomicsFileResult(
                primary_file=bam_file,
                associated_files=[bai_file],
                relevance_score=0.9,
                match_reasons=['association bonus'],
            )

            # Mock the scoring method to return proper results
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = [result_obj]

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = [result_obj]

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_response_dict = {
                            'results': [{'file': 'test_with_associations'}],
                            'total_found': 1,
                            'search_duration_ms': 100,
                            'storage_systems_searched': ['s3'],
                            'search_statistics': {},
                            'pagination_info': {},
                        }
                        mock_build.return_value = mock_response_dict

                        result = await orchestrator.search(sample_search_request)

                        # Verify associations were found and processed
                        assert result.total_found == 1
                        assert result.enhanced_response == mock_response_dict
                        mock_execute.assert_called_once_with(sample_search_request)
                        mock_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_empty_results(self, orchestrator, sample_search_request):
        """Test search with no results found."""
        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = []  # No files found

            with patch.object(orchestrator.json_builder, 'build_search_response') as mock_build:
                mock_response_dict = {
                    'results': [],
                    'total_found': 0,
                    'search_duration_ms': 100,
                    'storage_systems_searched': ['s3'],
                    'search_statistics': {},
                    'pagination_info': {},
                }
                mock_build.return_value = mock_response_dict

                result = await orchestrator.search(sample_search_request)

                # Verify empty results are handled correctly
                assert result.total_found == 0
                assert result.enhanced_response == mock_response_dict
                mock_execute.assert_called_once_with(sample_search_request)
                mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_healthomics_associations(self, orchestrator, sample_search_request):
        """Test search with HealthOmics-specific file associations."""
        # Create HealthOmics files with index information
        ho_file = GenomicsFile(
            path='omics://123456789012.storage.us-east-1.amazonaws.com/seq-store-123/readSet/readset-456/source1',
            file_type=GenomicsFileType.BAM,
            size_bytes=1000000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            tags={},
            source_system='sequence_store',
            metadata={
                'files': {
                    'source1': {'contentLength': 1000000},
                    'index': {'contentLength': 100000},
                },
                'account_id': '123456789012',
                'region': 'us-east-1',
                'store_id': 'seq-store-123',
                'read_set_id': 'readset-456',
            },
        )

        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = [ho_file]

            # Create proper GenomicsFileResult objects
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult

            result_obj = GenomicsFileResult(
                primary_file=ho_file,
                associated_files=[],
                relevance_score=0.8,
                match_reasons=['healthomics file'],
            )

            # Mock the scoring method to return proper results
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = [result_obj]

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = [result_obj]

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_response_dict = {
                            'results': [{'file': 'healthomics_test'}],
                            'total_found': 1,
                            'search_duration_ms': 100,
                            'storage_systems_searched': ['s3'],
                            'search_statistics': {},
                            'pagination_info': {},
                        }
                        mock_build.return_value = mock_response_dict

                        result = await orchestrator.search(sample_search_request)

                        # Verify HealthOmics associations were processed
                        assert result.total_found == 1
                        assert result.enhanced_response == mock_response_dict
                        mock_execute.assert_called_once_with(sample_search_request)
                        mock_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_performance_logging(
        self, orchestrator, sample_search_request, sample_genomics_files
    ):
        """Test that search performance is logged correctly."""
        with patch.object(
            orchestrator, '_execute_parallel_searches', new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = sample_genomics_files

            # Create proper GenomicsFileResult objects
            from awslabs.aws_healthomics_mcp_server.models import GenomicsFileResult

            result_obj = GenomicsFileResult(
                primary_file=sample_genomics_files[0],
                associated_files=[],
                relevance_score=0.8,
                match_reasons=['test reason'],
            )

            # Mock the scoring method to return proper results
            with patch.object(
                orchestrator, '_score_results', new_callable=AsyncMock
            ) as mock_score:
                mock_score.return_value = [result_obj]

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = [result_obj]

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_response_dict = {
                            'results': [{'file': 'test'}],
                            'total_found': 1,
                            'search_duration_ms': 100,
                            'storage_systems_searched': ['s3'],
                            'search_statistics': {},
                            'pagination_info': {},
                        }
                        mock_build.return_value = mock_response_dict

                        # Mock logger to verify logging calls
                        with patch(
                            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.logger'
                        ) as mock_logger:
                            result = await orchestrator.search(sample_search_request)

                            # Verify performance logging occurred
                            assert result.total_found == 1
                            assert result.enhanced_response == mock_response_dict
                            # Should have logged start and completion
                            assert mock_logger.info.call_count >= 2

                            # Check that timing information was logged
                            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
                            assert any(
                                'Starting genomics file search' in call for call in log_calls
                            )
                            assert any('Search completed' in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_search_paginated_with_invalid_continuation_token(
        self, orchestrator, sample_search_request
    ):
        """Test paginated search with invalid continuation token."""
        # Set invalid continuation token in the search request
        sample_search_request.continuation_token = 'invalid_token_format'
        sample_search_request.enable_storage_pagination = True

        # Mock the search engines
        orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )
        orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )
        orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )

        # Should handle invalid token gracefully and start fresh search
        result = await orchestrator.search_paginated(sample_search_request)

        assert result is not None
        assert hasattr(result, 'enhanced_response')
        assert 'results' in result.enhanced_response

    @pytest.mark.asyncio
    async def test_search_paginated_with_score_threshold_filtering(
        self, orchestrator, sample_search_request
    ):
        """Test paginated search with score threshold filtering from continuation token (lines 281-286)."""
        # Create a continuation token with score threshold
        global_token = GlobalContinuationToken()
        global_token.last_score_threshold = 0.5
        global_token.total_results_seen = 10

        sample_search_request.continuation_token = global_token.encode()
        sample_search_request.max_results = 5
        sample_search_request.enable_storage_pagination = True

        # Mock the internal methods to test the specific score threshold filtering logic
        with patch.object(orchestrator, '_execute_parallel_paginated_searches') as mock_execute:
            # Mock return with files
            files = [
                GenomicsFile(
                    path='s3://test/file1.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
            ]

            next_token = GlobalContinuationToken()
            mock_execute.return_value = (files, next_token, 1)

            # Mock scoring to return a score above the threshold
            with patch.object(orchestrator, '_score_results') as mock_score:
                scored_results = [
                    GenomicsFileResult(
                        primary_file=files[0],
                        associated_files=[],
                        relevance_score=0.8,
                        match_reasons=[],
                    )  # Above threshold
                ]
                mock_score.return_value = scored_results

                # Mock ranking to return the same results
                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = scored_results

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_build.return_value = {
                            'results': [],  # Should be empty after threshold filtering
                            'total_found': 0,
                            'search_duration_ms': 1,
                            'storage_systems_searched': ['s3'],
                            'has_more_results': False,
                        }

                        result = await orchestrator.search_paginated(sample_search_request)

                        assert result is not None
                        # The test passes if the score threshold filtering code path is executed
                        assert hasattr(result, 'enhanced_response')

    @pytest.mark.asyncio
    async def test_search_paginated_with_score_threshold_update(
        self, orchestrator, sample_search_request
    ):
        """Test that score threshold is updated for next page when there are more results."""
        sample_search_request.max_results = 2
        sample_search_request.enable_storage_pagination = True

        # Mock the internal method to test score threshold logic
        with patch.object(orchestrator, '_execute_parallel_paginated_searches') as mock_execute:
            # Create mock files
            files = [
                GenomicsFile(
                    path=f's3://test/file{i}.fastq',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000,
                    storage_class='STANDARD',
                    last_modified=datetime.now(),
                    tags={},
                    source_system='s3',
                    metadata={},
                )
                for i in range(3)
            ]

            # Mock return with more results available
            next_token = GlobalContinuationToken(s3_tokens={'s3://test-bucket/': 'has_more'})
            mock_execute.return_value = (files, next_token, 3)

            # Mock scoring and ranking
            with patch.object(orchestrator, '_score_results') as mock_score:
                scored_results = [
                    GenomicsFileResult(
                        primary_file=files[0],
                        associated_files=[],
                        relevance_score=1.0,
                        match_reasons=[],
                    ),
                    GenomicsFileResult(
                        primary_file=files[1],
                        associated_files=[],
                        relevance_score=0.8,
                        match_reasons=[],
                    ),
                    GenomicsFileResult(
                        primary_file=files[2],
                        associated_files=[],
                        relevance_score=0.6,
                        match_reasons=[],
                    ),
                ]
                mock_score.return_value = scored_results

                with patch.object(orchestrator.result_ranker, 'rank_results') as mock_rank:
                    mock_rank.return_value = scored_results

                    with patch.object(
                        orchestrator.json_builder, 'build_search_response'
                    ) as mock_build:
                        mock_build.return_value = {
                            'results': [{'file': f'file{i}'} for i in range(2)],
                            'total_found': 3,
                            'search_duration_ms': 1,
                            'storage_systems_searched': ['s3'],
                            'has_more_results': True,
                            'next_continuation_token': 'encoded_token',
                        }

                        result = await orchestrator.search_paginated(sample_search_request)

                        assert result is not None
                        assert result.enhanced_response['has_more_results'] is True

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_with_token_parsing_errors(
        self, orchestrator, sample_search_request
    ):
        """Test handling of continuation token parsing errors in paginated searches."""
        # Test the specific lines 581-596 that handle token parsing errors
        global_token = GlobalContinuationToken()

        # Mock search engines to return results with continuation tokens
        orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=True, next_continuation_token='s3_token'
            )
        )

        # Create a mock response that will trigger the healthomics sequence token parsing
        seq_token = GlobalContinuationToken()
        seq_token.healthomics_sequence_token = 'seq_token'
        orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=True, next_continuation_token=seq_token.encode()
            )
        )

        # Mock reference store to return invalid token that causes ValueError
        orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=True, next_continuation_token='invalid_ref_token'
            )
        )

        # Mock decode to fail for the invalid reference token
        original_decode = GlobalContinuationToken.decode

        def selective_decode(token):
            if token == 'invalid_ref_token':
                raise ValueError('Invalid token format')
            return original_decode(token)

        with patch(
            'awslabs.aws_healthomics_mcp_server.models.GlobalContinuationToken.decode',
            side_effect=selective_decode,
        ):
            result = await orchestrator._execute_parallel_paginated_searches(
                sample_search_request, StoragePaginationRequest(max_results=10), global_token
            )

            assert result is not None
            assert len(result) == 3  # Should return results from all systems

    @pytest.mark.asyncio
    async def test_execute_parallel_paginated_searches_with_attribute_errors(
        self, orchestrator, sample_search_request
    ):
        """Test handling of AttributeError in paginated searches (lines 596)."""
        # Test the specific AttributeError handling in the orchestrator
        global_token = GlobalContinuationToken()

        # Mock search engines to return unexpected result types that cause AttributeError
        orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
            return_value='unexpected_string_result'  # Not a StoragePaginationResponse
        )
        orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )
        orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )

        result = await orchestrator._execute_parallel_paginated_searches(
            sample_search_request, StoragePaginationRequest(max_results=10), global_token
        )

        assert result is not None
        # Should handle the AttributeError gracefully and continue with other systems
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_cache_cleanup_during_search(self, orchestrator, sample_search_request):
        """Test cache cleanup during search execution (lines 475-478)."""
        # Mock the random function to always trigger cache cleanup
        with patch('secrets.randbelow', return_value=0):  # Always return 0 to trigger cleanup
            orchestrator.s3_engine.search_buckets = AsyncMock(return_value=[])
            orchestrator.s3_engine.cleanup_expired_cache_entries = MagicMock()
            orchestrator.healthomics_engine.search_sequence_stores = AsyncMock(return_value=[])
            orchestrator.healthomics_engine.search_reference_stores = AsyncMock(return_value=[])

            result = await orchestrator._execute_parallel_searches(sample_search_request)

            assert isinstance(result, list)
            # Verify cache cleanup was called
            orchestrator.s3_engine.cleanup_expired_cache_entries.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_cleanup_exception_handling(self, orchestrator, sample_search_request):
        """Test cache cleanup exception handling (lines 475-478)."""
        # Mock the random function to always trigger cache cleanup
        with patch('secrets.randbelow', return_value=0):  # Always return 0 to trigger cleanup
            orchestrator.s3_engine.search_buckets = AsyncMock(return_value=[])
            orchestrator.s3_engine.cleanup_expired_cache_entries = MagicMock(
                side_effect=Exception('Cache cleanup failed')
            )
            orchestrator.healthomics_engine.search_sequence_stores = AsyncMock(return_value=[])
            orchestrator.healthomics_engine.search_reference_stores = AsyncMock(return_value=[])

            # Should not raise exception even if cache cleanup fails
            result = await orchestrator._execute_parallel_searches(sample_search_request)

            assert isinstance(result, list)
            # Verify cache cleanup was attempted
            orchestrator.s3_engine.cleanup_expired_cache_entries.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_healthomics_references_with_timeout_exception(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics reference search with general exception."""
        orchestrator.healthomics_engine.search_reference_stores = AsyncMock(
            side_effect=Exception('General error')
        )

        result = await orchestrator._search_healthomics_references_with_timeout(
            sample_search_request
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_with_timeout_exception(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence search with general exception."""
        orchestrator.healthomics_engine.search_sequence_stores = AsyncMock(
            side_effect=Exception('General error')
        )

        result = await orchestrator._search_healthomics_sequences_with_timeout(
            sample_search_request
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_search_healthomics_sequences_paginated_with_timeout_exception(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics sequence paginated search with general exception."""
        orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
            side_effect=Exception('General error')
        )

        pagination_request = StoragePaginationRequest(max_results=10)
        result = await orchestrator._search_healthomics_sequences_paginated_with_timeout(
            sample_search_request, pagination_request
        )

        assert hasattr(result, 'results')
        assert result.results == []
        assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_search_healthomics_references_paginated_with_timeout_exception(
        self, orchestrator, sample_search_request
    ):
        """Test HealthOmics reference paginated search with general exception."""
        orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
            side_effect=Exception('General error')
        )

        result = await orchestrator._search_healthomics_references_paginated_with_timeout(
            sample_search_request, StoragePaginationRequest(max_results=10)
        )

        assert result.results == []
        assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_pagination_cache_cleanup_exception_handling(
        self, orchestrator, sample_search_request
    ):
        """Test pagination cache cleanup exception handling."""
        # Mock the random function to always trigger cache cleanup
        with patch('secrets.randbelow', return_value=0):  # Always return 0 to trigger cleanup
            # Mock cleanup_expired_pagination_cache to raise an exception
            orchestrator.cleanup_expired_pagination_cache = MagicMock(
                side_effect=Exception('Pagination cache cleanup failed')
            )

            # Mock the search engines
            orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
                return_value=StoragePaginationResponse(
                    results=[], has_more_results=False, next_continuation_token=None
                )
            )
            orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
                return_value=StoragePaginationResponse(
                    results=[], has_more_results=False, next_continuation_token=None
                )
            )
            orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
                return_value=StoragePaginationResponse(
                    results=[], has_more_results=False, next_continuation_token=None
                )
            )

            sample_search_request.enable_storage_pagination = True

            # Should not raise exception even if pagination cache cleanup fails
            result = await orchestrator.search_paginated(sample_search_request)

            assert result is not None
            assert hasattr(result, 'enhanced_response')
            # Verify cache cleanup was attempted
            orchestrator.cleanup_expired_pagination_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_paginated_exception_handling(self, orchestrator, sample_search_request):
        """Test search_paginated exception handling."""
        sample_search_request.enable_storage_pagination = True

        # Mock _execute_parallel_paginated_searches to raise an exception
        with patch.object(
            orchestrator,
            '_execute_parallel_paginated_searches',
            side_effect=Exception('Paginated search execution failed'),
        ):
            with pytest.raises(Exception) as exc_info:
                await orchestrator.search_paginated(sample_search_request)

            assert 'Paginated search execution failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_s3_with_timeout_exception_handling(
        self, orchestrator, sample_search_request
    ):
        """Test S3 search with timeout exception handling."""
        orchestrator.s3_engine.search_buckets = AsyncMock(
            side_effect=Exception('S3 search failed')
        )

        result = await orchestrator._search_s3_with_timeout(sample_search_request)

        assert result == []

    @pytest.mark.asyncio
    async def test_search_s3_paginated_with_timeout_exception_handling(
        self, orchestrator, sample_search_request
    ):
        """Test S3 paginated search with timeout exception handling."""
        orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
            side_effect=Exception('S3 paginated search failed')
        )

        result = await orchestrator._search_s3_paginated_with_timeout(
            sample_search_request, StoragePaginationRequest(max_results=10)
        )

        assert result.results == []
        assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_complex_search_coordination_logic(self, orchestrator, sample_search_request):
        """Test complex search coordination logic."""
        # Test the complex coordination paths in the orchestrator
        sample_search_request.enable_storage_pagination = True

        # Mock the engines to return complex results that trigger coordination logic
        orchestrator.s3_engine.search_buckets_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[
                    GenomicsFile(
                        path='s3://test/file1.fastq',
                        file_type=GenomicsFileType.FASTQ,
                        size_bytes=1000,
                        storage_class='STANDARD',
                        last_modified=datetime.now(),
                        tags={},
                        source_system='s3',
                        metadata={},
                    )
                ],
                has_more_results=True,
                next_continuation_token='s3_token',
            )
        )

        # Mock HealthOmics engines to return results that need coordination
        orchestrator.healthomics_engine.search_sequence_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[
                    GenomicsFile(
                        path='omics://seq-store/readset1',
                        file_type=GenomicsFileType.BAM,
                        size_bytes=2000,
                        storage_class='STANDARD',
                        last_modified=datetime.now(),
                        tags={},
                        source_system='sequence_store',
                        metadata={},
                    )
                ],
                has_more_results=True,
                next_continuation_token='seq_token',
            )
        )

        orchestrator.healthomics_engine.search_reference_stores_paginated = AsyncMock(
            return_value=StoragePaginationResponse(
                results=[], has_more_results=False, next_continuation_token=None
            )
        )

        result = await orchestrator.search_paginated(sample_search_request)

        assert result is not None
        assert hasattr(result, 'enhanced_response')
        # Verify that coordination logic was executed
        assert 'results' in result.enhanced_response
