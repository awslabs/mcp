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

"""Tests for file type detector."""

from awslabs.aws_healthomics_mcp_server.models import GenomicsFileType
from awslabs.aws_healthomics_mcp_server.search.file_type_detector import FileTypeDetector


class TestFileTypeDetector:
    """Test cases for file type detector."""

    def test_detect_file_type_fastq_files(self):
        """Test detection of FASTQ files."""
        fastq_files = [
            'sample.fastq',
            'sample.fastq.gz',
            'sample.fastq.bz2',
            'sample.fq',
            'sample.fq.gz',
            'sample.fq.bz2',
            'path/to/sample.fastq',
            'SAMPLE.FASTQ',  # Case insensitive
            'Sample.Fastq.Gz',  # Mixed case
        ]

        for file_path in fastq_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == GenomicsFileType.FASTQ, f'Failed for {file_path}'

    def test_detect_file_type_fasta_files(self):
        """Test detection of FASTA files."""
        fasta_files = [
            'reference.fasta',
            'reference.fasta.gz',
            'reference.fasta.bz2',
            'reference.fa',
            'reference.fa.gz',
            'reference.fa.bz2',
            'path/to/reference.fasta',
            'REFERENCE.FASTA',  # Case insensitive
        ]

        for file_path in fasta_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == GenomicsFileType.FASTA, f'Failed for {file_path}'

    def test_detect_file_type_fna_files(self):
        """Test detection of FNA files."""
        fna_files = [
            'genome.fna',
            'genome.fna.gz',
            'genome.fna.bz2',
            'path/to/genome.fna',
        ]

        for file_path in fna_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == GenomicsFileType.FNA, f'Failed for {file_path}'

    def test_detect_file_type_alignment_files(self):
        """Test detection of alignment files."""
        alignment_files = [
            ('sample.bam', GenomicsFileType.BAM),
            ('sample.cram', GenomicsFileType.CRAM),
            ('sample.sam', GenomicsFileType.SAM),
            ('sample.sam.gz', GenomicsFileType.SAM),
            ('sample.sam.bz2', GenomicsFileType.SAM),
        ]

        for file_path, expected_type in alignment_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_detect_file_type_variant_files(self):
        """Test detection of variant files."""
        variant_files = [
            ('variants.vcf', GenomicsFileType.VCF),
            ('variants.vcf.gz', GenomicsFileType.VCF),
            ('variants.vcf.bz2', GenomicsFileType.VCF),
            ('variants.gvcf', GenomicsFileType.GVCF),
            ('variants.gvcf.gz', GenomicsFileType.GVCF),
            ('variants.gvcf.bz2', GenomicsFileType.GVCF),
            ('variants.bcf', GenomicsFileType.BCF),
        ]

        for file_path, expected_type in variant_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_detect_file_type_annotation_files(self):
        """Test detection of annotation files."""
        annotation_files = [
            ('regions.bed', GenomicsFileType.BED),
            ('regions.bed.gz', GenomicsFileType.BED),
            ('regions.bed.bz2', GenomicsFileType.BED),
            ('genes.gff', GenomicsFileType.GFF),
            ('genes.gff.gz', GenomicsFileType.GFF),
            ('genes.gff.bz2', GenomicsFileType.GFF),
            ('genes.gff3', GenomicsFileType.GFF),
            ('genes.gff3.gz', GenomicsFileType.GFF),
            ('genes.gff3.bz2', GenomicsFileType.GFF),
            ('genes.gtf', GenomicsFileType.GFF),
            ('genes.gtf.gz', GenomicsFileType.GFF),
            ('genes.gtf.bz2', GenomicsFileType.GFF),
        ]

        for file_path, expected_type in annotation_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_detect_file_type_index_files(self):
        """Test detection of index files."""
        index_files = [
            ('sample.bai', GenomicsFileType.BAI),
            ('sample.bam.bai', GenomicsFileType.BAI),
            ('sample.crai', GenomicsFileType.CRAI),
            ('sample.cram.crai', GenomicsFileType.CRAI),
            ('reference.fai', GenomicsFileType.FAI),
            ('reference.fasta.fai', GenomicsFileType.FAI),
            ('reference.fa.fai', GenomicsFileType.FAI),
            ('reference.fna.fai', GenomicsFileType.FAI),
            ('reference.dict', GenomicsFileType.DICT),
            ('variants.tbi', GenomicsFileType.TBI),
            ('variants.vcf.gz.tbi', GenomicsFileType.TBI),
            ('variants.gvcf.gz.tbi', GenomicsFileType.TBI),
            ('variants.csi', GenomicsFileType.CSI),
            ('variants.vcf.gz.csi', GenomicsFileType.CSI),
            ('variants.gvcf.gz.csi', GenomicsFileType.CSI),
            ('variants.bcf.csi', GenomicsFileType.CSI),
        ]

        for file_path, expected_type in index_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_detect_file_type_bwa_index_files(self):
        """Test detection of BWA index files."""
        bwa_files = [
            ('reference.amb', GenomicsFileType.BWA_AMB),
            ('reference.ann', GenomicsFileType.BWA_ANN),
            ('reference.bwt', GenomicsFileType.BWA_BWT),
            ('reference.pac', GenomicsFileType.BWA_PAC),
            ('reference.sa', GenomicsFileType.BWA_SA),
            ('reference.64.amb', GenomicsFileType.BWA_AMB),
            ('reference.64.ann', GenomicsFileType.BWA_ANN),
            ('reference.64.bwt', GenomicsFileType.BWA_BWT),
            ('reference.64.pac', GenomicsFileType.BWA_PAC),
            ('reference.64.sa', GenomicsFileType.BWA_SA),
        ]

        for file_path, expected_type in bwa_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_detect_file_type_unknown_files(self):
        """Test detection of unknown file types."""
        unknown_files = [
            'document.txt',
            'image.jpg',
            'data.csv',
            'script.py',
            'config.json',
            'readme.md',
            'file_without_extension',
            'file.unknown',
        ]

        for file_path in unknown_files:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result is None, f'Should be None for {file_path}'

    def test_detect_file_type_empty_or_none(self):
        """Test detection with empty or None input."""
        assert FileTypeDetector.detect_file_type('') is None
        # Note: None input would cause a type error, so we skip this test case

    def test_detect_file_type_longest_match_priority(self):
        """Test that longest extension matches take priority."""
        # .vcf.gz.tbi should match as TBI, not VCF
        result = FileTypeDetector.detect_file_type('variants.vcf.gz.tbi')
        assert result == GenomicsFileType.TBI

        # .fasta.fai should match as FAI, not FASTA
        result = FileTypeDetector.detect_file_type('reference.fasta.fai')
        assert result == GenomicsFileType.FAI

        # .bam.bai should match as BAI, not BAM
        result = FileTypeDetector.detect_file_type('alignment.bam.bai')
        assert result == GenomicsFileType.BAI

    def test_is_compressed_file(self):
        """Test compressed file detection."""
        compressed_files = [
            'file.gz',
            'file.bz2',
            'file.xz',
            'file.lz4',
            'file.zst',
            'sample.fastq.gz',
            'reference.fasta.bz2',
            'path/to/file.gz',
            'FILE.GZ',  # Case insensitive
        ]

        for file_path in compressed_files:
            result = FileTypeDetector.is_compressed_file(file_path)
            assert result is True, f'Should be compressed: {file_path}'

    def test_is_not_compressed_file(self):
        """Test non-compressed file detection."""
        uncompressed_files = [
            'file.txt',
            'sample.fastq',
            'reference.fasta',
            'variants.vcf',
            'file_without_extension',
            'file.unknown',
        ]

        for file_path in uncompressed_files:
            result = FileTypeDetector.is_compressed_file(file_path)
            assert result is False, f'Should not be compressed: {file_path}'

    def test_is_compressed_file_empty_or_none(self):
        """Test compressed file detection with empty or None input."""
        assert FileTypeDetector.is_compressed_file('') is False
        # Note: None input would cause a type error, so we skip this test case

    def test_get_base_file_type(self):
        """Test getting base file type ignoring compression."""
        test_cases = [
            ('sample.fastq.gz', GenomicsFileType.FASTQ),
            ('sample.fastq.bz2', GenomicsFileType.FASTQ),
            ('reference.fasta.gz', GenomicsFileType.FASTA),
            ('variants.vcf.gz', GenomicsFileType.VCF),
            ('regions.bed.bz2', GenomicsFileType.BED),
            ('sample.fastq', GenomicsFileType.FASTQ),  # Already uncompressed
            ('unknown.txt.gz', None),  # Unknown base type
        ]

        for file_path, expected_type in test_cases:
            result = FileTypeDetector.get_base_file_type(file_path)
            assert result == expected_type, f'Failed for {file_path}'

    def test_get_base_file_type_empty_or_none(self):
        """Test getting base file type with empty or None input."""
        assert FileTypeDetector.get_base_file_type('') is None
        # Note: None input would cause a type error, so we skip this test case

    def test_is_genomics_file(self):
        """Test genomics file recognition."""
        genomics_files = [
            'sample.fastq',
            'reference.fasta',
            'alignment.bam',
            'variants.vcf',
            'regions.bed',
            'sample.bai',
            'reference.amb',
        ]

        for file_path in genomics_files:
            result = FileTypeDetector.is_genomics_file(file_path)
            assert result is True, f'Should be genomics file: {file_path}'

    def test_is_not_genomics_file(self):
        """Test non-genomics file recognition."""
        non_genomics_files = [
            'document.txt',
            'image.jpg',
            'data.csv',
            'script.py',
            'unknown.xyz',
        ]

        for file_path in non_genomics_files:
            result = FileTypeDetector.is_genomics_file(file_path)
            assert result is False, f'Should not be genomics file: {file_path}'

    def test_get_file_category(self):
        """Test file category classification."""
        category_tests = [
            (GenomicsFileType.FASTQ, 'sequence'),
            (GenomicsFileType.FASTA, 'sequence'),
            (GenomicsFileType.FNA, 'sequence'),
            (GenomicsFileType.BAM, 'alignment'),
            (GenomicsFileType.CRAM, 'alignment'),
            (GenomicsFileType.SAM, 'alignment'),
            (GenomicsFileType.VCF, 'variant'),
            (GenomicsFileType.GVCF, 'variant'),
            (GenomicsFileType.BCF, 'variant'),
            (GenomicsFileType.BED, 'annotation'),
            (GenomicsFileType.GFF, 'annotation'),
            (GenomicsFileType.BAI, 'index'),
            (GenomicsFileType.CRAI, 'index'),
            (GenomicsFileType.FAI, 'index'),
            (GenomicsFileType.DICT, 'index'),
            (GenomicsFileType.TBI, 'index'),
            (GenomicsFileType.CSI, 'index'),
            (GenomicsFileType.BWA_AMB, 'bwa_index'),
            (GenomicsFileType.BWA_ANN, 'bwa_index'),
            (GenomicsFileType.BWA_BWT, 'bwa_index'),
            (GenomicsFileType.BWA_PAC, 'bwa_index'),
            (GenomicsFileType.BWA_SA, 'bwa_index'),
        ]

        for file_type, expected_category in category_tests:
            result = FileTypeDetector.get_file_category(file_type)
            assert result == expected_category, f'Failed for {file_type}'

    def test_matches_file_type_filter_exact_match(self):
        """Test file type filter matching with exact type matches."""
        test_cases = [
            ('sample.fastq', 'fastq', True),
            ('reference.fasta', 'fasta', True),
            ('alignment.bam', 'bam', True),
            ('variants.vcf', 'vcf', True),
            ('sample.fastq', 'bam', False),
            ('reference.fasta', 'vcf', False),
        ]

        for file_path, filter_type, expected in test_cases:
            result = FileTypeDetector.matches_file_type_filter(file_path, filter_type)
            assert result == expected, f'Failed for {file_path} with filter {filter_type}'

    def test_matches_file_type_filter_category_match(self):
        """Test file type filter matching with category matches."""
        test_cases = [
            ('sample.fastq', 'sequence', True),
            ('reference.fasta', 'sequence', True),
            ('alignment.bam', 'alignment', True),
            ('variants.vcf', 'variant', True),
            ('regions.bed', 'annotation', True),
            ('sample.bai', 'index', True),
            ('reference.amb', 'bwa_index', True),
            ('sample.fastq', 'alignment', False),
            ('alignment.bam', 'variant', False),
        ]

        for file_path, filter_category, expected in test_cases:
            result = FileTypeDetector.matches_file_type_filter(file_path, filter_category)
            assert result == expected, f'Failed for {file_path} with filter {filter_category}'

    def test_matches_file_type_filter_aliases(self):
        """Test file type filter matching with aliases."""
        test_cases = [
            ('sample.fq', 'fq', True),  # fq alias for FASTQ
            ('reference.fa', 'fa', True),  # fa alias for FASTA
            ('reference.fasta', 'reference', True),  # reference alias for FASTA
            ('sample.fastq', 'reads', True),  # reads alias for FASTQ
            ('variants.vcf', 'variants', True),  # variants alias for variant category
            ('regions.bed', 'annotations', True),  # annotations alias for annotation category
            ('sample.bai', 'indexes', True),  # indexes alias for index category
            ('sample.fastq', 'unknown_alias', False),
        ]

        for file_path, filter_alias, expected in test_cases:
            result = FileTypeDetector.matches_file_type_filter(file_path, filter_alias)
            assert result == expected, f'Failed for {file_path} with alias {filter_alias}'

    def test_matches_file_type_filter_case_insensitive(self):
        """Test file type filter matching is case insensitive."""
        test_cases = [
            ('sample.fastq', 'FASTQ', True),
            ('sample.fastq', 'Fastq', True),
            ('sample.fastq', 'SEQUENCE', True),
            ('sample.fastq', 'Sequence', True),
            ('reference.fasta', 'FA', True),
            ('reference.fasta', 'REFERENCE', True),
        ]

        for file_path, filter_type, expected in test_cases:
            result = FileTypeDetector.matches_file_type_filter(file_path, filter_type)
            assert result == expected, f'Failed for {file_path} with filter {filter_type}'

    def test_matches_file_type_filter_unknown_file(self):
        """Test file type filter matching with unknown files."""
        unknown_files = ['document.txt', 'image.jpg', 'unknown.xyz']

        for file_path in unknown_files:
            result = FileTypeDetector.matches_file_type_filter(file_path, 'fastq')
            assert result is False, f'Unknown file {file_path} should not match any filter'

    def test_extension_mapping_completeness(self):
        """Test that all extensions in mapping are properly sorted."""
        # Verify that _SORTED_EXTENSIONS is properly sorted by length (longest first)
        extensions = FileTypeDetector._SORTED_EXTENSIONS
        for i in range(len(extensions) - 1):
            assert len(extensions[i]) >= len(extensions[i + 1]), (
                f'Extensions not properly sorted: {extensions[i]} should be >= {extensions[i + 1]}'
            )

    def test_extension_mapping_consistency(self):
        """Test that extension mapping is consistent."""
        # Verify that all keys in EXTENSION_MAPPING are in _SORTED_EXTENSIONS
        mapping_keys = set(FileTypeDetector.EXTENSION_MAPPING.keys())
        sorted_keys = set(FileTypeDetector._SORTED_EXTENSIONS)
        assert mapping_keys == sorted_keys, (
            'Extension mapping and sorted extensions are inconsistent'
        )

    def test_complex_file_paths(self):
        """Test detection with complex file paths."""
        complex_paths = [
            ('/path/to/data/sample.fastq.gz', GenomicsFileType.FASTQ),
            ('s3://bucket/prefix/reference.fasta', GenomicsFileType.FASTA),
            ('./relative/path/alignment.bam', GenomicsFileType.BAM),
            ('~/home/user/variants.vcf.gz', GenomicsFileType.VCF),
            ('file:///absolute/path/regions.bed', GenomicsFileType.BED),
            ('https://example.com/data/sample.fastq', GenomicsFileType.FASTQ),
        ]

        for file_path, expected_type in complex_paths:
            result = FileTypeDetector.detect_file_type(file_path)
            assert result == expected_type, f'Failed for complex path: {file_path}'
