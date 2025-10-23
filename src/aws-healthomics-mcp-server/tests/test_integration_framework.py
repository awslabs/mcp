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

"""Integration test framework validation tests."""

import asyncio
import json
import pytest
from datetime import datetime
from tests.fixtures.genomics_test_data import GenomicsTestDataFixtures
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock


class TestIntegrationFramework:
    """Tests to validate the integration test framework and fixtures."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = AsyncMock()
        context.error = AsyncMock()
        return context

    def test_genomics_test_data_fixtures_structure(self):
        """Test that the genomics test data fixtures are properly structured."""
        # Test S3 dataset
        s3_data = GenomicsTestDataFixtures.get_comprehensive_s3_dataset()
        assert isinstance(s3_data, list)
        assert len(s3_data) > 0

        # Validate S3 object structure
        first_s3_obj = s3_data[0]
        required_s3_fields = ['Key', 'Size', 'LastModified', 'StorageClass', 'TagSet']
        for field in required_s3_fields:
            assert field in first_s3_obj, f'Missing required S3 field: {field}'

        # Validate data types
        assert isinstance(first_s3_obj['Key'], str)
        assert isinstance(first_s3_obj['Size'], int)
        assert isinstance(first_s3_obj['LastModified'], datetime)
        assert isinstance(first_s3_obj['StorageClass'], str)
        assert isinstance(first_s3_obj['TagSet'], list)

        # Test HealthOmics sequence stores
        sequence_stores = GenomicsTestDataFixtures.get_healthomics_sequence_stores()
        assert isinstance(sequence_stores, list)
        assert len(sequence_stores) > 0

        first_store = sequence_stores[0]
        required_store_fields = ['id', 'name', 'description', 'arn', 'creationTime', 'readSets']
        for field in required_store_fields:
            assert field in first_store, f'Missing required store field: {field}'

        # Test HealthOmics reference stores
        reference_stores = GenomicsTestDataFixtures.get_healthomics_reference_stores()
        assert isinstance(reference_stores, list)
        assert len(reference_stores) > 0

    def test_large_dataset_generation(self):
        """Test that large dataset generation works correctly."""
        large_dataset = GenomicsTestDataFixtures.get_large_dataset_scenario(100)
        assert isinstance(large_dataset, list)
        assert len(large_dataset) == 100

        # Validate diversity in generated data
        file_types = set()
        storage_classes = set()
        for obj in large_dataset:
            file_types.add(obj['Key'].split('.')[-1])
            storage_classes.add(obj['StorageClass'])

        # Should have multiple file types and storage classes
        assert len(file_types) > 1
        assert len(storage_classes) > 1

    def test_cross_storage_scenarios(self):
        """Test that cross-storage scenarios are properly structured."""
        scenarios = GenomicsTestDataFixtures.get_cross_storage_scenarios()

        required_scenario_keys = [
            's3_data',
            'healthomics_sequences',
            'healthomics_references',
            'mixed_search_terms',
        ]
        for key in required_scenario_keys:
            assert key in scenarios, f'Missing scenario key: {key}'

        # Validate search terms
        search_terms = scenarios['mixed_search_terms']
        assert isinstance(search_terms, list)
        assert len(search_terms) > 0
        assert all(isinstance(term, str) for term in search_terms)

    def test_pagination_scenarios(self):
        """Test that pagination test scenarios are available."""
        scenarios = GenomicsTestDataFixtures.get_pagination_test_scenarios()

        expected_scenarios = [
            'small_dataset',
            'medium_dataset',
            'large_dataset',
            'very_large_dataset',
        ]
        for scenario in expected_scenarios:
            assert scenario in scenarios, f'Missing pagination scenario: {scenario}'
            assert isinstance(scenarios[scenario], list)

    def test_json_serialization_of_fixtures(self):
        """Test that all fixtures can be JSON serialized (important for mock responses)."""
        # Test S3 data serialization
        s3_data = GenomicsTestDataFixtures.get_comprehensive_s3_dataset()[:5]  # Test subset
        try:
            json_str = json.dumps(s3_data, default=str)
            parsed_back = json.loads(json_str)
            assert len(parsed_back) == 5
        except (TypeError, ValueError) as e:
            pytest.fail(f'S3 data is not JSON serializable: {e}')

        # Test HealthOmics data serialization
        ho_data = GenomicsTestDataFixtures.get_healthomics_sequence_stores()
        try:
            json_str = json.dumps(ho_data, default=str)
            parsed_back = json.loads(json_str)
            assert len(parsed_back) > 0
        except (TypeError, ValueError) as e:
            pytest.fail(f'HealthOmics data is not JSON serializable: {e}')

    def test_file_type_extraction_helper(self):
        """Test the file type extraction helper function."""
        test_cases = [
            ('sample.bam', 'bam'),
            ('reads.fastq.gz', 'fastq'),
            ('variants.vcf.gz', 'vcf'),
            ('reference.fasta', 'fasta'),
            ('index.bai', 'bai'),
            ('unknown.xyz', 'unknown'),
        ]

        for filename, expected_type in test_cases:
            extracted_type = self._extract_file_type(filename)
            assert extracted_type == expected_type, (
                f'Expected {expected_type} for {filename}, got {extracted_type}'
            )

    def test_file_size_formatting_helper(self):
        """Test the file size formatting helper function."""
        test_cases = [
            (1024, '1.0 KB'),
            (1048576, '1.0 MB'),
            (1073741824, '1.0 GB'),
            (1099511627776, '1.0 TB'),
        ]

        for size_bytes, expected_format in test_cases:
            formatted_size = self._format_file_size(size_bytes)
            assert formatted_size == expected_format, (
                f'Expected {expected_format} for {size_bytes}, got {formatted_size}'
            )

    def test_mock_response_creation_helpers(self):
        """Test that mock response creation helpers work correctly."""
        test_data = GenomicsTestDataFixtures.get_comprehensive_s3_dataset()[:3]

        # Test basic mock response creation
        mock_response = self._create_basic_mock_response(test_data)
        assert hasattr(mock_response, 'results')
        assert hasattr(mock_response, 'total_found')
        assert hasattr(mock_response, 'search_duration_ms')
        assert hasattr(mock_response, 'storage_systems_searched')

        # Validate response structure
        assert len(mock_response.results) == 3
        assert mock_response.total_found == 3
        assert isinstance(mock_response.search_duration_ms, int)
        assert isinstance(mock_response.storage_systems_searched, list)

    @pytest.mark.asyncio
    async def test_async_test_framework(self, mock_context):
        """Test that the async test framework is working correctly."""
        # Simple async operation
        await asyncio.sleep(0.01)

        # Test mock context
        assert mock_context is not None
        assert hasattr(mock_context, 'error')

        # Test that we can call async mock methods
        await mock_context.error('test error')
        mock_context.error.assert_called_once_with('test error')

    def test_datetime_handling_in_fixtures(self):
        """Test that datetime objects in fixtures are handled correctly."""
        s3_data = GenomicsTestDataFixtures.get_comprehensive_s3_dataset()

        for obj in s3_data[:5]:  # Test first 5 objects
            last_modified = obj['LastModified']
            assert isinstance(last_modified, datetime)
            assert last_modified.tzinfo is not None  # Should have timezone info

            # Test ISO format conversion
            iso_string = last_modified.isoformat()
            assert isinstance(iso_string, str)
            assert 'T' in iso_string  # ISO format should contain 'T'

    def test_tag_structure_in_fixtures(self):
        """Test that tag structures in fixtures are consistent."""
        s3_data = GenomicsTestDataFixtures.get_comprehensive_s3_dataset()

        for obj in s3_data:
            tag_set = obj.get('TagSet', [])
            assert isinstance(tag_set, list)

            for tag in tag_set:
                assert isinstance(tag, dict)
                assert 'Key' in tag
                assert 'Value' in tag
                assert isinstance(tag['Key'], str)
                assert isinstance(tag['Value'], str)

    # Helper methods for testing
    def _extract_file_type(self, key: str) -> str:
        """Extract file type from S3 key."""
        key_lower = key.lower()
        if key_lower.endswith('.bam'):
            return 'bam'
        elif key_lower.endswith('.bai'):
            return 'bai'
        elif key_lower.endswith('.fastq.gz') or key_lower.endswith('.fastq'):
            return 'fastq'
        elif key_lower.endswith('.vcf.gz') or key_lower.endswith('.vcf'):
            return 'vcf'
        elif key_lower.endswith('.fasta'):
            return 'fasta'
        else:
            return 'unknown'

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        size_float = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024.0:
                return f'{size_float:.1f} {unit}'
            size_float /= 1024.0
        return f'{size_float:.1f} PB'

    def _create_basic_mock_response(self, test_data: List[Dict]):
        """Create a basic mock response for testing."""
        mock_response = MagicMock()
        mock_response.results = []
        mock_response.total_found = len(test_data)
        mock_response.search_duration_ms = 100
        mock_response.storage_systems_searched = ['s3']

        for obj in test_data:
            result = {
                'primary_file': {
                    'path': f's3://genomics-data-bucket/{obj["Key"]}',
                    'file_type': self._extract_file_type(obj['Key']),
                    'size_bytes': obj['Size'],
                    'storage_class': obj['StorageClass'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'tags': {tag['Key']: tag['Value'] for tag in obj.get('TagSet', [])},
                    'source_system': 's3',
                },
                'associated_files': [],
                'relevance_score': 0.8,
                'match_reasons': ['test_match'],
            }
            mock_response.results.append(result)

        return mock_response
