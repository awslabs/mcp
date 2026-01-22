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

"""Defines constants used across the server."""

import os
from loguru import logger


# Service constants
DEFAULT_REGION = 'us-east-1'
DEFAULT_OMICS_SERVICE_NAME = 'omics'
DEFAULT_STORAGE_TYPE = 'DYNAMIC'
try:
    DEFAULT_MAX_RESULTS = int(os.environ.get('HEALTHOMICS_DEFAULT_MAX_RESULTS', '100'))
except ValueError:
    logger.warning(
        'Invalid value for HEALTHOMICS_DEFAULT_MAX_RESULTS environment variable. '
        'Using default value of 100.'
    )
    DEFAULT_MAX_RESULTS = 100

# Supported regions (as of June 2025)
# These are hardcoded as a fallback in case the boto3 session region query fails
HEALTHOMICS_SUPPORTED_REGIONS = [
    'ap-southeast-1',
    'eu-central-1',
    'eu-west-1',
    'eu-west-2',
    'il-central-1',
    'us-east-1',
    'us-west-2',
]


# Storage types
STORAGE_TYPE_STATIC = 'STATIC'
STORAGE_TYPE_DYNAMIC = 'DYNAMIC'
STORAGE_TYPES = [STORAGE_TYPE_STATIC, STORAGE_TYPE_DYNAMIC]

# Cache behaviors
CACHE_BEHAVIOR_ALWAYS = 'CACHE_ALWAYS'
CACHE_BEHAVIOR_ON_FAILURE = 'CACHE_ON_FAILURE'
CACHE_BEHAVIORS = [CACHE_BEHAVIOR_ALWAYS, CACHE_BEHAVIOR_ON_FAILURE]

# Run statuses
RUN_STATUS_PENDING = 'PENDING'
RUN_STATUS_STARTING = 'STARTING'
RUN_STATUS_RUNNING = 'RUNNING'
RUN_STATUS_COMPLETED = 'COMPLETED'
RUN_STATUS_FAILED = 'FAILED'
RUN_STATUS_CANCELLED = 'CANCELLED'
RUN_STATUSES = [
    RUN_STATUS_PENDING,
    RUN_STATUS_STARTING,
    RUN_STATUS_RUNNING,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_CANCELLED,
]

# Export types
EXPORT_TYPE_DEFINITION = 'DEFINITION'

# Genomics file search configuration
GENOMICS_SEARCH_S3_BUCKETS_ENV = 'GENOMICS_SEARCH_S3_BUCKETS'
GENOMICS_SEARCH_MAX_CONCURRENT_ENV = 'GENOMICS_SEARCH_MAX_CONCURRENT'
GENOMICS_SEARCH_TIMEOUT_ENV = 'GENOMICS_SEARCH_TIMEOUT_SECONDS'
GENOMICS_SEARCH_ENABLE_HEALTHOMICS_ENV = 'GENOMICS_SEARCH_ENABLE_HEALTHOMICS'
GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH_ENV = 'GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH'
GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE_ENV = 'GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE'
GENOMICS_SEARCH_RESULT_CACHE_TTL_ENV = 'GENOMICS_SEARCH_RESULT_CACHE_TTL'
GENOMICS_SEARCH_TAG_CACHE_TTL_ENV = 'GENOMICS_SEARCH_TAG_CACHE_TTL'

# Default values for genomics search
DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT = 10
DEFAULT_GENOMICS_SEARCH_TIMEOUT = 300
DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS = True
DEFAULT_GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH = True
DEFAULT_GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE = 100
DEFAULT_GENOMICS_SEARCH_RESULT_CACHE_TTL = 600
DEFAULT_GENOMICS_SEARCH_TAG_CACHE_TTL = 300

# Cache size limits - Maximum number of entries in the cache
DEFAULT_GENOMICS_SEARCH_MAX_FILE_CACHE_SIZE = 10000
DEFAULT_GENOMICS_SEARCH_MAX_TAG_CACHE_SIZE = 1000
DEFAULT_GENOMICS_SEARCH_MAX_RESULT_CACHE_SIZE = 100
DEFAULT_GENOMICS_SEARCH_MAX_PAGINATION_CACHE_SIZE = 50

# Cache cleanup behavior
DEFAULT_CACHE_CLEANUP_KEEP_RATIO = 0.8  # Keep at most 80% of entries when cleaning up by size

# Search limits and pagination
MAX_SEARCH_RESULTS_LIMIT = 10000  # Maximum allowed results per search
DEFAULT_HEALTHOMICS_PAGE_SIZE = 100  # Default pagination size for HealthOmics APIs
DEFAULT_S3_PAGE_SIZE = 1000  # Default pagination size for S3 operations
DEFAULT_RESULT_RANKER_FALLBACK_SIZE = 100  # Fallback size when max_results is invalid

# Rate limiting and performance
HEALTHOMICS_RATE_LIMIT_DELAY = 0.1  # Sleep delay between HealthOmics Storage API calls (10 TPS)

# Cache cleanup sweep probabilities for entries with expired TTLs (as percentages for clarity)
PAGINATION_CACHE_CLEANUP_PROBABILITY = 1  # 1% chance (1 in 100)
S3_CACHE_CLEANUP_PROBABILITY = 2  # 2% chance (1 in 50)

