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

"""Defines data models, Pydantic models, and validation logic."""

from awslabs.aws_healthomics_mcp_server.consts import (
    ERROR_STATIC_STORAGE_REQUIRES_CAPACITY,
)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator
from typing import Any, Dict, List, Optional


class WorkflowType(str, Enum):
    """Enum for workflow languages."""

    WDL = 'WDL'
    NEXTFLOW = 'NEXTFLOW'
    CWL = 'CWL'


class StorageType(str, Enum):
    """Enum for storage types."""

    STATIC = 'STATIC'
    DYNAMIC = 'DYNAMIC'


class CacheBehavior(str, Enum):
    """Enum for cache behaviors."""

    CACHE_ALWAYS = 'CACHE_ALWAYS'
    CACHE_ON_FAILURE = 'CACHE_ON_FAILURE'


class RunStatus(str, Enum):
    """Enum for run statuses."""

    PENDING = 'PENDING'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class ExportType(str, Enum):
    """Enum for export types."""

    DEFINITION = 'DEFINITION'
    PARAMETER_TEMPLATE = 'PARAMETER_TEMPLATE'


class WorkflowSummary(BaseModel):
    """Summary information about a workflow."""

    id: str
    arn: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: str
    type: str
    storageType: Optional[str] = None
    storageCapacity: Optional[int] = None
    creationTime: datetime


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: List[WorkflowSummary]
    nextToken: Optional[str] = None


class RunSummary(BaseModel):
    """Summary information about a run."""

    id: str
    arn: str
    name: Optional[str] = None
    parameters: Optional[dict] = None
    status: str
    workflowId: str
    workflowType: str
    creationTime: datetime
    startTime: Optional[datetime] = None
    stopTime: Optional[datetime] = None


class RunListResponse(BaseModel):
    """Response model for listing runs."""

    runs: List[RunSummary]
    nextToken: Optional[str] = None


class TaskSummary(BaseModel):
    """Summary information about a task."""

    taskId: str
    status: str
    name: str
    cpus: int
    memory: int
    startTime: Optional[datetime] = None
    stopTime: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""

    tasks: List[TaskSummary]
    nextToken: Optional[str] = None


class LogEvent(BaseModel):
    """Log event model."""

    timestamp: datetime
    message: str


class LogResponse(BaseModel):
    """Response model for retrieving logs."""

    events: List[LogEvent]
    nextToken: Optional[str] = None


class StorageRequest(BaseModel):
    """Model for storage requests."""

    storageType: StorageType
    storageCapacity: Optional[int] = None

    @model_validator(mode='after')
    def validate_storage_capacity(self):
        """Validate storage capacity."""
        if self.storageType == StorageType.STATIC and self.storageCapacity is None:
            raise ValueError(ERROR_STATIC_STORAGE_REQUIRES_CAPACITY)
        return self


class AnalysisResult(BaseModel):
    """Model for run analysis results."""

    taskName: str
    count: int
    meanRunningSeconds: float
    maximumRunningSeconds: float
    stdDevRunningSeconds: float
    maximumCpuUtilizationRatio: float
    meanCpuUtilizationRatio: float
    maximumMemoryUtilizationRatio: float
    meanMemoryUtilizationRatio: float
    recommendedCpus: int
    recommendedMemoryGiB: float
    recommendedInstanceType: str
    maximumEstimatedUSD: float
    meanEstimatedUSD: float


class AnalysisResponse(BaseModel):
    """Response model for run analysis."""

    results: List[AnalysisResult]


class RegistryMapping(BaseModel):
    """Model for registry mapping configuration."""

    upstreamRegistryUrl: str
    ecrRepositoryPrefix: str
    upstreamRepositoryPrefix: Optional[str]
    ecrAccountId: Optional[str]


class ImageMapping(BaseModel):
    """Model for image mapping configuration."""

    sourceImage: str
    destinationImage: str


class ContainerRegistryMap(BaseModel):
    """Model for container registry mapping configuration."""

    registryMappings: List[RegistryMapping] = []
    imageMappings: List[ImageMapping] = []

    @field_validator('registryMappings', 'imageMappings', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v: Any) -> List[Any]:
        """Convert None values to empty lists for consistency."""
        return [] if v is None else v


# Genomics File Search Models


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

    path: str  # S3 path or access point path
    file_type: GenomicsFileType
    size_bytes: int
    storage_class: str
    last_modified: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    source_system: str = ''  # 's3', 'sequence_store', 'reference_store'
    metadata: Dict[str, Any] = field(default_factory=dict)


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
