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

"""Search-related models for genomics file search and pagination."""

from .s3 import S3File
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional


class GenomicsFileType(str, Enum):
    """Enumeration of supported genomics file types."""

    # Sequence files
    FASTQ = 'fastq'
    FASTA = 'fasta'
    FNA = 'fna'

    # Alignment files
    BAM = 'bam'
    CRAM = 'cram'
    SAM = 'sam'

    # Variant files
    VCF = 'vcf'
    GVCF = 'gvcf'
    BCF = 'bcf'

    # Annotation files
    BED = 'bed'
    GFF = 'gff'

    # Index files
    BAI = 'bai'
    CRAI = 'crai'
    FAI = 'fai'
    DICT = 'dict'
    TBI = 'tbi'
    CSI = 'csi'

    # BWA index files
    BWA_AMB = 'bwa_amb'
    BWA_ANN = 'bwa_ann'
    BWA_BWT = 'bwa_bwt'
    BWA_PAC = 'bwa_pac'
    BWA_SA = 'bwa_sa'


@dataclass
class GenomicsFile:
    """Represents a genomics file with metadata."""

    path: str  # S3 path or access point path (kept for backward compatibility)
    file_type: GenomicsFileType
    size_bytes: int
    storage_class: str
    last_modified: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    source_system: str = ''  # 's3', 'sequence_store', 'reference_store'
    metadata: Dict[str, Any] = field(default_factory=dict)
    _s3_file: Optional[S3File] = field(default=None, init=False)

    @property
    def s3_file(self) -> Optional[S3File]:
        """Get the S3File representation of this genomics file if it's an S3 path."""
        if self._s3_file is None and self.path.startswith('s3://'):
            try:
                self._s3_file = S3File.from_uri(
                    self.path,
                    size_bytes=self.size_bytes,
                    last_modified=self.last_modified,
                    storage_class=self.storage_class,
                    tags=self.tags,
                )
            except ValueError:
                # If URI parsing fails, return None
                return None
        return self._s3_file

    @property
    def uri(self) -> str:
        """Get the URI for this file (alias for path for consistency)."""
        return self.path

    @property
    def filename(self) -> str:
        """Extract the filename from the path."""
        if self.s3_file:
            return self.s3_file.filename
        # Fallback for non-S3 paths
        return self.path.split('/')[-1] if '/' in self.path else self.path

    @property
    def extension(self) -> str:
        """Extract the file extension."""
        if self.s3_file:
            return self.s3_file.extension
        # Fallback for non-S3 paths
        filename = self.filename
        if '.' not in filename:
            return ''
        return filename.split('.')[-1].lower()

    @classmethod
    def from_s3_file(
        cls,
        s3_file: S3File,
        file_type: GenomicsFileType,
        source_system: str = 's3',
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'GenomicsFile':
        """Create a GenomicsFile from an S3File instance.

        Args:
            s3_file: S3File instance
            file_type: Type of genomics file
            source_system: Source system identifier
            metadata: Additional metadata

        Returns:
            GenomicsFile instance
        """
        genomics_file = cls(
            path=s3_file.uri,
            file_type=file_type,
            size_bytes=s3_file.size_bytes or 0,
            storage_class=s3_file.storage_class or '',
            last_modified=s3_file.last_modified or datetime.now(),
            tags=s3_file.tags.copy(),
            source_system=source_system,
            metadata=metadata or {},
        )
        genomics_file._s3_file = s3_file
        return genomics_file

    def get_presigned_url(self, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for this file if it's in S3.

        Args:
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL or None if not an S3 file
        """
        if self.s3_file:
            return self.s3_file.get_presigned_url(expiration)
        return None


@dataclass
class GenomicsFileResult:
    """Represents a search result with primary file and associated files."""

    primary_file: GenomicsFile
    associated_files: List[GenomicsFile] = field(default_factory=list)
    relevance_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class FileGroup:
    """Represents a group of related genomics files."""

    primary_file: GenomicsFile
    associated_files: List[GenomicsFile] = field(default_factory=list)
    group_type: str = ''  # 'bam_index', 'fastq_pair', 'fasta_index', etc.


@dataclass
class SearchConfig:
    """Configuration for genomics file search."""

    s3_bucket_paths: List[str] = field(default_factory=list)
    max_concurrent_searches: int = 10
    search_timeout_seconds: int = 300
    enable_healthomics_search: bool = True
    default_max_results: int = 100
    enable_s3_tag_search: bool = True  # Enable/disable S3 tag-based searching
    max_tag_retrieval_batch_size: int = 100  # Maximum objects to retrieve tags for in batch
    result_cache_ttl_seconds: int = 600  # Result cache TTL (10 minutes)
    tag_cache_ttl_seconds: int = 300  # Tag cache TTL (5 minutes)

    # Cache size limits
    max_tag_cache_size: int = 1000  # Maximum number of tag cache entries
    max_result_cache_size: int = 100  # Maximum number of result cache entries
    max_pagination_cache_size: int = 50  # Maximum number of pagination cache entries
    cache_cleanup_keep_ratio: float = 0.8  # Ratio of entries to keep during size-based cleanup

    # Pagination performance optimization settings
    enable_cursor_based_pagination: bool = (
        True  # Enable cursor-based pagination for large datasets
    )
    pagination_cache_ttl_seconds: int = 1800  # Pagination state cache TTL (30 minutes)
    max_pagination_buffer_size: int = 10000  # Maximum buffer size for ranking-aware pagination
    min_pagination_buffer_size: int = 500  # Minimum buffer size for ranking-aware pagination
    enable_pagination_metrics: bool = True  # Enable pagination performance metrics
    pagination_score_threshold_tolerance: float = (
        0.001  # Score threshold tolerance for pagination consistency
    )


class GenomicsFileSearchRequest(BaseModel):
    """Request model for genomics file search."""

    file_type: Optional[str] = None
    search_terms: List[str] = []
    max_results: int = 100
    include_associated_files: bool = True
    offset: int = 0
    continuation_token: Optional[str] = None

    # Storage-level pagination parameters
    enable_storage_pagination: bool = False  # Enable efficient storage-level pagination
    pagination_buffer_size: int = 500  # Buffer size for ranking-aware pagination

    # Adhoc S3 bucket support
    adhoc_s3_buckets: Optional[List[str]] = None  # Additional S3 bucket paths to search

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        """Validate max_results parameter."""
        if v <= 0:
            raise ValueError('max_results must be greater than 0')
        if v > 10000:
            raise ValueError('max_results cannot exceed 10000')
        return v

    @field_validator('pagination_buffer_size')
    @classmethod
    def validate_buffer_size(cls, v: int) -> int:
        """Validate pagination_buffer_size parameter."""
        if v < 100:
            raise ValueError('pagination_buffer_size must be at least 100')
        if v > 50000:
            raise ValueError('pagination_buffer_size cannot exceed 50000')
        return v

    @field_validator('adhoc_s3_buckets')
    @classmethod
    def validate_adhoc_s3_buckets(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate adhoc_s3_buckets parameter."""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError('adhoc_s3_buckets must be a list of S3 bucket paths')

        if len(v) == 0:
            return None  # Empty list is equivalent to None

        if len(v) > 50:  # Reasonable limit to prevent abuse
            raise ValueError('adhoc_s3_buckets cannot contain more than 50 bucket paths')

        # Basic format validation for each bucket path
        from awslabs.aws_healthomics_mcp_server.utils.s3_utils import (
            validate_and_normalize_s3_path,
        )

        validated_paths = []
        for bucket_path in v:
            if not isinstance(bucket_path, str):
                raise ValueError('All adhoc_s3_buckets entries must be strings')

            try:
                validated_path = validate_and_normalize_s3_path(bucket_path)
                validated_paths.append(validated_path)
            except ValueError as e:
                raise ValueError(f'Invalid S3 bucket path "{bucket_path}": {str(e)}')

        return validated_paths


class GenomicsFileSearchResponse(BaseModel):
    """Response model for genomics file search."""

    results: List[Dict[str, Any]]  # Will contain serialized GenomicsFileResult objects
    total_found: int
    search_duration_ms: int
    storage_systems_searched: List[str]
    enhanced_response: Optional[Dict[str, Any]] = (
        None  # Enhanced response with additional metadata
    )


# Storage-level pagination models


@dataclass
class StoragePaginationRequest:
    """Request model for storage-level pagination."""

    max_results: int = 100
    continuation_token: Optional[str] = None
    buffer_size: int = 500  # Buffer size for ranking-aware pagination

    def __post_init__(self):
        """Validate pagination request parameters."""
        if self.max_results <= 0:
            raise ValueError('max_results must be greater than 0')
        if self.max_results > 10000:
            raise ValueError('max_results cannot exceed 10000')
        if self.buffer_size < self.max_results:
            self.buffer_size = max(self.max_results * 2, 500)


@dataclass
class StoragePaginationResponse:
    """Response model for storage-level pagination."""

    results: List[GenomicsFile]
    next_continuation_token: Optional[str] = None
    has_more_results: bool = False
    total_scanned: int = 0
    buffer_overflow: bool = False  # Indicates if buffer was exceeded during ranking


@dataclass
class GlobalContinuationToken:
    """Global continuation token that coordinates pagination across multiple storage systems."""

    s3_tokens: Dict[str, str] = field(default_factory=dict)  # bucket_path -> continuation_token
    healthomics_sequence_token: Optional[str] = None
    healthomics_reference_token: Optional[str] = None
    last_score_threshold: Optional[float] = None  # For ranking-aware pagination
    page_number: int = 0
    total_results_seen: int = 0

    def encode(self) -> str:
        """Encode the continuation token to a string for client use."""
        import base64
        import json

        token_data = {
            's3_tokens': self.s3_tokens,
            'healthomics_sequence_token': self.healthomics_sequence_token,
            'healthomics_reference_token': self.healthomics_reference_token,
            'last_score_threshold': self.last_score_threshold,
            'page_number': self.page_number,
            'total_results_seen': self.total_results_seen,
        }

        json_str = json.dumps(token_data, separators=(',', ':'))
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return encoded

    @classmethod
    def decode(cls, token_str: str) -> 'GlobalContinuationToken':
        """Decode a continuation token string back to a GlobalContinuationToken object."""
        import base64
        import json

        try:
            decoded = base64.b64decode(token_str.encode('utf-8')).decode('utf-8')
            token_data = json.loads(decoded)

            return cls(
                s3_tokens=token_data.get('s3_tokens', {}),
                healthomics_sequence_token=token_data.get('healthomics_sequence_token'),
                healthomics_reference_token=token_data.get('healthomics_reference_token'),
                last_score_threshold=token_data.get('last_score_threshold'),
                page_number=token_data.get('page_number', 0),
                total_results_seen=token_data.get('total_results_seen', 0),
            )
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f'Invalid continuation token format: {e}')

    def is_empty(self) -> bool:
        """Check if this is an empty/initial continuation token."""
        return (
            not self.s3_tokens
            and not self.healthomics_sequence_token
            and not self.healthomics_reference_token
            and self.page_number == 0
        )

    def has_more_pages(self) -> bool:
        """Check if there are more pages available from any storage system."""
        return (
            bool(self.s3_tokens)
            or bool(self.healthomics_sequence_token)
            or bool(self.healthomics_reference_token)
        )


@dataclass
class PaginationMetrics:
    """Metrics for pagination performance analysis."""

    page_number: int = 0
    total_results_fetched: int = 0
    total_objects_scanned: int = 0
    buffer_overflows: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls_made: int = 0
    search_duration_ms: int = 0
    ranking_duration_ms: int = 0
    storage_fetch_duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            'page_number': self.page_number,
            'total_results_fetched': self.total_results_fetched,
            'total_objects_scanned': self.total_objects_scanned,
            'buffer_overflows': self.buffer_overflows,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'api_calls_made': self.api_calls_made,
            'search_duration_ms': self.search_duration_ms,
            'ranking_duration_ms': self.ranking_duration_ms,
            'storage_fetch_duration_ms': self.storage_fetch_duration_ms,
            'efficiency_ratio': self.total_results_fetched / max(self.total_objects_scanned, 1),
            'cache_hit_ratio': self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
        }


