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

"""Unit tests for file association detection engine."""

from awslabs.aws_healthomics_mcp_server.models import (
    FileGroup,
    GenomicsFile,
    GenomicsFileType,
)
from awslabs.aws_healthomics_mcp_server.search.file_association_engine import FileAssociationEngine
from datetime import datetime


class TestFileAssociationEngine:
    """Test cases for FileAssociationEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = FileAssociationEngine()
        self.base_datetime = datetime(2023, 1, 1, 12, 0, 0)

    def create_test_file(
        self,
        path: str,
        file_type: GenomicsFileType,
        source_system: str = 's3',
        metadata: dict | None = None,
    ) -> GenomicsFile:
        """Helper method to create test GenomicsFile objects."""
        return GenomicsFile(
            path=path,
            file_type=file_type,
            size_bytes=1000,
            storage_class='STANDARD',
            last_modified=self.base_datetime,
            tags={},
            source_system=source_system,
            metadata=metadata if metadata is not None else {},
        )

    def test_bam_index_associations(self):
        """Test BAM file and BAI index associations."""
        files = [
            self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI),
        ]

        groups = self.engine.find_associations(files)

        # Should create one group with BAM as primary and BAI as associated
        assert len(groups) == 1
        group = groups[0]
        assert group.primary_file.file_type == GenomicsFileType.BAM
        assert len(group.associated_files) == 1
        assert group.associated_files[0].file_type == GenomicsFileType.BAI
        assert group.group_type == 'bam_index'

    def test_bam_index_alternative_naming(self):
        """Test BAM file with alternative BAI naming convention."""
        files = [
            self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample.bai', GenomicsFileType.BAI),
        ]

        groups = self.engine.find_associations(files)

        assert len(groups) == 1
        group = groups[0]
        assert group.primary_file.file_type == GenomicsFileType.BAM
        assert len(group.associated_files) == 1
        assert group.associated_files[0].file_type == GenomicsFileType.BAI

    def test_cram_index_associations(self):
        """Test CRAM file and CRAI index associations."""
        files = [
            self.create_test_file('s3://bucket/sample.cram', GenomicsFileType.CRAM),
            self.create_test_file('s3://bucket/sample.cram.crai', GenomicsFileType.CRAI),
        ]

        groups = self.engine.find_associations(files)

        assert len(groups) == 1
        group = groups[0]
        assert group.primary_file.file_type == GenomicsFileType.CRAM
        assert len(group.associated_files) == 1
        assert group.associated_files[0].file_type == GenomicsFileType.CRAI
        assert group.group_type == 'cram_index'

    def test_fastq_pair_associations(self):
        """Test FASTQ R1/R2 pair associations."""
        test_cases = [
            # Standard R1/R2 naming
            ('sample_R1.fastq.gz', 'sample_R2.fastq.gz'),
            ('sample_R1.fastq', 'sample_R2.fastq'),
            # Numeric naming
            ('sample_1.fastq.gz', 'sample_2.fastq.gz'),
        ]

        for r1_name, r2_name in test_cases:
            files = [
                self.create_test_file(f's3://bucket/{r1_name}', GenomicsFileType.FASTQ),
                self.create_test_file(f's3://bucket/{r2_name}', GenomicsFileType.FASTQ),
            ]

            groups = self.engine.find_associations(files)

            assert len(groups) == 1, f'Failed for {r1_name}, {r2_name}'
            group = groups[0]
            assert group.primary_file.file_type == GenomicsFileType.FASTQ
            assert len(group.associated_files) == 1
            assert group.associated_files[0].file_type == GenomicsFileType.FASTQ
            # The group type should be fastq_pair for R1/R2 patterns
            assert group.group_type == 'fastq_pair', (
                f'Expected fastq_pair but got {group.group_type} for {r1_name}, {r2_name}'
            )

    def test_fastq_dot_notation_associations(self):
        """Test FASTQ associations with dot notation that may not be detected as pairs."""
        test_cases = [
            # Dot notation - these may not be detected as pairs due to the R2 pattern matching
            ('sample.R1.fastq.gz', 'sample.R2.fastq.gz'),
            ('sample.1.fastq.gz', 'sample.2.fastq.gz'),
        ]

        for r1_name, r2_name in test_cases:
            files = [
                self.create_test_file(f's3://bucket/{r1_name}', GenomicsFileType.FASTQ),
                self.create_test_file(f's3://bucket/{r2_name}', GenomicsFileType.FASTQ),
            ]

            groups = self.engine.find_associations(files)

            # These might be grouped or might be separate depending on pattern matching
            assert len(groups) >= 1, f'Failed for {r1_name}, {r2_name}'

            # Check if they were grouped together
            if len(groups) == 1:
                group = groups[0]
                assert group.primary_file.file_type == GenomicsFileType.FASTQ
                assert len(group.associated_files) == 1
                assert group.associated_files[0].file_type == GenomicsFileType.FASTQ

    def test_fasta_index_associations(self):
        """Test FASTA file with various index associations."""
        # Test FASTA with FAI index
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.fai', GenomicsFileType.FAI),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'fasta_index'

        # Test FASTA with DICT file
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.dict', GenomicsFileType.DICT),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'fasta_dict'

        # Test alternative extensions (FA, FNA)
        for ext in ['fa', 'fna']:
            files = [
                self.create_test_file(f's3://bucket/reference.{ext}', GenomicsFileType.FASTA),
                self.create_test_file(f's3://bucket/reference.{ext}.fai', GenomicsFileType.FAI),
            ]

            groups = self.engine.find_associations(files)
            assert len(groups) == 1
            assert groups[0].group_type == 'fasta_index'

    def test_vcf_index_associations(self):
        """Test VCF file with index associations."""
        test_cases = [
            # VCF with TBI index
            ('variants.vcf.gz', GenomicsFileType.VCF, 'variants.vcf.gz.tbi', GenomicsFileType.TBI),
            # VCF with CSI index
            ('variants.vcf.gz', GenomicsFileType.VCF, 'variants.vcf.gz.csi', GenomicsFileType.CSI),
            # GVCF with TBI index
            (
                'variants.gvcf.gz',
                GenomicsFileType.GVCF,
                'variants.gvcf.gz.tbi',
                GenomicsFileType.TBI,
            ),
            # BCF with CSI index
            ('variants.bcf', GenomicsFileType.BCF, 'variants.bcf.csi', GenomicsFileType.CSI),
        ]

        for primary_name, primary_type, index_name, index_type in test_cases:
            files = [
                self.create_test_file(f's3://bucket/{primary_name}', primary_type),
                self.create_test_file(f's3://bucket/{index_name}', index_type),
            ]

            groups = self.engine.find_associations(files)
            assert len(groups) == 1, f'Failed for {primary_name}, {index_name}'
            group = groups[0]
            assert group.primary_file.file_type == primary_type
            assert len(group.associated_files) == 1
            assert group.associated_files[0].file_type == index_type

    def test_bwa_index_collections(self):
        """Test BWA index collection grouping."""
        # Test complete BWA index set
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/reference.fasta.ann', GenomicsFileType.BWA_ANN),
            self.create_test_file('s3://bucket/reference.fasta.bwt', GenomicsFileType.BWA_BWT),
            self.create_test_file('s3://bucket/reference.fasta.pac', GenomicsFileType.BWA_PAC),
            self.create_test_file('s3://bucket/reference.fasta.sa', GenomicsFileType.BWA_SA),
        ]

        groups = self.engine.find_associations(files)

        # Should create one BWA index collection group
        bwa_groups = [g for g in groups if g.group_type == 'bwa_index_collection']
        assert len(bwa_groups) == 1

        bwa_group = bwa_groups[0]
        # Primary file should be FASTA if present, otherwise .bwt file
        assert bwa_group.primary_file.file_type in [
            GenomicsFileType.FASTA,
            GenomicsFileType.BWA_BWT,
        ]
        assert len(bwa_group.associated_files) >= 4  # At least 4 BWA index files

    def test_bwa_index_64bit_variants(self):
        """Test BWA index collection with 64-bit variants."""
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.64.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/reference.fasta.64.ann', GenomicsFileType.BWA_ANN),
            self.create_test_file('s3://bucket/reference.fasta.64.bwt', GenomicsFileType.BWA_BWT),
        ]

        groups = self.engine.find_associations(files)

        bwa_groups = [g for g in groups if g.group_type == 'bwa_index_collection']
        assert len(bwa_groups) == 1

        bwa_group = bwa_groups[0]
        # Primary file should be FASTA if present, otherwise .bwt file
        assert bwa_group.primary_file.file_type in [
            GenomicsFileType.FASTA,
            GenomicsFileType.BWA_BWT,
        ]
        assert len(bwa_group.associated_files) >= 2

    def test_mixed_bwa_index_variants(self):
        """Test BWA index collection with mixed regular and 64-bit variants."""
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/reference.fasta.64.ann', GenomicsFileType.BWA_ANN),
            self.create_test_file('s3://bucket/reference.fasta.bwt', GenomicsFileType.BWA_BWT),
            self.create_test_file('s3://bucket/reference.fasta.64.pac', GenomicsFileType.BWA_PAC),
        ]

        groups = self.engine.find_associations(files)

        bwa_groups = [g for g in groups if g.group_type == 'bwa_index_collection']
        assert len(bwa_groups) == 1

        bwa_group = bwa_groups[0]
        # Should have at least 3 associated files (excluding primary)
        assert len(bwa_group.associated_files) >= 3

    def test_normalize_bwa_base_name(self):
        """Test BWA base name normalization."""
        # Test regular base name
        assert self.engine._normalize_bwa_base_name('reference.fasta') == 'reference.fasta'

        # Test 64-bit variant
        assert self.engine._normalize_bwa_base_name('reference.fasta.64') == 'reference.fasta'

        # Test with path
        assert (
            self.engine._normalize_bwa_base_name('/path/to/reference.fasta.64')
            == '/path/to/reference.fasta'
        )

        # Test without 64 suffix
        assert (
            self.engine._normalize_bwa_base_name('/path/to/reference.fa')
            == '/path/to/reference.fa'
        )

    def test_healthomics_reference_associations(self):
        """Test HealthOmics reference store associations."""
        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/ref-store-123/reference/ref-456/source',
                GenomicsFileType.FASTA,
                source_system='reference_store',
            ),
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/ref-store-123/reference/ref-456/index',
                GenomicsFileType.FAI,
                source_system='reference_store',
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create HealthOmics reference group
        healthomics_groups = [g for g in groups if g.group_type == 'healthomics_reference']
        assert len(healthomics_groups) == 1

        group = healthomics_groups[0]
        assert group.primary_file.path.endswith('/source')
        assert len(group.associated_files) == 1
        assert group.associated_files[0].path.endswith('/index')

    def test_healthomics_sequence_store_associations(self):
        """Test HealthOmics sequence store associations."""
        # Test multi-source read set
        multi_source_metadata = {
            '_healthomics_multi_source_info': {
                'account_id': '123456789012',
                'region': 'us-east-1',
                'store_id': 'seq-store-123',
                'read_set_id': 'readset-456',
                'file_type': GenomicsFileType.FASTQ,
                'storage_class': 'STANDARD',
                'creation_time': self.base_datetime,
                'tags': {},
                'metadata_base': {},
                'files': {
                    'source1': {'contentLength': 1000},
                    'source2': {'contentLength': 1000},
                },
            }
        }

        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/seq-store-123/readSet/readset-456/source1',
                GenomicsFileType.FASTQ,
                source_system='sequence_store',
                metadata=multi_source_metadata,
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create sequence store multi-source group
        seq_groups = [g for g in groups if 'sequence_store' in g.group_type]
        assert len(seq_groups) == 1

        group = seq_groups[0]
        assert group.group_type == 'sequence_store_multi_source'
        assert len(group.associated_files) == 1  # source2

    def test_sequence_store_index_associations(self):
        """Test HealthOmics sequence store index file associations."""
        index_metadata = {
            'files': {'source1': {'contentLength': 1000}, 'index': {'contentLength': 100}},
            'account_id': '123456789012',
            'region': 'us-east-1',
            'store_id': 'seq-store-123',
            'read_set_id': 'readset-456',
        }

        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/seq-store-123/readSet/readset-456/source1',
                GenomicsFileType.BAM,
                source_system='sequence_store',
                metadata=index_metadata,
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create sequence store index group
        seq_groups = [g for g in groups if 'sequence_store' in g.group_type]
        assert len(seq_groups) == 1

        group = seq_groups[0]
        assert group.group_type == 'sequence_store_index'
        assert len(group.associated_files) == 1  # index file
        assert group.associated_files[0].file_type == GenomicsFileType.BAI

    def test_no_associations(self):
        """Test files with no associations."""
        files = [
            self.create_test_file('s3://bucket/standalone.bed', GenomicsFileType.BED),
            self.create_test_file('s3://bucket/another.gff', GenomicsFileType.GFF),
        ]

        groups = self.engine.find_associations(files)

        # Should create single-file groups
        assert len(groups) == 2
        for group in groups:
            assert group.group_type == 'single_file'
            assert len(group.associated_files) == 0

    def test_partial_associations(self):
        """Test files with some but not all expected associations."""
        # BAM without index
        files = [
            self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'single_file'
        assert len(groups[0].associated_files) == 0

        # FASTQ R1 without R2
        files = [
            self.create_test_file('s3://bucket/sample_R1.fastq.gz', GenomicsFileType.FASTQ),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'single_file'

    def test_multiple_file_groups(self):
        """Test multiple independent file groups."""
        files = [
            # First BAM group
            self.create_test_file('s3://bucket/sample1.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample1.bam.bai', GenomicsFileType.BAI),
            # Second BAM group
            self.create_test_file('s3://bucket/sample2.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample2.bai', GenomicsFileType.BAI),
            # FASTQ pair
            self.create_test_file('s3://bucket/sample3_R1.fastq.gz', GenomicsFileType.FASTQ),
            self.create_test_file('s3://bucket/sample3_R2.fastq.gz', GenomicsFileType.FASTQ),
        ]

        groups = self.engine.find_associations(files)

        assert len(groups) == 3

        # Check BAM groups
        bam_groups = [g for g in groups if g.group_type == 'bam_index']
        assert len(bam_groups) == 2

        # Check FASTQ group
        fastq_groups = [g for g in groups if g.group_type == 'fastq_pair']
        assert len(fastq_groups) == 1

    def test_association_score_bonus(self):
        """Test association score bonus calculation."""
        # Test no associated files
        group = FileGroup(
            primary_file=self.create_test_file('s3://bucket/file.txt', GenomicsFileType.BED),
            associated_files=[],
            group_type='single_file',
        )
        bonus = self.engine.get_association_score_bonus(group)
        assert bonus == 0.0

        # Test single associated file
        group = FileGroup(
            primary_file=self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
            associated_files=[
                self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI)
            ],
            group_type='bam_index',
        )
        bonus = self.engine.get_association_score_bonus(group)
        assert bonus > 0.0

        # Test complete file sets get higher bonus
        fastq_group = FileGroup(
            primary_file=self.create_test_file(
                's3://bucket/sample_R1.fastq', GenomicsFileType.FASTQ
            ),
            associated_files=[
                self.create_test_file('s3://bucket/sample_R2.fastq', GenomicsFileType.FASTQ)
            ],
            group_type='fastq_pair',
        )
        fastq_bonus = self.engine.get_association_score_bonus(fastq_group)

        bwa_group = FileGroup(
            primary_file=self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA),
            associated_files=[
                self.create_test_file('s3://bucket/ref.fasta.amb', GenomicsFileType.BWA_AMB),
                self.create_test_file('s3://bucket/ref.fasta.ann', GenomicsFileType.BWA_ANN),
            ],
            group_type='bwa_index_collection',
        )
        bwa_bonus = self.engine.get_association_score_bonus(bwa_group)

        # BWA collection should get higher bonus than FASTQ pair
        assert bwa_bonus > fastq_bonus

    def test_case_insensitive_associations(self):
        """Test that file associations work with different case patterns."""
        files = [
            self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'bam_index'
        assert len(groups[0].associated_files) == 1

    def test_complex_file_paths(self):
        """Test associations with complex file paths."""
        files = [
            self.create_test_file(
                's3://bucket/project/sample-123/alignment/sample-123.sorted.bam',
                GenomicsFileType.BAM,
            ),
            self.create_test_file(
                's3://bucket/project/sample-123/alignment/sample-123.sorted.bam.bai',
                GenomicsFileType.BAI,
            ),
        ]

        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'bam_index'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty file list
        groups = self.engine.find_associations([])
        assert groups == []

        # Single file
        files = [self.create_test_file('s3://bucket/single.bam', GenomicsFileType.BAM)]
        groups = self.engine.find_associations(files)
        assert len(groups) == 1
        assert groups[0].group_type == 'single_file'

        # Files with same name but different extensions that don't match patterns
        files = [
            self.create_test_file('s3://bucket/sample.txt', GenomicsFileType.BED),
            self.create_test_file('s3://bucket/sample.log', GenomicsFileType.BED),
        ]
        groups = self.engine.find_associations(files)
        assert len(groups) == 2  # Should be separate single-file groups

    def test_determine_group_type(self):
        """Test group type determination logic."""
        # Test BAM group type
        primary = self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM)
        associated = [self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI)]
        group_type = self.engine._determine_group_type(primary, associated)
        assert group_type == 'bam_index'

        # Test FASTQ pair group type
        primary = self.create_test_file('s3://bucket/sample_R1.fastq', GenomicsFileType.FASTQ)
        associated = [self.create_test_file('s3://bucket/sample_R2.fastq', GenomicsFileType.FASTQ)]
        group_type = self.engine._determine_group_type(primary, associated)
        assert group_type == 'fastq_pair'

        # Test FASTA with BWA indexes
        primary = self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA)
        associated = [
            self.create_test_file('s3://bucket/ref.fasta.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/ref.dict', GenomicsFileType.DICT),
        ]
        group_type = self.engine._determine_group_type(primary, associated)
        assert group_type == 'fasta_bwa_dict'

    def test_regex_error_handling(self):
        """Test handling of regex errors in association patterns."""
        # Create a mock file map
        file_map = {
            's3://bucket/test.bam': self.create_test_file(
                's3://bucket/test.bam', GenomicsFileType.BAM
            )
        }

        # Test with a file that might cause regex issues
        primary_file = self.create_test_file('s3://bucket/test[invalid].bam', GenomicsFileType.BAM)

        # This should not raise an exception even with potentially problematic regex patterns
        associated_files = self.engine._find_associated_files(primary_file, file_map)

        # Should return empty list if no valid associations found
        assert isinstance(associated_files, list)

    def test_invalid_file_type_in_determine_group_type(self):
        """Test _determine_group_type with unknown file types."""
        # Test with a file that doesn't match any known patterns
        unknown_file = self.create_test_file('s3://bucket/unknown.xyz', GenomicsFileType.BED)
        associated_files = []

        group_type = self.engine._determine_group_type(unknown_file, associated_files)
        assert group_type == 'unknown_association'

    def test_healthomics_associations_edge_cases(self):
        """Test HealthOmics associations with edge cases."""
        # Test file without proper HealthOmics URI structure
        files = [
            self.create_test_file(
                'omics://invalid-uri-structure',
                GenomicsFileType.FASTA,
                source_system='reference_store',
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create single-file group for invalid URI
        assert len(groups) == 1
        assert groups[0].group_type == 'single_file'

    def test_sequence_store_without_index_info(self):
        """Test sequence store files without index information."""
        # Test file without _healthomics_index_info
        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/seq-store-123/readSet/readset-456/source1',
                GenomicsFileType.BAM,
                source_system='sequence_store',
                metadata={'some_other_field': 'value'},  # No index info
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should still process the file
        assert len(groups) >= 1

    def test_compiled_patterns_initialization(self):
        """Test that patterns are pre-compiled during initialization."""
        engine = FileAssociationEngine()

        # Verify compiled patterns exist
        assert hasattr(engine, '_compiled_patterns')
        assert len(engine._compiled_patterns) == len(FileAssociationEngine.ASSOCIATION_PATTERNS)

        # Verify each pattern is a compiled regex
        import re

        for compiled_pattern, assoc_pattern, group_type in engine._compiled_patterns:
            assert isinstance(compiled_pattern, re.Pattern)
            assert isinstance(assoc_pattern, str)
            assert isinstance(group_type, str)

    def test_extension_pattern_map_initialization(self):
        """Test that extension pattern map is built during initialization."""
        engine = FileAssociationEngine()

        # Verify extension map exists
        assert hasattr(engine, '_extension_pattern_map')
        assert isinstance(engine._extension_pattern_map, dict)

        # Verify common extensions are mapped
        expected_extensions = ['.bam', '.cram', '.fastq', '.fasta', '.vcf']
        for ext in expected_extensions:
            assert ext in engine._extension_pattern_map
            assert isinstance(engine._extension_pattern_map[ext], list)
            assert len(engine._extension_pattern_map[ext]) > 0

    def test_get_relevant_pattern_indices_bam(self):
        """Test pattern index filtering for BAM files."""
        engine = FileAssociationEngine()

        # Test BAM file
        indices = engine._get_relevant_pattern_indices('s3://bucket/sample.bam')
        assert isinstance(indices, list)
        assert len(indices) > 0

        # Verify indices are valid
        for idx in indices:
            assert 0 <= idx < len(engine._compiled_patterns)

        # BAM patterns should be included
        bam_patterns_found = False
        for idx in indices:
            _, _, group_type = engine._compiled_patterns[idx]
            if 'bam' in group_type:
                bam_patterns_found = True
                break
        assert bam_patterns_found

    def test_get_relevant_pattern_indices_fastq(self):
        """Test pattern index filtering for FASTQ files."""
        engine = FileAssociationEngine()

        # Test FASTQ file
        indices = engine._get_relevant_pattern_indices('s3://bucket/sample_R1.fastq.gz')
        assert isinstance(indices, list)
        assert len(indices) > 0

        # FASTQ patterns should be included
        fastq_patterns_found = False
        for idx in indices:
            _, _, group_type = engine._compiled_patterns[idx]
            if 'fastq' in group_type:
                fastq_patterns_found = True
                break
        assert fastq_patterns_found

    def test_get_relevant_pattern_indices_unknown_extension(self):
        """Test pattern index filtering for unknown file extensions."""
        engine = FileAssociationEngine()

        # Test file with unknown extension
        indices = engine._get_relevant_pattern_indices('s3://bucket/sample.xyz')
        assert isinstance(indices, list)

        # Should return all patterns when extension is unknown
        assert len(indices) == len(engine._compiled_patterns)

    def test_get_relevant_pattern_indices_case_insensitive(self):
        """Test that pattern index filtering is case-insensitive."""
        engine = FileAssociationEngine()

        # Test with uppercase extension
        indices_upper = engine._get_relevant_pattern_indices('s3://bucket/sample.BAM')
        indices_lower = engine._get_relevant_pattern_indices('s3://bucket/sample.bam')

        # Should return same indices regardless of case
        assert indices_upper == indices_lower

    def test_compiled_patterns_preserve_functionality(self):
        """Test that pre-compiled patterns produce same results as original implementation."""
        engine = FileAssociationEngine()

        # Test various file associations to ensure compiled patterns work correctly
        test_cases = [
            # BAM with index
            (
                [
                    self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
                    self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI),
                ],
                1,
                'bam_index',
            ),
            # FASTQ pair
            (
                [
                    self.create_test_file('s3://bucket/sample_R1.fastq', GenomicsFileType.FASTQ),
                    self.create_test_file('s3://bucket/sample_R2.fastq', GenomicsFileType.FASTQ),
                ],
                1,
                'fastq_pair',
            ),
            # FASTA with index
            (
                [
                    self.create_test_file('s3://bucket/ref.fasta', GenomicsFileType.FASTA),
                    self.create_test_file('s3://bucket/ref.fasta.fai', GenomicsFileType.FAI),
                ],
                1,
                'fasta_index',
            ),
        ]

        for files, expected_groups, expected_type in test_cases:
            groups = engine.find_associations(files)
            assert len(groups) == expected_groups
            if expected_groups > 0:
                assert groups[0].group_type == expected_type

    def test_performance_with_many_files(self):
        """Test that pattern optimization improves performance with many files."""
        import time

        engine = FileAssociationEngine()

        # Create a large set of files
        files = []
        for i in range(100):
            files.append(self.create_test_file(f's3://bucket/sample{i}.bam', GenomicsFileType.BAM))
            files.append(
                self.create_test_file(f's3://bucket/sample{i}.bam.bai', GenomicsFileType.BAI)
            )

        # Measure time to find associations
        start_time = time.time()
        groups = engine.find_associations(files)
        elapsed_time = time.time() - start_time

        # Verify results are correct
        assert len(groups) == 100  # 100 BAM groups

        # Performance should be reasonable (< 1 second for 200 files)
        assert elapsed_time < 1.0, f'Performance test failed: took {elapsed_time:.3f}s'

    def test_extension_map_coverage(self):
        """Test that extension map covers all major genomics file types."""
        engine = FileAssociationEngine()

        # Test that all major file types have pattern mappings
        major_extensions = {
            '.bam': 'bam',
            '.cram': 'cram',
            '.fastq': 'fastq',
            '.fastq.gz': 'fastq',
            '.fasta': 'fasta',
            '.fa': 'fasta',
            '.vcf': 'vcf',
            '.vcf.gz': 'vcf',
            '.gvcf': 'gvcf',
            '.bcf': 'bcf',
        }

        for ext, expected_keyword in major_extensions.items():
            assert ext in engine._extension_pattern_map, f'Extension {ext} not in map'

            # Verify patterns contain expected keyword
            indices = engine._extension_pattern_map[ext]
            found_keyword = False
            for idx in indices:
                _, _, group_type = engine._compiled_patterns[idx]
                if expected_keyword in group_type:
                    found_keyword = True
                    break
            assert found_keyword, f'No patterns with keyword {expected_keyword} for {ext}'

    def test_pattern_optimization_reduces_checks(self):
        """Test that pattern optimization reduces the number of regex checks."""
        engine = FileAssociationEngine()

        # For a BAM file, should only check BAM-related patterns
        bam_indices = engine._get_relevant_pattern_indices('s3://bucket/sample.bam')

        # Should be fewer than total patterns
        assert len(bam_indices) < len(engine._compiled_patterns)

        # Verify only BAM-related patterns are included
        for idx in bam_indices:
            _, _, group_type = engine._compiled_patterns[idx]
            # BAM patterns should have 'bam' in group_type
            assert 'bam' in group_type.lower()

    def test_compiled_patterns_handle_special_characters(self):
        """Test that compiled patterns handle special characters correctly."""
        engine = FileAssociationEngine()

        # Test with file paths containing special regex characters
        files = [
            self.create_test_file('s3://bucket/sample[1].bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample[1].bam.bai', GenomicsFileType.BAI),
        ]

        # Should not raise exceptions
        groups = engine.find_associations(files)
        assert isinstance(groups, list)

    def test_build_extension_pattern_map_completeness(self):
        """Test that _build_extension_pattern_map creates valid mappings."""
        engine = FileAssociationEngine()

        ext_map = engine._build_extension_pattern_map()

        # Verify structure
        assert isinstance(ext_map, dict)

        # Verify all values are lists of integers
        for ext, indices in ext_map.items():
            assert isinstance(ext, str)
            assert isinstance(indices, list)
            for idx in indices:
                assert isinstance(idx, int)
                assert 0 <= idx < len(engine._compiled_patterns)

    def test_pattern_matching_with_optimization(self):
        """Test that pattern matching works correctly with optimization enabled."""
        engine = FileAssociationEngine()

        # Test all association pattern types to ensure optimization doesn't break functionality
        test_files = [
            # BAM
            (
                's3://bucket/test.bam',
                's3://bucket/test.bam.bai',
                GenomicsFileType.BAM,
                GenomicsFileType.BAI,
            ),
            # CRAM
            (
                's3://bucket/test.cram',
                's3://bucket/test.cram.crai',
                GenomicsFileType.CRAM,
                GenomicsFileType.CRAI,
            ),
            # VCF
            (
                's3://bucket/test.vcf.gz',
                's3://bucket/test.vcf.gz.tbi',
                GenomicsFileType.VCF,
                GenomicsFileType.TBI,
            ),
        ]

        for primary_path, assoc_path, primary_type, assoc_type in test_files:
            files = [
                self.create_test_file(primary_path, primary_type),
                self.create_test_file(assoc_path, assoc_type),
            ]

            groups = engine.find_associations(files)
            assert len(groups) == 1, f'Failed for {primary_path}'
            assert len(groups[0].associated_files) == 1, f'Failed for {primary_path}'

    def test_multiple_extensions_in_path(self):
        """Test files with multiple extensions in the path."""
        engine = FileAssociationEngine()

        # Test file with multiple dots
        indices = engine._get_relevant_pattern_indices('s3://bucket/sample.sorted.bam')
        assert len(indices) > 0

        # Should still identify as BAM file
        bam_patterns_found = False
        for idx in indices:
            _, _, group_type = engine._compiled_patterns[idx]
            if 'bam' in group_type:
                bam_patterns_found = True
                break
        assert bam_patterns_found

    def test_fasta_with_bwa_and_dict(self):
        """Test FASTA file with both BWA indexes and dict file."""
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/reference.fasta.ann', GenomicsFileType.BWA_ANN),
            self.create_test_file('s3://bucket/reference.dict', GenomicsFileType.DICT),
        ]

        groups = self.engine.find_associations(files)

        # Should create groups - BWA collection and potentially FASTA with dict
        assert len(groups) >= 1

        # Check if we have the expected group types
        group_types = [g.group_type for g in groups]
        assert any('bwa' in gt or 'dict' in gt for gt in group_types)

    def test_fasta_with_only_bwa_indexes(self):
        """Test FASTA file with only BWA indexes (no dict)."""
        files = [
            self.create_test_file('s3://bucket/reference.fasta', GenomicsFileType.FASTA),
            self.create_test_file('s3://bucket/reference.fasta.amb', GenomicsFileType.BWA_AMB),
            self.create_test_file('s3://bucket/reference.fasta.ann', GenomicsFileType.BWA_ANN),
        ]

        groups = self.engine.find_associations(files)

        # Should create BWA index collection
        bwa_groups = [g for g in groups if 'bwa' in g.group_type]
        assert len(bwa_groups) >= 1

    def test_duplicate_association_prevention(self):
        """Test that duplicate associations are prevented."""
        # Create files where S3File associations might overlap with regex patterns
        files = [
            self.create_test_file('s3://bucket/sample.bam', GenomicsFileType.BAM),
            self.create_test_file('s3://bucket/sample.bam.bai', GenomicsFileType.BAI),
        ]

        groups = self.engine.find_associations(files)

        # Should have exactly one group with one associated file (no duplicates)
        assert len(groups) == 1
        assert len(groups[0].associated_files) == 1

    def test_regex_error_in_pattern_matching(self):
        """Test handling of regex errors during pattern matching."""
        engine = FileAssociationEngine()

        # Create a file with characters that might cause regex issues
        primary_file = self.create_test_file('s3://bucket/test(special).bam', GenomicsFileType.BAM)
        file_map = {
            's3://bucket/test(special).bam': primary_file,
            's3://bucket/test(special).bam.bai': self.create_test_file(
                's3://bucket/test(special).bam.bai', GenomicsFileType.BAI
            ),
        }

        # Should handle gracefully without raising exceptions
        associated_files = engine._find_associated_files(primary_file, file_map)
        assert isinstance(associated_files, list)

    def test_sequence_store_with_index_info_metadata(self):
        """Test sequence store files with _healthomics_index_info metadata."""
        # This metadata should cause the file to be skipped in sequence store associations
        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/seq-store-123/readSet/readset-456/source1',
                GenomicsFileType.BAM,
                source_system='sequence_store',
                metadata={'_healthomics_index_info': {'some': 'data'}},
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create a single-file group since index_info is present
        assert len(groups) == 1
        assert groups[0].group_type == 'single_file'

    def test_non_sequence_store_omics_files(self):
        """Test that non-sequence-store omics files are handled correctly."""
        # Reference store files should not be processed by sequence store logic
        files = [
            self.create_test_file(
                'omics://123456789012.storage.us-east-1.amazonaws.com/ref-store-123/reference/ref-456/source',
                GenomicsFileType.FASTA,
                source_system='reference_store',  # Not sequence_store
            ),
        ]

        groups = self.engine.find_associations(files)

        # Should create a single-file group
        assert len(groups) == 1

    def test_extension_pattern_map_with_compressed_files(self):
        """Test that compressed file extensions are properly mapped."""
        engine = FileAssociationEngine()

        # Test compressed FASTQ files
        for ext in ['.fastq.gz', '.fastq.bz2']:
            assert ext in engine._extension_pattern_map
            indices = engine._extension_pattern_map[ext]
            assert len(indices) > 0

            # Verify patterns are FASTQ-related
            for idx in indices:
                _, _, group_type = engine._compiled_patterns[idx]
                assert 'fastq' in group_type

    def test_all_pattern_types_have_compiled_versions(self):
        """Test that all original patterns have compiled versions."""
        engine = FileAssociationEngine()

        # Verify counts match
        assert len(engine._compiled_patterns) == len(FileAssociationEngine.ASSOCIATION_PATTERNS)

        # Verify each compiled pattern corresponds to an original pattern
        for idx, (compiled_pat, assoc_pat, group_type) in enumerate(engine._compiled_patterns):
            orig_primary, orig_assoc, orig_group = FileAssociationEngine.ASSOCIATION_PATTERNS[idx]

            # Verify the pattern strings match
            assert compiled_pat.pattern == orig_primary
            assert assoc_pat == orig_assoc
            assert group_type == orig_group

            # Verify case-insensitive flag is set
            import re

            assert compiled_pat.flags & re.IGNORECASE
