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

"""Property-based tests for ECR data models.

Feature: ecr-container-tools
"""

from awslabs.aws_healthomics_mcp_server.models.ecr import (
    UPSTREAM_REGISTRY_URLS,
    ContainerAvailabilityResponse,
    ContainerImage,
    ECRRepository,
    ECRRepositoryListResponse,
    HealthOmicsAccessStatus,
    PullThroughCacheListResponse,
    PullThroughCacheRule,
    UpstreamRegistry,
    ValidationIssue,
    ValidationResult,
)
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st


# =============================================================================
# Hypothesis Strategies for ECR Models
# =============================================================================

# Strategy for generating valid SHA256 digests
sha256_digest_strategy = st.text(
    alphabet='0123456789abcdef',
    min_size=64,
    max_size=64,
).map(lambda s: f'sha256:{s}')

# Strategy for generating valid repository names (ECR naming rules)
repository_name_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_/',  # pragma: allowlist secret
    min_size=1,
    max_size=100,
).filter(lambda s: not s.startswith('-') and not s.startswith('_') and not s.endswith('-'))

# Strategy for generating valid image tags
image_tag_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789.-_',
    min_size=1,
    max_size=128,
).filter(lambda s: not s.startswith('.') and not s.startswith('-'))

# Strategy for generating positive integers for image size
positive_int_or_none_strategy = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=10**12),  # Up to 1TB
)

# Strategy for generating datetime or None
datetime_or_none_strategy = st.one_of(
    st.none(),
    st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 1, 1),
        timezones=st.just(timezone.utc),
    ),
)


# Strategy for generating valid ContainerImage instances
@st.composite
def container_image_strategy(draw):
    """Generate valid ContainerImage instances."""
    return ContainerImage(
        repository_name=draw(repository_name_strategy),
        image_tag=draw(st.one_of(st.none(), image_tag_strategy)),
        image_digest=draw(sha256_digest_strategy),
        image_size_bytes=draw(positive_int_or_none_strategy),
        pushed_at=draw(datetime_or_none_strategy),
        exists=True,  # For available images, exists is always True
    )


# Strategy for generating ContainerAvailabilityResponse with available image
@st.composite
def available_container_response_strategy(draw):
    """Generate ContainerAvailabilityResponse where image is available."""
    image = draw(container_image_strategy())
    return ContainerAvailabilityResponse(
        available=True,
        image=image,
        repository_exists=True,
        is_pull_through_cache=draw(st.booleans()),
        message=draw(st.text(min_size=1, max_size=200)),
    )


# =============================================================================
# Property 6: Container Image Response Completeness
# Feature: ecr-container-tools, Property 6: Container Image Response Completeness
# Validates: Requirements 2.3
# =============================================================================


