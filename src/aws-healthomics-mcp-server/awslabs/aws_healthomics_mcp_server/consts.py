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
# These are hardcoded as a fallback in case the SSM parameter store query fails
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

# Default values for genomics search
DEFAULT_GENOMICS_SEARCH_MAX_CONCURRENT = 10
DEFAULT_GENOMICS_SEARCH_TIMEOUT = 300
DEFAULT_GENOMICS_SEARCH_ENABLE_HEALTHOMICS = True

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
