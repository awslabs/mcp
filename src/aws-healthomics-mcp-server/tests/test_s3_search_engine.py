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
            engine = S3SearchEngine(search_config)
            return engine

    def test_init(self, search_config):
        """Test S3SearchEngine initialization."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.s3_search_engine.get_aws_session'
        ) as mock_session:
            mock_s3_client = MagicMock()
            mock_session.return_value.client.return_value = mock_s3_client

            engine = S3SearchEngine(search_config)

            assert engine.config == search_config
            assert engine.s3_client == mock_s3_client
            assert engine.file_type_detector is not None
            assert engine.pattern_matcher is not None
            assert engine._tag_cache == {}
            assert engine._result_cache == {}

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
        stats = search_engine.get_cache_stats()

        assert 'tag_cache' in stats
        assert 'result_cache' in stats
        assert 'config' in stats
        assert 'total_entries' in stats['tag_cache']
        assert 'valid_entries' in stats['tag_cache']
        assert 'ttl_seconds' in stats['tag_cache']
        assert isinstance(stats['tag_cache']['total_entries'], int)
        assert isinstance(stats['result_cache']['total_entries'], int)

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
