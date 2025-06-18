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

"""Constants used throughout the S3 Tables MCP Server.

This module contains all the constant values used across the S3 Tables MCP Server,
including version information, regex patterns for validation, and field definitions
for Pydantic models.
"""

from pydantic import Field


# Patterns
TABLE_BUCKET_NAME_PATTERN = r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]'
"""
Regex pattern for validating S3 bucket names.
Valid bucket names must:
- Be between 3 and 63 characters long
- Start and end with a letter or number
- Contain only lowercase letters, numbers, and hyphens
- Not contain consecutive hyphens
"""

TABLE_BUCKET_ARN_PATTERN = (
    r'arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[a-z0-9_-]{3,63}'
)
"""
Regex pattern for validating S3 bucket ARNs.
Format: arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[bucket-name]
Example: arn:aws:s3:::my-bucket
"""

TABLE_NAME_PATTERN = r'[0-9a-z_]*'
"""
Regex pattern for validating table names.
Valid table names must:
- Contain only lowercase letters, numbers, and underscores
- Have a maximum length of 255 characters
"""

TABLE_ARN_PATTERN = (
    r'arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[a-z0-9_-]{3,63}/table/[0-9a-f-]{36}'
)
"""
Regex pattern for validating table ARNs.
Format: arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[bucket-name]/table/[uuid]
Example: arn:aws:s3:::my-bucket/table/123e4567-e89b-12d3-a456-426614174000
"""

# Field Definitions
TABLE_BUCKET_ARN_FIELD = Field(
    ...,
    description='Table bucket ARN',
    pattern=TABLE_BUCKET_ARN_PATTERN,
    min_length=1,
    max_length=2048,
)
"""
Pydantic field for table bucket ARN validation.
Required field that must match the TABLE_BUCKET_ARN_PATTERN.
"""

TABLE_ARN_FIELD = Field(..., description='Table ARN', pattern=TABLE_ARN_PATTERN)
"""
Pydantic field for table ARN validation.
Required field that must match the TABLE_ARN_PATTERN.
"""

NAMESPACE_NAME_FIELD = Field(
    ..., description='Namespace name', pattern=r'^[0-9a-z_]+$', min_length=1, max_length=255
)
"""
Pydantic field for namespace name validation.
Required field that must:
- Contain only lowercase letters, numbers, and underscores
- Have a maximum length of 255 characters
"""

TABLE_NAME_FIELD = Field(
    ..., description='Table name', pattern=TABLE_NAME_PATTERN, min_length=1, max_length=255
)
"""
Pydantic field for table name validation.
Required field that must:
- Match the TABLE_NAME_PATTERN
- Have a maximum length of 255 characters
"""

REGION_NAME_FIELD = Field(default=None, description='AWS region name')
"""
Pydantic field for AWS region name.
Optional field that can be used to specify the AWS region for operations.
Example values: 'us-east-1', 'eu-west-1', 'ap-southeast-2'
"""

# Query-specific fields
QUERY_FIELD = Field(
    default=None,
    description='Optional SQL query. If not provided, will execute SELECT * FROM table. Must be a read operation.',
    min_length=1,
    max_length=10000,
)
"""
Pydantic field for SQL query validation.
Optional field that must be a valid read operation.
"""

OUTPUT_LOCATION_FIELD = Field(
    default=None,
    description='Optional S3 location for query results. If not provided, will use default Athena results bucket.',
    pattern=r'^s3://[a-z0-9-]+/[a-z0-9-./]*$',
    min_length=1,
    max_length=2048,
)
"""
Pydantic field for output location validation.
Optional field that must be a valid S3 URI.
"""

WORKGROUP_FIELD = Field(
    default='primary',
    description='Athena workgroup to use for query execution.',
    pattern=r'^[a-zA-Z0-9_-]+$',
    min_length=1,
    max_length=128,
)
"""
Pydantic field for workgroup validation.
Optional field that must contain only letters, numbers, hyphens, and underscores.
Defaults to 'primary'.
"""
