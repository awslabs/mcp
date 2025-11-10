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

"""Unit tests for scoring engine."""

from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.scoring_engine import ScoringEngine
from datetime import datetime
from unittest.mock import patch


class TestScoringEngine:
    """Test cases for ScoringEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scoring_engine = ScoringEngine()
        self.base_datetime = datetime(2023, 1, 1, 12, 0, 0)

    def create_test_file(
        self,
        path: str,
        file_type: GenomicsFileType,
        storage_class: str = 'STANDARD',
        tags: dict | None = None,
        metadata: dict | None = None,
    ) -> GenomicsFile:
        """Helper method to create test GenomicsFile objects."""
        return GenomicsFile(
            path=path,
            file_type=file_type,
            size_bytes=1000,
            storage_class=storage_class,
            last_modified=self.base_datetime,
            tags=tags if tags is not None else {},
            source_system='s3',
            metadata=metadata if metadata is not None else {},
        )

    def test_calculate_score_basic(self):
        """Test basic score calculation."""
        file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)

        score, reasons = self.scoring_engine.calculate_score(
            file=file, search_terms=['test'], file_type_filter='bam', associated_files=[]
        )

        assert 0.0 <= score <= 1.0
        assert len(reasons) > 0
        assert 'Overall relevance score' in reasons[0]

    def test_pattern_match_scoring(self):
        """Test pattern matching component of scoring."""
        file = self.create_test_file('s3://bucket/sample1.bam', GenomicsFileType.BAM)

        # Test exact match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['sample1'])
        assert score > 0.8  # Should get high score for exact match

        # Test substring match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['sample'])
        assert 0.5 < score < 1.0  # Should get medium score for substring match

        # Test no match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['nomatch'])
        assert score == 0.0

    def test_pattern_match_with_tags(self):
        """Test pattern matching against file tags."""
        file = self.create_test_file(
            's3://bucket/file.bam',
            GenomicsFileType.BAM,
            tags={'project': 'genomics', 'sample_type': 'tumor'},
        )

        # Test tag value match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['genomics'])
        assert score > 0.0
        assert any('Tag' in reason for reason in reasons)

        # Test tag key match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['project'])
        assert score > 0.0

    def test_pattern_match_with_metadata(self):
        """Test pattern matching against HealthOmics metadata."""
        file = self.create_test_file(
            'omics://account.storage.region.amazonaws.com/store/readset/source1',
            GenomicsFileType.FASTQ,
            metadata={
                'reference_name': 'GRCh38',
                'sample_id': 'SAMPLE123',
                'subject_id': 'SUBJECT456',
            },
        )

        # Test metadata field match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['GRCh38'])
        assert score > 0.0
        assert any('reference_name' in reason for reason in reasons)

        # Test sample ID match
        score, reasons = self.scoring_engine._calculate_pattern_score(file, ['SAMPLE123'])
        assert score > 0.0

    def test_file_type_relevance_scoring(self):
        """Test file type relevance scoring."""
        file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)

        # Test exact file type match
        score, reasons = self.scoring_engine._calculate_file_type_score(file, 'bam')
        assert score == 1.0
        assert 'Exact file type match' in reasons[0]

        # Test related file type - SAM is related to BAM but gets lower score
        score, reasons = self.scoring_engine._calculate_file_type_score(file, 'sam')
        assert score > 0.0  # Should get some score for related type
        # Note: The actual score depends on the relationship configuration

        # Test unrelated file type
        score, reasons = self.scoring_engine._calculate_file_type_score(file, 'fastq')
        assert score < 0.5
        assert 'Unrelated file type' in reasons[0]

        # Test no file type filter
        score, reasons = self.scoring_engine._calculate_file_type_score(file, None)
        assert score == 0.8
        assert 'No file type filter' in reasons[0]

    def test_file_type_index_relationships(self):
        """Test file type relationships for index files."""
        bai_file = self.create_test_file('s3://bucket/test.bai', GenomicsFileType.BAI)

        # BAI should be relevant when searching for BAM
        score, reasons = self.scoring_engine._calculate_file_type_score(bai_file, 'bam')
        assert score == 0.7
        assert 'Index file type' in reasons[0]  # Adjusted to match actual message

        # Test reverse relationship
        bam_file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)
        score, reasons = self.scoring_engine._calculate_file_type_score(bam_file, 'bai')
        assert score == 0.7
        assert 'Target is index of this file type' in reasons[0]

    def test_association_scoring(self):
        """Test associated files scoring."""
        primary_file = self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM)

        # Test no associated files
        score, reasons = self.scoring_engine._calculate_association_score(primary_file, [])
        assert score == 0.5
        assert 'No associated files' in reasons[0]

        # Test with associated files
        associated_files = [
            self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI)
        ]
        score, reasons = self.scoring_engine._calculate_association_score(
            primary_file, associated_files
        )
        assert score > 0.5
        assert 'Associated files bonus' in reasons[0]

        # Test complete file set bonus
        with patch.object(self.scoring_engine, '_is_complete_file_set', return_value=True):
            score, reasons = self.scoring_engine._calculate_association_score(
                primary_file, associated_files
            )
            assert score > 0.7  # Should get complete set bonus
            assert any('Complete file set bonus' in reason for reason in reasons)

    def test_storage_accessibility_scoring(self):
        """Test storage accessibility scoring."""
        # Test standard storage
        file = self.create_test_file(
            's3://bucket/test.bam', GenomicsFileType.BAM, storage_class='STANDARD'
        )
        score, reasons = self.scoring_engine._calculate_storage_score(file)
        assert score == 1.0
        assert 'Standard storage class' in reasons[0]

        # Test infrequent access
        file = self.create_test_file(
            's3://bucket/test.bam', GenomicsFileType.BAM, storage_class='STANDARD_IA'
        )
        score, reasons = self.scoring_engine._calculate_storage_score(file)
        assert 0.9 <= score < 1.0
        assert 'High accessibility storage' in reasons[0]

        # Test glacier storage
        file = self.create_test_file(
            's3://bucket/test.bam', GenomicsFileType.BAM, storage_class='GLACIER'
        )
        score, reasons = self.scoring_engine._calculate_storage_score(file)
        assert score == 0.7
        assert 'Low accessibility storage' in reasons[0]

        # Test unknown storage class
        file = self.create_test_file(
            's3://bucket/test.bam', GenomicsFileType.BAM, storage_class='UNKNOWN'
        )
        score, reasons = self.scoring_engine._calculate_storage_score(file)
        assert score == 0.8  # Default for unknown classes

    def test_complete_file_set_detection(self):
        """Test complete file set detection."""
        # Test BAM + BAI
        bam_file = self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM)
        bai_file = self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI)
        assert self.scoring_engine._is_complete_file_set(bam_file, [bai_file])

        # Test CRAM + CRAI
        cram_file = self.create_test_file('s3://bucket/sample.cram', GenomicsFileType.CRAM)
        crai_file = self.create_test_file('s3://bucket/sample.cram.crai', GenomicsFileType.CRAI)
        assert self.scoring_engine._is_complete_file_set(cram_file, [crai_file])

        # Test FASTA + FAI + DICT
        fasta_file = self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA)
        fai_file = self.create_test_file('s3://bucket/ref.fasta.fai', GenomicsFileType.FAI)
        dict_file = self.create_test_file('s3://bucket/ref.dict', GenomicsFileType.DICT)
        assert self.scoring_engine._is_complete_file_set(fasta_file, [fai_file, dict_file])

        # Test incomplete set
        assert not self.scoring_engine._is_complete_file_set(
            fasta_file, [fai_file]
        )  # Missing DICT

    def test_fastq_pair_detection(self):
        """Test FASTQ pair detection."""
        # Test R1/R2 pair
        r1_file = self.create_test_file('s3://bucket/sample_R1.fastq.gz', GenomicsFileType.FASTQ)
        r2_file = self.create_test_file('s3://bucket/sample_R2.fastq.gz', GenomicsFileType.FASTQ)
        assert self.scoring_engine._has_fastq_pair(r1_file, [r2_file])

        # Test reverse (R2 as primary)
        assert self.scoring_engine._has_fastq_pair(r2_file, [r1_file])

        # Test numeric naming
        file1 = self.create_test_file('s3://bucket/sample_1.fastq.gz', GenomicsFileType.FASTQ)
        file2 = self.create_test_file('s3://bucket/sample_2.fastq.gz', GenomicsFileType.FASTQ)
        assert self.scoring_engine._has_fastq_pair(file1, [file2])

        # Test dot notation
        r1_dot = self.create_test_file('s3://bucket/sample.R1.fastq.gz', GenomicsFileType.FASTQ)
        r2_dot = self.create_test_file('s3://bucket/sample.R2.fastq.gz', GenomicsFileType.FASTQ)
        assert self.scoring_engine._has_fastq_pair(r1_dot, [r2_dot])

        # Test no pair
        single_file = self.create_test_file('s3://bucket/single.fastq.gz', GenomicsFileType.FASTQ)
        assert not self.scoring_engine._has_fastq_pair(single_file, [])

        # Test non-FASTQ file
        bam_file = self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM)
        assert not self.scoring_engine._has_fastq_pair(bam_file, [r2_file])

    def test_weighted_scoring(self):
        """Test that final scores use correct weights."""
        file = self.create_test_file(
            's3://bucket/test_sample.bam', GenomicsFileType.BAM, tags={'project': 'test'}
        )

        # Mock individual scoring components to test weighting
        with patch.object(
            self.scoring_engine, '_calculate_pattern_score', return_value=(1.0, ['pattern'])
        ):
            with patch.object(
                self.scoring_engine, '_calculate_file_type_score', return_value=(1.0, ['type'])
            ):
                with patch.object(
                    self.scoring_engine,
                    '_calculate_association_score',
                    return_value=(1.0, ['assoc']),
                ):
                    with patch.object(
                        self.scoring_engine,
                        '_calculate_storage_score',
                        return_value=(1.0, ['storage']),
                    ):
                        score, reasons = self.scoring_engine.calculate_score(
                            file=file,
                            search_terms=['test'],
                            file_type_filter='bam',
                            associated_files=[],
                        )

                        # With all components at 1.0, final score should be 1.0 (allowing for floating point precision)
                        assert abs(score - 1.0) < 0.001

        # Test with different component scores
        with patch.object(
            self.scoring_engine, '_calculate_pattern_score', return_value=(0.8, ['pattern'])
        ):
            with patch.object(
                self.scoring_engine, '_calculate_file_type_score', return_value=(0.6, ['type'])
            ):
                with patch.object(
                    self.scoring_engine,
                    '_calculate_association_score',
                    return_value=(0.4, ['assoc']),
                ):
                    with patch.object(
                        self.scoring_engine,
                        '_calculate_storage_score',
                        return_value=(0.2, ['storage']),
                    ):
                        score, reasons = self.scoring_engine.calculate_score(
                            file=file,
                            search_terms=['test'],
                            file_type_filter='bam',
                            associated_files=[],
                        )

                        # Calculate expected weighted score
                        expected = (0.8 * 0.4) + (0.6 * 0.3) + (0.4 * 0.2) + (0.2 * 0.1)
                        assert abs(score - expected) < 0.001

    def test_rank_results(self):
        """Test result ranking functionality."""
        file1 = self.create_test_file('s3://bucket/file1.bam', GenomicsFileType.BAM)
        file2 = self.create_test_file('s3://bucket/file2.bam', GenomicsFileType.BAM)
        file3 = self.create_test_file('s3://bucket/file3.bam', GenomicsFileType.BAM)

        # Create scored results with different scores
        scored_results = [
            (file1, 0.5, ['reason1']),
            (file3, 0.9, ['reason3']),
            (file2, 0.7, ['reason2']),
        ]

        ranked_results = self.scoring_engine.rank_results(scored_results)

        # Should be sorted by score in descending order
        assert len(ranked_results) == 3
        assert ranked_results[0][1] == 0.9  # file3
        assert ranked_results[1][1] == 0.7  # file2
        assert ranked_results[2][1] == 0.5  # file1

    def test_match_metadata_edge_cases(self):
        """Test metadata matching edge cases."""
        # Test empty metadata
        score, reasons = self.scoring_engine._match_metadata({}, ['test'])
        assert score == 0.0
        assert reasons == []

        # Test empty search terms
        metadata = {'name': 'test'}
        score, reasons = self.scoring_engine._match_metadata(metadata, [])
        assert score == 0.0
        assert reasons == []

        # Test non-string metadata values
        metadata = {'count': 123, 'active': True, 'name': 'test'}
        score, reasons = self.scoring_engine._match_metadata(metadata, ['test'])
        assert score > 0.0  # Should match the string value

        # Test None values in metadata
        metadata = {'name': None, 'description': 'test_description'}
        score, reasons = self.scoring_engine._match_metadata(metadata, ['test'])
        assert score > 0.0  # Should match description

    def test_scoring_edge_cases(self):
        """Test edge cases in scoring."""
        file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)

        # Test with empty search terms
        score, reasons = self.scoring_engine.calculate_score(
            file=file, search_terms=[], file_type_filter=None, associated_files=None
        )
        assert 0.0 <= score <= 1.0
        assert len(reasons) > 0

        # Test with None associated files
        score, reasons = self.scoring_engine.calculate_score(
            file=file, search_terms=['test'], file_type_filter='bam', associated_files=None
        )
        assert 0.0 <= score <= 1.0

    def test_file_type_relationships(self):
        """Test file type relationship definitions."""
        # Test that relationships are properly defined
        assert GenomicsFileType.BAM in self.scoring_engine.file_type_relationships
        assert GenomicsFileType.FASTA in self.scoring_engine.file_type_relationships
        assert GenomicsFileType.VCF in self.scoring_engine.file_type_relationships

        # Test BAM relationships
        bam_relations = self.scoring_engine.file_type_relationships[GenomicsFileType.BAM]
        assert GenomicsFileType.BAM in bam_relations['primary']
        assert GenomicsFileType.BAI in bam_relations['indexes']
        assert GenomicsFileType.SAM in bam_relations['related']

        # Test FASTA relationships
        fasta_relations = self.scoring_engine.file_type_relationships[GenomicsFileType.FASTA]
        assert GenomicsFileType.FAI in fasta_relations['indexes']
        assert GenomicsFileType.BWA_AMB in fasta_relations['related']

    def test_storage_multipliers(self):
        """Test storage class multiplier definitions."""
        # Test that all expected storage classes have multipliers
        expected_classes = [
            'STANDARD',
            'STANDARD_IA',
            'ONEZONE_IA',
            'REDUCED_REDUNDANCY',
            'GLACIER',
            'DEEP_ARCHIVE',
            'INTELLIGENT_TIERING',
        ]

        for storage_class in expected_classes:
            assert storage_class in self.scoring_engine.storage_multipliers
            assert 0.0 < self.scoring_engine.storage_multipliers[storage_class] <= 1.0

        # Test that STANDARD has the highest multiplier
        assert self.scoring_engine.storage_multipliers['STANDARD'] == 1.0

        # Test that archive classes have lower multipliers
        assert self.scoring_engine.storage_multipliers['GLACIER'] < 1.0
        assert self.scoring_engine.storage_multipliers['DEEP_ARCHIVE'] < 1.0

    def test_scoring_weights_sum_to_one(self):
        """Test that scoring weights sum to 1.0."""
        total_weight = sum(self.scoring_engine.weights.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_score_bounds(self):
        """Test that scores are always within valid bounds."""
        file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)

        # Test various scenarios to ensure scores stay in bounds
        test_scenarios = [
            (['exact_match'], 'bam', []),
            (['partial'], 'fastq', []),
            ([], None, []),
            (['no_match_at_all'], 'unknown_type', []),
        ]

        for search_terms, file_type_filter, associated_files in test_scenarios:
            score, reasons = self.scoring_engine.calculate_score(
                file=file,
                search_terms=search_terms,
                file_type_filter=file_type_filter,
                associated_files=associated_files,
            )

            assert 0.0 <= score <= 1.0, (
                f'Score {score} out of bounds for scenario {search_terms}, {file_type_filter}'
            )
            assert len(reasons) > 0, (
                f'No reasons provided for scenario {search_terms}, {file_type_filter}'
            )

    def test_comprehensive_scoring_scenario(self):
        """Test a comprehensive scoring scenario with all components."""
        # Create a file that should score well
        file = self.create_test_file(
            's3://bucket/genomics_project/sample123_tumor.bam',
            GenomicsFileType.BAM,
            storage_class='STANDARD',
            tags={'project': 'genomics', 'sample_type': 'tumor', 'quality': 'high'},
            metadata={'sample_id': 'SAMPLE123', 'reference_name': 'GRCh38'},
        )

        # Create associated files
        associated_files = [
            self.create_test_file(
                's3://bucket/genomics_project/sample123_tumor.bam.bai', GenomicsFileType.BAI
            )
        ]

        score, reasons = self.scoring_engine.calculate_score(
            file=file,
            search_terms=['sample123', 'tumor'],
            file_type_filter='bam',
            associated_files=associated_files,
        )

        # Should get a high score due to:
        # - Good pattern matches (path and tags)
        # - Exact file type match
        # - Associated files
        # - Standard storage
        assert score > 0.8
        assert len(reasons) >= 5  # Should have reasons from all components

        # Check that all scoring components are represented
        reason_text = ' '.join(reasons)
        assert 'Overall relevance score' in reason_text
        assert any('match' in reason.lower() for reason in reasons)
        assert any('file type' in reason.lower() for reason in reasons)
        assert any(
            'associated' in reason.lower() or 'bonus' in reason.lower() for reason in reasons
        )
        assert any('storage' in reason.lower() for reason in reasons)

    def test_unknown_file_type_filter(self):
        """Test scoring with unknown file type filter."""
        file = self.create_test_file('s3://bucket/test.bam', GenomicsFileType.BAM)

        # Test with unknown file type filter
        score, reasons = self.scoring_engine._calculate_file_type_score(file, 'unknown_type')
        assert score == 0.5  # Should return neutral score
        assert 'Unknown file type filter' in reasons[0]

    def test_reverse_file_type_relationships(self):
        """Test reverse file type relationships."""
        # Test when target type is an index of the file type
        fasta_file = self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA)

        # FAI is an index of FASTA
        score, reasons = self.scoring_engine._calculate_file_type_score(fasta_file, 'fai')
        assert score == 0.7
        assert 'Target is index of this file type' in reasons[0]

    def test_metadata_matching_with_non_string_values(self):
        """Test metadata matching with non-string values."""
        metadata = {
            'count': 123,
            'active': True,
            'data': None,
            'list_field': ['item1', 'item2'],
            'dict_field': {'nested': 'value'},
        }

        # Should only match string values
        score, reasons = self.scoring_engine._match_metadata(metadata, ['test'])
        assert score == 0.0  # No string matches
        assert reasons == []

    def test_fastq_pair_detection_edge_cases(self):
        """Test FASTQ pair detection edge cases."""
        # Test with non-FASTQ file
        bam_file = self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM)
        fastq_file = self.create_test_file('s3://bucket/sample_R2.fastq', GenomicsFileType.FASTQ)

        # Should return False for non-FASTQ primary file
        assert not self.scoring_engine._has_fastq_pair(bam_file, [fastq_file])

        # Test with FASTQ file that doesn't have pair patterns
        single_fastq = self.create_test_file('s3://bucket/single.fastq', GenomicsFileType.FASTQ)
        other_fastq = self.create_test_file('s3://bucket/other.fastq', GenomicsFileType.FASTQ)

        # Should return False when no R1/R2 patterns match
        assert not self.scoring_engine._has_fastq_pair(single_fastq, [other_fastq])

    def test_complete_file_set_detection_edge_cases(self):
        """Test complete file set detection with edge cases."""
        # Test FASTA with only FAI (incomplete set)
        fasta_file = self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA)
        fai_file = self.create_test_file('s3://bucket/ref.fasta.fai', GenomicsFileType.FAI)

        # Should return False - needs both FAI and DICT for complete set
        assert not self.scoring_engine._is_complete_file_set(fasta_file, [fai_file])

        # Test with unrelated file type
        bed_file = self.create_test_file('s3://bucket/regions.bed', GenomicsFileType.BED)
        other_file = self.create_test_file('s3://bucket/other.txt', GenomicsFileType.BED)

        # Should return False for unrelated file types
        assert not self.scoring_engine._is_complete_file_set(bed_file, [other_file])
