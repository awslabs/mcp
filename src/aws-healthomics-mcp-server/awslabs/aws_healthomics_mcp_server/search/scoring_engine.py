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

"""Scoring engine for genomics file search results."""

from ..models import GenomicsFile, GenomicsFileType
from .pattern_matcher import PatternMatcher
from typing import Any, Dict, List, Optional, Tuple


class ScoringEngine:
    """Calculates relevance scores for genomics files based on multiple weighted factors."""

    def __init__(self):
        """Initialize the scoring engine with default weights."""
        self.pattern_matcher = PatternMatcher()

        # Scoring weights (must sum to 1.0)
        self.weights = {
            'pattern_match': 0.4,  # 40% - How well patterns match
            'file_type_relevance': 0.3,  # 30% - File type relevance
            'associated_files': 0.2,  # 20% - Bonus for associated files
            'storage_accessibility': 0.1,  # 10% - Storage tier penalty/bonus
        }

        # Storage class scoring multipliers
        self.storage_multipliers = {
            'STANDARD': 1.0,
            'STANDARD_IA': 0.95,
            'ONEZONE_IA': 0.9,
            'REDUCED_REDUNDANCY': 0.85,
            'GLACIER': 0.7,
            'DEEP_ARCHIVE': 0.6,
            'INTELLIGENT_TIERING': 0.95,
        }

        # File type relationships for relevance scoring
        self.file_type_relationships = {
            GenomicsFileType.FASTQ: {
                'primary': [GenomicsFileType.FASTQ],
                'related': [],
                'indexes': [],
            },
            GenomicsFileType.FASTA: {
                'primary': [GenomicsFileType.FASTA, GenomicsFileType.FNA],
                'related': [
                    GenomicsFileType.BWA_AMB,
                    GenomicsFileType.BWA_ANN,
                    GenomicsFileType.BWA_BWT,
                    GenomicsFileType.BWA_PAC,
                    GenomicsFileType.BWA_SA,
                ],
                'indexes': [GenomicsFileType.FAI, GenomicsFileType.DICT],
            },
            GenomicsFileType.BAM: {
                'primary': [GenomicsFileType.BAM],
                'related': [GenomicsFileType.SAM, GenomicsFileType.CRAM],
                'indexes': [GenomicsFileType.BAI],
            },
            GenomicsFileType.CRAM: {
                'primary': [GenomicsFileType.CRAM],
                'related': [GenomicsFileType.BAM, GenomicsFileType.SAM],
                'indexes': [GenomicsFileType.CRAI],
            },
            GenomicsFileType.VCF: {
                'primary': [GenomicsFileType.VCF, GenomicsFileType.GVCF],
                'related': [GenomicsFileType.BCF],
                'indexes': [GenomicsFileType.TBI, GenomicsFileType.CSI],
            },
        }

    def calculate_score(
        self,
        file: GenomicsFile,
        search_terms: List[str],
        file_type_filter: Optional[str] = None,
        associated_files: Optional[List[GenomicsFile]] = None,
    ) -> Tuple[float, List[str]]:
        """Calculate comprehensive relevance score for a genomics file.

        Args:
            file: The genomics file to score
            search_terms: List of search terms to match against
            file_type_filter: Optional file type filter from search request
            associated_files: List of associated files (for bonus scoring)

        Returns:
            Tuple of (final_score, scoring_reasons)
        """
        if associated_files is None:
            associated_files = []

        scoring_reasons = []

        # 1. Pattern Match Score (40% weight)
        pattern_score, pattern_reasons = self._calculate_pattern_score(file, search_terms)
        scoring_reasons.extend(pattern_reasons)

        # 2. File Type Relevance Score (30% weight)
        type_score, type_reasons = self._calculate_file_type_score(file, file_type_filter)
        scoring_reasons.extend(type_reasons)

        # 3. Associated Files Bonus (20% weight)
        association_score, association_reasons = self._calculate_association_score(
            file, associated_files
        )
        scoring_reasons.extend(association_reasons)

        # 4. Storage Accessibility Score (10% weight)
        storage_score, storage_reasons = self._calculate_storage_score(file)
        scoring_reasons.extend(storage_reasons)

        # Calculate weighted final score
        final_score = (
            pattern_score * self.weights['pattern_match']
            + type_score * self.weights['file_type_relevance']
            + association_score * self.weights['associated_files']
            + storage_score * self.weights['storage_accessibility']
        )

        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, final_score))

        # Add overall score explanation
        scoring_reasons.insert(0, f'Overall relevance score: {final_score:.3f}')

        return final_score, scoring_reasons

    def _calculate_pattern_score(
        self, file: GenomicsFile, search_terms: List[str]
    ) -> Tuple[float, List[str]]:
        """Calculate score based on pattern matching against file path, tags, and metadata."""
        if not search_terms:
            return 0.5, ['No search terms provided - neutral pattern score']

        # Match against file path
        path_score, path_reasons = self.pattern_matcher.match_file_path(file.path, search_terms)

        # Match against tags
        tag_score, tag_reasons = self.pattern_matcher.match_tags(file.tags, search_terms)

        # Match against metadata (especially important for HealthOmics files)
        metadata_score, metadata_reasons = self._match_metadata(file.metadata, search_terms)

        # Take the best score among path, tag, and metadata matches
        best_score = max(path_score, tag_score, metadata_score)

        if best_score == metadata_score and metadata_score > 0:
            return metadata_score, [f'Metadata matching: {reason}' for reason in metadata_reasons]
        elif best_score == path_score and path_score > 0:
            return path_score, [f'Path matching: {reason}' for reason in path_reasons]
        elif best_score == tag_score and tag_score > 0:
            return tag_score, [f'Tag matching: {reason}' for reason in tag_reasons]
        else:
            return 0.0, ['No pattern matches found']

    def _calculate_file_type_score(
        self, file: GenomicsFile, file_type_filter: Optional[str]
    ) -> Tuple[float, List[str]]:
        """Calculate score based on file type relevance."""
        if not file_type_filter:
            return 0.8, ['No file type filter - neutral type score']

        try:
            target_type = GenomicsFileType(file_type_filter.lower())
        except ValueError:
            return 0.5, [f"Unknown file type filter '{file_type_filter}' - neutral score"]

        # Exact match
        if file.file_type == target_type:
            return 1.0, [f'Exact file type match: {file.file_type.value}']

        # Check if it's a related type
        relationships = self.file_type_relationships.get(target_type, {})

        if file.file_type in relationships.get('related', []):
            return 0.8, [
                f'Related file type: {file.file_type.value} (target: {target_type.value})'
            ]

        if file.file_type in relationships.get('indexes', []):
            return 0.7, [f'Index file type: {file.file_type.value} (target: {target_type.value})']

        # Check reverse relationships (if target is an index of this file type)
        for file_type, relations in self.file_type_relationships.items():
            if file.file_type == file_type and target_type in relations.get('indexes', []):
                return 0.7, [f'Target is index of this file type: {target_type.value}']

        return 0.3, [f'Unrelated file type: {file.file_type.value} (target: {target_type.value})']

    def _calculate_association_score(
        self, file: GenomicsFile, associated_files: List[GenomicsFile]
    ) -> Tuple[float, List[str]]:
        """Calculate bonus score based on associated files."""
        if not associated_files:
            return 0.5, ['No associated files - neutral association score']

        # Base score starts at 0.5 (neutral)
        base_score = 0.5

        # Add bonus for each associated file (up to 0.5 total bonus)
        association_bonus = min(0.5, len(associated_files) * 0.1)

        # Additional bonus for complete file sets
        complete_set_bonus = 0.0
        if self._is_complete_file_set(file, associated_files):
            complete_set_bonus = 0.2

        final_score = min(1.0, base_score + association_bonus + complete_set_bonus)

        reasons = [
            f'Associated files bonus: +{association_bonus:.2f} for {len(associated_files)} files'
        ]

        if complete_set_bonus > 0:
            reasons.append(f'Complete file set bonus: +{complete_set_bonus:.2f}')

        return final_score, reasons

    def _calculate_storage_score(self, file: GenomicsFile) -> Tuple[float, List[str]]:
        """Calculate score based on storage accessibility."""
        storage_class = file.storage_class.upper()
        multiplier = self.storage_multipliers.get(
            storage_class, 0.8
        )  # Default for unknown classes

        if multiplier == 1.0:
            return 1.0, [f'Standard storage class: {storage_class}']
        elif multiplier >= 0.9:
            return multiplier, [
                f'High accessibility storage: {storage_class} (score: {multiplier})'
            ]
        elif multiplier >= 0.8:
            return multiplier, [
                f'Medium accessibility storage: {storage_class} (score: {multiplier})'
            ]
        else:
            return multiplier, [
                f'Low accessibility storage: {storage_class} (score: {multiplier})'
            ]

    def _is_complete_file_set(
        self, primary_file: GenomicsFile, associated_files: List[GenomicsFile]
    ) -> bool:
        """Check if the file set represents a complete genomics file collection."""
        file_types = {f.file_type for f in associated_files}

        # Check for complete BAM set (BAM + BAI)
        if primary_file.file_type == GenomicsFileType.BAM and GenomicsFileType.BAI in file_types:
            return True

        # Check for complete CRAM set (CRAM + CRAI)
        if primary_file.file_type == GenomicsFileType.CRAM and GenomicsFileType.CRAI in file_types:
            return True

        # Check for complete FASTA set (FASTA + FAI + DICT)
        if (
            primary_file.file_type in [GenomicsFileType.FASTA, GenomicsFileType.FNA]
            and GenomicsFileType.FAI in file_types
            and GenomicsFileType.DICT in file_types
        ):
            return True

        # Check for FASTQ pairs (R1 + R2)
        if primary_file.file_type == GenomicsFileType.FASTQ:
            return self._has_fastq_pair(primary_file, associated_files)

        return False

    def _has_fastq_pair(
        self, primary_file: GenomicsFile, associated_files: List[GenomicsFile]
    ) -> bool:
        """Check if a FASTQ file has its R1/R2 pair in the associated files.

        Args:
            primary_file: The primary FASTQ file to check
            associated_files: List of associated files to search for the pair

        Returns:
            True if a matching pair is found, False otherwise
        """
        if primary_file.file_type != GenomicsFileType.FASTQ:
            return False

        # Extract filename from path
        primary_filename = primary_file.path.split('/')[-1]

        # Common R1/R2 patterns to check
        r1_patterns = ['_R1_', '_R1.', 'R1_', 'R1.', '_1_', '_1.']
        r2_patterns = ['_R2_', '_R2.', 'R2_', 'R2.', '_2_', '_2.']

        # Check if primary file contains R1 pattern and look for R2 pair
        for r1_pattern in r1_patterns:
            if r1_pattern in primary_filename:
                # Generate expected R2 filename by replacing R1 with R2
                expected_r2_filename = primary_filename.replace(
                    r1_pattern, r1_pattern.replace('1', '2')
                )

                # Check if any associated file matches the expected R2 filename
                for assoc_file in associated_files:
                    if assoc_file.file_type == GenomicsFileType.FASTQ and assoc_file.path.endswith(
                        expected_r2_filename
                    ):
                        return True

        # Check if primary file contains R2 pattern and look for R1 pair
        for r2_pattern in r2_patterns:
            if r2_pattern in primary_filename:
                # Generate expected R1 filename by replacing R2 with R1
                expected_r1_filename = primary_filename.replace(
                    r2_pattern, r2_pattern.replace('2', '1')
                )

                # Check if any associated file matches the expected R1 filename
                for assoc_file in associated_files:
                    if assoc_file.file_type == GenomicsFileType.FASTQ and assoc_file.path.endswith(
                        expected_r1_filename
                    ):
                        return True

        return False

    def rank_results(
        self, scored_results: List[Tuple[GenomicsFile, float, List[str]]]
    ) -> List[Tuple[GenomicsFile, float, List[str]]]:
        """Rank results by score in descending order.

        Args:
            scored_results: List of (file, score, reasons) tuples

        Returns:
            Sorted list of results by score (highest first)
        """
        return sorted(scored_results, key=lambda x: x[1], reverse=True)

    def _match_metadata(
        self, metadata: Dict[str, Any], search_terms: List[str]
    ) -> Tuple[float, List[str]]:
        """Match patterns against HealthOmics file metadata.

        Args:
            metadata: Dictionary of metadata key-value pairs
            search_terms: List of search terms to match against

        Returns:
            Tuple of (score, match_reasons)
        """
        if not search_terms or not metadata:
            return 0.0, []

        max_score = 0.0
        all_match_reasons = []

        # Check specific metadata fields that are likely to contain searchable names
        searchable_fields = [
            'reference_name',
            'read_set_name',
            'name',
            'description',
            'subject_id',
            'sample_id',
            'store_name',
            'store_description',
        ]

        for field in searchable_fields:
            if field in metadata and isinstance(metadata[field], str) and metadata[field]:
                field_value = metadata[field]
                score, reasons = self.pattern_matcher.calculate_match_score(
                    field_value, search_terms
                )
                if score > 0:
                    max_score = max(max_score, score)
                    # Add all matching reasons for this field
                    field_reasons = [f'{field} "{field_value}": {reason}' for reason in reasons]
                    all_match_reasons.extend(field_reasons)

        # Also check all other string metadata values
        for key, value in metadata.items():
            if key not in searchable_fields and isinstance(value, str) and value:
                score, reasons = self.pattern_matcher.calculate_match_score(value, search_terms)
                if score > 0:
                    max_score = max(max_score, score)
                    # Add all matching reasons for this field
                    field_reasons = [f'{key} "{value}": {reason}' for reason in reasons]
                    all_match_reasons.extend(field_reasons)

        return max_score, all_match_reasons