class TestContainerImageResponseCompleteness:
    """Property 6: Container Image Response Completeness.

    **Validates: Requirements 2.3**

    *For any* container availability check where the image exists, the response SHALL include:
    - image_digest (non-empty string starting with 'sha256:')
    - image_size_bytes (positive integer or None)
    - pushed_at (datetime or None)
    """

    @settings(max_examples=100)
    @given(response=available_container_response_strategy())
    def test_image_digest_format_when_available(self, response: ContainerAvailabilityResponse):
        """Property 6.1: When image is available, image_digest must be non-empty and start with 'sha256:'.

        Feature: ecr-container-tools, Property 6: Container Image Response Completeness
        **Validates: Requirements 2.3**
        """
        # When image is available, image must be present
        assert response.image is not None, 'Available response must include image'

        # image_digest must be non-empty string starting with 'sha256:'
        assert response.image.image_digest is not None, 'image_digest must not be None'
        assert isinstance(response.image.image_digest, str), 'image_digest must be a string'
        assert len(response.image.image_digest) > 0, 'image_digest must be non-empty'
        assert response.image.image_digest.startswith('sha256:'), (
            "image_digest must start with 'sha256:'"
        )

        # Verify the digest has the correct format (sha256: followed by 64 hex characters)
        digest_value = response.image.image_digest[7:]  # Remove 'sha256:' prefix
        assert len(digest_value) == 64, 'SHA256 digest must be 64 hex characters'
        assert all(c in '0123456789abcdef' for c in digest_value), (
            'SHA256 digest must contain only hex characters'
        )

    @settings(max_examples=100)
    @given(response=available_container_response_strategy())
    def test_image_size_bytes_type_when_available(self, response: ContainerAvailabilityResponse):
        """Property 6.2: When image is available, image_size_bytes must be positive integer or None.

        Feature: ecr-container-tools, Property 6: Container Image Response Completeness
        **Validates: Requirements 2.3**
        """
        assert response.image is not None, 'Available response must include image'

        # image_size_bytes must be positive integer or None
        if response.image.image_size_bytes is not None:
            assert isinstance(response.image.image_size_bytes, int), (
                'image_size_bytes must be an integer'
            )
            assert response.image.image_size_bytes > 0, 'image_size_bytes must be positive'

    @settings(max_examples=100)
    @given(response=available_container_response_strategy())
    def test_pushed_at_type_when_available(self, response: ContainerAvailabilityResponse):
        """Property 6.3: When image is available, pushed_at must be datetime or None.

        Feature: ecr-container-tools, Property 6: Container Image Response Completeness
        **Validates: Requirements 2.3**
        """
        assert response.image is not None, 'Available response must include image'

        # pushed_at must be datetime or None
        if response.image.pushed_at is not None:
            assert isinstance(response.image.pushed_at, datetime), (
                'pushed_at must be a datetime instance'
            )

    @settings(max_examples=100)
    @given(response=available_container_response_strategy())
    def test_complete_response_structure_when_available(
        self, response: ContainerAvailabilityResponse
    ):
        """Property 6.4: When image is available, all required fields must be present with correct types.

        Feature: ecr-container-tools, Property 6: Container Image Response Completeness
        **Validates: Requirements 2.3**
        """
        # Response must indicate availability
        assert response.available is True, 'Response must indicate image is available'

        # Image must be present
        assert response.image is not None, 'Available response must include image'

        # Verify all required fields are present
        assert hasattr(response.image, 'image_digest'), 'image must have image_digest field'
        assert hasattr(response.image, 'image_size_bytes'), (
            'image must have image_size_bytes field'
        )
        assert hasattr(response.image, 'pushed_at'), 'image must have pushed_at field'
        assert hasattr(response.image, 'repository_name'), 'image must have repository_name field'

        # Verify image_digest format
        assert response.image.image_digest.startswith('sha256:')

        # Verify image_size_bytes constraint
        if response.image.image_size_bytes is not None:
            assert response.image.image_size_bytes > 0

        # Verify pushed_at type
        if response.image.pushed_at is not None:
            assert isinstance(response.image.pushed_at, datetime)


# =============================================================================
# Additional Unit Tests for ECR Models
# =============================================================================


class TestContainerImageModel:
    """Unit tests for ContainerImage model."""

    def test_container_image_with_all_fields(self):
        """Test ContainerImage with all fields populated."""
        pushed_time = datetime.now(timezone.utc)
        image = ContainerImage(
            repository_name='my-repo/my-image',
            image_tag='v1.0.0',
            image_digest='sha256:' + 'a' * 64,
            image_size_bytes=1024000,
            pushed_at=pushed_time,
            exists=True,
        )

        assert image.repository_name == 'my-repo/my-image'
        assert image.image_tag == 'v1.0.0'
        assert image.image_digest == 'sha256:' + 'a' * 64
        assert image.image_size_bytes == 1024000
        assert image.pushed_at == pushed_time
        assert image.exists is True

    def test_container_image_with_minimal_fields(self):
        """Test ContainerImage with only required fields."""
        image = ContainerImage(
            repository_name='my-repo',
            image_digest='sha256:' + 'b' * 64,
        )

        assert image.repository_name == 'my-repo'
        assert image.image_tag is None
        assert image.image_digest == 'sha256:' + 'b' * 64
        assert image.image_size_bytes is None
        assert image.pushed_at is None
        assert image.exists is True  # Default value

    def test_container_image_exists_false(self):
        """Test ContainerImage with exists=False."""
        image = ContainerImage(
            repository_name='my-repo',
            image_digest='sha256:' + 'c' * 64,
            exists=False,
        )

        assert image.exists is False


