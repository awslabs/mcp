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

"""JSON response builder for genomics file search results."""

from awslabs.aws_healthomics_mcp_server.consts import (
    MATCH_QUALITY_EXCELLENT,
    MATCH_QUALITY_EXCELLENT_THRESHOLD,
    MATCH_QUALITY_FAIR,
    MATCH_QUALITY_FAIR_THRESHOLD,
    MATCH_QUALITY_GOOD,
    MATCH_QUALITY_GOOD_THRESHOLD,
    MATCH_QUALITY_POOR,
    S3_STORAGE_CLASS_DEEP_ARCHIVE,
    S3_STORAGE_CLASS_GLACIER,
    S3_STORAGE_CLASS_GLACIER_IR,
    S3_STORAGE_CLASS_INTELLIGENT_TIERING,
    S3_STORAGE_CLASS_ONEZONE_IA,
    S3_STORAGE_CLASS_REDUCED_REDUNDANCY,
    S3_STORAGE_CLASS_STANDARD,
    S3_STORAGE_CLASS_STANDARD_IA,
    STORAGE_TIER_COLD,
    STORAGE_TIER_HOT,
    STORAGE_TIER_UNKNOWN,
    STORAGE_TIER_WARM,
)
from awslabs.aws_healthomics_mcp_server.models import GenomicsFile, GenomicsFileResult
from loguru import logger
from typing import Any, Dict, List, Optional


