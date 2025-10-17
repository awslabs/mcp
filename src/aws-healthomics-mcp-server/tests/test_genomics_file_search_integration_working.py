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

"""Working integration tests for genomics file search functionality."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.genomics_file_search import (
    get_supported_file_types,
    search_genomics_files,
)
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


class TestGenomicsFileSearchIntegration:
    """Integration tests for genomics file search functionality."""

    @pytest.fixture
    def search_tool_wrapper(self):
        """Create a test wrapper for the search_genomics_files function."""
        return MCPToolTestWrapper(search_genomics_files)

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = AsyncMock()
        context.error = AsyncMock()
        return context

    def _create_mock_search_response(self, results_count: int = 2, search_duration_ms: int = 150):
        """Create a mock search response with proper structure."""
        # Create mock results
        results = []
        for i in range(results_count):
            result = {
                'primary_file': {
                    'path': f's3://test-bucket/file{i}.bam',
                    'file_type': 'bam',
                    'size_bytes': 1000000000,
                    'size_human_readable': '1.0 GB',
                    'storage_class': 'STANDARD',
                    'last_modified': '2023-01-15T10:30:00Z',
                    'tags': {'sample_id': f'patient{i}'},
                    'source_system': 's3',
                    'metadata': {},
                    'file_info': {},
                },
                'associated_files': [],
                'file_group': {
                    'total_files': 1,
                    'total_size_bytes': 1000000000,
                    'has_associations': False,
                    'association_types': [],
                },
                'relevance_score': 0.8,
                'match_reasons': ['file_type_match'],
                'ranking_info': {'pattern_match_score': 0.8},
            }
            results.append(result)

        # Create mock response object
        mock_response = MagicMock()
        mock_response.results = results
        mock_response.total_found = results_count
        mock_response.search_duration_ms = search_duration_ms
        mock_response.storage_systems_searched = ['s3']
        mock_response.enhanced_response = None

        return mock_response

    @pytest.mark.asyncio
    async def test_search_genomics_files_success(self, search_tool_wrapper, mock_context):
        """Test successful genomics file search."""
        # Create mock orchestrator that returns our mock response
        mock_orchestrator = MagicMock()
        mock_response = self._create_mock_search_response(results_count=2)
        mock_orchestrator.search = AsyncMock(return_value=mock_response)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            # Execute search using the wrapper
            result = await search_tool_wrapper.call(
                ctx=mock_context,
                file_type='bam',
                search_terms=['patient1'],
                max_results=10,
            )

            # Validate response structure
            assert isinstance(result, dict)
            assert 'results' in result
            assert 'total_found' in result
            assert 'search_duration_ms' in result
            assert 'storage_systems_searched' in result

            # Validate results content
            assert len(result['results']) == 2
            assert result['total_found'] == 2
            assert result['search_duration_ms'] == 150
            assert 's3' in result['storage_systems_searched']

            # Validate individual result structure
            first_result = result['results'][0]
            assert 'primary_file' in first_result
            assert 'associated_files' in first_result
            assert 'relevance_score' in first_result

            # Validate file metadata
            primary_file = first_result['primary_file']
            assert primary_file['file_type'] == 'bam'
            assert primary_file['source_system'] == 's3'

    @pytest.mark.asyncio
    async def test_search_with_default_parameters(self, search_tool_wrapper, mock_context):
        """Test search with default parameters."""
        mock_orchestrator = MagicMock()
        mock_response = self._create_mock_search_response(results_count=1)
        mock_orchestrator.search = AsyncMock(return_value=mock_response)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            # Test with minimal parameters (using defaults)
            result = await search_tool_wrapper.call(ctx=mock_context)

            # Should use default values and return results
            assert isinstance(result, dict)
            assert result['total_found'] == 1

            # Verify the orchestrator was called with correct defaults
            mock_orchestrator.search.assert_called_once()
            call_args = mock_orchestrator.search.call_args[0][0]  # First positional argument

            # Check that default values were used
            assert call_args.max_results == 100  # Default from Field
            assert call_args.include_associated_files is True  # Default from Field
            assert call_args.search_terms == []  # Default from Field

    @pytest.mark.asyncio
    async def test_search_configuration_error(self, search_tool_wrapper, mock_context):
        """Test handling of configuration errors."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            side_effect=ValueError('Configuration error: Missing S3 buckets'),
        ):
            # Should raise an exception and report error to context
            with pytest.raises(Exception) as exc_info:
                await search_tool_wrapper.call(
                    ctx=mock_context,
                    file_type='bam',
                )

            # Verify error was reported to context
            mock_context.error.assert_called()
            assert 'Configuration error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_execution_error(self, search_tool_wrapper, mock_context):
        """Test handling of search execution errors."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.search = AsyncMock(side_effect=Exception('Search failed'))

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            # Should raise an exception and report error to context
            with pytest.raises(Exception) as exc_info:
                await search_tool_wrapper.call(
                    ctx=mock_context,
                    file_type='fastq',
                )

            # Verify error was reported to context
            mock_context.error.assert_called()
            assert 'Search failed' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_file_type(self, search_tool_wrapper, mock_context):
        """Test handling of invalid file type."""
        # Should raise ValueError for invalid file type before reaching orchestrator
        with pytest.raises(ValueError) as exc_info:
            await search_tool_wrapper.call(
                ctx=mock_context,
                file_type='invalid_type',
            )

        assert 'Invalid file_type' in str(exc_info.value)
        # Error should also be reported to context
        mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, search_tool_wrapper, mock_context):
        """Test search with pagination enabled."""
        mock_orchestrator = MagicMock()
        mock_response = self._create_mock_search_response(results_count=5)
        mock_orchestrator.search_paginated = AsyncMock(return_value=mock_response)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            # Test with pagination enabled
            result = await search_tool_wrapper.call(
                ctx=mock_context,
                file_type='vcf',
                enable_storage_pagination=True,
                pagination_buffer_size=1000,
            )

            # Should call search_paginated instead of search
            mock_orchestrator.search_paginated.assert_called_once()
            mock_orchestrator.search.assert_not_called()

            # Validate results
            assert result['total_found'] == 5

    def test_wrapper_functionality(self, search_tool_wrapper):
        """Test that the wrapper correctly handles Field defaults."""
        defaults = search_tool_wrapper.get_defaults()

        # Check that we have the expected defaults from Field annotations
        assert 'search_terms' in defaults
        assert defaults['search_terms'] == []
        assert 'max_results' in defaults
        assert defaults['max_results'] == 100
        assert 'include_associated_files' in defaults
        assert defaults['include_associated_files'] is True
        assert 'enable_storage_pagination' in defaults
        assert defaults['enable_storage_pagination'] is False
        assert 'pagination_buffer_size' in defaults
        assert defaults['pagination_buffer_size'] == 500

    @pytest.mark.asyncio
    async def test_enhanced_response_handling(self, search_tool_wrapper, mock_context):
        """Test handling of enhanced response format."""
        mock_orchestrator = MagicMock()
        mock_response = self._create_mock_search_response(results_count=1)

        # Add enhanced response
        enhanced_response = {
            'results': mock_response.results,
            'total_found': mock_response.total_found,
            'search_duration_ms': mock_response.search_duration_ms,
            'storage_systems_searched': mock_response.storage_systems_searched,
            'performance_metrics': {'results_per_second': 100},
            'metadata': {'file_type_distribution': {'bam': 1}},
        }
        mock_response.enhanced_response = enhanced_response
        mock_orchestrator.search = AsyncMock(return_value=mock_response)

        with patch(
            'awslabs.aws_healthomics_mcp_server.search.genomics_search_orchestrator.GenomicsSearchOrchestrator.from_environment',
            return_value=mock_orchestrator,
        ):
            result = await search_tool_wrapper.call(
                ctx=mock_context,
                file_type='bam',
            )

            # Should use enhanced response when available
            assert 'performance_metrics' in result
            assert 'metadata' in result
            assert result['performance_metrics']['results_per_second'] == 100


class TestGetSupportedFileTypes:
    """Tests for the get_supported_file_types function."""

    @pytest.fixture
    def file_types_tool_wrapper(self):
        """Create a test wrapper for the get_supported_file_types function."""
        return MCPToolTestWrapper(get_supported_file_types)

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = AsyncMock()
        context.error = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_get_supported_file_types_success(self, file_types_tool_wrapper, mock_context):
        """Test successful retrieval of supported file types."""
        result = await file_types_tool_wrapper.call(ctx=mock_context)

        # Validate response structure
        assert isinstance(result, dict)
        assert 'supported_file_types' in result
        assert 'all_valid_types' in result
        assert 'total_types_supported' in result

        # Validate supported file types structure
        file_types = result['supported_file_types']
        expected_categories = [
            'sequence_files',
            'alignment_files',
            'variant_files',
            'annotation_files',
            'index_files',
            'bwa_index_files',
        ]

        for category in expected_categories:
            assert category in file_types
            assert isinstance(file_types[category], dict)
            assert len(file_types[category]) > 0

        # Validate specific file types exist
        assert 'fastq' in file_types['sequence_files']
        assert 'bam' in file_types['alignment_files']
        assert 'vcf' in file_types['variant_files']
        assert 'bed' in file_types['annotation_files']
        assert 'bai' in file_types['index_files']
        assert 'bwa_amb' in file_types['bwa_index_files']

        # Validate all_valid_types
        all_types = result['all_valid_types']
        assert isinstance(all_types, list)
        assert len(all_types) > 0
        assert 'fastq' in all_types
        assert 'bam' in all_types
        assert 'vcf' in all_types

        # Validate total count
        assert result['total_types_supported'] == len(all_types)
        assert result['total_types_supported'] > 15  # Should have many file types

    @pytest.mark.asyncio
    async def test_get_supported_file_types_descriptions(
        self, file_types_tool_wrapper, mock_context
    ):
        """Test that file type descriptions are meaningful."""
        result = await file_types_tool_wrapper.call(ctx=mock_context)

        file_types = result['supported_file_types']

        # Check that descriptions are provided and meaningful
        fastq_desc = file_types['sequence_files']['fastq']
        assert 'FASTQ' in fastq_desc
        assert 'sequence' in fastq_desc.lower()

        bam_desc = file_types['alignment_files']['bam']
        assert 'Binary' in bam_desc or 'BAM' in bam_desc
        assert 'alignment' in bam_desc.lower() or 'Alignment' in bam_desc

        vcf_desc = file_types['variant_files']['vcf']
        assert 'Variant' in vcf_desc
        assert 'Call' in vcf_desc or 'Format' in vcf_desc

    @pytest.mark.asyncio
    async def test_get_supported_file_types_sorted_output(
        self, file_types_tool_wrapper, mock_context
    ):
        """Test that the all_valid_types list is sorted."""
        result = await file_types_tool_wrapper.call(ctx=mock_context)

        all_types = result['all_valid_types']
        assert all_types == sorted(all_types), 'all_valid_types should be sorted alphabetically'

    @pytest.mark.asyncio
    async def test_get_supported_file_types_consistency(
        self, file_types_tool_wrapper, mock_context
    ):
        """Test consistency between supported_file_types and all_valid_types."""
        result = await file_types_tool_wrapper.call(ctx=mock_context)

        # Collect all types from categories
        collected_types = []
        for category in result['supported_file_types'].values():
            collected_types.extend(category.keys())

        # Should match all_valid_types (when sorted)
        assert sorted(collected_types) == result['all_valid_types']
        assert len(collected_types) == result['total_types_supported']

    @pytest.mark.asyncio
    async def test_get_supported_file_types_error_handling(
        self, file_types_tool_wrapper, mock_context
    ):
        """Test error handling in get_supported_file_types."""
        # Mock an exception during execution
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.genomics_file_search.logger'
        ) as mock_logger:
            # Patch something that would cause an exception
            with patch('builtins.sorted', side_effect=Exception('Test error')):
                with pytest.raises(Exception) as exc_info:
                    await file_types_tool_wrapper.call(ctx=mock_context)

                # Verify error was logged and reported to context
                mock_logger.error.assert_called()
                mock_context.error.assert_called()
                assert 'Test error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_supported_file_types_no_context_error(
        self, file_types_tool_wrapper, mock_context
    ):
        """Test that the function doesn't call context.error on success."""
        await file_types_tool_wrapper.call(ctx=mock_context)

        # Should not have called error on successful execution
        mock_context.error.assert_not_called()
