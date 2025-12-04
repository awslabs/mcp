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

"""AWS HealthOmics MCP Server data models package."""

# Core HealthOmics models
from .core import (
    AnalysisResponse,
    AnalysisResult,
    CacheBehavior,
    ContainerRegistryMap,
    ExportType,
    ImageMapping,
    LogEvent,
    LogResponse,
    RegistryMapping,
    RunListResponse,
    RunStatus,
    RunSummary,
    StorageRequest,
    StorageType,
    TaskListResponse,
    TaskSummary,
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowType,
)

# S3 file models and utilities
from .s3 import (
    S3File,
    build_s3_uri,
    create_s3_file_from_object,
    get_s3_file_associations,
    parse_s3_uri,
)

# Search models and utilities
from .search import (
    CursorBasedPaginationToken,
    FileGroup,
    GenomicsFile,
    GenomicsFileResult,
    GenomicsFileSearchRequest,
    GenomicsFileSearchResponse,
    GenomicsFileType,
    GlobalContinuationToken,
    PaginationCacheEntry,
    PaginationMetrics,
    SearchConfig,
    StoragePaginationRequest,
    StoragePaginationResponse,
    create_genomics_file_from_s3_object,
)

__all__ = [
    # Core models
    'AnalysisResponse',
    'AnalysisResult',
    'CacheBehavior',
    'ContainerRegistryMap',
    'ExportType',
    'ImageMapping',
    'LogEvent',
    'LogResponse',
    'RegistryMapping',
    'RunListResponse',
    'RunStatus',
    'RunSummary',
    'StorageRequest',
    'StorageType',
    'TaskListResponse',
    'TaskSummary',
    'WorkflowListResponse',
    'WorkflowSummary',
    'WorkflowType',
    # S3 models
    'S3File',
    'build_s3_uri',
    'create_s3_file_from_object',
    'get_s3_file_associations',
    'parse_s3_uri',
    # Search models
    'CursorBasedPaginationToken',
    'FileGroup',
    'GenomicsFile',
    'GenomicsFileResult',
    'GenomicsFileSearchRequest',
    'GenomicsFileSearchResponse',
    'GenomicsFileType',
    'GlobalContinuationToken',
    'PaginationCacheEntry',
    'PaginationMetrics',
    'SearchConfig',
    'StoragePaginationRequest',
    'StoragePaginationResponse',
    'create_genomics_file_from_s3_object',
]
