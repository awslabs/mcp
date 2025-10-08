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

"""File association detection engine for genomics files."""

import re
from awslabs.aws_healthomics_mcp_server.models import (
    FileGroup,
    GenomicsFile,
)
from pathlib import Path
from typing import Dict, List, Set


class FileAssociationEngine:
    """Engine for detecting and grouping associated genomics files."""

    # Association patterns: (primary_pattern, associated_pattern, group_type)
    ASSOCIATION_PATTERNS = [
        # BAM index patterns
        (r'(.+)\.bam$', r'\1.bam.bai', 'bam_index'),
        (r'(.+)\.bam$', r'\1.bai', 'bam_index'),
        # CRAM index patterns
        (r'(.+)\.cram$', r'\1.cram.crai', 'cram_index'),
        (r'(.+)\.cram$', r'\1.crai', 'cram_index'),
        # FASTQ pair patterns (R1/R2)
        (r'(.+)_R1\.fastq(\.gz|\.bz2)?$', r'\1_R2.fastq\2', 'fastq_pair'),
        (r'(.+)_1\.fastq(\.gz|\.bz2)?$', r'\1_2.fastq\2', 'fastq_pair'),
        (r'(.+)\.R1\.fastq(\.gz|\.bz2)?$', r'\1.R2.fastq\2', 'fastq_pair'),
        (r'(.+)\.1\.fastq(\.gz|\.bz2)?$', r'\1.2.fastq\2', 'fastq_pair'),
        # FASTA index patterns
        (r'(.+)\.fasta$', r'\1.fasta.fai', 'fasta_index'),
        (r'(.+)\.fasta$', r'\1.fai', 'fasta_index'),
        (r'(.+)\.fasta$', r'\1.dict', 'fasta_dict'),
        (r'(.+)\.fa$', r'\1.fa.fai', 'fasta_index'),
        (r'(.+)\.fa$', r'\1.fai', 'fasta_index'),
        (r'(.+)\.fa$', r'\1.dict', 'fasta_dict'),
        (r'(.+)\.fna$', r'\1.fna.fai', 'fasta_index'),
        (r'(.+)\.fna$', r'\1.fai', 'fasta_index'),
        (r'(.+)\.fna$', r'\1.dict', 'fasta_dict'),
        # VCF index patterns
        (r'(.+)\.vcf(\.gz)?$', r'\1.vcf\2.tbi', 'vcf_index'),
        (r'(.+)\.vcf(\.gz)?$', r'\1.vcf\2.csi', 'vcf_index'),
        (r'(.+)\.gvcf(\.gz)?$', r'\1.gvcf\2.tbi', 'gvcf_index'),
        (r'(.+)\.gvcf(\.gz)?$', r'\1.gvcf\2.csi', 'gvcf_index'),
        (r'(.+)\.bcf$', r'\1.bcf.csi', 'bcf_index'),
    ]

    # BWA index collection patterns - all files that should be grouped together
    BWA_INDEX_EXTENSIONS = ['.amb', '.ann', '.bwt', '.pac', '.sa']

    def __init__(self):
        """Initialize the file association engine."""
        pass

    def find_associations(self, files: List[GenomicsFile]) -> List[FileGroup]:
        """Find file associations and group related files together.

        Args:
            files: List of genomics files to analyze

        Returns:
            List of FileGroup objects with associated files grouped together
        """
        # Create a mapping of file paths to GenomicsFile objects for quick lookup
        file_map = {file.path: file for file in files}

        # Track which files have been grouped to avoid duplicates
        grouped_files: Set[str] = set()
        file_groups: List[FileGroup] = []

        # First, handle BWA index collections
        bwa_groups = self._find_bwa_index_groups(files, file_map)
        for group in bwa_groups:
            file_groups.append(group)
            grouped_files.update([f.path for f in [group.primary_file] + group.associated_files])

        # Then handle other association patterns
        for file in files:
            if file.path in grouped_files:
                continue

            associated_files = self._find_associated_files(file, file_map)
            if associated_files:
                # Determine the group type based on the associations found
                group_type = self._determine_group_type(file, associated_files)

                file_group = FileGroup(
                    primary_file=file, associated_files=associated_files, group_type=group_type
                )
                file_groups.append(file_group)

                # Mark all files in this group as processed
                grouped_files.add(file.path)
                grouped_files.update([f.path for f in associated_files])

        # Add remaining ungrouped files as single-file groups
        for file in files:
            if file.path not in grouped_files:
                file_group = FileGroup(
                    primary_file=file, associated_files=[], group_type='single_file'
                )
                file_groups.append(file_group)

        return file_groups

    def _find_associated_files(
        self, primary_file: GenomicsFile, file_map: Dict[str, GenomicsFile]
    ) -> List[GenomicsFile]:
        """Find files associated with the given primary file."""
        associated_files = []
        primary_path = primary_file.path

        # Iterate through original patterns to maintain correct pairing
        for orig_primary, orig_assoc, group_type in self.ASSOCIATION_PATTERNS:
            try:
                # Check if the primary pattern matches
                if re.search(orig_primary, primary_path, re.IGNORECASE):
                    # Generate the expected associated file path
                    expected_assoc_path = re.sub(
                        orig_primary, orig_assoc, primary_path, flags=re.IGNORECASE
                    )

                    # Check if the associated file exists in our file map
                    if expected_assoc_path in file_map and expected_assoc_path != primary_path:
                        associated_files.append(file_map[expected_assoc_path])
            except re.error:
                # Skip if regex substitution fails
                continue

        return associated_files

    def _find_bwa_index_groups(
        self, files: List[GenomicsFile], file_map: Dict[str, GenomicsFile]
    ) -> List[FileGroup]:
        """Find BWA index collections and group them together."""
        bwa_groups = []

        # Group files by their base name (without BWA extension)
        bwa_base_groups: Dict[str, List[GenomicsFile]] = {}

        for file in files:
            file_path = Path(file.path)

            # Check if this is a BWA index file
            for ext in self.BWA_INDEX_EXTENSIONS:
                if file_path.name.endswith(ext):
                    # Extract the base name (remove BWA extension)
                    base_name = str(file_path).replace(ext, '')

                    if base_name not in bwa_base_groups:
                        bwa_base_groups[base_name] = []
                    bwa_base_groups[base_name].append(file)
                    break

        # Create groups for BWA index collections (need at least 2 files)
        for base_name, bwa_files in bwa_base_groups.items():
            if len(bwa_files) >= 2:
                # Sort files to have a consistent primary file (e.g., .bwt file as primary)
                bwa_files.sort(key=lambda f: f.path)

                # Use the first file as primary, rest as associated
                primary_file = bwa_files[0]
                associated_files = bwa_files[1:]

                bwa_group = FileGroup(
                    primary_file=primary_file,
                    associated_files=associated_files,
                    group_type='bwa_index_collection',
                )
                bwa_groups.append(bwa_group)

        return bwa_groups

    def _determine_group_type(
        self, primary_file: GenomicsFile, associated_files: List[GenomicsFile]
    ) -> str:
        """Determine the group type based on the primary file and its associations."""
        primary_path = primary_file.path.lower()

        # Check file extensions to determine group type
        if primary_path.endswith('.bam'):
            return 'bam_index'
        elif primary_path.endswith('.cram'):
            return 'cram_index'
        elif 'fastq' in primary_path and any(
            '_R2' in f.path or '_2' in f.path for f in associated_files
        ):
            return 'fastq_pair'
        elif any(ext in primary_path for ext in ['.fasta', '.fa', '.fna']):
            # Check if associated files include dict files
            if any('.dict' in f.path for f in associated_files):
                return 'fasta_dict'
            else:
                return 'fasta_index'
        elif '.vcf' in primary_path:
            return 'vcf_index'
        elif '.gvcf' in primary_path:
            return 'gvcf_index'
        elif primary_path.endswith('.bcf'):
            return 'bcf_index'

        return 'unknown_association'

    def get_association_score_bonus(self, file_group: FileGroup) -> float:
        """Calculate a score bonus based on the number and type of associated files.

        Args:
            file_group: The file group to score

        Returns:
            Score bonus (0.0 to 1.0)
        """
        if not file_group.associated_files:
            return 0.0

        base_bonus = 0.1 * len(file_group.associated_files)

        # Additional bonus for complete file sets
        group_type_bonuses = {
            'fastq_pair': 0.2,  # Complete paired-end reads
            'bwa_index_collection': 0.3,  # Complete BWA index
            'fasta_dict': 0.25,  # FASTA with both index and dict
        }

        type_bonus = group_type_bonuses.get(file_group.group_type, 0.1)

        # Cap the total bonus at 0.5
        return min(base_bonus + type_bonus, 0.5)
