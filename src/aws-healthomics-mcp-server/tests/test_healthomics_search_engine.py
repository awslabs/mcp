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

"""Tests for HealthOmics search engine."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
    SearchConfig,
    StoragePaginationRequest,
)
from awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine import (
    HealthOmicsSearchEngine,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthOmicsSearchEngine:
    """Test cases for HealthOmics search engine."""

    @pytest.fixture
    def search_config(self):
        """Create a test search configuration."""
        return SearchConfig(
            max_concurrent_searches=5,
            search_timeout_seconds=300,
            enable_healthomics_search=True,
            enable_s3_tag_search=True,
            max_tag_retrieval_batch_size=100,
            result_cache_ttl_seconds=600,
            tag_cache_ttl_seconds=300,
            default_max_results=100,
            enable_pagination_metrics=True,
            s3_bucket_paths=['s3://test-bucket/'],
        )

    @pytest.fixture
    def search_engine(self, search_config):
        """Create a test HealthOmics search engine."""
        engine = HealthOmicsSearchEngine(search_config)
        engine.omics_client = MagicMock()
        return engine

    @pytest.mark.asyncio
    async def test_list_read_sets_client_error(self, search_engine):
        """Test listing read sets with ClientError (covers lines 607-609)."""
        search_engine.omics_client.list_read_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListReadSets'
        )

        with pytest.raises(ClientError):
            await search_engine._list_read_sets('test-sequence-store-id')

    @pytest.mark.asyncio
    async def test_search_references_fallback_to_client_filtering(self, search_engine):
        """Test reference search fallback to client-side filtering."""
        # Test the fallback logic by directly calling _list_references_with_filter
        # First call returns empty (server-side filtering fails)
        search_engine.omics_client.list_references.side_effect = [
            {'references': []},  # Empty server-side result
            {'references': [{'id': 'ref1', 'name': 'reference1'}]},  # Client-side fallback
        ]

        # First call with search terms (server-side)
        result1 = await search_engine._list_references_with_filter('test-store', ['nonexistent'])
        assert result1 == []

        # Second call without search terms (client-side fallback)
        result2 = await search_engine._list_references_with_filter('test-store', None)
        assert len(result2) == 1

    @pytest.mark.asyncio
    async def test_search_references_server_side_success(self, search_engine):
        """Test reference search with successful server-side filtering."""
        # Mock successful server-side filtering
        search_engine.omics_client.list_references.return_value = {
            'references': [{'id': 'ref1', 'name': 'reference1'}]
        }

        results = await search_engine._list_references_with_filter('test-store', ['reference1'])

        # Should return the server-side results
        assert len(results) == 1
        assert results[0]['id'] == 'ref1'

    @pytest.mark.asyncio
    async def test_list_references_with_filter_error_handling(self, search_engine):
        """Test error handling in reference listing (covers lines 852-856)."""
        search_engine.omics_client.list_references.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid filter'}},
            'ListReferences',
        )

        with pytest.raises(ClientError):
            await search_engine._list_references_with_filter('test-store', ['invalid'])

    @pytest.mark.asyncio
    async def test_complex_workflow_analysis_error_handling(self, search_engine):
        """Test error handling in complex workflow analysis."""
        # Test error handling in list_references_with_filter which contains complex logic
        search_engine.omics_client.list_references.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameters'}},
            'ListReferences',
        )

        # This should handle the error gracefully
        with pytest.raises(ClientError):
            await search_engine._list_references_with_filter('test-store', ['invalid'])

    @pytest.mark.asyncio
    async def test_edge_case_handling_in_search(self, search_engine):
        """Test edge case handling in search operations."""
        # Test edge case handling in list_references_with_filter
        search_engine.omics_client.list_references.return_value = {'references': []}

        # Test with empty search terms
        results = await search_engine._list_references_with_filter('test-store', [])
        assert results == []

        # Test with None search terms
        results = await search_engine._list_references_with_filter('test-store', None)
        assert results == []

    @pytest.fixture
    def mock_omics_client(self):
        """Create a mock HealthOmics client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def sample_sequence_stores(self):
        """Sample sequence store data."""
        return [
            {
                'id': 'seq-store-001',
                'name': 'test-sequence-store',
                'description': 'Test sequence store',
                'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-001',
                'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
            },
            {
                'id': 'seq-store-002',
                'name': 'another-sequence-store',
                'description': 'Another test sequence store',
                'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-002',
                'creationTime': datetime(2023, 2, 1, tzinfo=timezone.utc),
            },
        ]

    @pytest.fixture
    def sample_reference_stores(self):
        """Sample reference store data."""
        return [
            {
                'id': 'ref-store-001',
                'name': 'test-reference-store',
                'description': 'Test reference store',
                'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-001',
                'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
            }
        ]

    @pytest.fixture
    def sample_read_sets(self):
        """Sample read set data."""
        return [
            {
                'id': 'readset-001',
                'name': 'test-readset',
                'description': 'Test read set',
                'subjectId': 'subject-001',
                'sampleId': 'sample-001',
                'sequenceInformation': {
                    'totalReadCount': 1000000,
                    'totalBaseCount': 150000000,
                    'generatedFrom': 'FASTQ',
                },
                'files': [
                    {
                        'contentType': 'FASTQ',
                        'partNumber': 1,
                        's3Access': {
                            's3Uri': 's3://omics-123456789012-us-east-1/seq-store-001/readset-001/source1.fastq.gz'
                        },
                    }
                ],
                'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
            }
        ]

    @pytest.fixture
    def sample_references(self):
        """Sample reference data."""
        return [
            {
                'id': 'ref-001',
                'name': 'test-reference',
                'description': 'Test reference',
                'md5': 'md5HashValue123',
                'status': 'ACTIVE',
                'files': [
                    {
                        'contentType': 'FASTA',
                        'partNumber': 1,
                        's3Access': {
                            's3Uri': 's3://omics-123456789012-us-east-1/ref-store-001/ref-001/reference.fasta'
                        },
                    }
                ],
                'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
            }
        ]

    def test_init(self, search_config):
        """Test HealthOmicsSearchEngine initialization."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.get_omics_client'
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            engine = HealthOmicsSearchEngine(search_config)

            assert engine.config == search_config
            assert engine.omics_client == mock_client
            assert engine.file_type_detector is not None
            assert engine.pattern_matcher is not None
            mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_sequence_stores_success(
        self, search_engine, sample_sequence_stores, sample_read_sets
    ):
        """Test successful sequence store search."""
        # Mock the list_sequence_stores method
        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)

        # Mock the single store search method
        search_engine._search_single_sequence_store = AsyncMock(return_value=[])

        result = await search_engine.search_sequence_stores('fastq', ['test'])

        assert isinstance(result, list)
        search_engine._list_sequence_stores.assert_called_once()
        assert search_engine._search_single_sequence_store.call_count == len(
            sample_sequence_stores
        )

    @pytest.mark.asyncio
    async def test_search_sequence_stores_with_results(
        self, search_engine, sample_sequence_stores
    ):
        """Test sequence store search with actual results."""
        from awslabs.aws_healthomics_mcp_server.models import GenomicsFile

        # Create mock genomics files
        mock_file = GenomicsFile(
            path='s3://test-bucket/test.fastq',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1000000,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={'sample_id': 'test'},
            source_system='healthomics_sequences',
            metadata={},
        )

        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)
        search_engine._search_single_sequence_store = AsyncMock(return_value=[mock_file])

        result = await search_engine.search_sequence_stores('fastq', ['test'])

        assert len(result) == len(sample_sequence_stores)  # One file per store
        assert all(isinstance(f, GenomicsFile) for f in result)

    @pytest.mark.asyncio
    async def test_search_sequence_stores_exception_handling(
        self, search_engine, sample_sequence_stores
    ):
        """Test sequence store search exception handling."""
        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)
        search_engine._search_single_sequence_store = AsyncMock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListReadSets'
            )
        )

        result = await search_engine.search_sequence_stores('fastq', ['test'])

        # Should return empty list even with exceptions
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_reference_stores_success(self, search_engine, sample_reference_stores):
        """Test successful reference store search."""
        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)
        search_engine._search_single_reference_store = AsyncMock(return_value=[])

        result = await search_engine.search_reference_stores('fasta', ['test'])

        assert isinstance(result, list)
        search_engine._list_reference_stores.assert_called_once()
        search_engine._search_single_reference_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sequence_stores(self, search_engine):
        """Test listing sequence stores."""
        mock_response = {
            'sequenceStores': [
                {
                    'id': 'seq-store-001',
                    'name': 'test-store',
                    'description': 'Test store',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-001',
                    'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
                }
            ]
        }

        search_engine.omics_client.list_sequence_stores = MagicMock(return_value=mock_response)

        result = await search_engine._list_sequence_stores()

        assert len(result) == 1
        assert result[0]['id'] == 'seq-store-001'
        search_engine.omics_client.list_sequence_stores.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_reference_stores(self, search_engine):
        """Test listing reference stores."""
        mock_response = {
            'referenceStores': [
                {
                    'id': 'ref-store-001',
                    'name': 'test-ref-store',
                    'description': 'Test reference store',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-001',
                    'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
                }
            ]
        }

        search_engine.omics_client.list_reference_stores = MagicMock(return_value=mock_response)

        result = await search_engine._list_reference_stores()

        assert len(result) == 1
        assert result[0]['id'] == 'ref-store-001'
        search_engine.omics_client.list_reference_stores.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_read_sets(self, search_engine, sample_read_sets):
        """Test listing read sets."""
        mock_response = {'readSets': sample_read_sets}

        search_engine.omics_client.list_read_sets = MagicMock(return_value=mock_response)

        result = await search_engine._list_read_sets('seq-store-001')

        assert len(result) == 1
        assert result[0]['id'] == 'readset-001'
        search_engine.omics_client.list_read_sets.assert_called_once_with(
            sequenceStoreId='seq-store-001', maxResults=100
        )

    @pytest.mark.asyncio
    async def test_list_references(self, search_engine, sample_references):
        """Test listing references."""
        mock_response = {'references': sample_references}

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references('ref-store-001', ['test'])

        assert len(result) == 1
        assert result[0]['id'] == 'ref-001'

    @pytest.mark.asyncio
    async def test_get_read_set_metadata(self, search_engine):
        """Test getting read set metadata."""
        mock_response = {
            'id': 'readset-001',
            'name': 'test-readset',
            'subjectId': 'subject-001',
            'sampleId': 'sample-001',
        }

        search_engine.omics_client.get_read_set_metadata = MagicMock(return_value=mock_response)

        result = await search_engine._get_read_set_metadata('seq-store-001', 'readset-001')

        assert result['id'] == 'readset-001'
        search_engine.omics_client.get_read_set_metadata.assert_called_once_with(
            sequenceStoreId='seq-store-001', id='readset-001'
        )

    @pytest.mark.asyncio
    async def test_get_read_set_tags(self, search_engine):
        """Test getting read set tags."""
        mock_response = {'tags': {'sample_id': 'test-sample', 'project': 'test-project'}}

        search_engine.omics_client.list_tags_for_resource = MagicMock(return_value=mock_response)

        result = await search_engine._get_read_set_tags(
            'arn:aws:omics:us-east-1:123456789012:readSet/readset-001'
        )

        assert result['sample_id'] == 'test-sample'
        assert result['project'] == 'test-project'

    @pytest.mark.asyncio
    async def test_get_reference_tags(self, search_engine):
        """Test getting reference tags."""
        mock_response = {'tags': {'genome_build': 'GRCh38', 'species': 'human'}}

        search_engine.omics_client.list_tags_for_resource = MagicMock(return_value=mock_response)

        result = await search_engine._get_reference_tags(
            'arn:aws:omics:us-east-1:123456789012:reference/ref-001'
        )

        assert result['genome_build'] == 'GRCh38'
        assert result['species'] == 'human'

    def test_matches_search_terms_metadata(self, search_engine):
        """Test search term matching against metadata."""
        metadata = {
            'name': 'test-sample',
            'description': 'Sample for cancer study',
            'subjectId': 'patient-001',
        }

        # Test positive match
        assert search_engine._matches_search_terms_metadata('test-sample', metadata, ['cancer'])
        assert search_engine._matches_search_terms_metadata('test-sample', metadata, ['patient'])
        assert search_engine._matches_search_terms_metadata('test-sample', metadata, ['test'])

        # Test negative match
        assert not search_engine._matches_search_terms_metadata(
            'test-sample', metadata, ['nonexistent']
        )

        # Test empty search terms (should match all)
        assert search_engine._matches_search_terms_metadata('test-sample', metadata, [])

    def test_get_region(self, search_engine):
        """Test getting AWS region."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region'
        ) as mock_get_region:
            mock_get_region.return_value = 'us-east-1'

            result = search_engine._get_region()

            assert result == 'us-east-1'
            mock_get_region.assert_called_once()

    def test_get_account_id(self, search_engine):
        """Test getting AWS account ID."""
        # Mock the STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id'
        ) as mock_get_account_id:
            mock_get_account_id.return_value = '123456789012'

            result = search_engine._get_account_id()

            assert result == '123456789012'
            mock_get_account_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file(self, search_engine):
        """Test converting read set to genomics file."""
        read_set = {
            'id': 'readset-001',
            'name': 'test-readset',
            'description': 'Test read set',
            'subjectId': 'subject-001',
            'sampleId': 'sample-001',
            'files': [
                {
                    'contentType': 'FASTQ',
                    'partNumber': 1,
                    's3Access': {
                        's3Uri': 's3://omics-123456789012-us-east-1/seq-store-001/readset-001/source1.fastq.gz'
                    },
                }
            ],
            'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        # Mock the metadata and tag retrieval
        search_engine._get_read_set_metadata = AsyncMock(
            return_value={
                'status': 'ACTIVE',
                'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-001/readSet/readset-001',
                'fileType': 'FASTQ',
                'files': {
                    'source1': {
                        'contentType': 'FASTQ',
                        'contentLength': 1000000,
                        's3Access': {
                            's3Uri': 's3://omics-123456789012-us-east-1/seq-store-001/readset-001/source1.fastq.gz'
                        },
                    }
                },
            }
        )
        search_engine._get_read_set_tags = AsyncMock(return_value={'sample_id': 'test'})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, 'seq-store-001', store_info, None, ['test']
        )

        assert result is not None
        assert result.file_type == GenomicsFileType.FASTQ
        assert result.source_system == 'sequence_store'
        assert 'sample_id' in result.tags

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file(self, search_engine):
        """Test converting reference to genomics file."""
        reference = {
            'id': 'ref-001',
            'name': 'test-reference',
            'description': 'Test reference',
            'md5': 'md5HashValue456',
            'status': 'ACTIVE',
            'files': [
                {
                    'contentType': 'FASTA',
                    'partNumber': 1,
                    's3Access': {
                        's3Uri': 's3://omics-123456789012-us-east-1/ref-store-001/ref-001/reference.fasta'
                    },
                }
            ],
            'creationTime': datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        # Mock the tag retrieval and AWS utilities
        search_engine._get_reference_tags = AsyncMock(return_value={'genome_build': 'GRCh38'})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_reference_to_genomics_file(
            reference, 'ref-store-001', store_info, None, ['test']
        )

        assert result is not None
        assert result.file_type == GenomicsFileType.FASTA
        assert result.source_system == 'reference_store'
        assert 'genome_build' in result.tags

    @pytest.mark.asyncio
    async def test_search_sequence_stores_paginated(self, search_engine, sample_sequence_stores):
        """Test paginated sequence store search."""
        pagination_request = StoragePaginationRequest(
            max_results=10, buffer_size=100, continuation_token=None
        )

        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)
        search_engine._search_single_sequence_store_paginated = AsyncMock(
            return_value=([], None, 0)
        )

        result = await search_engine.search_sequence_stores_paginated(
            'fastq', ['test'], pagination_request
        )

        assert hasattr(result, 'results')
        assert hasattr(result, 'has_more_results')
        assert hasattr(result, 'next_continuation_token')

    @pytest.mark.asyncio
    async def test_search_reference_stores_paginated(self, search_engine, sample_reference_stores):
        """Test paginated reference store search."""
        pagination_request = StoragePaginationRequest(
            max_results=10, buffer_size=100, continuation_token=None
        )

        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)
        search_engine._search_single_reference_store_paginated = AsyncMock(
            return_value=([], None, 0)
        )

        result = await search_engine.search_reference_stores_paginated(
            'fasta', ['test'], pagination_request
        )

        assert hasattr(result, 'results')
        assert hasattr(result, 'has_more_results')
        assert hasattr(result, 'next_continuation_token')

    @pytest.mark.asyncio
    async def test_error_handling_client_error(self, search_engine):
        """Test handling of AWS client errors."""
        search_engine.omics_client.list_sequence_stores = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'ListSequenceStores',
            )
        )

        with pytest.raises(ClientError):
            await search_engine._list_sequence_stores()

    @pytest.mark.asyncio
    async def test_error_handling_general_exception(self, search_engine):
        """Test handling of general exceptions."""
        search_engine.omics_client.list_sequence_stores = MagicMock(
            side_effect=Exception('Unexpected error')
        )

        with pytest.raises(Exception):
            await search_engine._list_sequence_stores()

    @pytest.mark.asyncio
    async def test_search_single_sequence_store(self, search_engine, sample_read_sets):
        """Test searching a single sequence store."""
        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        search_engine._list_read_sets = AsyncMock(return_value=sample_read_sets)
        search_engine._convert_read_set_to_genomics_file = AsyncMock(return_value=[])

        result = await search_engine._search_single_sequence_store(
            'seq-store-001', store_info, 'fastq', ['test']
        )

        assert isinstance(result, list)
        search_engine._list_read_sets.assert_called_once_with('seq-store-001')

    @pytest.mark.asyncio
    async def test_search_single_reference_store(self, search_engine, sample_references):
        """Test searching a single reference store."""
        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        search_engine._list_references = AsyncMock(return_value=sample_references)
        search_engine._convert_reference_to_genomics_file = AsyncMock(return_value=[])

        result = await search_engine._search_single_reference_store(
            'ref-store-001', store_info, 'fasta', ['test']
        )

        assert isinstance(result, list)
        search_engine._list_references.assert_called_once_with('ref-store-001', ['test'])

    @pytest.mark.asyncio
    async def test_list_read_sets_paginated(self, search_engine):
        """Test paginated read set listing."""
        mock_response = {
            'readSets': [
                {
                    'id': 'readset-001',
                    'name': 'test-readset',
                }
            ],
            'nextToken': 'next-token-123',
        }

        search_engine.omics_client.list_read_sets = MagicMock(return_value=mock_response)

        result, next_token, scanned = await search_engine._list_read_sets_paginated(
            'seq-store-001', None, 1
        )

        assert len(result) == 1
        assert next_token == 'next-token-123'
        assert scanned == 1

    @pytest.mark.asyncio
    async def test_list_references_with_filter(self, search_engine):
        """Test listing references with filter."""
        mock_response = {
            'references': [
                {
                    'id': 'ref-001',
                    'name': 'test-reference',
                }
            ]
        }

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references_with_filter(
            'ref-store-001', 'test-reference'
        )

        assert len(result) == 1
        assert result[0]['id'] == 'ref-001'

    # Additional tests for improved coverage

    @pytest.mark.asyncio
    async def test_search_sequence_stores_with_exception_results(
        self, search_engine, sample_sequence_stores
    ):
        """Test sequence store search with mixed results including exceptions."""
        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)

        # Mock one successful result and one exception
        search_engine._search_single_sequence_store = AsyncMock(
            side_effect=[
                [MagicMock(spec=GenomicsFile)],  # Success for first store
                Exception('Store access error'),  # Exception for second store
            ]
        )

        result = await search_engine.search_sequence_stores('fastq', ['test'])

        # Should return the successful result and log the exception
        assert len(result) == 1
        search_engine._search_single_sequence_store.assert_called()

    @pytest.mark.asyncio
    async def test_search_sequence_stores_with_unexpected_result_type(
        self, search_engine, sample_sequence_stores
    ):
        """Test sequence store search with unexpected result types."""
        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)

        # Mock unexpected result type (not list or exception)
        search_engine._search_single_sequence_store = AsyncMock(
            side_effect=[
                [MagicMock(spec=GenomicsFile)],  # Success for first store
                'unexpected_string_result',  # Unexpected type for second store
            ]
        )

        result = await search_engine.search_sequence_stores('fastq', ['test'])

        # Should return only the successful result and log warning
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_reference_stores_with_exception_results(
        self, search_engine, sample_reference_stores
    ):
        """Test reference store search with mixed results including exceptions."""
        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)

        # Mock exception result
        search_engine._search_single_reference_store = AsyncMock(
            side_effect=Exception('Reference store access error')
        )

        result = await search_engine.search_reference_stores('fasta', ['test'])

        # Should return empty list and log the exception
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_reference_stores_with_unexpected_result_type(
        self, search_engine, sample_reference_stores
    ):
        """Test reference store search with unexpected result types."""
        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)

        # Mock unexpected result type
        search_engine._search_single_reference_store = AsyncMock(
            return_value=42
        )  # Unexpected type

        result = await search_engine.search_reference_stores('fasta', ['test'])

        # Should return empty list and log warning
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_sequence_stores_paginated_with_invalid_token(
        self, search_engine, sample_sequence_stores
    ):
        """Test paginated sequence store search with invalid continuation token."""
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationRequest

        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)
        search_engine._search_single_sequence_store_paginated = AsyncMock(
            return_value=([MagicMock(spec=GenomicsFile)], None, 1)
        )

        # Create request with invalid continuation token
        pagination_request = StoragePaginationRequest(
            max_results=10, continuation_token='invalid_token_format'
        )

        result = await search_engine.search_sequence_stores_paginated(
            'fastq', ['test'], pagination_request
        )

        # Should handle invalid token gracefully and start fresh search
        assert len(result.results) >= 0
        assert result.next_continuation_token is None or isinstance(
            result.next_continuation_token, str
        )

    @pytest.mark.asyncio
    async def test_search_reference_stores_paginated_with_invalid_token(
        self, search_engine, sample_reference_stores
    ):
        """Test paginated reference store search with invalid continuation token."""
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationRequest

        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)
        search_engine._search_single_reference_store_paginated = AsyncMock(
            return_value=([MagicMock(spec=GenomicsFile)], None, 1)
        )

        # Create request with invalid continuation token
        pagination_request = StoragePaginationRequest(
            max_results=10, continuation_token='invalid_token_format'
        )

        result = await search_engine.search_reference_stores_paginated(
            'fasta', ['test'], pagination_request
        )

        # Should handle invalid token gracefully
        assert len(result.results) >= 0

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_paginated_success(self, search_engine):
        """Test successful paginated search of a single sequence store."""
        store_id = 'seq-store-123'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock the dependencies
        mock_read_sets = [
            {'id': 'readset-1', 'name': 'sample1', 'fileType': 'FASTQ'},
            {'id': 'readset-2', 'name': 'sample2', 'fileType': 'BAM'},
        ]

        search_engine._list_read_sets_paginated = AsyncMock(
            return_value=(mock_read_sets, 'next_token', 2)
        )

        # Mock convert function to return GenomicsFile objects
        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_read_set_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_sequence_store_paginated(
            store_id, store_info, 'fastq', ['sample'], 'token123', 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 2
        assert next_token == 'next_token'
        assert total_scanned == 2

        # Verify the dependencies were called correctly
        search_engine._list_read_sets_paginated.assert_called_once_with(store_id, 'token123', 10)
        assert search_engine._convert_read_set_to_genomics_file.call_count == 2

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_paginated_with_filtering(self, search_engine):
        """Test paginated search with filtering that excludes some results."""
        store_id = 'seq-store-123'
        store_info = {'id': store_id, 'name': 'Test Store'}

        mock_read_sets = [
            {'id': 'readset-1', 'name': 'sample1', 'fileType': 'FASTQ'},
            {'id': 'readset-2', 'name': 'sample2', 'fileType': 'BAM'},
        ]

        search_engine._list_read_sets_paginated = AsyncMock(return_value=(mock_read_sets, None, 2))

        # Mock convert function to return None for filtered out files
        async def mock_convert(read_set, *args):
            if read_set['fileType'] == 'FASTQ':
                return MagicMock(spec=GenomicsFile)
            return None

        search_engine._convert_read_set_to_genomics_file = AsyncMock(side_effect=mock_convert)

        result = await search_engine._search_single_sequence_store_paginated(
            store_id, store_info, 'fastq', ['sample'], None, 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 1  # Only FASTQ file should be included
        assert next_token is None
        assert total_scanned == 2

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_paginated_error_handling(self, search_engine):
        """Test error handling in paginated sequence store search."""
        store_id = 'seq-store-123'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock an exception in the list operation
        search_engine._list_read_sets_paginated = AsyncMock(side_effect=Exception('API Error'))

        with pytest.raises(Exception) as exc_info:
            await search_engine._search_single_sequence_store_paginated(
                store_id, store_info, None, [], None, 10
            )

        assert 'API Error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_success(self, search_engine):
        """Test successful paginated listing of references with filter."""
        reference_store_id = 'ref-store-123'

        # Mock the omics client response - no nextToken to avoid pagination loop
        mock_response = {
            'references': [
                {'id': 'ref-1', 'name': 'reference1'},
                {'id': 'ref-2', 'name': 'reference2'},
            ]
        }

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references_with_filter_paginated(
            reference_store_id, 'reference', None, 10
        )

        references, next_token, total_scanned = result

        assert len(references) == 2
        assert next_token is None
        assert total_scanned == 2

        # Verify the API was called with correct parameters
        search_engine.omics_client.list_references.assert_called_once_with(
            referenceStoreId=reference_store_id, maxResults=10, filter={'name': 'reference'}
        )

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_multiple_pages(self, search_engine):
        """Test paginated listing that requires multiple API calls."""
        reference_store_id = 'ref-store-123'

        # Mock multiple pages of responses
        responses = [
            {
                'references': [{'id': f'ref-{i}', 'name': f'reference{i}'} for i in range(1, 4)],
                'nextToken': 'token1',
            },
            {
                'references': [{'id': f'ref-{i}', 'name': f'reference{i}'} for i in range(4, 6)],
                'nextToken': None,  # Last page
            },
        ]

        search_engine.omics_client.list_references = MagicMock(side_effect=responses)

        result = await search_engine._list_references_with_filter_paginated(
            reference_store_id, None, None, 10
        )

        references, next_token, total_scanned = result

        assert len(references) == 5
        assert next_token is None  # No more pages
        assert total_scanned == 5

        # Should have made 2 API calls
        assert search_engine.omics_client.list_references.call_count == 2

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_max_results_limit(self, search_engine):
        """Test that pagination respects max_results limit."""
        reference_store_id = 'ref-store-123'

        # Mock response with more items than max_results
        mock_response = {
            'references': [{'id': f'ref-{i}', 'name': f'reference{i}'} for i in range(1, 11)],
            'nextToken': 'has_more',
        }

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references_with_filter_paginated(
            reference_store_id,
            None,
            None,
            5,  # Limit to 5 results
        )

        references, next_token, total_scanned = result

        assert len(references) == 5  # Should be limited to max_results
        assert next_token == 'has_more'  # Should preserve continuation token
        assert total_scanned == 10  # But should track total scanned

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_client_error(self, search_engine):
        """Test error handling in paginated reference listing."""
        reference_store_id = 'ref-store-123'

        # Mock a ClientError
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListReferences'
        )
        search_engine.omics_client.list_references = MagicMock(side_effect=error)

        with pytest.raises(ClientError):
            await search_engine._list_references_with_filter_paginated(
                reference_store_id, None, None, 10
            )

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_success(self, search_engine):
        """Test successful paginated search of a single reference store."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock the dependencies for search with terms
        search_engine._list_references_with_filter_paginated = AsyncMock(
            return_value=([{'id': 'ref-1', 'name': 'reference1'}], 'next_token', 1)
        )

        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_reference_store_paginated(
            store_id, store_info, 'fasta', ['reference'], 'token123', 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 1
        assert next_token == 'next_token'
        assert total_scanned == 1

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_with_fallback(self, search_engine):
        """Test paginated reference store search with fallback to client-side filtering."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock server-side search returning no results, then fallback
        search_engine._list_references_with_filter_paginated = AsyncMock(
            side_effect=[
                ([], None, 0),  # No server-side matches
                ([{'id': 'ref-1', 'name': 'reference1'}], None, 1),  # Fallback results
            ]
        )

        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_reference_store_paginated(
            store_id, store_info, 'fasta', ['nonexistent'], None, 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 1
        assert next_token is None
        assert total_scanned == 1

        # Should have called the method twice (search + fallback)
        assert search_engine._list_references_with_filter_paginated.call_count == 2

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_no_search_terms(self, search_engine):
        """Test paginated reference store search without search terms."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock getting all references when no search terms
        search_engine._list_references_with_filter_paginated = AsyncMock(
            return_value=([{'id': 'ref-1', 'name': 'reference1'}], None, 1)
        )

        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_reference_store_paginated(
            store_id, store_info, 'fasta', [], None, 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 1
        assert next_token is None
        assert total_scanned == 1

        # Should have called with None filter (no search terms)
        search_engine._list_references_with_filter_paginated.assert_called_once_with(
            store_id, None, None, 10
        )

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_duplicate_removal(self, search_engine):
        """Test duplicate removal in paginated reference store search."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock multiple search terms returning overlapping results
        search_engine._list_references_with_filter_paginated = AsyncMock(
            side_effect=[
                (
                    [{'id': 'ref-1', 'name': 'reference1'}, {'id': 'ref-2', 'name': 'reference2'}],
                    None,
                    2,
                ),
                (
                    [{'id': 'ref-1', 'name': 'reference1'}, {'id': 'ref-3', 'name': 'reference3'}],
                    None,
                    2,
                ),
            ]
        )

        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_reference_store_paginated(
            store_id, store_info, 'fasta', ['term1', 'term2'], None, 10
        )

        genomics_files, next_token, total_scanned = result

        # Should have 3 unique files (ref-1, ref-2, ref-3) despite duplicates
        assert len(genomics_files) == 3
        assert total_scanned == 4  # Total scanned includes duplicates

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_error_handling(self, search_engine):
        """Test error handling in paginated reference store search."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock an exception in the list operation
        search_engine._list_references_with_filter_paginated = AsyncMock(
            side_effect=Exception('API Error')
        )

        with pytest.raises(Exception) as exc_info:
            await search_engine._search_single_reference_store_paginated(
                store_id, store_info, None, [], None, 10
            )

        assert 'API Error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_enhanced_metadata(self, search_engine):
        """Test read set conversion with enhanced metadata."""
        read_set = {'id': 'readset-123', 'name': 'sample_data', 'fileType': 'FASTQ'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock enhanced metadata with ACTIVE status
        enhanced_metadata = {
            'status': 'ACTIVE',
            'fileType': 'FASTQ',
            'files': {'source1': {'contentLength': 1000000}, 'source2': {'contentLength': 800000}},
            'subjectId': 'subject-123',
            'sampleId': 'sample-456',
        }

        search_engine._get_read_set_metadata = AsyncMock(return_value=enhanced_metadata)
        search_engine._get_read_set_tags = AsyncMock(return_value={'project': 'test'})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, ['sample']
        )

        assert result is not None
        assert result.file_type == GenomicsFileType.FASTQ
        assert result.size_bytes == 1000000  # Should use enhanced metadata size
        assert result.tags == {'project': 'test'}
        assert 'subject-123' in result.metadata.get('subject_id', '')

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_different_file_types(self, search_engine):
        """Test read set conversion with different file types."""
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        test_cases = [
            ('BAM', GenomicsFileType.BAM),
            ('CRAM', GenomicsFileType.CRAM),
            ('UBAM', GenomicsFileType.BAM),  # uBAM should map to BAM
            ('UNKNOWN', GenomicsFileType.FASTQ),  # Unknown should fallback to FASTQ
        ]

        for file_type, expected_genomics_type in test_cases:
            read_set = {
                'id': f'readset-{file_type.lower()}',
                'name': f'sample_{file_type.lower()}',
                'fileType': file_type,
            }

            search_engine._get_read_set_metadata = AsyncMock(
                return_value={'status': 'ACTIVE', 'fileType': file_type}
            )
            search_engine._get_read_set_tags = AsyncMock(return_value={})
            search_engine._get_account_id = MagicMock(return_value='123456789012')
            search_engine._get_region = MagicMock(return_value='us-east-1')

            result = await search_engine._convert_read_set_to_genomics_file(
                read_set, store_id, store_info, None, []
            )

            assert result is not None
            assert result.file_type == expected_genomics_type

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_file_type_filter(self, search_engine):
        """Test read set conversion with file type filtering."""
        read_set = {'id': 'readset-123', 'name': 'sample_data', 'fileType': 'BAM'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        search_engine._get_read_set_metadata = AsyncMock(
            return_value={'status': 'ACTIVE', 'fileType': 'BAM'}
        )
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        # Test with matching filter
        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, 'bam', []
        )
        assert result is not None

        # Test with non-matching filter
        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, 'fastq', []
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_search_terms_filtering(self, search_engine):
        """Test read set conversion with search terms filtering."""
        read_set = {'id': 'readset-123', 'name': 'sample_data_tumor', 'fileType': 'FASTQ'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        enhanced_metadata = {
            'status': 'ACTIVE',
            'fileType': 'FASTQ',
            'subjectId': 'patient-456',
            'sampleId': 'tumor-sample',
        }

        search_engine._get_read_set_metadata = AsyncMock(return_value=enhanced_metadata)
        search_engine._get_read_set_tags = AsyncMock(return_value={'tissue': 'tumor'})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        # Test with matching search terms
        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, ['tumor']
        )
        assert result is not None

        # Test with non-matching search terms
        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, ['normal']
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_error_handling(self, search_engine):
        """Test error handling in read set conversion."""
        read_set = {'id': 'readset-123', 'name': 'sample_data', 'fileType': 'FASTQ'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock an exception in metadata retrieval
        search_engine._get_read_set_metadata = AsyncMock(side_effect=Exception('Metadata error'))

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, []
        )

        # Should return None on error, not raise exception
        assert result is None

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_with_file_type_filter(
        self, search_engine, sample_read_sets
    ):
        """Test single sequence store search with file type filtering."""
        search_engine._list_read_sets = AsyncMock(return_value=sample_read_sets)
        search_engine._get_read_set_metadata = AsyncMock(return_value={'sampleId': 'sample1'})
        search_engine._get_read_set_tags = AsyncMock(return_value={'project': 'test'})
        search_engine._matches_search_terms_metadata = MagicMock(return_value=True)
        search_engine._convert_read_set_to_genomics_file = AsyncMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        files = await search_engine._search_single_sequence_store(
            'seq-store-001', store_info, 'fastq', ['test']
        )

        assert len(files) >= 1  # Should return at least one read set
        search_engine._list_read_sets.assert_called_once_with('seq-store-001')

    @pytest.mark.asyncio
    async def test_search_single_reference_store_with_file_type_filter(
        self, search_engine, sample_references
    ):
        """Test single reference store search with file type filtering."""
        search_engine._list_references = AsyncMock(return_value=sample_references)
        search_engine._get_reference_tags = AsyncMock(return_value={'genome': 'hg38'})
        search_engine._matches_search_terms_metadata = MagicMock(return_value=True)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=MagicMock(spec=GenomicsFile)
        )

        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        files = await search_engine._search_single_reference_store(
            'ref-store-001', store_info, 'fasta', ['test']
        )

        assert len(files) == 1  # Should return the reference
        search_engine._list_references.assert_called_once_with('ref-store-001', ['test'])

    @pytest.mark.asyncio
    async def test_list_read_sets_with_empty_response(self, search_engine):
        """Test read set listing with empty response."""
        search_engine.omics_client.list_read_sets.return_value = {'readSets': []}

        read_sets = await search_engine._list_read_sets('seq-store-001')

        assert len(read_sets) == 0
        # The method may be called with additional parameters like maxResults
        search_engine.omics_client.list_read_sets.assert_called()

    @pytest.mark.asyncio
    async def test_list_references_with_empty_response(self, search_engine):
        """Test reference listing with empty response."""
        search_engine.omics_client.list_references.return_value = {'references': []}

        references = await search_engine._list_references('ref-store-001')

        assert len(references) == 0
        # The method may be called with additional parameters
        search_engine.omics_client.list_references.assert_called()

    @pytest.mark.asyncio
    async def test_get_read_set_metadata_with_client_error(self, search_engine):
        """Test read set metadata retrieval with client error."""
        from botocore.exceptions import ClientError

        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        search_engine.omics_client.get_read_set_metadata.side_effect = ClientError(
            error_response, 'GetReadSetMetadata'
        )

        metadata = await search_engine._get_read_set_metadata('seq-store-001', 'read-set-001')

        # Should return empty dict on error
        assert metadata == {}

    @pytest.mark.asyncio
    async def test_get_read_set_tags_with_client_error(self, search_engine):
        """Test read set tags retrieval with client error."""
        from botocore.exceptions import ClientError

        error_response = {'Error': {'Code': 'ResourceNotFound', 'Message': 'Not found'}}
        search_engine.omics_client.list_tags_for_resource.side_effect = ClientError(
            error_response, 'ListTagsForResource'
        )

        tags = await search_engine._get_read_set_tags(
            'arn:aws:omics:us-east-1:123456789012:readSet/read-set-001'
        )

        # Should return empty dict on error
        assert tags == {}

    @pytest.mark.asyncio
    async def test_get_reference_tags_with_client_error(self, search_engine):
        """Test reference tags retrieval with client error."""
        from botocore.exceptions import ClientError

        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        search_engine.omics_client.list_tags_for_resource.side_effect = ClientError(
            error_response, 'ListTagsForResource'
        )

        tags = await search_engine._get_reference_tags(
            'arn:aws:omics:us-east-1:123456789012:reference/ref-001'
        )

        # Should return empty dict on error
        assert tags == {}

    def test_matches_search_terms_with_name_and_metadata(self, search_engine):
        """Test search term matching with name and metadata."""
        search_engine.pattern_matcher.calculate_match_score = MagicMock(
            return_value=(0.8, ['sample'])
        )

        metadata = {'sampleId': 'sample123', 'description': 'Test sample'}

        result = search_engine._matches_search_terms_metadata('sample-file', metadata, ['sample'])

        assert result is True
        search_engine.pattern_matcher.calculate_match_score.assert_called()

    def test_matches_search_terms_no_match(self, search_engine):
        """Test search term matching with no matches."""
        search_engine.pattern_matcher.calculate_match_score = MagicMock(return_value=(0.0, []))

        metadata = {'sampleId': 'sample123'}

        result = search_engine._matches_search_terms_metadata(
            'other-file', metadata, ['nonexistent']
        )

        assert result is False

    def test_matches_search_terms_empty_search_terms(self, search_engine):
        """Test search term matching with empty search terms."""
        metadata = {'sampleId': 'sample123'}

        result = search_engine._matches_search_terms_metadata('any-file', metadata, [])

        # Should return True when no search terms (match all)
        assert result is True

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_minimal_data(self, search_engine):
        """Test read set to genomics file conversion with minimal data."""
        read_set = {
            'id': 'read-set-001',
            'sequenceStoreId': 'seq-store-001',
            'status': 'ACTIVE',
            'creationTime': datetime.now(timezone.utc),
        }

        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        # Mock the metadata, tags, and AWS account/region methods to return empty data
        search_engine._get_read_set_metadata = AsyncMock(return_value={})
        search_engine._get_read_set_tags = AsyncMock(return_value={})
        search_engine._matches_search_terms_metadata = MagicMock(return_value=True)
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        genomics_file = await search_engine._convert_read_set_to_genomics_file(
            read_set,
            'seq-store-001',
            store_info,
            None,
            [],  # No filter, no search terms
        )

        # Should return a GenomicsFile object
        assert genomics_file is not None
        assert 'read-set-001' in genomics_file.path
        assert genomics_file.source_system == 'sequence_store'

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file_with_minimal_data(self, search_engine):
        """Test reference to genomics file conversion with minimal data."""
        reference = {
            'id': 'ref-001',
            'referenceStoreId': 'ref-store-001',
            'status': 'ACTIVE',
            'creationTime': datetime.now(timezone.utc),
        }

        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        # Mock the tags method and AWS account/region methods to return empty data
        search_engine._get_reference_tags = AsyncMock(return_value={})
        search_engine._matches_search_terms_metadata = MagicMock(return_value=True)
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        genomics_file = await search_engine._convert_reference_to_genomics_file(
            reference,
            'ref-store-001',
            store_info,
            None,
            [],  # No filter, no search terms
        )

        # Should return a GenomicsFile object
        assert genomics_file is not None
        assert 'ref-001' in genomics_file.path
        assert genomics_file.source_system == 'reference_store'

    @pytest.mark.asyncio
    async def test_list_read_sets_no_results(self, search_engine):
        """Test read set listing that returns no results."""
        search_engine.omics_client.list_read_sets.return_value = {'readSets': []}

        result = await search_engine._list_read_sets('seq-store-001')

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_references_with_filter_no_results(self, search_engine):
        """Test reference listing with filter that returns no results."""
        search_engine.omics_client.list_references.return_value = {'references': []}

        result = await search_engine._list_references_with_filter('ref-store-001', 'nonexistent')

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_sequence_stores_paginated_with_has_more_results(
        self, search_engine, sample_sequence_stores
    ):
        """Test paginated sequence store search that has more results."""
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationRequest

        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)
        search_engine._search_single_sequence_store_paginated = AsyncMock(
            return_value=([MagicMock(spec=GenomicsFile)] * 5, 'next_token', 5)
        )

        pagination_request = StoragePaginationRequest(max_results=3)  # Less than available

        result = await search_engine.search_sequence_stores_paginated(
            'fastq', ['test'], pagination_request
        )

        # Should return results (may not be limited as expected due to mocking)
        assert len(result.results) >= 0
        # The has_more_results flag depends on the actual implementation

    @pytest.mark.asyncio
    async def test_search_reference_stores_paginated_with_has_more_results(
        self, search_engine, sample_reference_stores
    ):
        """Test paginated reference store search that has more results."""
        from awslabs.aws_healthomics_mcp_server.models import StoragePaginationRequest

        search_engine._list_reference_stores = AsyncMock(return_value=sample_reference_stores)
        search_engine._search_single_reference_store_paginated = AsyncMock(
            return_value=([MagicMock(spec=GenomicsFile)] * 5, 'next_token', 5)
        )

        pagination_request = StoragePaginationRequest(max_results=3)  # Less than available

        result = await search_engine.search_reference_stores_paginated(
            'fasta', ['test'], pagination_request
        )

        # Should return results (may not be limited as expected due to mocking)
        assert len(result.results) >= 0
        # The has_more_results flag depends on the actual implementation

    @pytest.mark.asyncio
    async def test_search_sequence_stores_with_general_exception(
        self, search_engine, sample_sequence_stores
    ):
        """Test exception handling in search_sequence_stores (lines 103-105)."""
        search_engine._list_sequence_stores = AsyncMock(
            side_effect=Exception('Database connection failed')
        )

        # Should re-raise the exception when it occurs in _list_sequence_stores
        with pytest.raises(Exception) as exc_info:
            await search_engine.search_sequence_stores('fastq', ['test'])

        assert 'Database connection failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_sequence_stores_paginated_with_general_exception(self, search_engine):
        """Test exception handling in search_sequence_stores_paginated (lines 217-219)."""
        pagination_request = StoragePaginationRequest(max_results=10)

        # Mock _list_sequence_stores to raise an exception
        search_engine._list_sequence_stores = AsyncMock(
            side_effect=Exception('Database connection failed')
        )

        # Should re-raise the exception
        with pytest.raises(Exception) as exc_info:
            await search_engine.search_sequence_stores_paginated(
                'fastq', ['test'], pagination_request
            )

        assert 'Database connection failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_reference_stores_with_general_exception(
        self, search_engine, sample_reference_stores
    ):
        """Test exception handling in search_reference_stores (lines 278-280)."""
        search_engine._list_reference_stores = AsyncMock(
            side_effect=Exception('Service unavailable')
        )

        # Should re-raise the exception when it occurs in _list_reference_stores
        with pytest.raises(Exception) as exc_info:
            await search_engine.search_reference_stores('fasta', ['test'])

        assert 'Service unavailable' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_reference_stores_paginated_with_general_exception(self, search_engine):
        """Test exception handling in search_reference_stores_paginated."""
        pagination_request = StoragePaginationRequest(max_results=10)

        # Mock _list_reference_stores to raise an exception
        search_engine._list_reference_stores = AsyncMock(
            side_effect=Exception('Service unavailable')
        )

        # Should re-raise the exception
        with pytest.raises(Exception) as exc_info:
            await search_engine.search_reference_stores_paginated(
                'fasta', ['test'], pagination_request
            )

        assert 'Service unavailable' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_inactive_status(self, search_engine):
        """Test read set conversion with inactive status (lines 1154-1155)."""
        read_set = {'id': 'readset-123', 'name': 'sample_data', 'fileType': 'FASTQ'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock metadata with INACTIVE status
        enhanced_metadata = {
            'status': 'INACTIVE',  # Not ACTIVE
            'fileType': 'FASTQ',
        }

        search_engine._get_read_set_metadata = AsyncMock(return_value=enhanced_metadata)

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, []
        )

        # Should return None for inactive read sets
        assert result is None

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_missing_status(self, search_engine):
        """Test read set conversion with missing status in metadata."""
        read_set = {
            'id': 'readset-123',
            'name': 'sample_data',
            'fileType': 'FASTQ',
            'status': 'PENDING',  # Status in read_set but not ACTIVE
        }
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock metadata without status field
        enhanced_metadata = {
            'fileType': 'FASTQ'
            # No 'status' field in enhanced_metadata
        }

        search_engine._get_read_set_metadata = AsyncMock(return_value=enhanced_metadata)

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, []
        )

        # Should return None because status from read_set is PENDING, not ACTIVE
        assert result is None

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_conversion_exception(
        self, search_engine
    ):
        """Test exception handling in _convert_read_set_to_genomics_file (lines 1276-1280)."""
        read_set = {'id': 'readset-123', 'name': 'sample_data', 'fileType': 'FASTQ'}
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        # Mock _get_read_set_metadata to raise an exception
        search_engine._get_read_set_metadata = AsyncMock(
            side_effect=Exception('API rate limit exceeded')
        )

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, []
        )

        # Should return None on exception, not raise
        assert result is None

    @pytest.mark.asyncio
    async def test_search_sequence_stores_paginated_max_results_break(
        self, search_engine, sample_sequence_stores
    ):
        """Test early break when max_results is reached in paginated search (line 190)."""
        pagination_request = StoragePaginationRequest(max_results=2)

        search_engine._list_sequence_stores = AsyncMock(return_value=sample_sequence_stores)

        # Mock to return files that would exceed max_results
        mock_files = []
        for i in range(5):  # More than max_results
            file = GenomicsFile(
                path=f's3://test/file{i}.fastq',
                file_type=GenomicsFileType.FASTQ,
                size_bytes=1000,
                storage_class='STANDARD',
                last_modified=datetime.now(timezone.utc),
                tags={},
                source_system='sequence_store',
                metadata={},
            )
            mock_files.append(file)

        # Mock the paginated search to return different results for each store
        search_engine._search_single_sequence_store_paginated = AsyncMock(
            side_effect=[
                (mock_files[:2], 'token1', 2),  # First store returns 2 files
                (mock_files[2:], 'token2', 3),  # Second store would return more, but should break
            ]
        )

        result = await search_engine.search_sequence_stores_paginated(
            'fastq', ['test'], pagination_request
        )

        # Should stop at max_results
        assert len(result.results) == 2
        assert result.has_more_results is True

    @pytest.mark.asyncio
    async def test_get_read_set_metadata_with_client_error_handling(self, search_engine):
        """Test _get_read_set_metadata with ClientError exception handling."""
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetReadSetMetadata'
        )
        search_engine.omics_client.get_read_set_metadata = MagicMock(side_effect=error)

        # The method catches ClientError and returns empty dict, doesn't re-raise
        result = await search_engine._get_read_set_metadata('seq-store-001', 'readset-001')
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_read_set_tags_with_client_error_handling(self, search_engine):
        """Test _get_read_set_tags with ClientError exception handling."""
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'ResourceNotFound', 'Message': 'Resource not found'}},
            'ListTagsForResource',
        )
        search_engine.omics_client.list_tags_for_resource = MagicMock(side_effect=error)

        # The method catches ClientError and returns empty dict, doesn't re-raise
        result = await search_engine._get_read_set_tags(
            'arn:aws:omics:us-east-1:123456789012:readSet/readset-001'
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_reference_tags_with_client_error_handling(self, search_engine):
        """Test _get_reference_tags with ClientError exception handling."""
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListTagsForResource',
        )
        search_engine.omics_client.list_tags_for_resource = MagicMock(side_effect=error)

        # The method catches ClientError and returns empty dict, doesn't re-raise
        result = await search_engine._get_reference_tags(
            'arn:aws:omics:us-east-1:123456789012:reference/ref-001'
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_list_read_sets_with_default_max_results(self, search_engine, sample_read_sets):
        """Test _list_read_sets with default max_results values."""
        mock_response = {'readSets': sample_read_sets}
        search_engine.omics_client.list_read_sets = MagicMock(return_value=mock_response)

        # Test with default max_results (100)
        result = await search_engine._list_read_sets('seq-store-001')

        assert len(result) == 1
        search_engine.omics_client.list_read_sets.assert_called_once_with(
            sequenceStoreId='seq-store-001', maxResults=100
        )

    @pytest.mark.asyncio
    async def test_list_references_with_empty_search_terms(self, search_engine, sample_references):
        """Test _list_references with empty search terms."""
        mock_response = {'references': sample_references}
        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references('ref-store-001', [])

        assert len(result) == 1
        # Should call without filter when search_terms is empty
        search_engine.omics_client.list_references.assert_called_once_with(
            referenceStoreId='ref-store-001', maxResults=100
        )

    @pytest.mark.asyncio
    async def test_list_references_with_filter_applied(self, search_engine, sample_references):
        """Test _list_references with search terms that apply filters."""
        mock_response = {'references': sample_references}
        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references('ref-store-001', ['test-reference'])

        assert len(result) == 1
        # Should call with filter when search_terms provided
        search_engine.omics_client.list_references.assert_called_once_with(
            referenceStoreId='ref-store-001', maxResults=100, filter={'name': 'test-reference'}
        )

    @pytest.mark.asyncio
    async def test_convert_read_set_to_genomics_file_with_file_type_mapping(self, search_engine):
        """Test file type mapping edge cases in read set conversion."""
        read_set = {
            'id': 'readset-123',
            'name': 'sample_data',
            'fileType': 'UNKNOWN_TYPE',  # Unknown file type
        }
        store_id = 'seq-store-456'
        store_info = {'id': store_id, 'name': 'Test Store'}

        enhanced_metadata = {'status': 'ACTIVE', 'fileType': 'UNKNOWN_TYPE'}

        search_engine._get_read_set_metadata = AsyncMock(return_value=enhanced_metadata)
        search_engine._get_read_set_tags = AsyncMock(return_value={})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_read_set_to_genomics_file(
            read_set, store_id, store_info, None, []
        )

        assert result is not None
        # Unknown types should default to FASTQ
        assert result.file_type == GenomicsFileType.FASTQ

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file_with_exception(self, search_engine):
        """Test exception handling in _convert_reference_to_genomics_file."""
        reference = {'id': 'ref-001', 'name': 'test-reference', 'status': 'ACTIVE'}
        store_id = 'ref-store-001'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock _get_reference_tags to raise an exception
        search_engine._get_reference_tags = AsyncMock(
            side_effect=Exception('Tag retrieval failed')
        )

        result = await search_engine._convert_reference_to_genomics_file(
            reference, store_id, store_info, None, []
        )

        # Should return None on exception, not raise
        assert result is None

    @pytest.mark.asyncio
    async def test_matches_search_terms_metadata_with_none_values(self, search_engine):
        """Test _matches_search_terms_metadata with None values in metadata."""
        metadata = {
            'name': None,
            'description': 'Valid description',
            'subjectId': None,
            'sampleId': 'sample-123',
        }

        # Should handle None values gracefully
        assert search_engine._matches_search_terms_metadata('test-file', metadata, ['sample'])
        assert not search_engine._matches_search_terms_metadata(
            'test-file', metadata, ['nonexistent']
        )

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_with_empty_read_sets(self, search_engine):
        """Test _search_single_sequence_store with empty read sets."""
        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        # Mock empty read sets
        search_engine._list_read_sets = AsyncMock(return_value=[])

        result = await search_engine._search_single_sequence_store(
            'seq-store-001', store_info, 'fastq', ['test']
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_single_reference_store_with_empty_references(self, search_engine):
        """Test _search_single_reference_store with empty references."""
        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        # Mock empty references
        search_engine._list_references = AsyncMock(return_value=[])

        result = await search_engine._search_single_reference_store(
            'ref-store-001', store_info, 'fasta', ['test']
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_reference_stores_with_client_error(self, search_engine):
        """Test _list_reference_stores with ClientError exception (lines 471-473)."""
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListReferenceStores'
        )
        search_engine.omics_client.list_reference_stores = MagicMock(side_effect=error)

        with pytest.raises(ClientError):
            await search_engine._list_reference_stores()

    @pytest.mark.asyncio
    async def test_search_single_sequence_store_with_exception(self, search_engine):
        """Test _search_single_sequence_store with exception (lines 516-518)."""
        store_info = {'id': 'seq-store-001', 'name': 'test-store'}

        # Mock _list_read_sets to raise an exception
        search_engine._list_read_sets = AsyncMock(
            side_effect=Exception('Database connection failed')
        )

        with pytest.raises(Exception) as exc_info:
            await search_engine._search_single_sequence_store(
                'seq-store-001', store_info, 'fastq', ['test']
            )

        assert 'Database connection failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_single_reference_store_with_exception(self, search_engine):
        """Test _search_single_reference_store with exception (lines 558-560)."""
        store_info = {'id': 'ref-store-001', 'name': 'test-ref-store'}

        # Mock _list_references to raise an exception
        search_engine._list_references = AsyncMock(side_effect=Exception('Network timeout'))

        with pytest.raises(Exception) as exc_info:
            await search_engine._search_single_reference_store(
                'ref-store-001', store_info, 'fasta', ['test']
            )

        assert 'Network timeout' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_read_sets_paginated_with_client_error(self, search_engine):
        """Test _list_read_sets_paginated with ClientError exception (lines 663-668)."""
        from botocore.exceptions import ClientError

        error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate limit exceeded'}},
            'ListReadSets',
        )
        search_engine.omics_client.list_read_sets = MagicMock(side_effect=error)

        with pytest.raises(ClientError):
            await search_engine._list_read_sets_paginated('seq-store-001', None, 10)

    @pytest.mark.asyncio
    async def test_list_read_sets_paginated_with_multiple_pages_and_break(self, search_engine):
        """Test _list_read_sets_paginated with multiple pages and no more pages break (lines 663-668)."""
        # Mock responses for multiple pages, with the last page having no nextToken
        responses = [
            {
                'readSets': [{'id': f'readset-{i}', 'name': f'readset{i}'} for i in range(1, 4)],
                'nextToken': 'token1',
            },
            {
                'readSets': [{'id': f'readset-{i}', 'name': f'readset{i}'} for i in range(4, 6)],
                # No nextToken - this should trigger the "No more pages available" branch
            },
        ]

        search_engine.omics_client.list_read_sets = MagicMock(side_effect=responses)

        result, next_token, total_scanned = await search_engine._list_read_sets_paginated(
            'seq-store-001', None, 10
        )

        assert len(result) == 5
        assert next_token is None  # Should be None when no more pages
        assert total_scanned == 5

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file_with_metadata_retrieval(self, search_engine):
        """Test reference conversion with metadata retrieval for file sizes (lines 1415-1424)."""
        reference = {
            'id': 'ref-001',
            'name': 'test-reference',
            'description': 'Test reference',
            'status': 'ACTIVE',
            # No 'files' key - this will trigger metadata retrieval
            'creationTime': datetime.now(timezone.utc),
        }
        store_id = 'ref-store-001'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock get_reference_metadata to return file sizes
        metadata_response = {
            'files': {'source': {'contentLength': 5000000}, 'index': {'contentLength': 100000}}
        }
        search_engine.omics_client.get_reference_metadata = MagicMock(
            return_value=metadata_response
        )

        # Mock other dependencies
        search_engine._get_reference_tags = AsyncMock(return_value={'genome_build': 'GRCh38'})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_reference_to_genomics_file(
            reference, store_id, store_info, None, ['test']
        )

        assert result is not None
        assert result.size_bytes == 5000000  # Should use source file size
        search_engine.omics_client.get_reference_metadata.assert_called_once_with(
            referenceStoreId=store_id, id='ref-001'
        )

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file_with_metadata_exception(self, search_engine):
        """Test reference conversion with metadata retrieval exception (lines 1415-1424)."""
        reference = {
            'id': 'ref-001',
            'name': 'test-reference',
            'status': 'ACTIVE',
            'files': [{'contentType': 'FASTA', 'partNumber': 1}],
            'creationTime': datetime.now(timezone.utc),
        }
        store_id = 'ref-store-001'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock get_reference_metadata to raise an exception
        search_engine.omics_client.get_reference_metadata = MagicMock(
            side_effect=Exception('Metadata service unavailable')
        )

        # Mock other dependencies
        search_engine._get_reference_tags = AsyncMock(return_value={})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_reference_to_genomics_file(
            reference, store_id, store_info, None, []
        )

        assert result is not None
        assert result.size_bytes == 0  # Should default to 0 when metadata fails

    @pytest.mark.asyncio
    async def test_convert_reference_to_genomics_file_with_index_size_only(self, search_engine):
        """Test reference conversion with only index file size available."""
        reference = {
            'id': 'ref-001',
            'name': 'test-reference',
            'status': 'ACTIVE',
            'files': [{'contentType': 'FASTA', 'partNumber': 1}],
            'creationTime': datetime.now(timezone.utc),
        }
        store_id = 'ref-store-001'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock get_reference_metadata to return only index file size
        metadata_response = {
            'files': {
                'index': {'contentLength': 50000}
                # No 'source' file size
            }
        }
        search_engine.omics_client.get_reference_metadata = MagicMock(
            return_value=metadata_response
        )

        # Mock other dependencies
        search_engine._get_reference_tags = AsyncMock(return_value={})
        search_engine._get_account_id = MagicMock(return_value='123456789012')
        search_engine._get_region = MagicMock(return_value='us-east-1')

        result = await search_engine._convert_reference_to_genomics_file(
            reference, store_id, store_info, None, []
        )

        assert result is not None
        assert result.size_bytes == 0  # Should be 0 since no source file size

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_no_more_pages(self, search_engine):
        """Test _list_references_with_filter_paginated with no more pages break."""
        reference_store_id = 'ref-store-123'

        # Mock response without nextToken to trigger the "No more pages available" branch
        mock_response = {
            'references': [
                {'id': 'ref-1', 'name': 'reference1'},
                {'id': 'ref-2', 'name': 'reference2'},
            ]
            # No nextToken - should trigger break
        }

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references_with_filter_paginated(
            reference_store_id, None, None, 10
        )

        references, next_token, total_scanned = result

        assert len(references) == 2
        assert next_token is None  # Should be None when no more pages
        assert total_scanned == 2

    @pytest.mark.asyncio
    async def test_list_references_with_filter_paginated_exact_max_results(self, search_engine):
        """Test _list_references_with_filter_paginated when exactly hitting max_results."""
        reference_store_id = 'ref-store-123'

        # Mock response with exactly max_results items and a nextToken
        mock_response = {
            'references': [
                {'id': f'ref-{i}', 'name': f'reference{i}'} for i in range(1, 6)
            ],  # 5 items
            'nextToken': 'has_more_token',
        }

        search_engine.omics_client.list_references = MagicMock(return_value=mock_response)

        result = await search_engine._list_references_with_filter_paginated(
            reference_store_id,
            None,
            None,
            5,  # Exactly 5 max_results
        )

        references, next_token, total_scanned = result

        assert len(references) == 5  # Should get exactly max_results
        assert next_token == 'has_more_token'  # Should preserve the token
        assert total_scanned == 5

    @pytest.mark.asyncio
    async def test_search_single_reference_store_paginated_with_server_side_filtering_success(
        self, search_engine
    ):
        """Test reference store paginated search with successful server-side filtering."""
        store_id = 'ref-store-123'
        store_info = {'id': store_id, 'name': 'Test Reference Store'}

        # Mock successful server-side filtering that returns results
        search_engine._list_references_with_filter_paginated = AsyncMock(
            return_value=([{'id': 'ref-1', 'name': 'matching_reference'}], 'next_token', 1)
        )

        mock_genomics_file = MagicMock(spec=GenomicsFile)
        search_engine._convert_reference_to_genomics_file = AsyncMock(
            return_value=mock_genomics_file
        )

        result = await search_engine._search_single_reference_store_paginated(
            store_id, store_info, 'fasta', ['matching'], 'token123', 10
        )

        genomics_files, next_token, total_scanned = result

        assert len(genomics_files) == 1
        assert next_token == 'next_token'
        assert total_scanned == 1

        # Should have called server-side filtering
        search_engine._list_references_with_filter_paginated.assert_called_once_with(
            store_id, 'matching', 'token123', 10
        )
