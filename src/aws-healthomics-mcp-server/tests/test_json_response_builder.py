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

"""Tests for JSON response builder."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.json_response_builder import JsonResponseBuilder
from datetime import datetime, timezone


class TestJsonResponseBuilder:
    """Test cases for JSON response builder."""

    @pytest.fixture
    def builder(self):
        """Create a test JSON response builder."""
        return JsonResponseBuilder()

    @pytest.fixture
    def sample_genomics_file(self):
        """Create a sample GenomicsFile."""
        return GenomicsFile(
            path='s3://bucket/data/sample.fastq.gz',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1048576,  # 1 MB
            storage_class='STANDARD',
            last_modified=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            tags={'sample_id': 'test_sample', 'project': 'genomics'},
            source_system='s3',
            metadata={'description': 'Test sample file'},
        )

    @pytest.fixture
    def sample_associated_file(self):
        """Create a sample associated GenomicsFile."""
        return GenomicsFile(
            path='s3://bucket/data/sample.bam.bai',
            file_type=GenomicsFileType.BAI,
            size_bytes=1024,  # 1 KB
            storage_class='STANDARD',
            last_modified=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            tags={'sample_id': 'test_sample'},
            source_system='s3',
            metadata={},
        )

    @pytest.fixture
    def sample_result(self, sample_genomics_file, sample_associated_file):
        """Create a sample GenomicsFileResult."""
        return GenomicsFileResult(
            primary_file=sample_genomics_file,
            associated_files=[sample_associated_file],
            relevance_score=0.85,
            match_reasons=['Matched search term in filename', 'Tag match: sample_id'],
        )

    def test_init(self, builder):
        """Test JsonResponseBuilder initialization."""
        assert isinstance(builder, JsonResponseBuilder)

    def test_build_search_response_basic(self, builder, sample_result):
        """Test basic search response building."""
        results = [sample_result]
        response = builder.build_search_response(
            results=results, total_found=1, search_duration_ms=150, storage_systems_searched=['s3']
        )

        # Check basic structure
        assert 'results' in response
        assert 'total_found' in response
        assert 'returned_count' in response
        assert 'search_duration_ms' in response
        assert 'storage_systems_searched' in response
        assert 'performance_metrics' in response
        assert 'metadata' in response

        # Check values
        assert response['total_found'] == 1
        assert response['returned_count'] == 1
        assert response['search_duration_ms'] == 150
        assert response['storage_systems_searched'] == ['s3']
        assert len(response['results']) == 1

    def test_build_search_response_with_optional_params(self, builder, sample_result):
        """Test search response building with optional parameters."""
        results = [sample_result]
        search_stats = {'files_scanned': 100, 'cache_hits': 5}
        pagination_info = {'page': 1, 'per_page': 10, 'has_next': False}

        response = builder.build_search_response(
            results=results,
            total_found=1,
            search_duration_ms=150,
            storage_systems_searched=['s3', 'healthomics'],
            search_statistics=search_stats,
            pagination_info=pagination_info,
        )

        assert 'search_statistics' in response
        assert 'pagination' in response
        assert response['search_statistics'] == search_stats
        assert response['pagination'] == pagination_info

    def test_build_search_response_empty_results(self, builder):
        """Test search response building with empty results."""
        response = builder.build_search_response(
            results=[], total_found=0, search_duration_ms=50, storage_systems_searched=['s3']
        )

        assert response['total_found'] == 0
        assert response['returned_count'] == 0
        assert len(response['results']) == 0
        assert response['metadata']['file_type_distribution'] == {}

    def test_serialize_results(self, builder, sample_result):
        """Test result serialization."""
        results = [sample_result]
        serialized = builder._serialize_results(results)

        assert len(serialized) == 1
        result_dict = serialized[0]

        # Check structure
        assert 'primary_file' in result_dict
        assert 'associated_files' in result_dict
        assert 'file_group' in result_dict
        assert 'relevance_score' in result_dict
        assert 'match_reasons' in result_dict
        assert 'ranking_info' in result_dict

        # Check values
        assert result_dict['relevance_score'] == 0.85
        assert len(result_dict['associated_files']) == 1
        assert result_dict['file_group']['total_files'] == 2
        assert result_dict['file_group']['has_associations'] is True

    def test_serialize_genomics_file(self, builder, sample_genomics_file):
        """Test GenomicsFile serialization."""
        serialized = builder._serialize_genomics_file(sample_genomics_file)

        # Check basic fields
        assert serialized['path'] == 's3://bucket/data/sample.fastq.gz'
        assert serialized['file_type'] == 'fastq'
        assert serialized['size_bytes'] == 1048576
        assert serialized['storage_class'] == 'STANDARD'
        assert serialized['source_system'] == 's3'
        assert serialized['tags'] == {'sample_id': 'test_sample', 'project': 'genomics'}

        # Check computed fields
        assert 'size_human_readable' in serialized
        assert 'file_info' in serialized
        assert serialized['file_info']['extension'] == 'fastq.gz'
        assert serialized['file_info']['basename'] == 'sample.fastq.gz'
        assert serialized['file_info']['is_compressed'] is True
        assert serialized['file_info']['storage_tier'] == 'hot'

    def test_build_performance_metrics(self, builder):
        """Test performance metrics building."""
        metrics = builder._build_performance_metrics(
            search_duration_ms=2000, returned_count=50, total_found=100
        )

        assert metrics['search_duration_seconds'] == 2.0
        assert metrics['results_per_second'] == 25.0
        assert metrics['search_efficiency']['total_found'] == 100
        assert metrics['search_efficiency']['returned_count'] == 50
        assert metrics['search_efficiency']['truncated'] is True
        assert metrics['search_efficiency']['truncation_ratio'] == 0.5

    def test_build_performance_metrics_zero_duration(self, builder):
        """Test performance metrics with zero duration."""
        metrics = builder._build_performance_metrics(
            search_duration_ms=0, returned_count=10, total_found=10
        )

        assert metrics['results_per_second'] == 0
        assert metrics['search_efficiency']['truncated'] is False

    def test_build_response_metadata(self, builder, sample_result):
        """Test response metadata building."""
        results = [sample_result]
        metadata = builder._build_response_metadata(results)

        assert 'file_type_distribution' in metadata
        assert 'source_system_distribution' in metadata
        assert 'association_summary' in metadata

        # Check file type distribution (primary + associated)
        assert metadata['file_type_distribution']['fastq'] == 1
        assert metadata['file_type_distribution']['bai'] == 1

        # Check source system distribution
        assert metadata['source_system_distribution']['s3'] == 1

        # Check association summary
        assert metadata['association_summary']['files_with_associations'] == 1
        assert metadata['association_summary']['total_associated_files'] == 1
        assert metadata['association_summary']['association_ratio'] == 1.0

    def test_build_response_metadata_empty_results(self, builder):
        """Test response metadata with empty results."""
        metadata = builder._build_response_metadata([])

        assert metadata['file_type_distribution'] == {}
        assert metadata['source_system_distribution'] == {}
        assert metadata['association_summary']['files_with_associations'] == 0

    def test_get_association_types(self, builder):
        """Test association type detection."""
        # Test alignment index
        bai_file = GenomicsFile(
            path='test.bai',
            file_type=GenomicsFileType.BAI,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        types = builder._get_association_types([bai_file])
        assert 'alignment_index' in types

        # Test sequence index
        fai_file = GenomicsFile(
            path='test.fai',
            file_type=GenomicsFileType.FAI,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        types = builder._get_association_types([fai_file])
        assert 'sequence_index' in types

        # Test variant index
        tbi_file = GenomicsFile(
            path='test.tbi',
            file_type=GenomicsFileType.TBI,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        types = builder._get_association_types([tbi_file])
        assert 'variant_index' in types

        # Test BWA index collection
        bwa_file = GenomicsFile(
            path='test.bwa_amb',
            file_type=GenomicsFileType.BWA_AMB,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        types = builder._get_association_types([bwa_file])
        assert 'bwa_index_collection' in types

        # Test paired reads
        fastq1 = GenomicsFile(
            path='test_1.fastq',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        fastq2 = GenomicsFile(
            path='test_2.fastq',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1024,
            storage_class='STANDARD',
            last_modified=datetime.now(timezone.utc),
            tags={},
            source_system='s3',
            metadata={},
        )
        types = builder._get_association_types([fastq1, fastq2])
        assert 'paired_reads' in types

        # Test empty list
        types = builder._get_association_types([])
        assert types == []

    def test_build_score_breakdown(self, builder, sample_result):
        """Test score breakdown building."""
        breakdown = builder._build_score_breakdown(sample_result)

        assert breakdown['total_score'] == 0.85
        assert breakdown['has_associations_bonus'] is True
        assert breakdown['association_count'] == 1
        assert breakdown['match_reasons_count'] == 2

    def test_assess_match_quality(self, builder):
        """Test match quality assessment."""
        assert builder._assess_match_quality(0.9) == 'excellent'
        assert builder._assess_match_quality(0.7) == 'good'
        assert builder._assess_match_quality(0.5) == 'fair'
        assert builder._assess_match_quality(0.3) == 'poor'

    def test_format_file_size(self, builder):
        """Test file size formatting."""
        assert builder._format_file_size(0) == '0 B'
        assert builder._format_file_size(512) == '512 B'
        assert builder._format_file_size(1024) == '1.0 KB'
        assert builder._format_file_size(1048576) == '1.0 MB'
        assert builder._format_file_size(1073741824) == '1.0 GB'
        assert builder._format_file_size(1536) == '1.5 KB'

    def test_extract_file_extension(self, builder):
        """Test file extension extraction."""
        assert builder._extract_file_extension('file.txt') == 'txt'
        assert builder._extract_file_extension('file.fastq.gz') == 'fastq.gz'
        assert builder._extract_file_extension('file.vcf.bz2') == 'vcf.bz2'
        assert builder._extract_file_extension('file.gz') == 'gz'
        assert builder._extract_file_extension('file') == ''
        assert builder._extract_file_extension('path/to/file.bam') == 'bam'
        # Test edge case: compressed file with only two parts
        assert builder._extract_file_extension('file.gz') == 'gz'
        assert builder._extract_file_extension('file.bz2') == 'bz2'

    def test_extract_basename(self, builder):
        """Test basename extraction."""
        assert builder._extract_basename('file.txt') == 'file.txt'
        assert builder._extract_basename('path/to/file.txt') == 'file.txt'
        assert builder._extract_basename('s3://bucket/path/file.fastq') == 'file.fastq'

    def test_is_compressed_file(self, builder):
        """Test compressed file detection."""
        assert builder._is_compressed_file('file.gz') is True
        assert builder._is_compressed_file('file.bz2') is True
        assert builder._is_compressed_file('file.zip') is True
        assert builder._is_compressed_file('file.xz') is True
        assert builder._is_compressed_file('file.txt') is False
        assert builder._is_compressed_file('file.fastq') is False

    def test_categorize_storage_tier(self, builder):
        """Test storage tier categorization."""
        assert builder._categorize_storage_tier('STANDARD') == 'hot'
        assert builder._categorize_storage_tier('REDUCED_REDUNDANCY') == 'hot'
        assert builder._categorize_storage_tier('STANDARD_IA') == 'warm'
        assert builder._categorize_storage_tier('ONEZONE_IA') == 'warm'
        assert builder._categorize_storage_tier('GLACIER') == 'cold'
        assert builder._categorize_storage_tier('DEEP_ARCHIVE') == 'cold'
        assert builder._categorize_storage_tier('UNKNOWN_CLASS') == 'unknown'

    def test_complex_workflow(self, builder):
        """Test complex workflow with multiple files and associations."""
        # Create multiple files with different types
        primary_file = GenomicsFile(
            path='s3://bucket/sample.bam',
            file_type=GenomicsFileType.BAM,
            size_bytes=5000000,  # 5 MB
            storage_class='STANDARD_IA',
            last_modified=datetime(2023, 1, 1, tzinfo=timezone.utc),
            tags={'sample': 'test', 'type': 'alignment'},
            source_system='s3',
            metadata={'aligner': 'bwa'},
        )

        index_file = GenomicsFile(
            path='s3://bucket/sample.bam.bai',
            file_type=GenomicsFileType.BAI,
            size_bytes=50000,  # 50 KB
            storage_class='STANDARD_IA',
            last_modified=datetime(2023, 1, 1, tzinfo=timezone.utc),
            tags={'sample': 'test'},
            source_system='s3',
            metadata={},
        )

        result1 = GenomicsFileResult(
            primary_file=primary_file,
            associated_files=[index_file],
            relevance_score=0.92,
            match_reasons=['Exact filename match', 'Tag match: sample'],
        )

        # Create second result without associations
        single_file = GenomicsFile(
            path='s3://bucket/other.fastq.gz',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=2000000,  # 2 MB
            storage_class='GLACIER',
            last_modified=datetime(2023, 1, 2, tzinfo=timezone.utc),
            tags={'sample': 'other'},
            source_system='healthomics',
            metadata={},
        )

        result2 = GenomicsFileResult(
            primary_file=single_file,
            associated_files=[],
            relevance_score=0.65,
            match_reasons=['Partial filename match'],
        )

        results = [result1, result2]

        # Build complete response
        response = builder.build_search_response(
            results=results,
            total_found=2,
            search_duration_ms=500,
            storage_systems_searched=['s3', 'healthomics'],
            search_statistics={'files_scanned': 1000, 'cache_hits': 10},
            pagination_info={'page': 1, 'per_page': 10},
        )

        # Verify complex response structure
        assert len(response['results']) == 2
        assert response['total_found'] == 2
        assert response['returned_count'] == 2

        # Check metadata aggregation
        metadata = response['metadata']
        assert metadata['file_type_distribution']['bam'] == 1
        assert metadata['file_type_distribution']['bai'] == 1
        assert metadata['file_type_distribution']['fastq'] == 1
        assert metadata['source_system_distribution']['s3'] == 1
        assert metadata['source_system_distribution']['healthomics'] == 1
        assert metadata['association_summary']['files_with_associations'] == 1
        assert metadata['association_summary']['association_ratio'] == 0.5

        # Check performance metrics
        perf = response['performance_metrics']
        assert perf['search_duration_seconds'] == 0.5
        assert perf['results_per_second'] == 4.0

        # Check individual result serialization
        result1_dict = response['results'][0]
        assert result1_dict['relevance_score'] == 0.92
        assert result1_dict['file_group']['total_files'] == 2
        assert result1_dict['file_group']['has_associations'] is True
        assert 'alignment_index' in result1_dict['file_group']['association_types']
        assert result1_dict['ranking_info']['match_quality'] == 'excellent'

        result2_dict = response['results'][1]
        assert result2_dict['relevance_score'] == 0.65
        assert result2_dict['file_group']['total_files'] == 1
        assert result2_dict['file_group']['has_associations'] is False
        assert result2_dict['ranking_info']['match_quality'] == 'good'
