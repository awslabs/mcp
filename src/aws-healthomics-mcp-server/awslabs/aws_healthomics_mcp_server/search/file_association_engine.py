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
    get_s3_file_associations,
)
from pathlib import Path
from typing import Dict, List, Pattern, Set, Tuple


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
        # BWA index patterns (regular and 64-bit variants)
        (r'(.+\.(fasta|fa|fna))$', r'\1.amb', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.ann', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.bwt', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.pac', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.sa', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.64.amb', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.64.ann', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.64.bwt', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.64.pac', 'bwa_index'),
        (r'(.+\.(fasta|fa|fna))$', r'\1.64.sa', 'bwa_index'),
    ]

    # BWA index collection patterns - all files that should be grouped together
    # Includes both regular and 64-bit variants
    BWA_INDEX_EXTENSIONS = [
        '.amb',
        '.ann',
        '.bwt',
        '.pac',
        '.sa',
        '.64.amb',
        '.64.ann',
        '.64.bwt',
        '.64.pac',
        '.64.sa',
    ]

    def __init__(self):
        """Initialize the file association engine with pre-compiled regex patterns.

        Pre-compiling patterns significantly improves performance when processing
        large numbers of files, as it avoids repeated regex compilation overhead.
        """
        # Pre-compile all regex patterns for better performance
        self._compiled_patterns: List[Tuple[Pattern[str], str, str]] = [
            (re.compile(primary_pattern, re.IGNORECASE), assoc_pattern, group_type)
            for primary_pattern, assoc_pattern, group_type in self.ASSOCIATION_PATTERNS
        ]

        # Build extension-based lookup table for fast pattern filtering
        self._extension_pattern_map = self._build_extension_pattern_map()

    def _build_extension_pattern_map(self) -> Dict[str, List[int]]:
        """Build a lookup table mapping file extensions to relevant pattern indices.

        This allows us to skip irrelevant patterns when processing files,
        further improving performance by reducing the number of regex operations.

        Returns:
            Dictionary mapping file extensions to lists of pattern indices
        """
        ext_map: Dict[str, List[int]] = {}

        # Define which extensions are relevant for each pattern
        # This is based on the primary pattern in ASSOCIATION_PATTERNS
        extension_hints = {
            '.bam': ['bam'],
            '.cram': ['cram'],
            '.fastq': ['fastq'],
            '.fastq.gz': ['fastq'],
            '.fastq.bz2': ['fastq'],
            '.fq': ['fastq'],
            '.fq.gz': ['fastq'],
            '.fasta': ['fasta'],
            '.fa': ['fasta'],
            '.fna': ['fasta'],
            '.vcf': ['vcf'],
            '.vcf.gz': ['vcf'],
            '.gvcf': ['gvcf'],
            '.gvcf.gz': ['gvcf'],
            '.bcf': ['bcf'],
        }

        # Map pattern keywords to indices
        for idx, (_, _, group_type) in enumerate(self.ASSOCIATION_PATTERNS):
            for ext, keywords in extension_hints.items():
                # Check if any keyword matches the group type
                if any(keyword in group_type for keyword in keywords):
                    if ext not in ext_map:
                        ext_map[ext] = []
                    ext_map[ext].append(idx)

        return ext_map

    def _get_relevant_pattern_indices(self, file_path: str) -> List[int]:
        """Get indices of patterns relevant to the given file path.

        Args:
            file_path: Path to the file

        Returns:
            List of pattern indices to check, or all indices if no optimization applies
        """
        file_path_lower = file_path.lower()

        # Check for matching extensions
        for ext, pattern_indices in self._extension_pattern_map.items():
            if ext in file_path_lower:
                return pattern_indices

        # If no specific extension match, return all patterns
        return list(range(len(self._compiled_patterns)))

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

        # Handle HealthOmics-specific associations
        healthomics_groups = self._find_healthomics_associations(files, file_map)
        for group in healthomics_groups:
            file_groups.append(group)
            grouped_files.update([f.path for f in [group.primary_file] + group.associated_files])

        # Handle HealthOmics sequence store associations (BAM/CRAM index files)
        sequence_store_groups = self._find_sequence_store_associations(files, file_map)
        for group in sequence_store_groups:
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

        # For S3 files, use the centralized S3File association logic first
        if primary_file.path.startswith('s3://') and primary_file.s3_file:
            s3_associations = get_s3_file_associations(primary_file.s3_file)
            for s3_assoc in s3_associations:
                assoc_path = s3_assoc.uri
                if assoc_path in file_map and assoc_path != primary_file.path:
                    associated_files.append(file_map[assoc_path])

        # Fall back to regex-based pattern matching for additional associations
        # or for non-S3 files (like HealthOmics access points)
        primary_path = primary_file.path

        # Get relevant pattern indices for optimization
        relevant_indices = self._get_relevant_pattern_indices(primary_path)

        for pattern_idx in relevant_indices:
            compiled_primary, assoc_pattern, group_type = self._compiled_patterns[pattern_idx]
            try:
                # Check if the primary pattern matches (using pre-compiled pattern)
                if compiled_primary.search(primary_path):
                    # Generate the expected associated file path
                    expected_assoc_path = compiled_primary.sub(assoc_pattern, primary_path)

                    # Check if the associated file exists in our file map
                    if expected_assoc_path in file_map and expected_assoc_path != primary_path:
                        # Avoid duplicates from S3File associations
                        if not any(af.path == expected_assoc_path for af in associated_files):
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
            file_name = file_path.name

            # Check if this is a BWA index file and extract base name
            base_name = None
            for ext in self.BWA_INDEX_EXTENSIONS:
                if file_name.endswith(ext):
                    # Extract the base name by removing the BWA extension from the end
                    base_name = str(file_path)[: -len(ext)]
                    break

            if base_name:
                # Normalize base name to handle both regular and 64-bit variants
                # For files like "ref.fasta.64.amb" and "ref.fasta.amb",
                # we want them to group under "ref.fasta"
                normalized_base = self._normalize_bwa_base_name(base_name)

                if normalized_base not in bwa_base_groups:
                    bwa_base_groups[normalized_base] = []
                bwa_base_groups[normalized_base].append(file)

        # Create groups for BWA index collections (need at least 2 files)
        for base_name, bwa_files in bwa_base_groups.items():
            if len(bwa_files) >= 2:
                # Sort files to have a consistent primary file
                # Prioritize the original FASTA file if present, otherwise use .bwt file
                bwa_files.sort(
                    key=lambda f: (
                        0
                        if any(f.path.endswith(ext) for ext in ['.fasta', '.fa', '.fna'])
                        else 1
                        if '.bwt' in f.path
                        else 2
                    )
                )

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

    def _normalize_bwa_base_name(self, base_name: str) -> str:
        """Normalize BWA base name to handle both regular and 64-bit variants.

        For example:
        - "ref.fasta" -> "ref.fasta"
        - "ref.fasta.64" -> "ref.fasta"
        - "/path/to/ref.fasta.64" -> "/path/to/ref.fasta"
        """
        # Remove trailing .64 if present (for 64-bit BWA indexes)
        if base_name.endswith('.64'):
            return base_name[:-3]
        return base_name

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
            # Check if associated files include BWA index files
            has_bwa_indexes = any(
                any(f.path.endswith(bwa_ext) for bwa_ext in self.BWA_INDEX_EXTENSIONS)
                for f in associated_files
            )
            # Check if associated files include dict files
            has_dict = any('.dict' in f.path for f in associated_files)

            if has_bwa_indexes and has_dict:
                return 'fasta_bwa_dict'
            elif has_bwa_indexes:
                return 'fasta_bwa_index'
            elif has_dict:
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
            'fasta_bwa_index': 0.35,  # FASTA with BWA indexes
            'fasta_bwa_dict': 0.4,  # FASTA with BWA indexes and dict
        }

        type_bonus = group_type_bonuses.get(file_group.group_type, 0.1)

        # Cap the total bonus at 0.5
        return min(base_bonus + type_bonus, 0.5)

    def _find_healthomics_associations(
        self, files: List[GenomicsFile], file_map: Dict[str, GenomicsFile]
    ) -> List[FileGroup]:
        """Find HealthOmics-specific file associations.

        HealthOmics files have specific URI patterns and associations that don't follow
        traditional file extension patterns.

        Args:
            files: List of genomics files to analyze
            file_map: Dictionary mapping file paths to GenomicsFile objects

        Returns:
            List of FileGroup objects for HealthOmics associations
        """
        healthomics_groups = []

        # Group HealthOmics files by their base URI (without /source or /index)
        healthomics_base_groups: Dict[str, Dict[str, GenomicsFile]] = {}

        for file in files:
            # Check if this is a HealthOmics URI
            if file.path.startswith('omics://') and file.source_system == 'reference_store':
                # Extract the base URI (everything before /source or /index)
                if '/source' in file.path:
                    base_uri = file.path.replace('/source', '')
                    file_type = 'source'
                elif '/index' in file.path:
                    base_uri = file.path.replace('/index', '')
                    file_type = 'index'
                else:
                    continue  # Skip if not source or index

                if base_uri not in healthomics_base_groups:
                    healthomics_base_groups[base_uri] = {}

                healthomics_base_groups[base_uri][file_type] = file

        # Create file groups for HealthOmics references that have both source and index
        for base_uri, file_types in healthomics_base_groups.items():
            if 'source' in file_types and 'index' in file_types:
                primary_file = file_types['source']
                associated_files = [file_types['index']]

                healthomics_group = FileGroup(
                    primary_file=primary_file,
                    associated_files=associated_files,
                    group_type='healthomics_reference',
                )
                healthomics_groups.append(healthomics_group)

        return healthomics_groups

    def _find_sequence_store_associations(
        self, files: List[GenomicsFile], file_map: Dict[str, GenomicsFile]
    ) -> List[FileGroup]:
        """Find HealthOmics sequence store file associations.

        For sequence stores, this handles:
        1. Multi-source read sets (source1, source2, etc.) - paired-end FASTQ files
        2. Index files (BAM/CRAM index files)

        Args:
            files: List of genomics files to analyze
            file_map: Dictionary mapping file paths to GenomicsFile objects

        Returns:
            List of FileGroup objects for sequence store associations
        """
        sequence_store_groups = []

        for file in files:
            # Skip if not a sequence store file
            if not (file.path.startswith('omics://') and file.source_system == 'sequence_store'):
                continue

            # Skip if this is a reference store file with index info
            if file.metadata.get('_healthomics_index_info') is not None:
                continue

            associated_files = []

            # Handle multi-source read sets (source2, source3, etc.)
            multi_source_info = file.metadata.get('_healthomics_multi_source_info')
            if multi_source_info:
                files_info = multi_source_info['files']

                # Create associated files for source2, source3, etc.
                for source_key in sorted(files_info.keys()):
                    if source_key.startswith('source') and source_key != 'source1':
                        source_info = files_info[source_key]

                        # Create URI for this source
                        source_uri = f'omics://{multi_source_info["account_id"]}.storage.{multi_source_info["region"]}.amazonaws.com/{multi_source_info["store_id"]}/readSet/{multi_source_info["read_set_id"]}/{source_key}'

                        # Create virtual GenomicsFile for this source
                        source_file = GenomicsFile(
                            path=source_uri,
                            file_type=multi_source_info['file_type'],
                            size_bytes=source_info.get('contentLength', 0),
                            storage_class=multi_source_info['storage_class'],
                            last_modified=multi_source_info['creation_time'],
                            tags=multi_source_info['tags'],
                            source_system='sequence_store',
                            metadata={
                                **multi_source_info['metadata_base'],
                                'source_number': source_key,
                                'is_associated_source': True,
                                'primary_file_uri': file.path,
                                's3_access_uri': source_info.get('s3Access', {}).get('s3Uri', ''),
                                'omics_uri': source_uri,
                            },
                        )
                        associated_files.append(source_file)

            # Handle index files (BAM/CRAM)
            if 'files' in file.metadata:
                files_info = file.metadata['files']

                if 'index' in files_info:
                    index_info = files_info['index']

                    # Get connection info from metadata or parse from URI
                    account_id = file.metadata.get('account_id')
                    region = file.metadata.get('region')
                    if not account_id or not region:
                        # Parse from URI as fallback
                        account_id = file.path.split('.')[0].split('//')[1]
                        region = file.path.split('.')[2]

                    store_id = file.metadata.get('store_id', '')
                    read_set_id = file.metadata.get('read_set_id', '')

                    index_uri = f'omics://{account_id}.storage.{region}.amazonaws.com/{store_id}/readSet/{read_set_id}/index'

                    # Determine index file type based on primary file type
                    if file.file_type.value == 'bam':
                        from awslabs.aws_healthomics_mcp_server.models import GenomicsFileType

                        index_file_type = GenomicsFileType.BAI
                    elif file.file_type.value == 'cram':
                        from awslabs.aws_healthomics_mcp_server.models import GenomicsFileType

                        index_file_type = GenomicsFileType.CRAI
                    else:
                        index_file_type = None  # No index for other file types

                    if index_file_type:
                        # Create virtual index file
                        index_file = GenomicsFile(
                            path=index_uri,
                            file_type=index_file_type,
                            size_bytes=index_info.get('contentLength', 0),
                            storage_class=file.storage_class,
                            last_modified=file.last_modified,
                            tags=file.tags,  # Inherit tags from primary file
                            source_system='sequence_store',
                            metadata={
                                **file.metadata,  # Inherit metadata from primary file
                                'is_index_file': True,
                                'primary_file_uri': file.path,
                                's3_access_uri': index_info.get('s3Access', {}).get('s3Uri', ''),
                            },
                        )
                        associated_files.append(index_file)

            # Create file group if we have associated files
            if associated_files:
                # Determine group type based on what we found
                has_sources = any(
                    hasattr(f, 'metadata') and f.metadata.get('is_associated_source')
                    for f in associated_files
                )
                has_index = any(
                    hasattr(f, 'metadata') and f.metadata.get('is_index_file')
                    for f in associated_files
                )

                if has_sources and has_index:
                    group_type = 'sequence_store_multi_source_with_index'
                elif has_sources:
                    group_type = 'sequence_store_multi_source'
                else:
                    group_type = 'sequence_store_index'

                sequence_store_group = FileGroup(
                    primary_file=file,
                    associated_files=associated_files,
                    group_type=group_type,
                )
                sequence_store_groups.append(sequence_store_group)

        return sequence_store_groups