class JsonResponseBuilder:
    """Builds structured JSON responses for genomics file search results."""

    def __init__(self):
        """Initialize the JSON response builder."""
        pass

    def build_search_response(
        self,
        results: List[GenomicsFileResult],
        total_found: int,
        search_duration_ms: int,
        storage_systems_searched: List[str],
        search_statistics: Optional[Dict[str, Any]] = None,
        pagination_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a comprehensive JSON response for genomics file search.

        Args:
            results: List of GenomicsFileResult objects
            total_found: Total number of files found before pagination
            search_duration_ms: Time taken for the search in milliseconds
            storage_systems_searched: List of storage systems that were searched
            search_statistics: Optional search statistics and metrics
            pagination_info: Optional pagination information

        Returns:
            Dictionary containing structured JSON response with all required metadata
        """
        logger.info(f'Building JSON response for {len(results)} results')

        # Serialize the results with full metadata
        serialized_results = self._serialize_results(results)

        # Build the base response structure
        response = {
            'results': serialized_results,
            'total_found': total_found,
            'returned_count': len(results),
            'search_duration_ms': search_duration_ms,
            'storage_systems_searched': storage_systems_searched,
        }

        # Add search statistics if provided
        if search_statistics:
            response['search_statistics'] = search_statistics

        # Add pagination information if provided
        if pagination_info:
            response['pagination'] = pagination_info

        # Add performance metrics
        response['performance_metrics'] = self._build_performance_metrics(
            search_duration_ms, len(results), total_found
        )

        # Add metadata about the response structure
        response['metadata'] = self._build_response_metadata(results)

        logger.info(f'Built JSON response with {len(serialized_results)} serialized results')
        return response

    def _serialize_results(self, results: List[GenomicsFileResult]) -> List[Dict[str, Any]]:
        """Serialize GenomicsFileResult objects to dictionaries for JSON response.

        Args:
            results: List of GenomicsFileResult objects to serialize

        Returns:
            List of dictionaries representing the results with clear relationships for grouped files
        """
        serialized_results = []

        for result in results:
            # Serialize primary file with full metadata
            primary_file_dict = self._serialize_genomics_file(result.primary_file)

            # Serialize associated files with full metadata
            associated_files_list = []
            for assoc_file in result.associated_files:
                assoc_file_dict = self._serialize_genomics_file(assoc_file)
                associated_files_list.append(assoc_file_dict)

            # Create result dictionary with clear relationships
            result_dict = {
                'primary_file': primary_file_dict,
                'associated_files': associated_files_list,
                'file_group': {
                    'total_files': 1 + len(result.associated_files),
                    'total_size_bytes': (
                        result.primary_file.size_bytes
                        + sum(f.size_bytes for f in result.associated_files)
                    ),
                    'has_associations': len(result.associated_files) > 0,
                    'association_types': self._get_association_types(result.associated_files),
                },
                'relevance_score': result.relevance_score,
                'match_reasons': result.match_reasons,
                'ranking_info': {
                    'score_breakdown': self._build_score_breakdown(result),
                    'match_quality': self._assess_match_quality(result.relevance_score),
                },
            }

            serialized_results.append(result_dict)

        return serialized_results

    def _serialize_genomics_file(self, file: GenomicsFile) -> Dict[str, Any]:
        """Serialize a GenomicsFile object to a dictionary.

        Args:
            file: GenomicsFile object to serialize

        Returns:
            Dictionary representation of the GenomicsFile with all metadata
        """
        # Start with basic dataclass fields
        base_dict = {
            'path': file.path,
            'file_type': file.file_type.value,
            'size_bytes': file.size_bytes,
            'storage_class': file.storage_class,
            'last_modified': file.last_modified.isoformat(),
            'tags': file.tags,
            'source_system': file.source_system,
            'metadata': file.metadata,
        }

        # Use S3File model for enhanced file information if available
        if file.s3_file:
            s3_file = file.s3_file
            file_info = {
                'extension': self._extract_file_extension(
                    file.path
                ),  # Use genomics-aware extension logic
                'basename': s3_file.filename,
                'directory': s3_file.directory,
                'is_compressed': self._is_compressed_file(file.path),
                'storage_tier': self._categorize_storage_tier(file.storage_class),
                's3_info': {
                    'bucket': s3_file.bucket,
                    'key': s3_file.key,
                    'console_url': s3_file.console_url,
                    'arn': s3_file.arn,
                },
            }
        else:
            # Fallback to manual extraction for non-S3 files
            file_info = {
                'extension': self._extract_file_extension(file.path),
                'basename': self._extract_basename(file.path),
                'is_compressed': self._is_compressed_file(file.path),
                'storage_tier': self._categorize_storage_tier(file.storage_class),
            }

        # Add computed/enhanced fields
        base_dict.update(
            {
                'size_human_readable': self._format_file_size(file.size_bytes),
                'file_info': file_info,
            }
        )

        return base_dict

    def _build_performance_metrics(
        self, search_duration_ms: int, returned_count: int, total_found: int
    ) -> Dict[str, Any]:
        """Build performance metrics for the search operation.

        Args:
            search_duration_ms: Time taken for the search in milliseconds
            returned_count: Number of results returned
            total_found: Total number of results found

        Returns:
            Dictionary containing performance metrics
        """
        return {
            'search_duration_seconds': search_duration_ms / 1000.0,
            'results_per_second': returned_count / (search_duration_ms / 1000.0)
            if search_duration_ms > 0
            else 0,
            'search_efficiency': {
                'total_found': total_found,
                'returned_count': returned_count,
                'truncated': total_found > returned_count,
                'truncation_ratio': (total_found - returned_count) / total_found
                if total_found > 0
                else 0,
            },
        }

    def _build_response_metadata(self, results: List[GenomicsFileResult]) -> Dict[str, Any]:
        """Build metadata about the response structure and content.

        Args:
            results: List of GenomicsFileResult objects

        Returns:
            Dictionary containing response metadata
        """
        if not results:
            return {
                'file_type_distribution': {},
                'source_system_distribution': {},
                'association_summary': {'files_with_associations': 0, 'total_associated_files': 0},
            }

        # Analyze file type distribution
        file_types = {}
        source_systems = {}
        files_with_associations = 0
        total_associated_files = 0

        for result in results:
            # Count primary file type
            file_type = result.primary_file.file_type.value
            file_types[file_type] = file_types.get(file_type, 0) + 1

            # Count source system
            source_system = result.primary_file.source_system
            source_systems[source_system] = source_systems.get(source_system, 0) + 1

            # Count associations
            if result.associated_files:
                files_with_associations += 1
                total_associated_files += len(result.associated_files)

                # Count associated file types
                for assoc_file in result.associated_files:
                    assoc_type = assoc_file.file_type.value
                    file_types[assoc_type] = file_types.get(assoc_type, 0) + 1

        return {
            'file_type_distribution': file_types,
            'source_system_distribution': source_systems,
            'association_summary': {
                'files_with_associations': files_with_associations,
                'total_associated_files': total_associated_files,
                'association_ratio': files_with_associations / len(results) if results else 0,
            },
        }

    def _get_association_types(self, associated_files: List[GenomicsFile]) -> List[str]:
        """Get the types of file associations present.

        Args:
            associated_files: List of associated GenomicsFile objects

        Returns:
            List of association type strings
        """
        if not associated_files:
            return []

        association_types = []
        file_types = [f.file_type.value for f in associated_files]

        # Detect common association patterns
        if any(ft in ['bai', 'crai'] for ft in file_types):
            association_types.append('alignment_index')
        if any(ft in ['fai', 'dict'] for ft in file_types):
            association_types.append('sequence_index')
        if any(ft in ['tbi', 'csi'] for ft in file_types):
            association_types.append('variant_index')
        if any(ft.startswith('bwa_') for ft in file_types):
            association_types.append('bwa_index_collection')
        if len([ft for ft in file_types if ft == 'fastq']) > 1:
            association_types.append('paired_reads')

        return association_types

    def _build_score_breakdown(self, result: GenomicsFileResult) -> Dict[str, Any]:
        """Build a breakdown of the relevance score components.

        Args:
            result: GenomicsFileResult object

        Returns:
            Dictionary containing score breakdown information
        """
        # This is a simplified breakdown - in a real implementation,
        # the scoring engine would provide detailed component scores
        return {
            'total_score': result.relevance_score,
            'has_associations_bonus': len(result.associated_files) > 0,
            'association_count': len(result.associated_files),
            'match_reasons_count': len(result.match_reasons),
        }

    def _assess_match_quality(self, score: float) -> str:
        """Assess the quality of the match based on the relevance score.

        Args:
            score: Relevance score

        Returns:
            String describing match quality
        """
        if score >= MATCH_QUALITY_EXCELLENT_THRESHOLD:
            return MATCH_QUALITY_EXCELLENT
        elif score >= MATCH_QUALITY_GOOD_THRESHOLD:
            return MATCH_QUALITY_GOOD
        elif score >= MATCH_QUALITY_FAIR_THRESHOLD:
            return MATCH_QUALITY_FAIR
        else:
            return MATCH_QUALITY_POOR

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: File size in bytes

        Returns:
            Human-readable file size string
        """
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f'{int(size)} {units[unit_index]}'
        else:
            return f'{size:.1f} {units[unit_index]}'

    def _extract_file_extension(self, path: str) -> str:
        """Extract file extension from path.

        Args:
            path: File path

        Returns:
            File extension (without dot)
        """
        if '.' not in path:
            return ''

        # Handle compressed files like .fastq.gz
        if path.endswith('.gz'):
            parts = path.split('.')
            if len(parts) >= 3:
                return f'{parts[-2]}.{parts[-1]}'
            else:
                return parts[-1]
        elif path.endswith('.bz2'):
            parts = path.split('.')
            if len(parts) >= 3:
                return f'{parts[-2]}.{parts[-1]}'
            else:
                return parts[-1]
        else:
            return path.split('.')[-1]

    def _extract_basename(self, path: str) -> str:
        """Extract basename from path.

        Args:
            path: File path

        Returns:
            File basename
        """
        return path.split('/')[-1] if '/' in path else path

    def _is_compressed_file(self, path: str) -> bool:
        """Check if file is compressed based on extension.

        Args:
            path: File path

        Returns:
            True if file appears to be compressed
        """
        return path.endswith(('.gz', '.bz2', '.zip', '.xz'))

    def _categorize_storage_tier(self, storage_class: str) -> str:
        """Categorize storage class into tiers.

        Args:
            storage_class: AWS S3 storage class

        Returns:
            Storage tier category
        """
        # Use constants for storage class comparison (case-insensitive)
        storage_class_upper = storage_class.upper()

        # Hot tier: Frequently accessed data
        if storage_class_upper in [S3_STORAGE_CLASS_STANDARD, S3_STORAGE_CLASS_REDUCED_REDUNDANCY]:
            return STORAGE_TIER_HOT
        # Warm tier: Infrequently accessed data with quick retrieval
        elif storage_class_upper in [
            S3_STORAGE_CLASS_STANDARD_IA,
            S3_STORAGE_CLASS_ONEZONE_IA,
            S3_STORAGE_CLASS_INTELLIGENT_TIERING,
        ]:
            return STORAGE_TIER_WARM
        # Cold tier: Archive data with longer retrieval times
        elif storage_class_upper in [
            S3_STORAGE_CLASS_GLACIER,
            S3_STORAGE_CLASS_GLACIER_IR,
            S3_STORAGE_CLASS_DEEP_ARCHIVE,
        ]:
            return STORAGE_TIER_COLD
        else:
            return STORAGE_TIER_UNKNOWN
