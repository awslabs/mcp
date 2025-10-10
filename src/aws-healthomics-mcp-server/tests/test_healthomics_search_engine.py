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
    def mock_omics_client(self):
        """Create a mock HealthOmics client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def search_engine(self, search_config):
        """Create a HealthOmics search engine instance."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.healthomics_search_engine.get_omics_client'
        ) as mock_get_client:
            mock_get_client.return_value = MagicMock()
            engine = HealthOmicsSearchEngine(search_config)
            return engine

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
                'md5': 'a1b2c3d4e5f6789012345678901234567890abcd',  # pragma: allowlist secret
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
            'md5': 'a1b2c3d4e5f6789012345678901234567890abcd',  # pragma: allowlist secret
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
