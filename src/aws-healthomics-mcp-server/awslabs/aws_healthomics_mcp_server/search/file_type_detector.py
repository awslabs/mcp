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

"""File type detection utilities for genomics files."""

from awslabs.aws_healthomics_mcp_server.models import GenomicsFileType
from typing import Optional


class FileTypeDetector:
    """Utility class for detecting genomics file types from file extensions."""

    # Mapping of file extensions to GenomicsFileType enum values
    # Includes both compressed and uncompressed variants
    EXTENSION_MAPPING = {
        # Sequence files
        '.fastq': GenomicsFileType.FASTQ,
        '.fastq.gz': GenomicsFileType.FASTQ,
        '.fastq.bz2': GenomicsFileType.FASTQ,
        '.fq': GenomicsFileType.FASTQ,
        '.fq.gz': GenomicsFileType.FASTQ,
        '.fq.bz2': GenomicsFileType.FASTQ,
        '.fasta': GenomicsFileType.FASTA,
        '.fasta.gz': GenomicsFileType.FASTA,
        '.fasta.bz2': GenomicsFileType.FASTA,
        '.fa': GenomicsFileType.FASTA,
        '.fa.gz': GenomicsFileType.FASTA,
        '.fa.bz2': GenomicsFileType.FASTA,
        '.fna': GenomicsFileType.FNA,
        '.fna.gz': GenomicsFileType.FNA,
        '.fna.bz2': GenomicsFileType.FNA,
        # Alignment files
        '.bam': GenomicsFileType.BAM,
        '.cram': GenomicsFileType.CRAM,
        '.sam': GenomicsFileType.SAM,
        '.sam.gz': GenomicsFileType.SAM,
        '.sam.bz2': GenomicsFileType.SAM,
        # Variant files
        '.vcf': GenomicsFileType.VCF,
        '.vcf.gz': GenomicsFileType.VCF,
        '.vcf.bz2': GenomicsFileType.VCF,
        '.gvcf': GenomicsFileType.GVCF,
        '.gvcf.gz': GenomicsFileType.GVCF,
        '.gvcf.bz2': GenomicsFileType.GVCF,
        '.bcf': GenomicsFileType.BCF,
        # Annotation files
        '.bed': GenomicsFileType.BED,
        '.bed.gz': GenomicsFileType.BED,
        '.bed.bz2': GenomicsFileType.BED,
        '.gff': GenomicsFileType.GFF,
        '.gff.gz': GenomicsFileType.GFF,
        '.gff.bz2': GenomicsFileType.GFF,
        '.gff3': GenomicsFileType.GFF,
        '.gff3.gz': GenomicsFileType.GFF,
        '.gff3.bz2': GenomicsFileType.GFF,
        '.gtf': GenomicsFileType.GFF,
        '.gtf.gz': GenomicsFileType.GFF,
        '.gtf.bz2': GenomicsFileType.GFF,
        # Index files
        '.bai': GenomicsFileType.BAI,
        '.bam.bai': GenomicsFileType.BAI,
        '.crai': GenomicsFileType.CRAI,
        '.cram.crai': GenomicsFileType.CRAI,
        '.fai': GenomicsFileType.FAI,
        '.fasta.fai': GenomicsFileType.FAI,
        '.fa.fai': GenomicsFileType.FAI,
        '.fna.fai': GenomicsFileType.FAI,
        '.dict': GenomicsFileType.DICT,
        '.tbi': GenomicsFileType.TBI,
        '.vcf.gz.tbi': GenomicsFileType.TBI,
        '.gvcf.gz.tbi': GenomicsFileType.TBI,
        '.csi': GenomicsFileType.CSI,
        '.vcf.gz.csi': GenomicsFileType.CSI,
        '.gvcf.gz.csi': GenomicsFileType.CSI,
        '.bcf.csi': GenomicsFileType.CSI,
        # BWA index files (regular and 64-bit variants)
        '.amb': GenomicsFileType.BWA_AMB,
        '.ann': GenomicsFileType.BWA_ANN,
        '.bwt': GenomicsFileType.BWA_BWT,
        '.pac': GenomicsFileType.BWA_PAC,
        '.sa': GenomicsFileType.BWA_SA,
        '.64.amb': GenomicsFileType.BWA_AMB,
        '.64.ann': GenomicsFileType.BWA_ANN,
        '.64.bwt': GenomicsFileType.BWA_BWT,
        '.64.pac': GenomicsFileType.BWA_PAC,
        '.64.sa': GenomicsFileType.BWA_SA,
    }

    # Pre-sorted extensions by length (longest first) for efficient matching
    _SORTED_EXTENSIONS = sorted(EXTENSION_MAPPING.keys(), key=len, reverse=True)

    @classmethod
    def detect_file_type(cls, file_path: str) -> Optional[GenomicsFileType]:
        """Detect the genomics file type from a file path.

        Args:
            file_path: The file path to analyze

        Returns:
            GenomicsFileType enum value if detected, None otherwise
        """
        if not file_path:
            return None

        # Convert to lowercase for case-insensitive matching
        path_lower = file_path.lower()

        # Try exact extension matches first (longest matches first)
        # Use pre-sorted extensions for efficiency
        for extension in cls._SORTED_EXTENSIONS:
            if path_lower.endswith(extension):
                return cls.EXTENSION_MAPPING[extension]

        return None

    @classmethod
    def is_compressed_file(cls, file_path: str) -> bool:
        """Check if a file is compressed based on its extension.

        Args:
            file_path: The file path to check

        Returns:
            True if the file appears to be compressed, False otherwise
        """
        if not file_path:
            return False

        path_lower = file_path.lower()
        compression_extensions = ['.gz', '.bz2', '.xz', '.lz4', '.zst']

        return any(path_lower.endswith(ext) for ext in compression_extensions)

    @classmethod
    def get_base_file_type(cls, file_path: str) -> Optional[GenomicsFileType]:
        """Get the base file type, ignoring compression extensions.

        Args:
            file_path: The file path to analyze

        Returns:
            GenomicsFileType enum value for the base file type, None if not detected
        """
        if not file_path:
            return None

        # Remove compression extensions to get the base file type
        path_lower = file_path.lower()

        # Remove common compression extensions
        for comp_ext in ['.gz', '.bz2', '.xz', '.lz4', '.zst']:
            if path_lower.endswith(comp_ext):
                path_lower = path_lower[: -len(comp_ext)]
                break

        # Now detect the file type from the base extension
        return cls.detect_file_type(path_lower)

    @classmethod
    def is_genomics_file(cls, file_path: str) -> bool:
        """Check if a file is a recognized genomics file type.

        Args:
            file_path: The file path to check

        Returns:
            True if the file is a recognized genomics file type, False otherwise
        """
        return cls.detect_file_type(file_path) is not None

    @classmethod
    def get_file_category(cls, file_type: GenomicsFileType) -> str:
        """Get the category of a genomics file type.

        Args:
            file_type: The GenomicsFileType to categorize

        Returns:
            String category name
        """
        sequence_types = {GenomicsFileType.FASTQ, GenomicsFileType.FASTA, GenomicsFileType.FNA}
        alignment_types = {GenomicsFileType.BAM, GenomicsFileType.CRAM, GenomicsFileType.SAM}
        variant_types = {GenomicsFileType.VCF, GenomicsFileType.GVCF, GenomicsFileType.BCF}
        annotation_types = {GenomicsFileType.BED, GenomicsFileType.GFF}
        index_types = {
            GenomicsFileType.BAI,
            GenomicsFileType.CRAI,
            GenomicsFileType.FAI,
            GenomicsFileType.DICT,
            GenomicsFileType.TBI,
            GenomicsFileType.CSI,
        }
        bwa_index_types = {
            GenomicsFileType.BWA_AMB,
            GenomicsFileType.BWA_ANN,
            GenomicsFileType.BWA_BWT,
            GenomicsFileType.BWA_PAC,
            GenomicsFileType.BWA_SA,
        }

        if file_type in sequence_types:
            return 'sequence'
        elif file_type in alignment_types:
            return 'alignment'
        elif file_type in variant_types:
            return 'variant'
        elif file_type in annotation_types:
            return 'annotation'
        elif file_type in index_types:
            return 'index'
        elif file_type in bwa_index_types:
            return 'bwa_index'
        else:
            return 'unknown'

    @classmethod
    def matches_file_type_filter(cls, file_path: str, file_type_filter: str) -> bool:
        """Check if a file matches a file type filter.

        Args:
            file_path: The file path to check
            file_type_filter: The file type filter (can be specific type or category)

        Returns:
            True if the file matches the filter, False otherwise
        """
        detected_type = cls.detect_file_type(file_path)
        if not detected_type:
            return False

        filter_lower = file_type_filter.lower()

        # Check for exact type match
        if detected_type.value.lower() == filter_lower:
            return True

        # Check for category match
        category = cls.get_file_category(detected_type)
        if category.lower() == filter_lower:
            return True

        # Check for common aliases
        aliases = {
            'fq': GenomicsFileType.FASTQ,
            'fa': GenomicsFileType.FASTA,
            'reference': GenomicsFileType.FASTA,
            'reads': GenomicsFileType.FASTQ,
            'variants': 'variant',
            'annotations': 'annotation',
            'indexes': 'index',
        }

        if filter_lower in aliases:
            alias_value = aliases[filter_lower]
            if isinstance(alias_value, GenomicsFileType):
                return detected_type == alias_value
            else:
                return category.lower() == alias_value.lower()

        return False
