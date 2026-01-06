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

"""Tests for adhoc S3 bucket functionality in genomics file search."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileSearchRequest,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator import (
    GenomicsSearchOrchestrator,
)
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import validate_adhoc_s3_buckets
from datetime import datetime
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch


class TestAdhocS3Buckets:
    """Test class for adhoc S3 bucket functionality."""

    def test_genomics_file_search_request_with_adhoc_buckets_valid(self):
        """Test GenomicsFileSearchRequest with valid adhoc buckets."""
        request = GenomicsFileSearchRequest(
            file_type='fastq',
            search_terms=['sample123'],
            max_results=50,
            adhoc_s3_buckets=['s3://test-bucket/genomics/', 's3://another-bucket/data/'],
        )

        assert request.adhoc_s3_buckets == [
            's3://test-bucket/genomics/',
            's3://another-bucket/data/',
        ]
        assert request.file_type == 'fastq'
        assert request.search_terms == ['sample123']

    def test_genomics_file_search_request_with_adhoc_buckets_none(self):
        """Test GenomicsFileSearchRequest with None adhoc buckets."""
        request = GenomicsFileSearchRequest(file_type='bam', search_terms=['alignment'])

        assert request.adhoc_s3_buckets is None

    def test_genomics_file_search_request_with_adhoc_buckets_empty_list(self):
        """Test GenomicsFileSearchRequest with empty adhoc buckets list."""
        request = GenomicsFileSearchRequest(file_type='vcf', adhoc_s3_buckets=[])

        assert request.adhoc_s3_buckets is None  # Empty list converted to None

    def test_genomics_file_search_request_with_invalid_adhoc_bucket_format(self):
        """Test GenomicsFileSearchRequest with invalid adhoc bucket format."""
        with pytest.raises(ValidationError) as exc_info:
            GenomicsFileSearchRequest(adhoc_s3_buckets=['invalid-bucket-path'])

        assert 'Invalid S3 bucket path' in str(exc_info.value)
        assert "S3 path must start with 's3://'" in str(exc_info.value)

    def test_genomics_file_search_request_with_too_many_adhoc_buckets(self):
        """Test GenomicsFileSearchRequest with too many adhoc buckets."""
        too_many_buckets = [f's3://bucket-{i}/' for i in range(51)]

        with pytest.raises(ValidationError) as exc_info:
            GenomicsFileSearchRequest(adhoc_s3_buckets=too_many_buckets)

        assert 'cannot contain more than 50 bucket paths' in str(exc_info.value)

    def test_genomics_file_search_request_with_non_string_adhoc_buckets(self):
        """Test GenomicsFileSearchRequest with non-string adhoc buckets."""
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally pass invalid type to test validation
            GenomicsFileSearchRequest(
                adhoc_s3_buckets=['s3://valid-bucket/', 123, 's3://another-bucket/']  # type: ignore
            )

        assert 'should be a valid string' in str(exc_info.value)

    def test_genomics_file_search_request_adhoc_buckets_normalization(self):
        """Test that adhoc bucket paths are normalized (trailing slash added)."""
        request = GenomicsFileSearchRequest(
            adhoc_s3_buckets=['s3://bucket-without-slash', 's3://bucket-with-slash/']
        )

        assert request.adhoc_s3_buckets == [
            's3://bucket-without-slash/',
            's3://bucket-with-slash/',
        ]

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_empty_list(self):
        """Test validate_adhoc_s3_buckets with empty list."""
        result = await validate_adhoc_s3_buckets([])
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_none(self):
        """Test validate_adhoc_s3_buckets with None."""
        result = await validate_adhoc_s3_buckets(None)
        assert result == []

    @pytest.mark.asyncio
    async def test_validate_adhoc_s3_buckets_access_denied(self):
        """Test validate_adhoc_s3_buckets with access denied buckets."""
        # This will fail with actual AWS calls, but should return empty list gracefully
        result = await validate_adhoc_s3_buckets(['s3://non-existent-bucket/'])
        assert result == []  # Should return empty list when validation fails

    @pytest.mark.asyncio
    async def test_orchestrator_get_all_s3_bucket_paths_no_adhoc(self):
        """Test _get_all_s3_bucket_paths with no adhoc buckets."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig

        config = SearchConfig(s3_bucket_paths=['s3://configured-bucket/'])
        orchestrator = GenomicsSearchOrchestrator(config)

        request = GenomicsFileSearchRequest(file_type='fastq')

        result = await orchestrator._get_all_s3_bucket_paths(request)
        assert result == ['s3://configured-bucket/']

    @pytest.mark.asyncio
    async def test_orchestrator_get_all_s3_bucket_paths_with_adhoc(self):
        """Test _get_all_s3_bucket_paths with adhoc buckets."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig

        config = SearchConfig(s3_bucket_paths=['s3://configured-bucket/'])
        orchestrator = GenomicsSearchOrchestrator(config)

        request = GenomicsFileSearchRequest(
            file_type='fastq', adhoc_s3_buckets=['s3://adhoc-bucket/']
        )

        # Mock the validation to return the adhoc bucket as valid
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.validate_adhoc_s3_buckets'
        ) as mock_validate:
            mock_validate.return_value = ['s3://adhoc-bucket/']

            result = await orchestrator._get_all_s3_bucket_paths(request)
            assert result == ['s3://configured-bucket/', 's3://adhoc-bucket/']

    @pytest.mark.asyncio
    async def test_orchestrator_get_all_s3_bucket_paths_validation_failure(self):
        """Test _get_all_s3_bucket_paths when adhoc bucket validation fails."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig

        config = SearchConfig(s3_bucket_paths=['s3://configured-bucket/'])
        orchestrator = GenomicsSearchOrchestrator(config)

        request = GenomicsFileSearchRequest(
            file_type='fastq', adhoc_s3_buckets=['s3://invalid-bucket/']
        )

        # Mock the validation to return empty list (validation failed)
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.validate_adhoc_s3_buckets'
        ) as mock_validate:
            mock_validate.return_value = []

            result = await orchestrator._get_all_s3_bucket_paths(request)
            assert result == ['s3://configured-bucket/']  # Only configured buckets

    @pytest.mark.asyncio
    async def test_orchestrator_get_all_s3_bucket_paths_validation_exception(self):
        """Test _get_all_s3_bucket_paths when adhoc bucket validation raises exception."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig

        config = SearchConfig(s3_bucket_paths=['s3://configured-bucket/'])
        orchestrator = GenomicsSearchOrchestrator(config)

        request = GenomicsFileSearchRequest(
            file_type='fastq', adhoc_s3_buckets=['s3://problematic-bucket/']
        )

        # Mock the validation to raise an exception
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.validation_utils.validate_adhoc_s3_buckets'
        ) as mock_validate:
            mock_validate.side_effect = Exception('Validation error')

            result = await orchestrator._get_all_s3_bucket_paths(request)
            assert result == ['s3://configured-bucket/']  # Should continue with configured buckets

    @pytest.mark.asyncio
    async def test_orchestrator_execute_parallel_searches_with_adhoc_buckets(self):
        """Test _execute_parallel_searches includes adhoc buckets in search."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig
        from awslabs.aws_healthomics_mcp_server.search.s3_search_engine import S3SearchEngine

        config = SearchConfig(
            s3_bucket_paths=['s3://configured-bucket/'], enable_healthomics_search=False
        )

        # Create a mock S3 engine
        mock_s3_engine = AsyncMock(spec=S3SearchEngine)
        orchestrator = GenomicsSearchOrchestrator(config, s3_engine=mock_s3_engine)

        request = GenomicsFileSearchRequest(
            file_type='fastq', search_terms=['sample'], adhoc_s3_buckets=['s3://adhoc-bucket/']
        )

        sample_files = [
            GenomicsFile(
                path='s3://adhoc-bucket/sample.fastq',
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
            orchestrator, '_search_s3_with_timeout_for_buckets', new_callable=AsyncMock
        ) as mock_s3:
            mock_s3.return_value = sample_files

            # Mock adhoc bucket validation
            with patch(
                'awslabs.aws_healthomics_mcp_server.utils.validation_utils.validate_adhoc_s3_buckets'
            ) as mock_validate:
                mock_validate.return_value = ['s3://adhoc-bucket/']

                result = await orchestrator._execute_parallel_searches(request)

                assert result == sample_files
                # Verify the method was called with both configured and adhoc buckets
                expected_buckets = ['s3://configured-bucket/', 's3://adhoc-bucket/']
                mock_s3.assert_called_once_with(request, expected_buckets)

    @pytest.mark.asyncio
    async def test_orchestrator_cache_key_includes_adhoc_buckets(self):
        """Test that pagination cache key includes adhoc buckets."""
        from awslabs.aws_healthomics_mcp_server.models import SearchConfig

        config = SearchConfig(s3_bucket_paths=['s3://configured-bucket/'])
        orchestrator = GenomicsSearchOrchestrator(config)

        request1 = GenomicsFileSearchRequest(file_type='fastq', search_terms=['sample'])
        request2 = GenomicsFileSearchRequest(
            file_type='fastq', search_terms=['sample'], adhoc_s3_buckets=['s3://adhoc-bucket/']
        )

        key1 = orchestrator._create_pagination_cache_key(request1, 1)
        key2 = orchestrator._create_pagination_cache_key(request2, 1)

        # Keys should be different because adhoc buckets are different
        assert key1 != key2

    def test_genomics_file_search_request_backward_compatibility(self):
        """Test that existing code without adhoc_s3_buckets still works."""
        # This should work exactly as before
        request = GenomicsFileSearchRequest(
            file_type='bam',
            search_terms=['alignment', 'sorted'],
            max_results=100,
            include_associated_files=True,
        )

        assert request.file_type == 'bam'
        assert request.search_terms == ['alignment', 'sorted']
        assert request.max_results == 100
        assert request.include_associated_files is True
        assert request.adhoc_s3_buckets is None  # Default value