# Buffer size optimization thresholds
CURSOR_PAGINATION_BUFFER_THRESHOLD = 5000  # Use cursor pagination above this buffer size
CURSOR_PAGINATION_PAGE_THRESHOLD = 10  # Use cursor pagination above this page number
BUFFER_EFFICIENCY_LOW_THRESHOLD = 0.1  # 10% efficiency threshold
BUFFER_EFFICIENCY_HIGH_THRESHOLD = 0.5  # 50% efficiency threshold

# Buffer size complexity multipliers
COMPLEXITY_MULTIPLIER_FILE_TYPE_FILTER = 0.8  # Reduce complexity when file type is filtered
COMPLEXITY_MULTIPLIER_ASSOCIATED_FILES = 1.2  # Increase complexity for associated files
COMPLEXITY_MULTIPLIER_BUFFER_OVERFLOW = 1.5  # Increase when buffer overflows occur
COMPLEXITY_MULTIPLIER_LOW_EFFICIENCY = 2.0  # Increase when efficiency is low
COMPLEXITY_MULTIPLIER_HIGH_EFFICIENCY = 0.8  # Decrease when efficiency is high

# Pattern matching thresholds and multipliers
FUZZY_MATCH_THRESHOLD = 0.6  # Minimum similarity for fuzzy matches
MULTIPLE_MATCH_BONUS_MULTIPLIER = 1.2  # 20% bonus for multiple pattern matches
TAG_MATCH_PENALTY_MULTIPLIER = 0.9  # 10% penalty for tag matches vs path matches
SUBSTRING_MATCH_MAX_MULTIPLIER = 0.8  # Maximum score multiplier for substring matches
FUZZY_MATCH_MAX_MULTIPLIER = 0.6  # Maximum score multiplier for fuzzy matches

# Match quality score thresholds
MATCH_QUALITY_EXCELLENT_THRESHOLD = 0.8
MATCH_QUALITY_GOOD_THRESHOLD = 0.6
MATCH_QUALITY_FAIR_THRESHOLD = 0.4

# Match quality labels
MATCH_QUALITY_EXCELLENT = 'excellent'
MATCH_QUALITY_GOOD = 'good'
MATCH_QUALITY_FAIR = 'fair'
MATCH_QUALITY_POOR = 'poor'

# Unit conversion constants
BYTES_PER_KILOBYTE = 1024
MILLISECONDS_PER_SECOND = 1000.0

# HealthOmics status constants
HEALTHOMICS_STATUS_ACTIVE = 'ACTIVE'

# HealthOmics storage class constants
HEALTHOMICS_STORAGE_CLASS_MANAGED = 'MANAGED'

# Storage tier constants
STORAGE_TIER_HOT = 'hot'
STORAGE_TIER_WARM = 'warm'
STORAGE_TIER_COLD = 'cold'
STORAGE_TIER_UNKNOWN = 'unknown'

# S3 storage class constants
S3_STORAGE_CLASS_STANDARD = 'STANDARD'
S3_STORAGE_CLASS_REDUCED_REDUNDANCY = 'REDUCED_REDUNDANCY'
S3_STORAGE_CLASS_STANDARD_IA = 'STANDARD_IA'
S3_STORAGE_CLASS_ONEZONE_IA = 'ONEZONE_IA'
S3_STORAGE_CLASS_INTELLIGENT_TIERING = 'INTELLIGENT_TIERING'
S3_STORAGE_CLASS_GLACIER = 'GLACIER'
S3_STORAGE_CLASS_DEEP_ARCHIVE = 'DEEP_ARCHIVE'
S3_STORAGE_CLASS_OUTPOSTS = 'OUTPOSTS'
S3_STORAGE_CLASS_GLACIER_IR = 'GLACIER_IR'

# Error messages

ERROR_INVALID_STORAGE_TYPE = 'Invalid storage type. Must be one of: {}'
ERROR_INVALID_CACHE_BEHAVIOR = 'Invalid cache behavior. Must be one of: {}'
ERROR_INVALID_RUN_STATUS = 'Invalid run status. Must be one of: {}'
ERROR_STATIC_STORAGE_REQUIRES_CAPACITY = (
    'Storage capacity is required when using STATIC storage type'
)
ERROR_NO_S3_BUCKETS_CONFIGURED = (
    'No S3 bucket paths configured. Set the GENOMICS_SEARCH_S3_BUCKETS environment variable '
    'with comma-separated S3 paths (e.g., "s3://bucket1/prefix1/,s3://bucket2/prefix2/")'
)
ERROR_INVALID_S3_BUCKET_PATH = (
    'Invalid S3 bucket path: {}. Must start with "s3://" and contain a valid bucket name'
)

# Genomics file index patterns
# Maps primary file extensions to their associated index file extensions
GENOMICS_INDEX_PATTERNS = {
    '.bam': ['.bam.bai', '.bai'],
    '.cram': ['.cram.crai', '.crai'],
    '.vcf': ['.vcf.tbi', '.tbi'],
    '.vcf.gz': ['.vcf.gz.tbi', '.tbi'],
    '.fasta': ['.fasta.fai', '.fai'],
    '.fa': ['.fa.fai', '.fai'],
    '.fna': ['.fna.fai', '.fai'],
}

# FASTQ paired-end read patterns
FASTQ_PAIR_PATTERNS = [
    ('_R1_', '_R2_'),
    ('_R1.', '_R2.'),
    ('_R2_', '_R1_'),
    ('_R2.', '_R1.'),
    ('_1.', '_2.'),
    ('_2.', '_1.'),
]

# FASTQ file extensions
FASTQ_EXTENSIONS = ['fastq', 'fq', 'fastq.gz', 'fq.gz']