class TestContainerAvailabilityResponseModel:
    """Unit tests for ContainerAvailabilityResponse model."""

    def test_available_response_with_image(self):
        """Test ContainerAvailabilityResponse when image is available."""
        image = ContainerImage(
            repository_name='my-repo',
            image_tag='latest',
            image_digest='sha256:' + 'd' * 64,
            image_size_bytes=5000000,
            pushed_at=datetime.now(timezone.utc),
        )

        response = ContainerAvailabilityResponse(
            available=True,
            image=image,
            repository_exists=True,
            is_pull_through_cache=False,
            message='Image found',
        )

        assert response.available is True
        assert response.image is not None
        assert response.image.image_digest.startswith('sha256:')
        assert response.repository_exists is True
        assert response.is_pull_through_cache is False
        assert response.message == 'Image found'

    def test_unavailable_response_without_image(self):
        """Test ContainerAvailabilityResponse when image is not available."""
        response = ContainerAvailabilityResponse(
            available=False,
            image=None,
            repository_exists=True,
            is_pull_through_cache=False,
            message='Image not found',
        )

        assert response.available is False
        assert response.image is None
        assert response.repository_exists is True
        assert response.message == 'Image not found'

    def test_response_repository_not_exists(self):
        """Test ContainerAvailabilityResponse when repository doesn't exist."""
        response = ContainerAvailabilityResponse(
            available=False,
            image=None,
            repository_exists=False,
            is_pull_through_cache=False,
            message='Repository not found',
        )

        assert response.available is False
        assert response.repository_exists is False

    def test_response_pull_through_cache(self):
        """Test ContainerAvailabilityResponse for pull-through cache repository."""
        image = ContainerImage(
            repository_name='docker-hub/nginx',
            image_tag='latest',
            image_digest='sha256:' + 'e' * 64,
        )

        response = ContainerAvailabilityResponse(
            available=True,
            image=image,
            repository_exists=True,
            is_pull_through_cache=True,
            message='Image available via pull-through cache',
        )

        assert response.is_pull_through_cache is True


class TestUpstreamRegistryEnum:
    """Unit tests for UpstreamRegistry enum."""

    def test_upstream_registry_values(self):
        """Test UpstreamRegistry enum values."""
        assert UpstreamRegistry.DOCKER_HUB == 'docker-hub'
        assert UpstreamRegistry.QUAY == 'quay'
        assert UpstreamRegistry.ECR_PUBLIC == 'ecr-public'

    def test_upstream_registry_urls_mapping(self):
        """Test UPSTREAM_REGISTRY_URLS mapping."""
        assert UPSTREAM_REGISTRY_URLS[UpstreamRegistry.DOCKER_HUB] == 'registry-1.docker.io'
        assert UPSTREAM_REGISTRY_URLS[UpstreamRegistry.QUAY] == 'quay.io'
        assert UPSTREAM_REGISTRY_URLS[UpstreamRegistry.ECR_PUBLIC] == 'public.ecr.aws'


class TestHealthOmicsAccessStatusEnum:
    """Unit tests for HealthOmicsAccessStatus enum."""

    def test_healthomics_access_status_values(self):
        """Test HealthOmicsAccessStatus enum values."""
        assert HealthOmicsAccessStatus.ACCESSIBLE == 'accessible'
        assert HealthOmicsAccessStatus.NOT_ACCESSIBLE == 'not_accessible'
        assert HealthOmicsAccessStatus.UNKNOWN == 'unknown'


class TestECRRepositoryModel:
    """Unit tests for ECRRepository model."""

    def test_ecr_repository_with_all_fields(self):
        """Test ECRRepository with all fields populated."""
        created_time = datetime.now(timezone.utc)
        repo = ECRRepository(
            repository_name='my-repo',
            repository_arn='arn:aws:ecr:us-east-1:123456789012:repository/my-repo',
            repository_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo',
            created_at=created_time,
            healthomics_accessible=HealthOmicsAccessStatus.ACCESSIBLE,
            missing_permissions=[],
        )

        assert repo.repository_name == 'my-repo'
        assert repo.healthomics_accessible == HealthOmicsAccessStatus.ACCESSIBLE

    def test_ecr_repository_default_values(self):
        """Test ECRRepository default values."""
        repo = ECRRepository(
            repository_name='my-repo',
            repository_arn='arn:aws:ecr:us-east-1:123456789012:repository/my-repo',
            repository_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo',
        )

        assert repo.created_at is None
        assert repo.healthomics_accessible == HealthOmicsAccessStatus.UNKNOWN
        assert repo.missing_permissions == []


