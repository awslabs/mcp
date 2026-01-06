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

"""Response models for Common Resource operations."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# IAM Models
# ============================================================================


class RoleSummary(BaseModel):
    """Summary of an IAM role."""

    role_name: str
    role_arn: str
    description: Optional[str] = None
    create_date: str
    assume_role_policy_document: Dict[str, Any]


class PolicySummary(BaseModel):
    """Summary of an IAM policy."""

    policy_type: str
    description: Optional[str] = None
    policy_document: Optional[Dict[str, Any]] = None


# ============================================================================
# Data Models
# ============================================================================


class ServiceRolesData(BaseModel):
    """Data model for listing IAM roles for a specific service."""

    service_type: str
    roles: List[RoleSummary]
    operation: str = 'get-roles-for-service'


class RoleDescriptionData(BaseModel):
    """Data model for describing an IAM role."""

    role_arn: str
    assume_role_policy_document: Dict[str, Any]
    description: Optional[str] = None
    managed_policies: List[PolicySummary]
    inline_policies: List[PolicySummary]
    operation: str = 'get-policies-for-role'


class AddInlinePolicyData(BaseModel):
    """Data model for adding an inline policy to an IAM role."""

    policy_name: str
    role_name: str
    permissions_added: Union[Dict[str, Any], List[Dict[str, Any]]]
    operation: str = 'add-inline-policy'


class CreateRoleData(BaseModel):
    """Data model for creating an IAM role."""

    role_name: str
    role_arn: str
    operation: str = 'create-data-processing-role'


# ============================================================================
# S3 Models
# ============================================================================


class BucketInfo(BaseModel):
    """Information about an S3 bucket."""

    name: str
    creation_date: str
    region: str
    object_count: str
    last_modified: str
    idle_status: str


class ListS3BucketsData(BaseModel):
    """Data model for listing S3 buckets."""

    region: str
    bucket_count: int
    buckets: List[BucketInfo]
    operation: str = 'list-s3-buckets'


class UploadToS3Data(BaseModel):
    """Data model for uploading to S3."""

    s3_uri: str
    bucket_name: str
    s3_key: str
    operation: str = 'upload-to-s3'


class AnalyzeS3UsageData(BaseModel):
    """Data model for S3 usage analysis."""

    analysis_summary: str
    service_usage: Dict[str, List[str]]
    operation: str = 'analyze-s3-usage-for-data-processing'
