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

"""ECR data models for container registry operations and HealthOmics integration."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class UpstreamRegistry(str, Enum):
    """Supported upstream registries for pull-through cache."""

    DOCKER_HUB = 'docker-hub'
    QUAY = 'quay'
    ECR_PUBLIC = 'ecr-public'


UPSTREAM_REGISTRY_URLS = {
    UpstreamRegistry.DOCKER_HUB: 'registry-1.docker.io',
    UpstreamRegistry.QUAY: 'quay.io',
    UpstreamRegistry.ECR_PUBLIC: 'public.ecr.aws',
}


class HealthOmicsAccessStatus(str, Enum):
    """Status of HealthOmics access to an ECR resource."""

    ACCESSIBLE = 'accessible'
    NOT_ACCESSIBLE = 'not_accessible'
    UNKNOWN = 'unknown'


class ECRRepository(BaseModel):
    """ECR repository information with HealthOmics access status."""

    repository_name: str
    repository_arn: str
    repository_uri: str
    created_at: Optional[datetime] = None
    healthomics_accessible: HealthOmicsAccessStatus = HealthOmicsAccessStatus.UNKNOWN
    missing_permissions: List[str] = Field(default_factory=list)


class ECRRepositoryListResponse(BaseModel):
    """Response for listing ECR repositories."""

    repositories: List[ECRRepository]
    next_token: Optional[str] = None
    total_count: int


class ContainerImage(BaseModel):
    """Container image information."""

    repository_name: str
    image_tag: Optional[str] = None
    image_digest: str
    image_size_bytes: Optional[int] = None
    pushed_at: Optional[datetime] = None
    exists: bool = True


class ContainerAvailabilityResponse(BaseModel):
    """Response for container availability check."""

    available: bool
    image: Optional[ContainerImage] = None
    repository_exists: bool = True
    is_pull_through_cache: bool = False
    healthomics_accessible: HealthOmicsAccessStatus = HealthOmicsAccessStatus.UNKNOWN
    missing_permissions: List[str] = Field(default_factory=list)
    message: str
    pull_through_initiated: bool = False
    pull_through_initiation_message: Optional[str] = None


class PullThroughCacheRule(BaseModel):
    """Pull-through cache rule information."""

    ecr_repository_prefix: str
    upstream_registry_url: str
    credential_arn: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    healthomics_usable: bool = False
    registry_permission_granted: bool = False
    repository_template_exists: bool = False
    repository_template_permission_granted: bool = False


class PullThroughCacheListResponse(BaseModel):
    """Response for listing pull-through cache rules."""

    rules: List[PullThroughCacheRule]
    next_token: Optional[str] = None


class ValidationIssue(BaseModel):
    """A validation issue found during configuration check."""

    severity: str  # 'error', 'warning', 'info'
    component: str  # 'registry_policy', 'repository_template', 'pull_through_cache'
    message: str
    remediation: str


class ValidationResult(BaseModel):
    """Result of HealthOmics ECR configuration validation."""

    valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    pull_through_caches_checked: int = 0
    repositories_checked: int = 0


class GrantAccessResponse(BaseModel):
    """Response for granting HealthOmics access to an ECR repository."""

    success: bool
    repository_name: str
    policy_updated: bool = False
    policy_created: bool = False
    previous_healthomics_accessible: HealthOmicsAccessStatus = HealthOmicsAccessStatus.UNKNOWN
    current_healthomics_accessible: HealthOmicsAccessStatus = HealthOmicsAccessStatus.UNKNOWN
    message: str


class CloneContainerResponse(BaseModel):
    """Response for cloning a container to ECR."""

    success: bool
    source_image: str
    source_registry: str
    source_digest: Optional[str] = None
    ecr_uri: Optional[str] = None
    ecr_digest: Optional[str] = None
    repository_created: bool = False
    used_pull_through_cache: bool = False
    used_codebuild: bool = False
    pull_through_cache_prefix: Optional[str] = None
    healthomics_accessible: HealthOmicsAccessStatus = HealthOmicsAccessStatus.UNKNOWN
    message: str