class TestValidationModels:
    """Unit tests for ValidationIssue and ValidationResult models."""

    def test_validation_issue(self):
        """Test ValidationIssue model."""
        issue = ValidationIssue(
            severity='error',
            component='registry_policy',
            message='Missing HealthOmics permissions',
            remediation='Add omics.amazonaws.com to the registry policy',
        )

        assert issue.severity == 'error'
        assert issue.component == 'registry_policy'
        assert issue.message == 'Missing HealthOmics permissions'
        assert issue.remediation == 'Add omics.amazonaws.com to the registry policy'

    def test_validation_result_valid(self):
        """Test ValidationResult when configuration is valid."""
        result = ValidationResult(
            valid=True,
            issues=[],
            pull_through_caches_checked=3,
            repositories_checked=10,
        )

        assert result.valid is True
        assert len(result.issues) == 0
        assert result.pull_through_caches_checked == 3
        assert result.repositories_checked == 10

    def test_validation_result_with_issues(self):
        """Test ValidationResult with validation issues."""
        issues = [
            ValidationIssue(
                severity='error',
                component='registry_policy',
                message='Missing permissions',
                remediation='Add required permissions',
            ),
            ValidationIssue(
                severity='warning',
                component='repository_template',
                message='Template not found',
                remediation='Create repository template',
            ),
        ]

        result = ValidationResult(
            valid=False,
            issues=issues,
            pull_through_caches_checked=2,
            repositories_checked=5,
        )

        assert result.valid is False
        assert len(result.issues) == 2
        assert result.issues[0].severity == 'error'
        assert result.issues[1].severity == 'warning'


class TestPullThroughCacheModels:
    """Unit tests for PullThroughCacheRule and PullThroughCacheListResponse models."""

    def test_pull_through_cache_rule(self):
        """Test PullThroughCacheRule model."""
        created_time = datetime.now(timezone.utc)
        rule = PullThroughCacheRule(
            ecr_repository_prefix='docker-hub',
            upstream_registry_url='registry-1.docker.io',
            credential_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-creds',
            created_at=created_time,
            updated_at=created_time,
            healthomics_usable=True,
            registry_permission_granted=True,
            repository_template_exists=True,
            repository_template_permission_granted=True,
        )

        assert rule.ecr_repository_prefix == 'docker-hub'
        assert rule.upstream_registry_url == 'registry-1.docker.io'
        assert rule.healthomics_usable is True

    def test_pull_through_cache_rule_defaults(self):
        """Test PullThroughCacheRule default values."""
        rule = PullThroughCacheRule(
            ecr_repository_prefix='quay',
            upstream_registry_url='quay.io',
        )

        assert rule.credential_arn is None
        assert rule.created_at is None
        assert rule.healthomics_usable is False
        assert rule.registry_permission_granted is False
        assert rule.repository_template_exists is False
        assert rule.repository_template_permission_granted is False

    def test_pull_through_cache_list_response(self):
        """Test PullThroughCacheListResponse model."""
        rules = [
            PullThroughCacheRule(
                ecr_repository_prefix='docker-hub',
                upstream_registry_url='registry-1.docker.io',
            ),
            PullThroughCacheRule(
                ecr_repository_prefix='quay',
                upstream_registry_url='quay.io',
            ),
        ]

        response = PullThroughCacheListResponse(
            rules=rules,
            next_token='next-page-token',
        )

        assert len(response.rules) == 2
        assert response.next_token == 'next-page-token'

    def test_pull_through_cache_list_response_empty(self):
        """Test PullThroughCacheListResponse with empty rules."""
        response = PullThroughCacheListResponse(rules=[])

        assert len(response.rules) == 0
        assert response.next_token is None


class TestECRRepositoryListResponse:
    """Unit tests for ECRRepositoryListResponse model."""

    def test_ecr_repository_list_response(self):
        """Test ECRRepositoryListResponse model."""
        repos = [
            ECRRepository(
                repository_name='repo1',
                repository_arn='arn:aws:ecr:us-east-1:123456789012:repository/repo1',
                repository_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/repo1',
            ),
            ECRRepository(
                repository_name='repo2',
                repository_arn='arn:aws:ecr:us-east-1:123456789012:repository/repo2',
                repository_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/repo2',
            ),
        ]

        response = ECRRepositoryListResponse(
            repositories=repos,
            next_token='next-token',
            total_count=100,
        )

        assert len(response.repositories) == 2
        assert response.next_token == 'next-token'
        assert response.total_count == 100

    def test_ecr_repository_list_response_empty(self):
        """Test ECRRepositoryListResponse with empty repositories."""
        response = ECRRepositoryListResponse(
            repositories=[],
            total_count=0,
        )

        assert len(response.repositories) == 0
        assert response.next_token is None
        assert response.total_count == 0
