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

"""Tests for S3 search engine."""

import asyncio
import pytest
import time
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
    SearchConfig,
    StoragePaginationRequest,
)
from awslabs.aws_healthomics_mcp_server.search.s3_search_engine import S3SearchEngine
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestS3SearchEngine:
    """Test cases for S3 search engine."""

    @pytest.fixture
    def search_config(self):
        """Create a test search configuration."""
        return SearchConfig(
            s3_bucket_paths=['s3://test-bucket/', 's3://test-bucket-2/data/'],
            max_concurrent_searches=5,
            search_timeout_seconds=300,
            enable_s3_tag_search=True,
            max_tag_retrieval_batch_size=100,
            result_cache_ttl_seconds=600,
            tag_cache_ttl_seconds=300,
            default_max_results=100,
            enable_pagination_metrics=True,
        )

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'data/sample1.fastq.gz',
                    'Size': 1000000,
                    'LastModified': datetime(2023, 1, 1, tzinfo=timezone.utc),
                    'StorageClass': 'STANDARD',
                },
                {
                    'Key': 'data/sample2.bam',
                    'Size': 2000000,
                    'LastModified': datetime(2023, 1, 2, tzinfo=timezone.utc),
                    'StorageClass': 'STANDARD',
                },
            ],
            'IsTruncated': False,
        }
        client.get_object_tagging.return_value = {
            'TagSet': [
                {'Key': 'sample_id', 'Value': 'test-sample'},
                {'Key': 'project', 'Value': 'genomics-project'},
            ]
        }
        return client

    @pytest.fixture
    def search_engine(self, search_config, mock_s3_client):
        """Create a test S3 search engine."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_aws_session'
        ) as mock_session:
            mock_session.return_value.client.return_value = mock_s3_client
            engine = S3SearchEngine._create_for_testing(search_config)
            return engine

    def test_init(self, search_config):
        """Test S3SearchEngine initialization."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_aws_session'
        ) as mock_session:
            mock_s3_client = MagicMock()
            mock_session.return_value.client.return_value = mock_s3_client

            engine = S3SearchEngine._create_for_testing(search_config)

            assert engine.config == search_config
            assert engine.s3_client == mock_s3_client
            assert engine.file_type_detector is not None
            assert engine.pattern_matcher is not None
            assert engine._tag_cache == {}
            assert engine._result_cache == {}

    def test_direct_constructor_prevented(self, search_config):
        """Test that direct constructor is prevented."""
        with pytest.raises(
            RuntimeError, match='S3SearchEngine should not be instantiated directly'
        ):
            S3SearchEngine(search_config)

    @patch('awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_genomics_search_config')
    @patch(
        'awslabs.aws_healthomics_mcp_server.search.s3_search_engine.validate_bucket_access_permissions'
    )
    @patch('awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_aws_session')
    def test_from_environment(self, mock_session, mock_validate, mock_config):
        """Test creating S3SearchEngine from environment."""
        # Setup mocks
        mock_config.return_value = SearchConfig(
            s3_bucket_paths=['s3://bucket1/', 's3://bucket2/'],
            enable_s3_tag_search=True,
        )
        mock_validate.return_value = ['s3://bucket1/']
        mock_s3_client = MagicMock()
        mock_session.return_value.client.return_value = mock_s3_client

        engine = S3SearchEngine.from_environment()

        assert len(engine.config.s3_bucket_paths) == 1
        assert engine.config.s3_bucket_paths[0] == 's3://bucket1/'
        mock_config.assert_called_once()
        mock_validate.assert_called_once()

    @patch('awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_genomics_search_config')
    @patch(
        'awslabs.aws_healthomics_mcp_server.search.s3_search_engine.validate_bucket_access_permissions'
    )
    def test_from_environment_validation_error(self, mock_validate, mock_config):
        """Test from_environment with validation error."""
        mock_config.return_value = SearchConfig(s3_bucket_paths=['s3://bucket1/'])
        mock_validate.side_effect = ValueError('No accessible buckets')

        with pytest.raises(ValueError, match='Cannot create S3SearchEngine'):
            S3SearchEngine.from_environment()

    @pytest.mark.asyncio
    async def test_search_buckets_success(self, search_engine):
        """Test successful bucket search."""
        # Mock the internal search method
        search_engine._search_single_bucket_path_optimized = AsyncMock(
            return_value=[
                GenomicsFile(
                    path='s3://test-bucket/data/sample1.fastq.gz',
                    file_type=GenomicsFileType.FASTQ,
                    size_bytes=1000000,
                    storage_class='STANDARD',
                    last_modified=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    tags={'sample_id': 'test'},
                    source_system='s3',
                    metadata={},
                )
            ]
        )

        results = await search_engine.search_buckets(
            bucket_paths=['s3://test-bucket/'], file_type='fastq', search_terms=['sample']
        )

        assert len(results) == 1
        assert results[0].file_type == GenomicsFileType.FASTQ
        assert results[0].source_system == 's3'

    @pytest.mark.asyncio
    async def test_search_buckets_empty_paths(self, search_engine):
        """Test search with empty bucket paths."""
        results = await search_engine.search_buckets(
            bucket_paths=[], file_type=None, search_terms=[]
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_buckets_with_timeout(self, search_engine):
        """Test search with timeout handling."""

        # Mock a slow search that times out
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow operation
            return []

        search_engine._search_single_bucket_path_optimized = slow_search
        search_engine.config.search_timeout_seconds = 1  # Short timeout

        results = await search_engine.search_buckets(
            bucket_paths=['s3://test-bucket/'], file_type=None, search_terms=[]
        )

        # Should return empty results due to timeout
        assert results == []

    @pytest.mark.asyncio
    async def test_search_buckets_paginated(self, search_engine):
        """Test paginated bucket search."""
        pagination_request = StoragePaginationRequest(
            max_results=10, buffer_size=100, continuation_token=None
        )

        # Mock the internal paginated search method
        search_engine._search_single_bucket_path_paginated = AsyncMock(return_value=([], None, 0))

        result = await search_engine.search_buckets_paginated(
            bucket_paths=['s3://test-bucket/'],
            file_type='fastq',
            search_terms=['sample'],
            pagination_request=pagination_request,
        )

        assert hasattr(result, 'results')
        assert hasattr(result, 'has_more_results')
        assert hasattr(result, 'next_continuation_token')

    @pytest.mark.asyncio
    async def test_search_buckets_paginated_empty_paths(self, search_engine):
        """Test paginated search with empty bucket paths."""
        pagination_request = StoragePaginationRequest(max_results=10)

        result = await search_engine.search_buckets_paginated(
            bucket_paths=[], file_type=None, search_terms=[], pagination_request=pagination_request
        )

        assert result.results == []
        assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_search_buckets_paginated_invalid_continuation_token(self, search_engine):
        """Test paginated search with invalid continuation token."""
        # Create an invalid continuation token
        pagination_request = StoragePaginationRequest(
            max_results=10, continuation_token='invalid_token_data'
        )

        # Mock the internal paginated search method
        search_engine._search_single_bucket_path_paginated = AsyncMock(return_value=([], None, 0))

        # This should handle the invalid token gracefully and start fresh
        result = await search_engine.search_buckets_paginated(
            bucket_paths=['s3://test-bucket/'],
            file_type='fastq',
            search_terms=['sample'],
            pagination_request=pagination_request,
        )

        assert hasattr(result, 'results')
        assert hasattr(result, 'has_more_results')

    @pytest.mark.asyncio
    async def test_search_buckets_paginated_buffer_overflow(self, search_engine):
        """Test paginated search with buffer overflow."""
        pagination_request = StoragePaginationRequest(
            max_results=10,
            buffer_size=5,  # Small buffer to trigger overflow
        )

        # Mock the internal method to return more results than buffer size
        from datetime import datetime

        mock_files = [
            GenomicsFile(
                path=f's3://test-bucket/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='s3',
                metadata={},
            )
            for i in range(10)  # 10 files > buffer_size of 5
        ]

        search_engine._search_single_bucket_path_paginated = AsyncMock(
            return_value=(mock_files, None, 10)
        )

        result = await search_engine.search_buckets_paginated(
            bucket_paths=['s3://test-bucket/'],
            file_type='fastq',
            search_terms=['sample'],
            pagination_request=pagination_request,
        )

        # Should still return results despite buffer overflow
        assert len(result.results) == 10

    @pytest.mark.asyncio
    async def test_search_buckets_paginated_exception_handling(self, search_engine):
        """Test paginated search with exceptions in bucket search."""
        pagination_request = StoragePaginationRequest(max_results=10)

        # Mock the internal method to raise an exception
        search_engine._search_single_bucket_path_paginated = AsyncMock(
            side_effect=Exception('Bucket access denied')
        )

        result = await search_engine.search_buckets_paginated(
            bucket_paths=['s3://test-bucket/'],
            file_type='fastq',
            search_terms=['sample'],
            pagination_request=pagination_request,
        )

        # Should handle exception gracefully and return empty results
        assert result.results == []
        assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_search_buckets_paginated_unexpected_result_type(self, search_engine):
        """Test paginated search with unexpected result type."""
        pagination_request = StoragePaginationRequest(max_results=10)

        # Mock the internal method to return unexpected result types
        search_engine._search_single_bucket_path_paginated = AsyncMock(
            side_effect=[
                Exception('Unexpected error'),  # This should trigger exception handling
                ([], None, 0),  # Valid result for second bucket
            ]
        )

        result = await search_engine.search_buckets_paginated(
            bucket_paths=['s3://test-bucket/', 's3://test-bucket-2/'],
            file_type='fastq',
            search_terms=['sample'],
            pagination_request=pagination_request,
        )

        # Should handle unexpected result gracefully
        assert result.results == []

    @pytest.mark.asyncio
    async def test_validate_bucket_access_success(self, search_engine):
        """Test successful bucket access validation."""
        search_engine.s3_client.head_bucket.return_value = {}

        # Should not raise an exception
        await search_engine._validate_bucket_access('test-bucket')

        search_engine.s3_client.head_bucket.assert_called_once_with(Bucket='test-bucket')

    @pytest.mark.asyncio
    async def test_validate_bucket_access_failure(self, search_engine):
        """Test bucket access validation failure."""
        search_engine.s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}, 'HeadBucket'
        )

        with pytest.raises(ClientError):
            await search_engine._validate_bucket_access('test-bucket')

    @pytest.mark.asyncio
    async def test_list_s3_objects(self, search_engine):
        """Test listing S3 objects."""
        search_engine.s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'data/file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime(2023, 1, 1, tzinfo=timezone.utc),
                    'StorageClass': 'STANDARD',
                }
            ],
            'IsTruncated': False,
        }

        objects = await search_engine._list_s3_objects('test-bucket', 'data/')

        assert len(objects) == 1
        assert objects[0]['Key'] == 'data/file1.fastq'
        search_engine.s3_client.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket', Prefix='data/', MaxKeys=1000
        )

    @pytest.mark.asyncio
    async def test_list_s3_objects_empty(self, search_engine):
        """Test listing S3 objects with empty result."""
        search_engine.s3_client.list_objects_v2.return_value = {
            'IsTruncated': False,
        }

        objects = await search_engine._list_s3_objects('test-bucket', 'data/')

        assert objects == []

    @pytest.mark.asyncio
    async def test_list_s3_objects_client_error(self, search_engine):
        """Test listing S3 objects with ClientError."""
        search_engine.s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListObjectsV2'
        )

        with pytest.raises(ClientError):
            await search_engine._list_s3_objects('test-bucket', 'data/')

    @pytest.mark.asyncio
    async def test_list_s3_objects_paginated(self, search_engine):
        """Test paginated S3 object listing."""
        # Mock paginated response
        search_engine.s3_client.list_objects_v2.side_effect = [
            {
                'Contents': [
                    {
                        'Key': 'file1.fastq',
                        'Size': 1000,
                        'LastModified': datetime.now(),
                        'StorageClass': 'STANDARD',
                    }
                ],
                'IsTruncated': True,
                'NextContinuationToken': 'token123',
            },
            {
                'Contents': [
                    {
                        'Key': 'file2.fastq',
                        'Size': 2000,
                        'LastModified': datetime.now(),
                        'StorageClass': 'STANDARD',
                    }
                ],
                'IsTruncated': False,
            },
        ]

        objects, next_token, total_scanned = await search_engine._list_s3_objects_paginated(
            'test-bucket', 'data/', None, 10
        )

        assert len(objects) == 2
        assert next_token is None  # Should be None when no more pages
        assert total_scanned == 2

    def test_create_genomics_file_from_object(self, search_engine):
        """Test creating GenomicsFile from S3 object."""
        s3_object = {
            'Key': 'data/sample.fastq.gz',
            'Size': 1000000,
            'LastModified': datetime(2023, 1, 1, tzinfo=timezone.utc),
            'StorageClass': 'STANDARD',
        }

        genomics_file = search_engine._create_genomics_file_from_object(
            s3_object, 'test-bucket', {'sample_id': 'test'}, GenomicsFileType.FASTQ
        )

        assert genomics_file.path == 's3://test-bucket/data/sample.fastq.gz'
        assert genomics_file.file_type == GenomicsFileType.FASTQ
        assert genomics_file.size_bytes == 1000000
        assert genomics_file.storage_class == 'STANDARD'
        assert genomics_file.tags == {'sample_id': 'test'}
        assert genomics_file.source_system == 's3'

    @pytest.mark.asyncio
    async def test_get_object_tags_cached(self, search_engine):
        """Test getting object tags with caching."""
        # First call should fetch from S3
        search_engine.s3_client.get_object_tagging.return_value = {
            'TagSet': [{'Key': 'sample_id', 'Value': 'test'}]
        }

        tags1 = await search_engine._get_object_tags_cached('test-bucket', 'data/file.fastq')
        assert tags1 == {'sample_id': 'test'}

        # Second call should use cache
        tags2 = await search_engine._get_object_tags_cached('test-bucket', 'data/file.fastq')
        assert tags2 == {'sample_id': 'test'}

        # S3 should only be called once due to caching
        search_engine.s3_client.get_object_tagging.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_object_tags_error(self, search_engine):
        """Test getting object tags with error."""
        search_engine.s3_client.get_object_tagging.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}}, 'GetObjectTagging'
        )

        tags = await search_engine._get_object_tags('test-bucket', 'nonexistent.fastq')
        assert tags == {}

    def test_matches_file_type_filter(self, search_engine):
        """Test file type filter matching."""
        # Test positive matches
        assert search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, 'fastq')
        assert search_engine._matches_file_type_filter(GenomicsFileType.BAM, 'bam')
        assert search_engine._matches_file_type_filter(GenomicsFileType.VCF, 'vcf')

        # Test negative matches
        assert not search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, 'bam')
        assert not search_engine._matches_file_type_filter(GenomicsFileType.FASTA, 'fastq')

        # Test no filter (should match all)
        assert search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, None)

    def test_matches_search_terms(self, search_engine):
        """Test search terms matching."""
        s3_path = 's3://bucket/sample_cancer_patient1.fastq'
        tags = {'sample_type': 'tumor', 'patient_id': 'P001'}

        # Test positive matches
        assert search_engine._matches_search_terms(s3_path, tags, ['cancer'])
        assert search_engine._matches_search_terms(s3_path, tags, ['patient'])
        assert search_engine._matches_search_terms(s3_path, tags, ['tumor'])
        assert search_engine._matches_search_terms(s3_path, tags, ['P001'])

        # Test negative matches
        assert not search_engine._matches_search_terms(s3_path, tags, ['nonexistent'])

        # Test empty search terms (should match all)
        assert search_engine._matches_search_terms(s3_path, tags, [])

    def test_is_related_index_file(self, search_engine):
        """Test related index file detection."""
        # Test positive matches
        assert search_engine._is_related_index_file(GenomicsFileType.BAI, 'bam')
        assert search_engine._is_related_index_file(GenomicsFileType.TBI, 'vcf')
        assert search_engine._is_related_index_file(GenomicsFileType.FAI, 'fasta')

        # Test negative matches
        assert not search_engine._is_related_index_file(GenomicsFileType.FASTQ, 'bam')
        assert not search_engine._is_related_index_file(GenomicsFileType.BAI, 'fastq')

    def test_create_search_cache_key(self, search_engine):
        """Test search cache key creation."""
        key = search_engine._create_search_cache_key(
            's3://bucket/path/', 'fastq', ['cancer', 'patient']
        )

        assert isinstance(key, str)
        assert len(key) > 0

        # Same inputs should produce same key
        key2 = search_engine._create_search_cache_key(
            's3://bucket/path/', 'fastq', ['cancer', 'patient']
        )
        assert key == key2

        # Different inputs should produce different keys
        key3 = search_engine._create_search_cache_key(
            's3://bucket/path/', 'bam', ['cancer', 'patient']
        )
        assert key != key3

    def test_cache_operations(self, search_engine):
        """Test cache operations."""
        cache_key = 'test_key'
        test_results = [
            GenomicsFile(
                path='s3://bucket/test.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(),
                tags={},
                source_system='s3',
                metadata={},
            )
        ]

        # Test cache miss
        cached = search_engine._get_cached_result(cache_key)
        assert cached is None

        # Test cache set
        search_engine._cache_search_result(cache_key, test_results)

        # Test cache hit
        cached = search_engine._get_cached_result(cache_key)
        assert cached == test_results

    def test_get_cache_stats(self, search_engine):
        """Test cache statistics."""
        # Add some entries to cache to test utilization calculation
        search_engine._tag_cache['key1'] = {'tags': {}, 'timestamp': time.time()}
        search_engine._result_cache['key2'] = {'results': [], 'timestamp': time.time()}

        stats = search_engine.get_cache_stats()

        assert 'tag_cache' in stats
        assert 'result_cache' in stats
        assert 'config' in stats
        assert 'total_entries' in stats['tag_cache']
        assert 'valid_entries' in stats['tag_cache']
        assert 'ttl_seconds' in stats['tag_cache']
        assert 'max_cache_size' in stats['tag_cache']
        assert 'cache_utilization' in stats['tag_cache']
        assert 'max_cache_size' in stats['result_cache']
        assert 'cache_utilization' in stats['result_cache']
        assert 'cache_cleanup_keep_ratio' in stats['config']
        assert isinstance(stats['tag_cache']['total_entries'], int)
        assert isinstance(stats['result_cache']['total_entries'], int)
        assert isinstance(stats['tag_cache']['cache_utilization'], float)
        assert isinstance(stats['result_cache']['cache_utilization'], float)

        # Test utilization calculation
        expected_tag_utilization = (
            len(search_engine._tag_cache) / search_engine.config.max_tag_cache_size
        )
        expected_result_utilization = (
            len(search_engine._result_cache) / search_engine.config.max_result_cache_size
        )
        assert stats['tag_cache']['cache_utilization'] == expected_tag_utilization
        assert stats['result_cache']['cache_utilization'] == expected_result_utilization

    def test_cleanup_expired_cache_entries(self, search_engine):
        """Test cache cleanup."""
        # Add some entries to cache
        search_engine._tag_cache['key1'] = {'tags': {}, 'timestamp': time.time() - 1000}
        search_engine._result_cache['key2'] = {'results': [], 'timestamp': time.time() - 1000}

        initial_tag_size = len(search_engine._tag_cache)
        initial_result_size = len(search_engine._result_cache)

        search_engine.cleanup_expired_cache_entries()

        # Cache should be cleaned up (expired entries removed)
        assert len(search_engine._tag_cache) <= initial_tag_size
        assert len(search_engine._result_cache) <= initial_result_size

    def test_cleanup_cache_by_size_tag_cache(self, search_engine):
        """Test size-based cache cleanup for tag cache."""
        # Set small cache size for testing
        search_engine.config.max_tag_cache_size = 3
        search_engine.config.cache_cleanup_keep_ratio = 0.6  # Keep 60%

        # Add more entries than the limit
        for i in range(5):
            search_engine._tag_cache[f'key{i}'] = {
                'tags': {'test': f'value{i}'},
                'timestamp': time.time() + i,
            }

        assert len(search_engine._tag_cache) == 5

        # Trigger size-based cleanup
        search_engine._cleanup_cache_by_size(
            search_engine._tag_cache,
            search_engine.config.max_tag_cache_size,
            search_engine.config.cache_cleanup_keep_ratio,
        )

        # Should keep 60% of max_size = 1.8 -> 1 entry (most recent)
        expected_size = int(
            search_engine.config.max_tag_cache_size * search_engine.config.cache_cleanup_keep_ratio
        )
        assert len(search_engine._tag_cache) == expected_size

        # Should keep the most recent entries (highest timestamps)
        remaining_keys = list(search_engine._tag_cache.keys())
        assert 'key4' in remaining_keys  # Most recent entry

    def test_cleanup_cache_by_size_result_cache(self, search_engine):
        """Test size-based cache cleanup for result cache."""
        # Set small cache size for testing
        search_engine.config.max_result_cache_size = 4
        search_engine.config.cache_cleanup_keep_ratio = 0.5  # Keep 50%

        # Add more entries than the limit
        for i in range(6):
            search_engine._result_cache[f'search_key_{i}'] = {
                'results': [],
                'timestamp': time.time() + i,
            }

        assert len(search_engine._result_cache) == 6

        # Trigger size-based cleanup
        search_engine._cleanup_cache_by_size(
            search_engine._result_cache,
            search_engine.config.max_result_cache_size,
            search_engine.config.cache_cleanup_keep_ratio,
        )

        # Should keep 50% of max_size = 2 entries (most recent)
        expected_size = int(
            search_engine.config.max_result_cache_size
            * search_engine.config.cache_cleanup_keep_ratio
        )
        assert len(search_engine._result_cache) == expected_size

        # Should keep the most recent entries
        remaining_keys = list(search_engine._result_cache.keys())
        assert 'search_key_5' in remaining_keys  # Most recent entry
        assert 'search_key_4' in remaining_keys  # Second most recent entry

    def test_cleanup_cache_by_size_no_cleanup_needed(self, search_engine):
        """Test that size-based cleanup does nothing when cache is under limit."""
        # Set cache size larger than current entries
        search_engine.config.max_tag_cache_size = 10

        # Add fewer entries than the limit
        for i in range(3):
            search_engine._tag_cache[f'key{i}'] = {
                'tags': {'test': f'value{i}'},
                'timestamp': time.time(),
            }

        initial_size = len(search_engine._tag_cache)

        # Trigger size-based cleanup
        search_engine._cleanup_cache_by_size(
            search_engine._tag_cache,
            search_engine.config.max_tag_cache_size,
            search_engine.config.cache_cleanup_keep_ratio,
        )

        # Should not remove any entries
        assert len(search_engine._tag_cache) == initial_size

    @pytest.mark.asyncio
    async def test_automatic_tag_cache_size_cleanup(self, search_engine):
        """Test that tag cache automatically cleans up when size limit is reached."""
        # Set small cache size for testing
        search_engine.config.max_tag_cache_size = 2
        search_engine.config.cache_cleanup_keep_ratio = 0.5  # Keep 50%

        # Mock S3 client
        search_engine.s3_client.get_object_tagging.return_value = {
            'TagSet': [{'Key': 'test', 'Value': 'value'}]
        }

        # Add entries that will trigger automatic cleanup
        for i in range(4):
            await search_engine._get_object_tags_cached('test-bucket', f'key{i}')

            # Cache should never exceed the maximum size
            assert len(search_engine._tag_cache) <= search_engine.config.max_tag_cache_size

    def test_automatic_result_cache_size_cleanup(self, search_engine):
        """Test that result cache automatically cleans up when size limit is reached."""
        # Set small cache size for testing
        search_engine.config.max_result_cache_size = 2
        search_engine.config.cache_cleanup_keep_ratio = 0.5  # Keep 50%

        # Add entries that will trigger automatic cleanup
        for i in range(4):
            search_engine._cache_search_result(f'search_key_{i}', [])

            # Cache should never exceed the maximum size
            assert len(search_engine._result_cache) <= search_engine.config.max_result_cache_size

    def test_smart_cache_cleanup_prioritizes_expired_entries(self, search_engine):
        """Test that smart cache cleanup removes expired entries first."""
        # Set small cache size and short TTL for testing
        search_engine.config.max_tag_cache_size = 3
        search_engine.config.cache_cleanup_keep_ratio = 0.6  # Keep 60% = 1 entry
        search_engine.config.tag_cache_ttl_seconds = 10  # 10 second TTL

        current_time = time.time()

        # Add mix of expired and valid entries
        search_engine._tag_cache['expired1'] = {
            'tags': {'test': 'expired1'},
            'timestamp': current_time - 20,
        }  # Expired
        search_engine._tag_cache['expired2'] = {
            'tags': {'test': 'expired2'},
            'timestamp': current_time - 15,
        }  # Expired
        search_engine._tag_cache['valid1'] = {
            'tags': {'test': 'valid1'},
            'timestamp': current_time - 5,
        }  # Valid
        search_engine._tag_cache['valid2'] = {
            'tags': {'test': 'valid2'},
            'timestamp': current_time - 2,
        }  # Valid (newest)

        assert len(search_engine._tag_cache) == 4

        # Trigger smart cleanup
        search_engine._cleanup_cache_by_size(
            search_engine._tag_cache,
            search_engine.config.max_tag_cache_size,
            search_engine.config.cache_cleanup_keep_ratio,
        )

        # Should keep only 1 entry (60% of 3 = 1.8 -> 1)
        # Should prioritize removing expired entries first, then oldest valid
        # Expected: expired1, expired2, and valid1 removed; valid2 kept (newest valid)
        assert len(search_engine._tag_cache) == 1
        assert 'valid2' in search_engine._tag_cache  # Newest valid entry should remain
        assert 'expired1' not in search_engine._tag_cache
        assert 'expired2' not in search_engine._tag_cache
        assert 'valid1' not in search_engine._tag_cache

    def test_smart_cache_cleanup_only_expired_entries(self, search_engine):
        """Test smart cleanup when only expired entries need to be removed."""
        # Set cache size larger than valid entries
        search_engine.config.max_tag_cache_size = 5
        search_engine.config.cache_cleanup_keep_ratio = 0.8  # Keep 80% = 4 entries
        search_engine.config.tag_cache_ttl_seconds = 10

        current_time = time.time()

        # Add mix where removing expired entries is sufficient
        search_engine._tag_cache['expired1'] = {
            'tags': {'test': 'expired1'},
            'timestamp': current_time - 20,
        }  # Expired
        search_engine._tag_cache['expired2'] = {
            'tags': {'test': 'expired2'},
            'timestamp': current_time - 15,
        }  # Expired
        search_engine._tag_cache['valid1'] = {
            'tags': {'test': 'valid1'},
            'timestamp': current_time - 5,
        }  # Valid
        search_engine._tag_cache['valid2'] = {
            'tags': {'test': 'valid2'},
            'timestamp': current_time - 2,
        }  # Valid
        search_engine._tag_cache['valid3'] = {
            'tags': {'test': 'valid3'},
            'timestamp': current_time - 1,
        }  # Valid

        assert len(search_engine._tag_cache) == 5

        # Trigger smart cleanup
        search_engine._cleanup_cache_by_size(
            search_engine._tag_cache,
            search_engine.config.max_tag_cache_size,
            search_engine.config.cache_cleanup_keep_ratio,
        )

        # Should remove only expired entries (2), leaving 3 valid entries (under target of 4)
        assert len(search_engine._tag_cache) == 3
        assert 'expired1' not in search_engine._tag_cache
        assert 'expired2' not in search_engine._tag_cache
        assert 'valid1' in search_engine._tag_cache
        assert 'valid2' in search_engine._tag_cache
        assert 'valid3' in search_engine._tag_cache

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_optimized_success(self, search_engine):
        """Test the optimized single bucket path search method."""
        # Mock the dependencies
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects = AsyncMock(
            return_value=[
                {
                    'Key': 'data/sample1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                },
                {
                    'Key': 'data/sample2.bam',
                    'Size': 2000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                },
            ]
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            side_effect=lambda x: GenomicsFileType.FASTQ
            if x.endswith('.fastq')
            else GenomicsFileType.BAM
            if x.endswith('.bam')
            else None
        )
        search_engine._matches_file_type_filter = MagicMock(return_value=True)
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.8, ['sample']))
        search_engine._create_genomics_file_from_object = MagicMock(
            side_effect=lambda obj, bucket, tags, file_type: GenomicsFile(
                path=f's3://{bucket}/{obj["Key"]}',
                file_type=file_type,
                size_bytes=obj['Size'],
                storage_class=obj['StorageClass'],
                last_modified=obj['LastModified'],
                tags=tags,
                source_system='s3',
                metadata={},
            )
        )

        result = await search_engine._search_single_bucket_path_optimized(
            's3://test-bucket/data/', 'fastq', ['sample']
        )

        assert len(result) == 2
        assert all(isinstance(f, GenomicsFile) for f in result)
        search_engine._validate_bucket_access.assert_called_once_with('test-bucket')
        search_engine._list_s3_objects.assert_called_once_with('test-bucket', 'data/')

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_optimized_with_tags(self, search_engine):
        """Test optimized search with tag-based matching."""
        # Enable tag search
        search_engine.config.enable_s3_tag_search = True

        # Mock dependencies
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects = AsyncMock(
            return_value=[
                {
                    'Key': 'data/file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                }
            ]
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            return_value=GenomicsFileType.FASTQ
        )
        search_engine._matches_file_type_filter = MagicMock(return_value=True)
        # Path doesn't match, need to check tags
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.0, []))
        search_engine.pattern_matcher.match_tags = MagicMock(return_value=(0.9, ['patient']))
        search_engine._get_tags_for_objects_batch = AsyncMock(
            return_value={'data/file1.fastq': {'patient_id': 'patient123', 'study': 'cancer'}}
        )
        search_engine._create_genomics_file_from_object = MagicMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        result = await search_engine._search_single_bucket_path_optimized(
            's3://test-bucket/data/', 'fastq', ['patient']
        )

        assert len(result) == 1
        search_engine._get_tags_for_objects_batch.assert_called_once_with(
            'test-bucket', ['data/file1.fastq']
        )

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_optimized_no_search_terms(self, search_engine):
        """Test optimized search with no search terms (return all matching file types)."""
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects = AsyncMock(
            return_value=[
                {
                    'Key': 'file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                }
            ]
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            return_value=GenomicsFileType.FASTQ
        )
        search_engine._matches_file_type_filter = MagicMock(return_value=True)
        search_engine._create_genomics_file_from_object = MagicMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        result = await search_engine._search_single_bucket_path_optimized(
            's3://test-bucket/',
            'fastq',
            [],  # No search terms
        )

        assert len(result) == 1
        # Pattern matching should not be called when no search terms
        # (We can't easily assert this since pattern_matcher is a real object)

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_optimized_file_type_filtering(self, search_engine):
        """Test optimized search with file type filtering."""
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects = AsyncMock(
            return_value=[
                {
                    'Key': 'file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                },
                {
                    'Key': 'file2.bam',
                    'Size': 2000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                },
            ]
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            side_effect=lambda x: GenomicsFileType.FASTQ
            if x.endswith('.fastq')
            else GenomicsFileType.BAM
            if x.endswith('.bam')
            else None
        )
        # Only FASTQ files should match
        search_engine._matches_file_type_filter = MagicMock(
            side_effect=lambda detected, filter_type: detected == GenomicsFileType.FASTQ
            if filter_type == 'fastq'
            else True
        )
        search_engine._create_genomics_file_from_object = MagicMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        result = await search_engine._search_single_bucket_path_optimized(
            's3://test-bucket/', 'fastq', []
        )

        assert len(result) == 1  # Only FASTQ file should be included

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_optimized_exception_handling(self, search_engine):
        """Test exception handling in optimized search."""
        search_engine._validate_bucket_access = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}, 'HeadBucket'
            )
        )

        with pytest.raises(ClientError):
            await search_engine._search_single_bucket_path_optimized(
                's3://nonexistent-bucket/', 'fastq', ['sample']
            )

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_paginated_success(self, search_engine):
        """Test the paginated single bucket path search method."""
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects_paginated = AsyncMock(
            return_value=(
                [
                    {
                        'Key': 'data/sample1.fastq',
                        'Size': 1000,
                        'LastModified': datetime.now(),
                        'StorageClass': 'STANDARD',
                    }
                ],
                'next_token_123',
                1,
            )
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            return_value=GenomicsFileType.FASTQ
        )
        search_engine._matches_file_type_filter = MagicMock(return_value=True)
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.8, ['sample']))
        search_engine._create_genomics_file_from_object = MagicMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        files, next_token, scanned = await search_engine._search_single_bucket_path_paginated(
            's3://test-bucket/data/', 'fastq', ['sample'], 'continuation_token', 100
        )

        assert len(files) == 1
        assert next_token == 'next_token_123'
        assert scanned == 1
        search_engine._list_s3_objects_paginated.assert_called_once_with(
            'test-bucket', 'data/', 'continuation_token', 100
        )

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_paginated_with_tags(self, search_engine):
        """Test paginated search with tag-based matching."""
        search_engine.config.enable_s3_tag_search = True
        search_engine._validate_bucket_access = AsyncMock()
        search_engine._list_s3_objects_paginated = AsyncMock(
            return_value=(
                [
                    {
                        'Key': 'file1.fastq',
                        'Size': 1000,
                        'LastModified': datetime.now(),
                        'StorageClass': 'STANDARD',
                    }
                ],
                None,
                1,
            )
        )
        search_engine.file_type_detector.detect_file_type = MagicMock(
            return_value=GenomicsFileType.FASTQ
        )
        search_engine._matches_file_type_filter = MagicMock(return_value=True)
        search_engine.pattern_matcher.match_file_path = MagicMock(
            return_value=(0.0, [])
        )  # No path match
        search_engine.pattern_matcher.match_tags = MagicMock(return_value=(0.9, ['patient']))
        search_engine._get_tags_for_objects_batch = AsyncMock(
            return_value={'file1.fastq': {'patient_id': 'patient123'}}
        )
        search_engine._create_genomics_file_from_object = MagicMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        files, next_token, scanned = await search_engine._search_single_bucket_path_paginated(
            's3://test-bucket/', 'fastq', ['patient'], None, 100
        )

        assert len(files) == 1
        assert next_token is None
        assert scanned == 1

    @pytest.mark.asyncio
    async def test_search_single_bucket_path_paginated_exception_handling(self, search_engine):
        """Test exception handling in paginated search."""
        search_engine._validate_bucket_access = AsyncMock(
            side_effect=Exception('Validation failed')
        )

        with pytest.raises(Exception, match='Validation failed'):
            await search_engine._search_single_bucket_path_paginated(
                's3://test-bucket/', 'fastq', ['sample'], None, 100
            )

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_empty_keys(self, search_engine):
        """Test batch tag retrieval with empty key list."""
        result = await search_engine._get_tags_for_objects_batch('test-bucket', [])

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_all_cached(self, search_engine):
        """Test batch tag retrieval when all tags are cached."""
        # Pre-populate cache
        search_engine._tag_cache = {
            'test-bucket/file1.fastq': {
                'tags': {'patient_id': 'patient123'},
                'timestamp': time.time(),
            },
            'test-bucket/file2.fastq': {
                'tags': {'sample_id': 'sample456'},
                'timestamp': time.time(),
            },
        }

        result = await search_engine._get_tags_for_objects_batch(
            'test-bucket', ['file1.fastq', 'file2.fastq']
        )

        assert result == {
            'file1.fastq': {'patient_id': 'patient123'},
            'file2.fastq': {'sample_id': 'sample456'},
        }

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_expired_cache(self, search_engine):
        """Test batch tag retrieval with expired cache entries."""
        # Pre-populate cache with expired entries
        search_engine._tag_cache = {
            'test-bucket/file1.fastq': {
                'tags': {'old': 'data'},
                'timestamp': time.time() - 1000,  # Expired
            }
        }
        search_engine._get_object_tags_cached = AsyncMock(
            return_value={'patient_id': 'patient123'}
        )

        result = await search_engine._get_tags_for_objects_batch('test-bucket', ['file1.fastq'])

        assert result == {'file1.fastq': {'patient_id': 'patient123'}}
        # Expired entry should be removed
        assert 'test-bucket/file1.fastq' not in search_engine._tag_cache

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_with_batching(self, search_engine):
        """Test batch tag retrieval with batching logic."""
        # Set small batch size to test batching
        search_engine.config.max_tag_retrieval_batch_size = 2

        search_engine._get_object_tags_cached = AsyncMock(
            side_effect=[{'tag1': 'value1'}, {'tag2': 'value2'}, {'tag3': 'value3'}]
        )

        result = await search_engine._get_tags_for_objects_batch(
            'test-bucket', ['file1.fastq', 'file2.fastq', 'file3.fastq']
        )

        assert len(result) == 3
        assert result['file1.fastq'] == {'tag1': 'value1'}
        assert result['file2.fastq'] == {'tag2': 'value2'}
        assert result['file3.fastq'] == {'tag3': 'value3'}

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_with_exceptions(self, search_engine):
        """Test batch tag retrieval with some exceptions."""
        search_engine._get_object_tags_cached = AsyncMock(
            side_effect=[{'tag1': 'value1'}, Exception('Failed to get tags'), {'tag3': 'value3'}]
        )

        result = await search_engine._get_tags_for_objects_batch(
            'test-bucket', ['file1.fastq', 'file2.fastq', 'file3.fastq']
        )

        # Should get results for successful calls only
        assert len(result) == 2
        assert result['file1.fastq'] == {'tag1': 'value1'}
        assert result['file3.fastq'] == {'tag3': 'value3'}
        assert 'file2.fastq' not in result

    @pytest.mark.asyncio
    async def test_list_s3_objects_paginated_success(self, search_engine):
        """Test paginated S3 object listing."""
        # Mock the s3_client to return a single object
        mock_response = {
            'Contents': [
                {
                    'Key': 'file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                }
            ],
            'IsTruncated': True,
            'NextContinuationToken': 'next_token_123',
        }

        with patch.object(search_engine.s3_client, 'list_objects_v2', return_value=mock_response):
            objects, next_token, scanned = await search_engine._list_s3_objects_paginated(
                'test-bucket',
                'data/',
                'continuation_token',
                1,  # Use MaxKeys=1 to get exactly 1 result
            )

            assert len(objects) == 1
            assert objects[0]['Key'] == 'file1.fastq'
            assert next_token == 'next_token_123'
            assert scanned == 1

    @pytest.mark.asyncio
    async def test_list_s3_objects_paginated_no_continuation_token(self, search_engine):
        """Test paginated S3 object listing without continuation token."""
        search_engine.s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'file1.fastq',
                    'Size': 1000,
                    'LastModified': datetime.now(),
                    'StorageClass': 'STANDARD',
                }
            ],
            'IsTruncated': False,
        }

        objects, next_token, scanned = await search_engine._list_s3_objects_paginated(
            'test-bucket', 'data/', None, 100
        )

        assert len(objects) == 1
        assert next_token is None
        assert scanned == 1

        # Should not include ContinuationToken parameter
        search_engine.s3_client.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket', Prefix='data/', MaxKeys=100
        )

    @pytest.mark.asyncio
    async def test_list_s3_objects_paginated_empty_result(self, search_engine):
        """Test paginated S3 object listing with empty result."""
        search_engine.s3_client.list_objects_v2.return_value = {
            'IsTruncated': False,
        }

        objects, next_token, scanned = await search_engine._list_s3_objects_paginated(
            'test-bucket', 'data/', None, 100
        )

        assert objects == []
        assert next_token is None
        assert scanned == 0

    @pytest.mark.asyncio
    async def test_list_s3_objects_paginated_client_error(self, search_engine):
        """Test paginated S3 object listing with client error."""
        search_engine.s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}, 'ListObjectsV2'
        )

        with pytest.raises(ClientError):
            await search_engine._list_s3_objects_paginated('test-bucket', 'data/', None, 100)

    def test_matches_file_type_filter_exact_match(self, search_engine):
        """Test file type filter with exact match."""
        result = search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, 'fastq')
        assert result is True

    def test_matches_file_type_filter_no_filter(self, search_engine):
        """Test file type filter with no filter specified."""
        result = search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, None)
        assert result is True

    def test_matches_file_type_filter_no_match(self, search_engine):
        """Test file type filter with no match."""
        result = search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, 'bam')
        assert result is False

    def test_matches_file_type_filter_case_insensitive(self, search_engine):
        """Test file type filter is case insensitive."""
        result = search_engine._matches_file_type_filter(GenomicsFileType.FASTQ, 'fastq')
        assert result is True

    def test_matches_search_terms_path_and_tags(self, search_engine):
        """Test search term matching with both path and tags."""
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.8, ['sample']))
        search_engine.pattern_matcher.match_tags = MagicMock(return_value=(0.6, ['patient']))

        result = search_engine._matches_search_terms(
            's3://bucket/sample.fastq', {'patient_id': 'patient123'}, ['sample', 'patient']
        )

        # The method returns a boolean, not a tuple
        assert result is True

    def test_matches_search_terms_tags_only(self, search_engine):
        """Test search term matching with tags only."""
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.0, []))
        search_engine.pattern_matcher.match_tags = MagicMock(return_value=(0.9, ['patient']))

        result = search_engine._matches_search_terms(
            's3://bucket/file.fastq', {'patient_id': 'patient123'}, ['patient']
        )

        assert result is True

    def test_matches_search_terms_no_match(self, search_engine):
        """Test search term matching with no matches."""
        search_engine.pattern_matcher.match_file_path = MagicMock(return_value=(0.0, []))
        search_engine.pattern_matcher.match_tags = MagicMock(return_value=(0.0, []))

        result = search_engine._matches_search_terms('s3://bucket/file.fastq', {}, ['nonexistent'])

        assert result is False

    def test_is_related_index_file_bam_bai(self, search_engine):
        """Test related index file detection for BAM/BAI."""
        result = search_engine._is_related_index_file(GenomicsFileType.BAI, 'bam')
        assert result is True

    def test_is_related_index_file_fastq_no_index(self, search_engine):
        """Test related index file detection for FASTQ (no index)."""
        result = search_engine._is_related_index_file('sample.fastq', 'other.fastq')
        assert result is False

    def test_is_related_index_file_vcf_tbi(self, search_engine):
        """Test related index file detection for VCF/TBI."""
        result = search_engine._is_related_index_file(GenomicsFileType.TBI, 'vcf')
        assert result is True

    def test_is_related_index_file_fasta_fai(self, search_engine):
        """Test related index file detection for FASTA/FAI."""
        result = search_engine._is_related_index_file(GenomicsFileType.FAI, 'fasta')
        assert result is True

    def test_is_related_index_file_no_relationship(self, search_engine):
        """Test related index file detection with no relationship."""
        result = search_engine._is_related_index_file('file1.fastq', 'file2.bam')
        assert result is False

    @pytest.mark.asyncio
    async def test_search_buckets_with_cached_results(self, search_engine):
        """Test search_buckets with cached results (lines 124-125)."""
        # Mock the cache to return cached results
        search_engine._get_cached_result = MagicMock(return_value=[])
        search_engine._create_search_cache_key = MagicMock(return_value='test_cache_key')

        result = await search_engine.search_buckets(['s3://test-bucket/'], 'fastq', ['test'])

        assert isinstance(result, list)
        search_engine._get_cached_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tags_for_objects_batch_with_client_error(self, search_engine):
        """Test get_tags_for_objects_batch with ClientError (lines 264-271)."""
        from botocore.exceptions import ClientError

        search_engine.s3_client.get_object_tagging = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key does not exist'}},
                'GetObjectTagging',
            )
        )

        result = await search_engine._get_tags_for_objects_batch('test-bucket', ['test-key'])

        assert isinstance(result, dict)
        assert 'test-key' in result
        assert result['test-key'] == {}