@dataclass
class PaginationCacheEntry:
    """Cache entry for pagination state and intermediate results."""

    search_key: str
    page_number: int
    intermediate_results: List[GenomicsFile] = field(default_factory=list)
    score_threshold: Optional[float] = None
    storage_tokens: Dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0
    metrics: Optional[PaginationMetrics] = None

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this cache entry has expired."""
        import time

        return time.time() - self.timestamp > ttl_seconds

    def update_timestamp(self) -> None:
        """Update the timestamp to current time."""
        import time

        self.timestamp = time.time()


@dataclass
class CursorBasedPaginationToken:
    """Cursor-based pagination token for very large datasets."""

    cursor_value: str  # Last seen value for cursor-based pagination
    cursor_type: str  # Type of cursor: 'score', 'timestamp', 'lexicographic'
    storage_cursors: Dict[str, str] = field(default_factory=dict)  # Per-storage cursor values
    page_size: int = 100
    total_seen: int = 0

    def encode(self) -> str:
        """Encode the cursor token to a string for client use."""
        import base64
        import json

        token_data = {
            'cursor_value': self.cursor_value,
            'cursor_type': self.cursor_type,
            'storage_cursors': self.storage_cursors,
            'page_size': self.page_size,
            'total_seen': self.total_seen,
        }

        json_str = json.dumps(token_data, separators=(',', ':'))
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return f'cursor:{encoded}'

    @classmethod
    def decode(cls, token_str: str) -> 'CursorBasedPaginationToken':
        """Decode a cursor token string back to a CursorBasedPaginationToken object."""
        import base64
        import json

        if not token_str.startswith('cursor:'):
            raise ValueError('Invalid cursor token format')

        try:
            encoded = token_str[7:]  # Remove 'cursor:' prefix
            decoded = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
            token_data = json.loads(decoded)

            return cls(
                cursor_value=token_data['cursor_value'],
                cursor_type=token_data['cursor_type'],
                storage_cursors=token_data.get('storage_cursors', {}),
                page_size=token_data.get('page_size', 100),
                total_seen=token_data.get('total_seen', 0),
            )
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f'Invalid cursor token format: {e}')


# Utility Functions for Search Models


def create_genomics_file_from_s3_object(
    bucket: str,
    s3_object: Dict[str, Any],
    file_type: GenomicsFileType,
    tags: Optional[Dict[str, str]] = None,
    source_system: str = 's3',
    metadata: Optional[Dict[str, Any]] = None,
) -> GenomicsFile:
    """Create a GenomicsFile instance from an S3 object dictionary.

    Args:
        bucket: S3 bucket name
        s3_object: S3 object dictionary from list_objects_v2 or similar
        file_type: Type of genomics file
        tags: Optional tags dictionary
        source_system: Source system identifier
        metadata: Additional metadata

    Returns:
        GenomicsFile instance
    """
    from .s3 import create_s3_file_from_object

    s3_file = create_s3_file_from_object(bucket, s3_object, tags)
    return GenomicsFile.from_s3_file(s3_file, file_type, source_system, metadata)
