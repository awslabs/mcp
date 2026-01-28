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

"""Property-based tests for ECR tools.

Feature: ecr-container-tools
"""

import botocore
import botocore.exceptions
import json
import pytest
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_ECR_PREFIXES
from awslabs.aws_healthomics_mcp_server.models.ecr import (
    UPSTREAM_REGISTRY_URLS,
    UpstreamRegistry,
)
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
    _is_pull_through_cache_repository,
    check_container_availability,
    create_pull_through_cache_for_healthomics,
    grant_healthomics_repository_access,
    list_ecr_repositories,
    list_pull_through_cache_rules,
)
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Hypothesis Strategies for ECR API Responses
# =============================================================================

# Strategy for generating valid pagination tokens
# AWS pagination tokens are typically base64-encoded strings
pagination_token_strategy = st.one_of(
    # Non-empty tokens (various formats AWS might use)
    st.text(
        alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=',  # pragma: allowlist secret
        min_size=1,
        max_size=500,
    ),
    # UUID-like tokens
    st.uuids().map(str),
    # Base64-like tokens
    st.binary(min_size=10, max_size=100).map(lambda b: b.hex()),
)

# Strategy for generating optional pagination tokens (including None for last page)
optional_pagination_token_strategy = st.one_of(
    st.none(),
    pagination_token_strategy,
)

# Strategy for generating valid ECR repository names
repository_name_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_/',  # pragma: allowlist secret
    min_size=1,
    max_size=100,
).filter(
    lambda s: (
        not s.startswith('-')
        and not s.startswith('_')
        and not s.startswith('/')
        and not s.endswith('-')
        and not s.endswith('/')
        and '//' not in s
    )
)

# Strategy for generating AWS account IDs
account_id_strategy = st.text(
    alphabet='0123456789',
    min_size=12,
    max_size=12,
)

# Strategy for generating AWS regions
region_strategy = st.sampled_from(
    [
        'us-east-1',
        'us-east-2',
        'us-west-1',
        'us-west-2',
        'eu-west-1',
        'eu-west-2',
        'eu-central-1',
        'ap-northeast-1',
        'ap-southeast-1',
        'ap-southeast-2',
    ]
)


@st.composite
def ecr_repository_strategy(draw) -> Dict[str, Any]:
    """Generate a valid ECR repository response object."""
    repo_name = draw(repository_name_strategy)
    account_id = draw(account_id_strategy)
    region = draw(region_strategy)

    return {
        'repositoryArn': f'arn:aws:ecr:{region}:{account_id}:repository/{repo_name}',
        'registryId': account_id,
        'repositoryName': repo_name,
        'repositoryUri': f'{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}',
        'createdAt': datetime.now(timezone.utc),
        'imageTagMutability': draw(st.sampled_from(['MUTABLE', 'IMMUTABLE'])),
        'imageScanningConfiguration': {'scanOnPush': draw(st.booleans())},
        'encryptionConfiguration': {'encryptionType': 'AES256'},
    }


@st.composite
def ecr_describe_repositories_response_strategy(draw) -> Dict[str, Any]:
    """Generate a valid ECR describe_repositories API response.

    This strategy generates responses that may or may not include a nextToken,
    simulating paginated AWS API responses.
    """
    # Generate 0-10 repositories
    num_repos = draw(st.integers(min_value=0, max_value=10))
    repositories = [draw(ecr_repository_strategy()) for _ in range(num_repos)]

    # Generate optional nextToken
    next_token = draw(optional_pagination_token_strategy)

    response: Dict[str, Any] = {
        'repositories': repositories,
    }

    # Only include nextToken if it's not None (simulating AWS behavior)
    if next_token is not None:
        response['nextToken'] = next_token

    return response


@st.composite
def ecr_response_with_token_strategy(draw) -> Dict[str, Any]:
    """Generate an ECR describe_repositories response that ALWAYS has a nextToken.

    This is used to specifically test the pagination token preservation property.
    """
    # Generate 1-10 repositories (at least one to make it realistic)
    num_repos = draw(st.integers(min_value=1, max_value=10))
    repositories = [draw(ecr_repository_strategy()) for _ in range(num_repos)]

    # Always generate a non-empty nextToken
    next_token = draw(pagination_token_strategy)

    return {
        'repositories': repositories,
        'nextToken': next_token,
    }


@st.composite
def ecr_response_without_token_strategy(draw) -> Dict[str, Any]:
    """Generate an ECR describe_repositories response that NEVER has a nextToken.

    This simulates the last page of results.
    """
    # Generate 0-10 repositories
    num_repos = draw(st.integers(min_value=0, max_value=10))
    repositories = [draw(ecr_repository_strategy()) for _ in range(num_repos)]

    return {
        'repositories': repositories,
        # No nextToken key - simulating last page
    }


# =============================================================================
# Hypothesis Strategies for Pull-Through Cache Detection
# =============================================================================

# Strategy for generating valid image suffixes (the part after the prefix/)
image_suffix_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_/',  # pragma: allowlist secret
    min_size=1,
    max_size=50,
).filter(lambda s: (not s.startswith('/') and not s.endswith('/') and '//' not in s))

# Strategy for generating image tags
image_tag_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789.-_',  # pragma: allowlist secret
    min_size=1,
    max_size=128,
).filter(lambda s: not s.startswith('.') and not s.startswith('-'))


@st.composite
def pull_through_cache_repository_strategy(draw) -> str:
    """Generate a repository name that matches a pull-through cache prefix.

    Pull-through cache repositories follow the pattern: {prefix}/{image-path}
    where prefix is one of: docker-hub, quay, ecr-public
    """
    # Choose one of the default ECR prefixes
    prefix = draw(st.sampled_from(list(DEFAULT_ECR_PREFIXES.values())))
    # Generate a valid image suffix
    suffix = draw(image_suffix_strategy)
    return f'{prefix}/{suffix}'


@st.composite
def non_pull_through_cache_repository_strategy(draw) -> str:
    """Generate a repository name that does NOT match any pull-through cache prefix.

    These are regular ECR repositories that don't start with docker-hub/, quay/, or ecr-public/
    """
    # Generate a repository name that doesn't start with any known prefix
    prefixes_to_avoid = list(DEFAULT_ECR_PREFIXES.values())

    # Strategy 1: Use a completely different prefix
    custom_prefix = draw(
        st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',  # pragma: allowlist secret
            min_size=1,
            max_size=20,
        ).filter(
            lambda s: (
                not s.startswith('-')
                and not s.startswith('_')
                and s not in prefixes_to_avoid
                and not any(s.startswith(p) for p in prefixes_to_avoid)
            )
        )
    )

    # Optionally add a suffix
    has_suffix = draw(st.booleans())
    if has_suffix:
        suffix = draw(image_suffix_strategy)
        return f'{custom_prefix}/{suffix}'
    return custom_prefix


# =============================================================================
# Property 7: Pull-Through Cache Detection
# Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
# Validates: Requirements 2.6
# =============================================================================


def _create_mock_ptc_rules_response(prefixes: list) -> dict:
    """Create a mock response for describe_pull_through_cache_rules with given prefixes."""
    return {
        'pullThroughCacheRules': [
            {'ecrRepositoryPrefix': prefix, 'upstreamRegistryUrl': f'https://{prefix}.io'}
            for prefix in prefixes
        ]
    }


def _create_mock_ecr_client() -> MagicMock:
    """Create a mock ECR client with default PTC rules configured.

    This ensures that _is_pull_through_cache_repository doesn't hang waiting
    for a real AWS API response when tests don't explicitly configure PTC rules.
    Also configures a default repository policy that grants HealthOmics access.
    """
    mock_client = MagicMock()
    # Default to returning the standard PTC prefixes
    mock_client.describe_pull_through_cache_rules.return_value = _create_mock_ptc_rules_response(
        list(DEFAULT_ECR_PREFIXES.values())
    )
    # Default to returning a policy that grants HealthOmics access
    mock_client.get_repository_policy.return_value = {
        'policyText': json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': 'HealthOmicsAccess',
                        'Effect': 'Allow',
                        'Principal': {'Service': 'omics.amazonaws.com'},
                        'Action': [
                            'ecr:BatchGetImage',
                            'ecr:GetDownloadUrlForLayer',
                        ],
                    }
                ],
            }
        )
    }
    return mock_client


class TestPullThroughCacheDetection:
    """Property 7: Pull-Through Cache Detection.

    **Validates: Requirements 2.6**

    *For any* repository name that matches a configured pull-through cache prefix
    pattern, the container availability response SHALL set `is_pull_through_cache: True`.
    """

    @settings(max_examples=100)
    @given(repository_name=pull_through_cache_repository_strategy())
    def test_pull_through_cache_prefix_detected(self, repository_name: str):
        """Property 7.1: Repository names with PTC prefixes are detected.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that starts with a pull-through cache prefix
        (docker-hub/, quay/, ecr-public/) followed by a slash, the
        _is_pull_through_cache_repository function SHALL return True when
        a matching pull-through cache rule exists.
        """
        # Mock ECR client to return pull-through cache rules for default prefixes
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is True, (
            f'Expected repository "{repository_name}" to be detected as pull-through cache, '
            f'but got {result}'
        )

    @settings(max_examples=100)
    @given(repository_name=non_pull_through_cache_repository_strategy())
    def test_non_pull_through_cache_prefix_not_detected(self, repository_name: str):
        """Property 7.2: Repository names without PTC prefixes are not detected.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that does NOT start with a pull-through cache prefix
        followed by a slash, the _is_pull_through_cache_repository function SHALL
        return False.
        """
        # Mock ECR client to return pull-through cache rules for default prefixes
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is False, (
            f'Expected repository "{repository_name}" to NOT be detected as pull-through cache, '
            f'but got {result}'
        )

    @settings(max_examples=100)
    @given(
        prefix=st.sampled_from(list(DEFAULT_ECR_PREFIXES.values())),
        suffix=image_suffix_strategy,
    )
    def test_all_default_prefixes_detected(self, prefix: str, suffix: str):
        """Property 7.3: All default ECR prefixes are correctly detected.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any of the default ECR prefixes (docker-hub, quay, ecr-public),
        a repository name in the format {prefix}/{suffix} SHALL be detected
        as a pull-through cache repository when a matching rule exists.
        """
        repository_name = f'{prefix}/{suffix}'

        # Mock ECR client to return pull-through cache rules for default prefixes
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is True, (
            f'Expected repository "{repository_name}" with prefix "{prefix}" '
            f'to be detected as pull-through cache'
        )

    @settings(max_examples=100)
    @given(prefix=st.sampled_from(list(DEFAULT_ECR_PREFIXES.values())))
    def test_prefix_without_slash_not_detected(self, prefix: str):
        """Property 7.4: Prefix alone without trailing slash is not detected.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        A repository name that exactly matches a prefix (without a trailing slash
        and image path) SHALL NOT be detected as a pull-through cache repository.
        """
        # Mock ECR client to return pull-through cache rules for default prefixes
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            # Just the prefix without a slash
            result = _is_pull_through_cache_repository(prefix)

        assert result is False, (
            f'Expected repository "{prefix}" (prefix only, no slash) '
            f'to NOT be detected as pull-through cache'
        )

    def test_custom_prefix_detected_when_rule_exists(self):
        """Property 7.4a: Custom PTC prefixes are detected when rules exist.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that matches a custom pull-through cache prefix
        (not just default prefixes), the function SHALL return True when a
        matching rule exists in ECR.
        """
        custom_prefix = 'my-custom-registry'
        repository_name = f'{custom_prefix}/my-image'

        # Mock ECR client to return a custom pull-through cache rule
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': custom_prefix,
                    'upstreamRegistryUrl': 'https://custom.registry.io',
                }
            ]
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is True, (
            f'Expected repository "{repository_name}" with custom prefix "{custom_prefix}" '
            f'to be detected as pull-through cache when rule exists'
        )

    def test_fallback_to_default_prefixes_on_access_denied(self):
        """Property 7.4b: Falls back to default prefix check on AccessDeniedException.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        When the describe_pull_through_cache_rules API call fails with
        AccessDeniedException, the function SHALL fall back to checking
        against default prefixes.
        """
        # Test with a default prefix repository
        repository_name = 'docker-hub/library/ubuntu'

        # Mock ECR client to raise AccessDeniedException
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribePullThroughCacheRules')
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is True, (
            f'Expected repository "{repository_name}" to be detected as pull-through cache '
            f'using fallback to default prefixes'
        )

    def test_no_rules_returns_false(self):
        """Property 7.4c: Returns False when no PTC rules exist.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        When no pull-through cache rules exist in the registry, the function
        SHALL return False for any repository name.
        """
        repository_name = 'docker-hub/library/ubuntu'

        # Mock ECR client to return empty rules
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _is_pull_through_cache_repository(repository_name)

        assert result is False, (
            f'Expected repository "{repository_name}" to NOT be detected as pull-through cache '
            f'when no rules exist'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(repository_name=pull_through_cache_repository_strategy())
    async def test_check_container_availability_sets_is_pull_through_cache_true(
        self, repository_name: str
    ):
        """Property 7.5: check_container_availability sets is_pull_through_cache=True for PTC repos.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that matches a pull-through cache prefix pattern,
        the check_container_availability response SHALL set is_pull_through_cache: True.
        """
        # Create mock ECR client that returns an image and PTC rules
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123def456',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name=repository_name,
                image_tag='latest',
                image_digest=None,
            )

        assert result['is_pull_through_cache'] is True, (
            f'Expected is_pull_through_cache=True for repository "{repository_name}", '
            f'but got {result["is_pull_through_cache"]}'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(repository_name=non_pull_through_cache_repository_strategy())
    async def test_check_container_availability_sets_is_pull_through_cache_false(
        self, repository_name: str
    ):
        """Property 7.6: check_container_availability sets is_pull_through_cache=False for non-PTC repos.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that does NOT match a pull-through cache prefix pattern,
        the check_container_availability response SHALL set is_pull_through_cache: False.
        """
        # Create mock ECR client that returns an image and PTC rules
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123def456',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name=repository_name,
                image_tag='latest',
                image_digest=None,
            )

        assert result['is_pull_through_cache'] is False, (
            f'Expected is_pull_through_cache=False for repository "{repository_name}", '
            f'but got {result["is_pull_through_cache"]}'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(repository_name=pull_through_cache_repository_strategy())
    async def test_ptc_detection_when_image_not_found(self, repository_name: str):
        """Property 7.7: PTC detection works even when image is not found.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that matches a pull-through cache prefix pattern,
        the is_pull_through_cache field SHALL be True even when the image is not found.
        """
        import botocore.exceptions

        # Create mock ECR client that raises ImageNotFoundException
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name=repository_name,
                image_tag='latest',
                image_digest=None,
            )

        assert result['is_pull_through_cache'] is True, (
            f'Expected is_pull_through_cache=True for repository "{repository_name}" '
            f'even when image not found, but got {result["is_pull_through_cache"]}'
        )
        assert result['available'] is False

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(repository_name=pull_through_cache_repository_strategy())
    async def test_ptc_detection_when_repository_not_found(self, repository_name: str):
        """Property 7.8: PTC detection works even when repository is not found.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that matches a pull-through cache prefix pattern,
        the is_pull_through_cache field SHALL be True even when the repository
        does not exist (it may be created on first pull).
        """
        import botocore.exceptions

        # Create mock ECR client that raises RepositoryNotFoundException
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name=repository_name,
                image_tag='latest',
                image_digest=None,
            )

        assert result['is_pull_through_cache'] is True, (
            f'Expected is_pull_through_cache=True for repository "{repository_name}" '
            f'even when repository not found, but got {result["is_pull_through_cache"]}'
        )
        assert result['repository_exists'] is False

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        repository_name=pull_through_cache_repository_strategy(),
        image_tag=image_tag_strategy,
    )
    async def test_ptc_detection_with_various_tags(self, repository_name: str, image_tag: str):
        """Property 7.9: PTC detection is independent of image tag.

        Feature: ecr-container-tools, Property 7: Pull-Through Cache Detection
        **Validates: Requirements 2.6**

        For any repository name that matches a pull-through cache prefix pattern,
        the is_pull_through_cache field SHALL be True regardless of the image tag
        being checked.
        """
        # Create mock ECR client that returns an image and PTC rules
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123def456',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': [image_tag],
                }
            ]
        }
        mock_client.describe_pull_through_cache_rules.return_value = (
            _create_mock_ptc_rules_response(list(DEFAULT_ECR_PREFIXES.values()))
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name=repository_name,
                image_tag=image_tag,
                image_digest=None,
            )

        assert result['is_pull_through_cache'] is True, (
            f'Expected is_pull_through_cache=True for repository "{repository_name}" '
            f'with tag "{image_tag}", but got {result["is_pull_through_cache"]}'
        )


# =============================================================================
# Property 8: Pagination Token Preservation
# Feature: ecr-container-tools, Property 8: Pagination Token Preservation
# Validates: Requirements 1.4
# =============================================================================


class TestPaginationTokenPreservation:
    """Property 8: Pagination Token Preservation.

    **Validates: Requirements 1.4**

    *For any* list operation (repositories or pull-through cache rules) where the
    AWS response contains a `nextToken`, the tool response SHALL include that token
    in the `next_token` field.
    """

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(aws_response=ecr_response_with_token_strategy())
    async def test_next_token_preserved_when_present(self, aws_response: Dict[str, Any]):
        """Property 8.1: When AWS response contains nextToken, tool response includes it.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        For any AWS ECR describe_repositories response that contains a nextToken,
        the list_ecr_repositories tool SHALL include that exact token in the
        next_token field of its response.
        """
        # Extract the expected token from the AWS response
        expected_token = aws_response['nextToken']

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Verify the token is preserved
        assert 'next_token' in result, (
            'Response must include next_token field when AWS response has nextToken'
        )
        assert result['next_token'] == expected_token, (
            f'Expected next_token to be "{expected_token}", got "{result["next_token"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(aws_response=ecr_response_without_token_strategy())
    async def test_next_token_none_when_not_present(self, aws_response: Dict[str, Any]):
        """Property 8.2: When AWS response has no nextToken, tool response has None.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        For any AWS ECR describe_repositories response that does NOT contain a
        nextToken (last page), the list_ecr_repositories tool SHALL have
        next_token=None in its response.
        """
        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Verify the token is None
        assert 'next_token' in result, 'Response must include next_token field'
        assert result['next_token'] is None, (
            f'Expected next_token to be None when AWS has no nextToken, '
            f'got "{result["next_token"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(aws_response=ecr_describe_repositories_response_strategy())
    async def test_next_token_matches_aws_response(self, aws_response: Dict[str, Any]):
        """Property 8.3: Tool next_token always matches AWS nextToken exactly.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        For any AWS ECR describe_repositories response, the list_ecr_repositories
        tool's next_token field SHALL exactly match the AWS response's nextToken
        (or be None if nextToken is absent).
        """
        # Determine expected token
        expected_token = aws_response.get('nextToken')

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Verify the token matches exactly
        assert result['next_token'] == expected_token, (
            f'Expected next_token to be "{expected_token}", got "{result["next_token"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        input_token=pagination_token_strategy,
        aws_response=ecr_response_with_token_strategy(),
    )
    async def test_input_token_passed_to_aws_and_output_preserved(
        self, input_token: str, aws_response: Dict[str, Any]
    ):
        """Property 8.4: Input token is passed to AWS and output token is preserved.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        When a next_token is provided as input, it SHALL be passed to the AWS API,
        and the response's nextToken SHALL be preserved in the output.
        """
        expected_output_token = aws_response['nextToken']

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=input_token,
                filter_healthomics_accessible=False,
            )

        # Verify the input token was passed to AWS
        mock_client.describe_repositories.assert_called_once()
        call_kwargs = mock_client.describe_repositories.call_args[1]
        assert call_kwargs.get('nextToken') == input_token, (
            f'Expected input token "{input_token}" to be passed to AWS API'
        )

        # Verify the output token is preserved
        assert result['next_token'] == expected_output_token, (
            f'Expected output next_token to be "{expected_output_token}", '
            f'got "{result["next_token"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        token=pagination_token_strategy,
        num_repos=st.integers(min_value=0, max_value=5),
    )
    async def test_token_preserved_regardless_of_repository_count(
        self, token: str, num_repos: int
    ):
        """Property 8.5: Token preservation is independent of repository count.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        The pagination token SHALL be preserved regardless of how many repositories
        are returned in the response (including zero repositories).
        """
        # Create AWS response with specified number of repos
        repositories = []
        for i in range(num_repos):
            repositories.append(
                {
                    'repositoryArn': f'arn:aws:ecr:us-east-1:123456789012:repository/repo{i}',
                    'registryId': '123456789012',
                    'repositoryName': f'repo{i}',
                    'repositoryUri': f'123456789012.dkr.ecr.us-east-1.amazonaws.com/repo{i}',
                    'createdAt': datetime.now(timezone.utc),
                }
            )

        aws_response = {
            'repositories': repositories,
            'nextToken': token,
        }

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Verify the token is preserved regardless of repo count
        assert result['next_token'] == token, (
            f'Expected next_token "{token}" to be preserved with {num_repos} repositories, '
            f'got "{result["next_token"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        token=pagination_token_strategy,
        filter_accessible=st.booleans(),
    )
    async def test_token_preserved_regardless_of_filter(self, token: str, filter_accessible: bool):
        """Property 8.6: Token preservation is independent of filtering.

        Feature: ecr-container-tools, Property 8: Pagination Token Preservation
        **Validates: Requirements 1.4**

        The pagination token SHALL be preserved regardless of whether
        filter_healthomics_accessible is True or False.
        """
        # Create AWS response with a repository
        aws_response = {
            'repositories': [
                {
                    'repositoryArn': 'arn:aws:ecr:us-east-1:123456789012:repository/test-repo',
                    'registryId': '123456789012',
                    'repositoryName': 'test-repo',
                    'repositoryUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
            'nextToken': token,
        }

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = aws_response
        # Mock get_repository_policy to return RepositoryPolicyNotFoundException
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        # Create mock context
        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=filter_accessible,
            )

        # Verify the token is preserved regardless of filter setting
        assert result['next_token'] == token, (
            f'Expected next_token "{token}" to be preserved with '
            f'filter_healthomics_accessible={filter_accessible}, '
            f'got "{result["next_token"]}"'
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _create_policy_not_found_exception():
    """Create a mock RepositoryPolicyNotFoundException for testing."""
    import botocore.exceptions

    error_response = {
        'Error': {
            'Code': 'RepositoryPolicyNotFoundException',
            'Message': 'Repository policy does not exist',
        }
    }
    return botocore.exceptions.ClientError(error_response, 'GetRepositoryPolicy')


def _create_access_denied_exception(operation_name: str = 'DescribeRepositories'):
    """Create a mock AccessDeniedException for testing."""
    import botocore.exceptions

    error_response = {
        'Error': {
            'Code': 'AccessDeniedException',
            'Message': 'User is not authorized to perform this operation',
        }
    }
    return botocore.exceptions.ClientError(error_response, operation_name)


def _create_client_error(code: str, message: str, operation_name: str = 'DescribeRepositories'):
    """Create a mock ClientError for testing."""
    import botocore.exceptions

    error_response = {
        'Error': {
            'Code': code,
            'Message': message,
        }
    }
    return botocore.exceptions.ClientError(error_response, operation_name)


def _create_healthomics_policy() -> str:
    """Create a sample repository policy that grants HealthOmics access."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                    'Resource': '*',
                }
            ],
        }
    )


def _create_partial_healthomics_policy() -> str:
    """Create a sample repository policy with partial HealthOmics permissions."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'PartialHealthOmicsAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage'],  # Missing GetDownloadUrlForLayer
                    'Resource': '*',
                }
            ],
        }
    )


def _create_sample_repository(
    name: str = 'test-repo',
    account_id: str = '123456789012',
    region: str = 'us-east-1',
) -> Dict[str, Any]:
    """Create a sample ECR repository response object."""
    return {
        'repositoryArn': f'arn:aws:ecr:{region}:{account_id}:repository/{name}',
        'registryId': account_id,
        'repositoryName': name,
        'repositoryUri': f'{account_id}.dkr.ecr.{region}.amazonaws.com/{name}',
        'createdAt': datetime.now(timezone.utc),
        'imageTagMutability': 'MUTABLE',
        'imageScanningConfiguration': {'scanOnPush': False},
        'encryptionConfiguration': {'encryptionType': 'AES256'},
    }


# =============================================================================
# Unit Tests for list_ecr_repositories
# Feature: ecr-container-tools
# Task 5.3: Write unit tests for list_ecr_repositories
# Requirements: 1.1, 1.4, 1.5
# =============================================================================


class TestListECRRepositoriesUnit:
    """Unit tests for list_ecr_repositories function.

    These tests cover:
    1. Successful listing with mocked ECR responses
    2. Pagination handling (passing next_token, receiving next_token)
    3. Error scenarios (AccessDeniedException, other ClientErrors, BotoCoreError)
    4. Filter by HealthOmics accessibility
    5. Empty repository list handling

    **Validates: Requirements 1.1, 1.4, 1.5**
    """

    @pytest.mark.asyncio
    async def test_successful_listing_single_repository(self):
        """Test successful listing with a single repository.

        **Validates: Requirement 1.1** - List ECR repositories in the specified region
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('my-repo')],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert 'repositories' in result
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['repository_name'] == 'my-repo'
        assert result['total_count'] == 1
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_successful_listing_multiple_repositories(self):
        """Test successful listing with multiple repositories.

        **Validates: Requirement 1.1** - List ECR repositories in the specified region
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                _create_sample_repository('repo-1'),
                _create_sample_repository('repo-2'),
                _create_sample_repository('repo-3'),
            ],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert len(result['repositories']) == 3
        assert result['total_count'] == 3
        repo_names = [r['repository_name'] for r in result['repositories']]
        assert 'repo-1' in repo_names
        assert 'repo-2' in repo_names
        assert 'repo-3' in repo_names

    @pytest.mark.asyncio
    async def test_empty_repository_list(self):
        """Test handling of empty repository list.

        **Validates: Requirement 1.1** - Handle case when no repositories exist
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert result['repositories'] == []
        assert result['total_count'] == 0
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_pagination_input_token_passed_to_api(self):
        """Test that input next_token is passed to the AWS API.

        **Validates: Requirement 1.4** - Support next_token for pagination
        """
        # Arrange
        input_token = 'test-pagination-token-12345'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('repo-1')],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=input_token,
                filter_healthomics_accessible=False,
            )

        # Assert
        mock_client.describe_repositories.assert_called_once()
        call_kwargs = mock_client.describe_repositories.call_args[1]
        assert call_kwargs['nextToken'] == input_token

    @pytest.mark.asyncio
    async def test_pagination_output_token_returned(self):
        """Test that output next_token from AWS is returned in response.

        **Validates: Requirement 1.4** - Support next_token for pagination
        """
        # Arrange
        output_token = 'next-page-token-67890'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('repo-1')],
            'nextToken': output_token,
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert result['next_token'] == output_token

    @pytest.mark.asyncio
    async def test_pagination_no_token_on_last_page(self):
        """Test that next_token is None when no more pages exist.

        **Validates: Requirement 1.4** - Support next_token for pagination
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('repo-1')],
            # No nextToken - this is the last page
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_max_results_passed_to_api(self):
        """Test that max_results parameter is passed to the AWS API.

        **Validates: Requirement 1.4** - Support pagination parameters
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=50,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        mock_client.describe_repositories.assert_called_once()
        call_kwargs = mock_client.describe_repositories.call_args[1]
        assert call_kwargs['maxResults'] == 50

    @pytest.mark.asyncio
    async def test_error_access_denied_exception(self):
        """Test handling of AccessDeniedException.

        **Validates: Requirement 1.5** - Return informative error message
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.side_effect = _create_access_denied_exception()

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception):
                await list_ecr_repositories(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                    filter_healthomics_accessible=False,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'Access denied' in error_message
        assert 'ecr:DescribeRepositories' in error_message

    @pytest.mark.asyncio
    async def test_error_other_client_error(self):
        """Test handling of other ClientError types.

        **Validates: Requirement 1.5** - Return informative error message
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.side_effect = _create_client_error(
            'ServiceUnavailableException',
            'The service is temporarily unavailable',
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception):
                await list_ecr_repositories(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                    filter_healthomics_accessible=False,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'ECR error' in error_message

    @pytest.mark.asyncio
    async def test_error_botocore_error(self):
        """Test handling of BotoCoreError.

        **Validates: Requirement 1.5** - Return informative error message
        """
        import botocore.exceptions

        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.side_effect = botocore.exceptions.BotoCoreError()

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception):
                await list_ecr_repositories(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                    filter_healthomics_accessible=False,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'AWS error' in error_message

    @pytest.mark.asyncio
    async def test_healthomics_accessible_repository(self):
        """Test repository with HealthOmics access permissions.

        **Validates: Requirement 1.2, 1.3** - Check repository policy for HealthOmics permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('accessible-repo')],
        }
        mock_client.get_repository_policy.return_value = {
            'policyText': _create_healthomics_policy(),
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['healthomics_accessible'] == 'accessible'
        assert result['repositories'][0]['missing_permissions'] == []

    @pytest.mark.asyncio
    async def test_healthomics_not_accessible_no_policy(self):
        """Test repository without policy is marked as not accessible.

        **Validates: Requirement 1.2, 1.3** - Check repository policy for HealthOmics permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('no-policy-repo')],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['healthomics_accessible'] == 'not_accessible'
        assert len(result['repositories'][0]['missing_permissions']) > 0

    @pytest.mark.asyncio
    async def test_healthomics_not_accessible_partial_permissions(self):
        """Test repository with partial HealthOmics permissions.

        **Validates: Requirement 1.2, 1.3** - Check repository policy for HealthOmics permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('partial-repo')],
        }
        mock_client.get_repository_policy.return_value = {
            'policyText': _create_partial_healthomics_policy(),
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['healthomics_accessible'] == 'not_accessible'
        assert 'ecr:GetDownloadUrlForLayer' in result['repositories'][0]['missing_permissions']

    @pytest.mark.asyncio
    async def test_filter_healthomics_accessible_true(self):
        """Test filtering to only return HealthOmics accessible repositories.

        **Validates: Requirement 1.2** - Filter by HealthOmics accessibility
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                _create_sample_repository('accessible-repo'),
                _create_sample_repository('not-accessible-repo'),
            ],
        }

        # First repo has policy, second doesn't
        def get_policy_side_effect(repositoryName):
            if repositoryName == 'accessible-repo':
                return {'policyText': _create_healthomics_policy()}
            else:
                raise _create_policy_not_found_exception()

        mock_client.get_repository_policy.side_effect = get_policy_side_effect

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=True,
            )

        # Assert - only accessible repo should be returned
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['repository_name'] == 'accessible-repo'
        assert result['total_count'] == 1

    @pytest.mark.asyncio
    async def test_filter_healthomics_accessible_false(self):
        """Test that all repositories are returned when filter is False.

        **Validates: Requirement 1.1** - List all repositories
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                _create_sample_repository('accessible-repo'),
                _create_sample_repository('not-accessible-repo'),
            ],
        }

        def get_policy_side_effect(repositoryName):
            if repositoryName == 'accessible-repo':
                return {'policyText': _create_healthomics_policy()}
            else:
                raise _create_policy_not_found_exception()

        mock_client.get_repository_policy.side_effect = get_policy_side_effect

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert - both repos should be returned
        assert len(result['repositories']) == 2
        assert result['total_count'] == 2

    @pytest.mark.asyncio
    async def test_filter_healthomics_accessible_empty_result(self):
        """Test filtering when no repositories are accessible.

        **Validates: Requirement 1.2** - Filter by HealthOmics accessibility
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                _create_sample_repository('repo-1'),
                _create_sample_repository('repo-2'),
            ],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=True,
            )

        # Assert - no repos should be returned
        assert len(result['repositories']) == 0
        assert result['total_count'] == 0

    @pytest.mark.asyncio
    async def test_repository_policy_check_error_marks_unknown(self):
        """Test that policy check errors result in unknown accessibility status.

        **Validates: Requirement 1.2** - Handle policy check errors gracefully
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [_create_sample_repository('error-repo')],
        }
        # Simulate an unexpected error when getting policy
        mock_client.get_repository_policy.side_effect = _create_client_error(
            'InternalServiceError',
            'Internal service error',
            'GetRepositoryPolicy',
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert - repo should be returned with unknown status
        assert len(result['repositories']) == 1
        assert result['repositories'][0]['healthomics_accessible'] == 'unknown'

    @pytest.mark.asyncio
    async def test_repository_fields_populated_correctly(self):
        """Test that all repository fields are populated correctly.

        **Validates: Requirement 1.1** - Return repository information
        """
        # Arrange
        created_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                {
                    'repositoryArn': 'arn:aws:ecr:us-east-1:123456789012:repository/test-repo',
                    'registryId': '123456789012',
                    'repositoryName': 'test-repo',
                    'repositoryUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo',
                    'createdAt': created_time,
                    'imageTagMutability': 'MUTABLE',
                }
            ],
        }
        mock_client.get_repository_policy.side_effect = _create_policy_not_found_exception()

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        repo = result['repositories'][0]
        assert repo['repository_name'] == 'test-repo'
        assert repo['repository_arn'] == 'arn:aws:ecr:us-east-1:123456789012:repository/test-repo'
        assert repo['repository_uri'] == '123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo'
        assert repo['created_at'] == created_time

    @pytest.mark.asyncio
    async def test_mixed_accessibility_statuses(self):
        """Test handling of repositories with mixed accessibility statuses.

        **Validates: Requirement 1.2, 1.3** - Check each repository's policy
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_repositories.return_value = {
            'repositories': [
                _create_sample_repository('accessible-repo'),
                _create_sample_repository('no-policy-repo'),
                _create_sample_repository('error-repo'),
            ],
        }

        def get_policy_side_effect(repositoryName):
            if repositoryName == 'accessible-repo':
                return {'policyText': _create_healthomics_policy()}
            elif repositoryName == 'no-policy-repo':
                raise _create_policy_not_found_exception()
            else:
                raise _create_client_error(
                    'InternalServiceError',
                    'Internal error',
                    'GetRepositoryPolicy',
                )

        mock_client.get_repository_policy.side_effect = get_policy_side_effect

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_ecr_repositories(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
                filter_healthomics_accessible=False,
            )

        # Assert
        assert len(result['repositories']) == 3

        # Find each repo by name and check status
        repos_by_name = {r['repository_name']: r for r in result['repositories']}
        assert repos_by_name['accessible-repo']['healthomics_accessible'] == 'accessible'
        assert repos_by_name['no-policy-repo']['healthomics_accessible'] == 'not_accessible'
        assert repos_by_name['error-repo']['healthomics_accessible'] == 'unknown'


# =============================================================================
# Unit Tests for check_container_availability
# Feature: ecr-container-tools
# Task 6.3: Write unit tests for check_container_availability
# Requirements: 2.3, 2.4, 2.5, 2.6
# =============================================================================


class TestCheckContainerAvailabilityUnit:
    """Unit tests for check_container_availability function.

    These tests cover:
    1. Image exists - returns image details (digest, size, push timestamp)
    2. Image not found - returns available=False with clear message
    3. Repository not found - returns repository_exists=False
    4. Pull-through cache detection - sets is_pull_through_cache correctly
    5. Invalid input validation (empty repository name, invalid digest format)
    6. Error handling (AccessDeniedException, other errors)

    **Validates: Requirements 2.3, 2.4, 2.5, 2.6**
    """

    # =========================================================================
    # Test: Image exists - returns image details
    # Validates: Requirement 2.3
    # =========================================================================

    @pytest.mark.asyncio
    async def test_image_exists_returns_details(self):
        """Test that existing image returns full details.

        **Validates: Requirement 2.3** - Return image details including digest, size, push timestamp
        """
        # Arrange
        pushed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123def456789',
                    'imageSizeInBytes': 52428800,  # 50 MB
                    'imagePushedAt': pushed_time,
                    'imageTags': ['latest', 'v1.0.0'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['repository_exists'] is True
        assert result['image'] is not None
        assert result['image']['image_digest'] == 'sha256:abc123def456789'
        assert result['image']['image_size_bytes'] == 52428800
        assert result['image']['pushed_at'] == pushed_time
        assert result['image']['repository_name'] == 'my-repo'

    @pytest.mark.asyncio
    async def test_image_exists_with_specific_tag(self):
        """Test that image with specific tag returns correct tag in response.

        **Validates: Requirement 2.3** - Return image details
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['v2.0.0', 'stable'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='v2.0.0',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['image']['image_tag'] == 'v2.0.0'

    @pytest.mark.asyncio
    async def test_image_exists_with_digest(self):
        """Test that image lookup by digest works correctly.

        **Validates: Requirement 2.3** - Return image details including digest
        """
        # Arrange
        digest = 'sha256:abc123def456'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': digest,
                    'imageSizeInBytes': 2048,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=digest,
            )

        # Assert
        assert result['available'] is True
        assert result['image']['image_digest'] == digest
        # Verify digest was used in API call
        mock_client.describe_images.assert_called_once()
        call_kwargs = mock_client.describe_images.call_args[1]
        assert call_kwargs['imageIds'][0]['imageDigest'] == digest

    # =========================================================================
    # Test: Image not found - returns available=False with clear message
    # Validates: Requirement 2.4
    # =========================================================================

    @pytest.mark.asyncio
    async def test_image_not_found_returns_clear_message(self):
        """Test that image not found returns available=False with clear message.

        **Validates: Requirement 2.4** - Return clear indication that image is not found
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'The image with imageId latest does not exist',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='nonexistent-tag',
                image_digest=None,
            )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is True
        assert result['image'] is None
        assert 'not found' in result['message'].lower()
        assert 'my-repo' in result['message']

    @pytest.mark.asyncio
    async def test_image_not_found_empty_image_details(self):
        """Test that empty imageDetails returns available=False.

        **Validates: Requirement 2.4** - Return clear indication that image is not found
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': []  # Empty list - no images found
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='missing-tag',
                image_digest=None,
            )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is True
        assert 'not found' in result['message'].lower()

    # =========================================================================
    # Test: Repository not found - returns repository_exists=False
    # Validates: Requirement 2.5
    # =========================================================================

    @pytest.mark.asyncio
    async def test_repository_not_found(self):
        """Test that repository not found returns repository_exists=False.

        **Validates: Requirement 2.5** - Indicate repository is missing
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'The repository with name nonexistent-repo does not exist',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='nonexistent-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is False
        assert result['image'] is None
        assert 'not found' in result['message'].lower()
        assert 'nonexistent-repo' in result['message']

    @pytest.mark.asyncio
    async def test_repository_not_found_ptc_message(self):
        """Test that PTC repository not found includes helpful message.

        **Validates: Requirement 2.5, 2.6** - Indicate repository may be created on first pull
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is False
        assert result['is_pull_through_cache'] is True
        # Message should indicate it may be created on first pull
        assert 'pull' in result['message'].lower() or 'created' in result['message'].lower()

    # =========================================================================
    # Test: Pull-through cache detection
    # Validates: Requirement 2.6
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ptc_detection_docker_hub(self):
        """Test pull-through cache detection for docker-hub prefix.

        **Validates: Requirement 2.6** - Indicate if image may be pulled on first access
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/nginx',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['is_pull_through_cache'] is True

    @pytest.mark.asyncio
    async def test_ptc_detection_quay(self):
        """Test pull-through cache detection for quay prefix.

        **Validates: Requirement 2.6** - Indicate if image may be pulled on first access
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:def456',
                    'imageSizeInBytes': 2048,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['v1.0'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='quay/biocontainers/samtools',
                image_tag='v1.0',
                image_digest=None,
            )

        # Assert
        assert result['is_pull_through_cache'] is True

    @pytest.mark.asyncio
    async def test_ptc_detection_ecr_public(self):
        """Test pull-through cache detection for ecr-public prefix.

        **Validates: Requirement 2.6** - Indicate if image may be pulled on first access
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:ghi789',
                    'imageSizeInBytes': 4096,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['stable'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='ecr-public/aws-genomics/nextflow',
                image_tag='stable',
                image_digest=None,
            )

        # Assert
        assert result['is_pull_through_cache'] is True

    @pytest.mark.asyncio
    async def test_non_ptc_repository(self):
        """Test that regular repositories are not marked as pull-through cache.

        **Validates: Requirement 2.6** - Correctly identify non-PTC repositories
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:xyz123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-custom-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['is_pull_through_cache'] is False

    @pytest.mark.asyncio
    async def test_ptc_image_not_found_message(self):
        """Test that PTC image not found includes helpful message about first access.

        **Validates: Requirement 2.6** - Indicate image may be pulled on first access
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='docker-hub/library/python',
                image_tag='3.11',
                image_digest=None,
            )

        # Assert
        assert result['available'] is False
        assert result['is_pull_through_cache'] is True
        # Message should mention first access
        assert 'first access' in result['message'].lower() or 'pull' in result['message'].lower()

    # =========================================================================
    # Test: Invalid input validation
    # Validates: Requirement 2.1
    # =========================================================================

    @pytest.mark.asyncio
    async def test_empty_repository_name(self):
        """Test that empty repository name returns validation error.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act - no need to mock ECR client since validation should fail first
        result = await check_container_availability(
            ctx=mock_ctx,
            repository_name='',
            image_tag='latest',
            image_digest=None,
        )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is False
        assert 'required' in result['message'].lower() or 'empty' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_repository_name(self):
        """Test that whitespace-only repository name returns validation error.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await check_container_availability(
            ctx=mock_ctx,
            repository_name='   ',
            image_tag='latest',
            image_digest=None,
        )

        # Assert
        assert result['available'] is False
        assert result['repository_exists'] is False
        assert 'required' in result['message'].lower() or 'empty' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_invalid_digest_format_no_sha256_prefix(self):
        """Test that digest without sha256: prefix returns validation error.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await check_container_availability(
            ctx=mock_ctx,
            repository_name='my-repo',
            image_tag='latest',
            image_digest='abc123def456',  # pragma: allowlist secret
        )

        # Assert
        assert result['available'] is False
        assert 'sha256' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_invalid_digest_format_wrong_prefix(self):
        """Test that digest with wrong prefix returns validation error.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await check_container_availability(
            ctx=mock_ctx,
            repository_name='my-repo',
            image_tag='latest',
            image_digest='md5:abc123def456',  # Wrong prefix
        )

        # Assert
        assert result['available'] is False
        assert 'sha256' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_valid_digest_format_accepted(self):
        """Test that valid sha256: digest format is accepted.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123def456',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest='sha256:abc123def456',
            )

        # Assert
        assert result['available'] is True
        # Verify the API was called (validation passed)
        mock_client.describe_images.assert_called_once()

    # =========================================================================
    # Test: Error handling
    # Validates: Requirement 2.1 (error handling)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_access_denied_exception(self):
        """Test handling of AccessDeniedException.

        **Validates: Requirement 2.1** - Handle AWS API errors
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform ecr:DescribeImages',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await check_container_availability(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                    image_tag='latest',
                    image_digest=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'Access denied' in error_message
        assert 'ecr:DescribeImages' in error_message

    @pytest.mark.asyncio
    async def test_other_client_error(self):
        """Test handling of other ClientError types.

        **Validates: Requirement 2.1** - Handle AWS API errors
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailableException',
                'Message': 'The service is temporarily unavailable',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await check_container_availability(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                    image_tag='latest',
                    image_digest=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'ECR error' in error_message

    @pytest.mark.asyncio
    async def test_botocore_error(self):
        """Test handling of BotoCoreError.

        **Validates: Requirement 2.1** - Handle AWS API errors
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.side_effect = botocore.exceptions.BotoCoreError()

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.BotoCoreError):
                await check_container_availability(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                    image_tag='latest',
                    image_digest=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'AWS error' in error_message

    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Test handling of unexpected exceptions.

        **Validates: Requirement 2.1** - Handle errors gracefully
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.side_effect = RuntimeError('Unexpected error')

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(RuntimeError):
                await check_container_availability(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                    image_tag='latest',
                    image_digest=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'Unexpected error' in error_message

    # =========================================================================
    # Test: API call verification
    # Validates: Requirement 2.2
    # =========================================================================

    @pytest.mark.asyncio
    async def test_api_called_with_tag(self):
        """Test that API is called with correct tag parameter.

        **Validates: Requirement 2.2** - Query ECR for specified image and tag
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['v1.2.3'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='v1.2.3',
                image_digest=None,
            )

        # Assert
        mock_client.describe_images.assert_called_once()
        call_kwargs = mock_client.describe_images.call_args[1]
        assert call_kwargs['repositoryName'] == 'my-repo'
        assert call_kwargs['imageIds'][0]['imageTag'] == 'v1.2.3'

    @pytest.mark.asyncio
    async def test_api_called_with_digest_takes_precedence(self):
        """Test that digest takes precedence over tag in API call.

        **Validates: Requirement 2.2** - Query ECR for specified image
        """
        # Arrange
        digest = 'sha256:abc123def456'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': digest,
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=digest,
            )

        # Assert - digest should be used, not tag
        mock_client.describe_images.assert_called_once()
        call_kwargs = mock_client.describe_images.call_args[1]
        assert 'imageDigest' in call_kwargs['imageIds'][0]
        assert call_kwargs['imageIds'][0]['imageDigest'] == digest
        assert 'imageTag' not in call_kwargs['imageIds'][0]

    @pytest.mark.asyncio
    async def test_default_tag_is_latest(self):
        """Test that default tag is 'latest' when not specified.

        **Validates: Requirement 2.2** - Query ECR for specified image and tag
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',  # Default value
                image_digest=None,
            )

        # Assert
        mock_client.describe_images.assert_called_once()
        call_kwargs = mock_client.describe_images.call_args[1]
        assert call_kwargs['imageIds'][0]['imageTag'] == 'latest'

    @pytest.mark.asyncio
    async def test_repository_name_trimmed(self):
        """Test that repository name is trimmed of whitespace.

        **Validates: Requirement 2.1** - Validate URI format
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await check_container_availability(
                ctx=mock_ctx,
                repository_name='  my-repo  ',  # With whitespace
                image_tag='latest',
                image_digest=None,
            )

        # Assert - repository name should be trimmed
        mock_client.describe_images.assert_called_once()
        call_kwargs = mock_client.describe_images.call_args[1]
        assert call_kwargs['repositoryName'] == 'my-repo'

    # =========================================================================
    # Test: HealthOmics accessibility check
    # Validates: Requirement 2.7 (HealthOmics access verification)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_healthomics_accessible_when_policy_grants_permissions(self):
        """Test that healthomics_accessible is 'accessible' when policy grants required permissions.

        **Validates: Requirement 2.7** - Check if HealthOmics can access the container
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        # Policy grants HealthOmics access (already set by _create_mock_ecr_client)

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['healthomics_accessible'] == 'accessible'
        assert result['missing_permissions'] == []

    @pytest.mark.asyncio
    async def test_healthomics_not_accessible_when_no_policy(self):
        """Test that healthomics_accessible is 'not_accessible' when no policy exists.

        **Validates: Requirement 2.7** - Check if HealthOmics can access the container
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        # No policy exists
        error_response = {
            'Error': {
                'Code': 'RepositoryPolicyNotFoundException',
                'Message': 'Repository policy does not exist',
            }
        }
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRepositoryPolicy'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['healthomics_accessible'] == 'not_accessible'
        assert 'ecr:BatchGetImage' in result['missing_permissions']
        assert 'ecr:GetDownloadUrlForLayer' in result['missing_permissions']
        assert 'WARNING' in result['message']

    @pytest.mark.asyncio
    async def test_healthomics_not_accessible_when_policy_missing_permissions(self):
        """Test that healthomics_accessible is 'not_accessible' when policy lacks permissions.

        **Validates: Requirement 2.7** - Check if HealthOmics can access the container
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        # Policy exists but doesn't grant HealthOmics access
        mock_client.get_repository_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Sid': 'OtherAccess',
                            'Effect': 'Allow',
                            'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                            'Action': ['ecr:GetDownloadUrlForLayer'],
                        }
                    ],
                }
            )
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['healthomics_accessible'] == 'not_accessible'
        assert len(result['missing_permissions']) > 0

    @pytest.mark.asyncio
    async def test_healthomics_unknown_when_policy_check_fails(self):
        """Test that healthomics_accessible is 'unknown' when policy check fails with other error.

        **Validates: Requirement 2.7** - Handle errors gracefully
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        # Policy check fails with unexpected error
        error_response = {
            'Error': {
                'Code': 'InternalServiceException',
                'Message': 'Internal service error',
            }
        }
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRepositoryPolicy'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['healthomics_accessible'] == 'unknown'
        assert 'could not be determined' in result['message']

    @pytest.mark.asyncio
    async def test_healthomics_accessible_with_wildcard_actions(self):
        """Test that healthomics_accessible is 'accessible' when policy uses wildcard actions.

        **Validates: Requirement 2.7** - Check if HealthOmics can access the container
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:abc123',
                    'imageSizeInBytes': 1024,
                    'imagePushedAt': datetime.now(timezone.utc),
                    'imageTags': ['latest'],
                }
            ]
        }
        # Policy grants HealthOmics access via wildcard
        mock_client.get_repository_policy.return_value = {
            'policyText': json.dumps(
                {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Sid': 'HealthOmicsAccess',
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': 'ecr:*',
                        }
                    ],
                }
            )
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await check_container_availability(
                ctx=mock_ctx,
                repository_name='my-repo',
                image_tag='latest',
                image_digest=None,
            )

        # Assert
        assert result['available'] is True
        assert result['healthomics_accessible'] == 'accessible'
        assert result['missing_permissions'] == []


# =============================================================================
# Unit Tests for list_pull_through_cache_rules
# Feature: ecr-container-tools
# Task 7.2: Write unit tests for list_pull_through_cache_rules
# Requirements: 3.1, 3.2, 3.6
# =============================================================================


def _create_sample_ptc_rule(
    prefix: str = 'docker-hub',
    upstream_url: str = 'registry-1.docker.io',
    credential_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sample pull-through cache rule response object."""
    rule = {
        'ecrRepositoryPrefix': prefix,
        'upstreamRegistryUrl': upstream_url,
        'createdAt': datetime.now(timezone.utc),
        'updatedAt': datetime.now(timezone.utc),
    }
    if credential_arn:
        rule['credentialArn'] = credential_arn
    return rule


def _create_registry_policy_not_found_exception():
    """Create a mock RegistryPolicyNotFoundException for testing."""
    error_response = {
        'Error': {
            'Code': 'RegistryPolicyNotFoundException',
            'Message': 'Registry policy does not exist',
        }
    }
    return botocore.exceptions.ClientError(error_response, 'GetRegistryPolicy')


def _create_template_not_found_exception():
    """Create a mock TemplateNotFoundException for testing."""
    error_response = {
        'Error': {
            'Code': 'TemplateNotFoundException',
            'Message': 'Repository creation template does not exist',
        }
    }
    return botocore.exceptions.ClientError(error_response, 'DescribeRepositoryCreationTemplates')


def _create_healthomics_registry_policy() -> str:
    """Create a sample registry policy that grants HealthOmics access."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsRegistryAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
    )


def _create_healthomics_template_policy() -> str:
    """Create a sample repository creation template policy that grants HealthOmics access."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsTemplateAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                    'Resource': '*',
                }
            ],
        }
    )


class TestListPullThroughCacheRulesUnit:
    """Unit tests for list_pull_through_cache_rules function.

    These tests cover:
    1. Successful listing with configured rules
    2. Empty rules case - returns empty list
    3. Permission checking integration - verifies registry policy and template checks
    4. Pagination handling (next_token)
    5. Error handling (AccessDeniedException, other errors)
    6. Rules with and without credentials

    **Validates: Requirements 3.1, 3.2, 3.6**
    """

    # =========================================================================
    # Test: Successful listing with configured rules
    # Validates: Requirement 3.1, 3.2
    # =========================================================================

    @pytest.mark.asyncio
    async def test_successful_listing_single_rule(self):
        """Test successful listing with a single pull-through cache rule.

        **Validates: Requirement 3.1** - Return all configured rules in the region
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io')
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert 'rules' in result
        assert len(result['rules']) == 1
        assert result['rules'][0]['ecr_repository_prefix'] == 'docker-hub'
        assert result['rules'][0]['upstream_registry_url'] == 'registry-1.docker.io'
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_successful_listing_multiple_rules(self):
        """Test successful listing with multiple pull-through cache rules.

        **Validates: Requirement 3.1** - Return all configured rules in the region
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
                _create_sample_ptc_rule('quay', 'quay.io'),
                _create_sample_ptc_rule('ecr-public', 'public.ecr.aws'),
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert len(result['rules']) == 3
        prefixes = [r['ecr_repository_prefix'] for r in result['rules']]
        assert 'docker-hub' in prefixes
        assert 'quay' in prefixes
        assert 'ecr-public' in prefixes

    @pytest.mark.asyncio
    async def test_rule_includes_upstream_registry_url(self):
        """Test that rules include upstream registry URL.

        **Validates: Requirement 3.2** - Include upstream registry URL
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['rules'][0]['upstream_registry_url'] == 'registry-1.docker.io'

    # =========================================================================
    # Test: Empty rules case - returns empty list
    # Validates: Requirement 3.6
    # =========================================================================

    @pytest.mark.asyncio
    async def test_empty_rules_returns_empty_list(self):
        """Test that empty rules returns empty list.

        **Validates: Requirement 3.6** - Return empty list if no rules exist
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['rules'] == []
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_empty_rules_no_registry_policy_check(self):
        """Test that registry policy is not checked when no rules exist.

        **Validates: Requirement 3.6** - Efficient handling of empty rules
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert - registry policy should not be checked when no rules exist
        mock_client.get_registry_policy.assert_not_called()

    # =========================================================================
    # Test: Permission checking integration
    # Validates: Requirements 3.3, 3.4, 3.5
    # =========================================================================

    @pytest.mark.asyncio
    async def test_healthomics_usable_when_all_permissions_granted(self):
        """Test that rule is marked usable when all permissions are granted.

        **Validates: Requirements 3.3, 3.4, 3.5** - Check registry and template permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'repositoryPolicy': _create_healthomics_template_policy(),
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rule = result['rules'][0]
        assert rule['healthomics_usable'] is True
        assert rule['registry_permission_granted'] is True
        assert rule['repository_template_exists'] is True
        assert rule['repository_template_permission_granted'] is True

    @pytest.mark.asyncio
    async def test_healthomics_not_usable_no_registry_policy(self):
        """Test that rule is not usable when registry policy is missing.

        **Validates: Requirement 3.3** - Check registry permissions policy
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'repositoryPolicy': _create_healthomics_template_policy(),
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rule = result['rules'][0]
        assert rule['healthomics_usable'] is False
        assert rule['registry_permission_granted'] is False

    @pytest.mark.asyncio
    async def test_healthomics_not_usable_no_template(self):
        """Test that rule is not usable when repository creation template is missing.

        **Validates: Requirement 3.4** - Check repository creation template exists
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rule = result['rules'][0]
        assert rule['healthomics_usable'] is False
        assert rule['registry_permission_granted'] is True
        assert rule['repository_template_exists'] is False

    @pytest.mark.asyncio
    async def test_healthomics_not_usable_template_missing_permissions(self):
        """Test that rule is not usable when template lacks required permissions.

        **Validates: Requirement 3.5** - Verify template grants required permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        # Template exists but has no policy (no permissions)
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'repositoryPolicy': None,  # No policy
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rule = result['rules'][0]
        assert rule['healthomics_usable'] is False
        assert rule['repository_template_exists'] is False
        assert rule['repository_template_permission_granted'] is False

    @pytest.mark.asyncio
    async def test_registry_policy_checked_once_for_all_rules(self):
        """Test that registry policy is checked only once for all rules.

        **Validates: Requirement 3.3** - Efficient permission checking
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
                _create_sample_ptc_rule('quay', 'quay.io'),
                _create_sample_ptc_rule('ecr-public', 'public.ecr.aws'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert - registry policy should be checked only once
        mock_client.get_registry_policy.assert_called_once()

    # =========================================================================
    # Test: Pagination handling
    # Validates: Requirement 3.1
    # =========================================================================

    @pytest.mark.asyncio
    async def test_pagination_input_token_passed_to_api(self):
        """Test that input next_token is passed to the AWS API.

        **Validates: Requirement 3.1** - Support pagination
        """
        # Arrange
        input_token = 'test-pagination-token-12345'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=input_token,
            )

        # Assert
        mock_client.describe_pull_through_cache_rules.assert_called_once()
        call_kwargs = mock_client.describe_pull_through_cache_rules.call_args[1]
        assert call_kwargs['nextToken'] == input_token

    @pytest.mark.asyncio
    async def test_pagination_output_token_returned(self):
        """Test that output next_token from AWS is returned in response.

        **Validates: Requirement 3.1** - Support pagination
        """
        # Arrange
        output_token = 'next-page-token-67890'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
            'nextToken': output_token,
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['next_token'] == output_token

    @pytest.mark.asyncio
    async def test_pagination_no_token_on_last_page(self):
        """Test that next_token is None when no more pages exist.

        **Validates: Requirement 3.1** - Support pagination
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
            # No nextToken - this is the last page
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['next_token'] is None

    @pytest.mark.asyncio
    async def test_max_results_passed_to_api(self):
        """Test that max_results parameter is passed to the AWS API.

        **Validates: Requirement 3.1** - Support pagination parameters
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=50,
                next_token=None,
            )

        # Assert
        mock_client.describe_pull_through_cache_rules.assert_called_once()
        call_kwargs = mock_client.describe_pull_through_cache_rules.call_args[1]
        assert call_kwargs['maxResults'] == 50

    # =========================================================================
    # Test: Error handling
    # Validates: Requirement 3.1
    # =========================================================================

    @pytest.mark.asyncio
    async def test_error_access_denied_exception(self):
        """Test handling of AccessDeniedException.

        **Validates: Requirement 3.1** - Return informative error message
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this operation',
            }
        }
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribePullThroughCacheRules')
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await list_pull_through_cache_rules(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'Access denied' in error_message
        assert 'ecr:DescribePullThroughCacheRules' in error_message

    @pytest.mark.asyncio
    async def test_error_other_client_error(self):
        """Test handling of other ClientError types.

        **Validates: Requirement 3.1** - Return informative error message
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailableException',
                'Message': 'The service is temporarily unavailable',
            }
        }
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribePullThroughCacheRules')
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await list_pull_through_cache_rules(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'ECR error' in error_message

    @pytest.mark.asyncio
    async def test_error_botocore_error(self):
        """Test handling of BotoCoreError.

        **Validates: Requirement 3.1** - Return informative error message
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.BotoCoreError()
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.BotoCoreError):
                await list_pull_through_cache_rules(
                    ctx=mock_ctx,
                    max_results=100,
                    next_token=None,
                )

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'AWS error' in error_message

    @pytest.mark.asyncio
    async def test_registry_policy_error_handled_gracefully(self):
        """Test that registry policy errors are handled gracefully.

        **Validates: Requirement 3.3** - Handle permission check errors
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        # Simulate an unexpected error when getting registry policy
        error_response = {
            'Error': {
                'Code': 'InternalServiceError',
                'Message': 'Internal service error',
            }
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRegistryPolicy'
        )
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert - should still return rules, but with permissions not granted
        assert len(result['rules']) == 1
        assert result['rules'][0]['registry_permission_granted'] is False

    @pytest.mark.asyncio
    async def test_template_error_handled_gracefully(self):
        """Test that template errors are handled gracefully.

        **Validates: Requirement 3.4** - Handle template check errors
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        # Simulate an unexpected error when getting template
        error_response = {
            'Error': {
                'Code': 'InternalServiceError',
                'Message': 'Internal service error',
            }
        }
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribeRepositoryCreationTemplates')
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert - should still return rules, but with template not found
        assert len(result['rules']) == 1
        assert result['rules'][0]['repository_template_exists'] is False

    # =========================================================================
    # Test: Rules with and without credentials
    # Validates: Requirement 3.2
    # =========================================================================

    @pytest.mark.asyncio
    async def test_rule_with_credential_arn(self):
        """Test that rules with credential ARN include it in response.

        **Validates: Requirement 3.2** - Include credential ARN if configured
        """
        # Arrange
        credential_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-hub-creds'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule(
                    'docker-hub', 'registry-1.docker.io', credential_arn=credential_arn
                ),
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['rules'][0]['credential_arn'] == credential_arn

    @pytest.mark.asyncio
    async def test_rule_without_credential_arn(self):
        """Test that rules without credential ARN have None.

        **Validates: Requirement 3.2** - Include credential ARN if configured
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('ecr-public', 'public.ecr.aws'),  # No credential
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        assert result['rules'][0]['credential_arn'] is None

    @pytest.mark.asyncio
    async def test_mixed_rules_with_and_without_credentials(self):
        """Test listing rules with mixed credential configurations.

        **Validates: Requirement 3.2** - Include credential ARN if configured
        """
        # Arrange
        credential_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-hub-creds'
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule(
                    'docker-hub', 'registry-1.docker.io', credential_arn=credential_arn
                ),
                _create_sample_ptc_rule('quay', 'quay.io'),  # No credential
                _create_sample_ptc_rule('ecr-public', 'public.ecr.aws'),  # No credential
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rules_by_prefix = {r['ecr_repository_prefix']: r for r in result['rules']}
        assert rules_by_prefix['docker-hub']['credential_arn'] == credential_arn
        assert rules_by_prefix['quay']['credential_arn'] is None
        assert rules_by_prefix['ecr-public']['credential_arn'] is None

    # =========================================================================
    # Test: Rule fields populated correctly
    # Validates: Requirement 3.2
    # =========================================================================

    @pytest.mark.asyncio
    async def test_rule_fields_populated_correctly(self):
        """Test that all rule fields are populated correctly.

        **Validates: Requirement 3.2** - Include all rule information
        """
        # Arrange
        created_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        updated_time = datetime(2024, 2, 20, 14, 45, 0, tzinfo=timezone.utc)
        credential_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:creds'

        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'credentialArn': credential_arn,
                    'createdAt': created_time,
                    'updatedAt': updated_time,
                }
            ],
        }
        mock_client.get_registry_policy.side_effect = _create_registry_policy_not_found_exception()
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert
        rule = result['rules'][0]
        assert rule['ecr_repository_prefix'] == 'docker-hub'
        assert rule['upstream_registry_url'] == 'registry-1.docker.io'
        assert rule['credential_arn'] == credential_arn
        assert rule['created_at'] == created_time
        assert rule['updated_at'] == updated_time

    @pytest.mark.asyncio
    async def test_template_checked_for_each_rule(self):
        """Test that repository creation template is checked for each rule.

        **Validates: Requirement 3.4** - Check template for each prefix
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                _create_sample_ptc_rule('docker-hub', 'registry-1.docker.io'),
                _create_sample_ptc_rule('quay', 'quay.io'),
            ],
        }
        mock_client.get_registry_policy.return_value = {
            'policyText': _create_healthomics_registry_policy(),
        }
        mock_client.describe_repository_creation_templates.side_effect = (
            _create_template_not_found_exception()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            await list_pull_through_cache_rules(
                ctx=mock_ctx,
                max_results=100,
                next_token=None,
            )

        # Assert - template should be checked for each rule
        assert mock_client.describe_repository_creation_templates.call_count == 2
        # Verify the prefixes were passed correctly
        calls = mock_client.describe_repository_creation_templates.call_args_list
        prefixes_checked = [call[1]['prefixes'][0] for call in calls]
        assert 'docker-hub' in prefixes_checked
        assert 'quay' in prefixes_checked


# =============================================================================
# Property 2: Registry Type to URL Mapping
# Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
# Validates: Requirements 4.2
# =============================================================================


class TestRegistryTypeToURLMapping:
    """Property 2: Registry Type to URL Mapping.

    **Validates: Requirements 4.2**

    *For any* valid upstream registry type (docker-hub, quay, ecr-public), the
    pull-through cache creation SHALL use the correct upstream registry URL:
    - docker-hub → registry-1.docker.io
    - quay → quay.io
    - ecr-public → public.ecr.aws
    """

    # Expected URL mappings as defined in the design document
    EXPECTED_URL_MAPPINGS = {
        'docker-hub': 'registry-1.docker.io',
        'quay': 'quay.io',
        'ecr-public': 'public.ecr.aws',
    }

    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(list(UpstreamRegistry)))
    def test_upstream_registry_urls_constant_mapping(self, registry_type: UpstreamRegistry):
        """Property 2.1: UPSTREAM_REGISTRY_URLS constant maps correctly.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any valid UpstreamRegistry enum value, the UPSTREAM_REGISTRY_URLS
        constant SHALL contain the correct upstream registry URL.
        """
        expected_url = self.EXPECTED_URL_MAPPINGS[registry_type.value]
        actual_url = UPSTREAM_REGISTRY_URLS[registry_type]

        assert actual_url == expected_url, (
            f'Expected UPSTREAM_REGISTRY_URLS[{registry_type}] to be "{expected_url}", '
            f'but got "{actual_url}"'
        )

    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(['docker-hub', 'quay', 'ecr-public']))
    def test_all_registry_types_have_url_mapping(self, registry_type: str):
        """Property 2.2: All valid registry types have URL mappings.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any valid registry type string, there SHALL exist a corresponding
        URL mapping in UPSTREAM_REGISTRY_URLS.
        """
        registry_enum = UpstreamRegistry(registry_type)
        assert registry_enum in UPSTREAM_REGISTRY_URLS, (
            f'Registry type "{registry_type}" should have a URL mapping in UPSTREAM_REGISTRY_URLS'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(['quay', 'ecr-public']))
    async def test_create_ptc_uses_correct_url_for_registry_type(self, registry_type: str):
        """Property 2.3: create_pull_through_cache_for_healthomics uses correct URL.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any valid upstream registry type, the create_pull_through_cache_for_healthomics
        function SHALL use the correct upstream registry URL when creating the
        pull-through cache rule.

        Note: Testing quay and ecr-public which don't require credentials.
        """
        expected_url = self.EXPECTED_URL_MAPPINGS[registry_type]

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': registry_type,
            'upstreamRegistryUrl': expected_url,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            _ = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry=registry_type,
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Verify the correct URL was used in the API call
        mock_client.create_pull_through_cache_rule.assert_called_once()
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs['upstreamRegistryUrl'] == expected_url, (
            f'Expected upstreamRegistryUrl to be "{expected_url}" for registry type '
            f'"{registry_type}", but got "{call_kwargs["upstreamRegistryUrl"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        credential_arn=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789:/-',  # pragma: allowlist secret
            min_size=20,
            max_size=100,
        ).map(lambda s: f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{s}')
    )
    async def test_docker_hub_uses_correct_url_with_credentials(self, credential_arn: str):
        """Property 2.4: Docker Hub registry type uses correct URL.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For docker-hub registry type (which requires credentials), the
        create_pull_through_cache_for_healthomics function SHALL use
        'registry-1.docker.io' as the upstream registry URL.
        """
        expected_url = 'registry-1.docker.io'

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'docker-hub',
            'upstreamRegistryUrl': expected_url,
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            _ = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='docker-hub',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Verify the correct URL was used in the API call
        mock_client.create_pull_through_cache_rule.assert_called_once()
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs['upstreamRegistryUrl'] == expected_url, (
            f'Expected upstreamRegistryUrl to be "{expected_url}" for docker-hub, '
            f'but got "{call_kwargs["upstreamRegistryUrl"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(['quay', 'ecr-public']))
    async def test_url_mapping_in_successful_response(self, registry_type: str):
        """Property 2.5: Successful response contains correct URL mapping.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any valid upstream registry type, when the pull-through cache is
        successfully created, the response SHALL contain the correct upstream
        registry URL in the rule details.
        """
        expected_url = self.EXPECTED_URL_MAPPINGS[registry_type]

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': registry_type,
            'upstreamRegistryUrl': expected_url,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry=registry_type,
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Verify the response contains the correct URL
        assert result['success'] is True, f'Expected success=True, got {result["success"]}'
        assert result['rule'] is not None, 'Expected rule to be present in response'
        assert result['rule']['upstream_registry_url'] == expected_url, (
            f'Expected upstream_registry_url in response to be "{expected_url}", '
            f'but got "{result["rule"]["upstream_registry_url"]}"'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(['quay', 'ecr-public']))
    async def test_url_mapping_when_rule_already_exists(self, registry_type: str):
        """Property 2.6: URL mapping is correct even when rule already exists.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any valid upstream registry type, when the pull-through cache rule
        already exists, the response SHALL still contain the correct upstream
        registry URL from the existing rule.
        """
        expected_url = self.EXPECTED_URL_MAPPINGS[registry_type]

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock rule already exists error
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'PullThroughCacheRuleAlreadyExistsException',
                    'Message': 'Rule already exists',
                }
            },
            'CreatePullThroughCacheRule',
        )

        # Mock describe to return existing rule
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': registry_type,
                    'upstreamRegistryUrl': expected_url,
                    'createdAt': datetime.now(timezone.utc),
                }
            ]
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry=registry_type,
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Verify the response contains the correct URL from existing rule
        assert result['success'] is True, f'Expected success=True, got {result["success"]}'
        assert result['rule'] is not None, 'Expected rule to be present in response'
        assert result['rule']['upstream_registry_url'] == expected_url, (
            f'Expected upstream_registry_url in response to be "{expected_url}", '
            f'but got "{result["rule"]["upstream_registry_url"]}"'
        )

    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(list(UpstreamRegistry)))
    def test_url_mapping_completeness(self, registry_type: UpstreamRegistry):
        """Property 2.7: All UpstreamRegistry enum values have URL mappings.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any UpstreamRegistry enum value, there SHALL be a corresponding
        entry in UPSTREAM_REGISTRY_URLS with a non-empty URL string.
        """
        assert registry_type in UPSTREAM_REGISTRY_URLS, (
            f'UpstreamRegistry.{registry_type.name} should have a URL mapping'
        )

        url = UPSTREAM_REGISTRY_URLS[registry_type]
        assert url is not None, f'URL for {registry_type} should not be None'
        assert isinstance(url, str), f'URL for {registry_type} should be a string'
        assert len(url) > 0, f'URL for {registry_type} should not be empty'

    @settings(max_examples=100)
    @given(registry_type=st.sampled_from(list(UpstreamRegistry)))
    def test_url_mapping_format_validity(self, registry_type: UpstreamRegistry):
        """Property 2.8: URL mappings are valid registry URLs.

        Feature: ecr-container-tools, Property 2: Registry Type to URL Mapping
        **Validates: Requirements 4.2**

        For any UpstreamRegistry enum value, the mapped URL SHALL be a valid
        registry URL format (containing a domain with at least one dot or
        being a well-known registry domain).
        """
        url = UPSTREAM_REGISTRY_URLS[registry_type]

        # Valid registry URLs should either contain a dot (domain) or be a known format
        valid_url_patterns = [
            'registry-1.docker.io',
            'quay.io',
            'public.ecr.aws',
        ]

        assert url in valid_url_patterns or '.' in url, (
            f'URL "{url}" for {registry_type} should be a valid registry URL format'
        )


# =============================================================================
# Property 3: Credential Requirement by Registry Type
# Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
# Validates: Requirements 4.5, 4.6
# =============================================================================


class TestCredentialRequirementByRegistryType:
    """Property 3: Credential Requirement by Registry Type.

    **Validates: Requirements 4.5, 4.6**

    *For any* pull-through cache creation request:
    - If upstream_registry is 'docker-hub' and credential_arn is None, the request
      SHALL be rejected with a validation error
    - If upstream_registry is 'quay' or 'ecr-public', the request SHALL succeed
      regardless of credential_arn presence
    """

    # Strategy for generating valid Secrets Manager ARNs
    credential_arn_strategy = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',  # pragma: allowlist secret
        min_size=5,
        max_size=50,
    ).map(lambda s: f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{s}')

    # Strategy for generating optional credential ARNs (including None)
    optional_credential_arn_strategy = st.one_of(
        st.none(),
        credential_arn_strategy,
    )

    # =========================================================================
    # Property 3.1: Docker Hub requires credentials
    # =========================================================================

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(data=st.data())
    async def test_docker_hub_without_credentials_rejected(self, data):
        """Property 3.1: Docker Hub without credentials is rejected.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.5**

        For any pull-through cache creation request where upstream_registry is
        'docker-hub' and credential_arn is None, the request SHALL be rejected
        with a validation error.
        """
        # Generate optional prefix (None or a valid prefix string)
        ecr_prefix = data.draw(
            st.one_of(
                st.none(),
                st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',  # pragma: allowlist secret
                    min_size=1,
                    max_size=20,
                ),
            )
        )

        mock_ctx = AsyncMock()

        # No need to mock ECR client - validation should fail before any API calls
        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='docker-hub',
            ecr_repository_prefix=ecr_prefix,
            credential_arn=None,  # No credentials provided
        )

        # Assert the request was rejected
        assert result['success'] is False, (
            'Expected success=False when docker-hub is used without credentials'
        )
        assert result['rule'] is None, (
            'Expected rule=None when docker-hub is used without credentials'
        )
        assert 'credential' in result['message'].lower(), (
            f'Expected error message to mention credentials, got: {result["message"]}'
        )
        assert 'docker' in result['message'].lower() or 'required' in result['message'].lower(), (
            f'Expected error message to indicate Docker Hub credential requirement, '
            f'got: {result["message"]}'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(credential_arn=credential_arn_strategy)
    async def test_docker_hub_with_credentials_accepted(self, credential_arn: str):
        """Property 3.2: Docker Hub with credentials is accepted.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.5**

        For any pull-through cache creation request where upstream_registry is
        'docker-hub' and a valid credential_arn is provided, the request SHALL
        proceed to create the pull-through cache rule.
        """
        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'docker-hub',
            'upstreamRegistryUrl': 'registry-1.docker.io',
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='docker-hub',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert the request was accepted and proceeded to API call
        assert result['success'] is True, (
            f'Expected success=True when docker-hub is used with credentials, got: {result}'
        )
        mock_client.create_pull_through_cache_rule.assert_called_once()

        # Verify credential ARN was passed to the API
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs.get('credentialArn') == credential_arn, (
            f'Expected credentialArn to be "{credential_arn}", '
            f'got "{call_kwargs.get("credentialArn")}"'
        )

    # =========================================================================
    # Property 3.3: Quay succeeds regardless of credential presence
    # =========================================================================

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(credential_arn=optional_credential_arn_strategy)
    async def test_quay_succeeds_regardless_of_credentials(self, credential_arn: Optional[str]):
        """Property 3.3: Quay succeeds regardless of credential_arn presence.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.6**

        For any pull-through cache creation request where upstream_registry is
        'quay', the request SHALL succeed regardless of whether credential_arn
        is provided or None.
        """
        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert the request succeeded
        assert result['success'] is True, (
            f'Expected success=True for quay with credential_arn={credential_arn}, got: {result}'
        )
        mock_client.create_pull_through_cache_rule.assert_called_once()

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(data=st.data())
    async def test_quay_without_credentials_proceeds_to_api(self, data):
        """Property 3.4: Quay without credentials proceeds to API call.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.6**

        For any pull-through cache creation request where upstream_registry is
        'quay' and credential_arn is None, the request SHALL proceed to make
        the ECR API call (not be rejected at validation).
        """
        # Generate optional prefix
        ecr_prefix = data.draw(
            st.one_of(
                st.none(),
                st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',  # pragma: allowlist secret
                    min_size=1,
                    max_size=20,
                ),
            )
        )

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': ecr_prefix or 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=ecr_prefix,
                credential_arn=None,
            )

        # Assert the API was called (validation passed)
        mock_client.create_pull_through_cache_rule.assert_called_once()
        assert result['success'] is True

    # =========================================================================
    # Property 3.5: ECR Public succeeds regardless of credential presence
    # =========================================================================

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(credential_arn=optional_credential_arn_strategy)
    async def test_ecr_public_succeeds_regardless_of_credentials(
        self, credential_arn: Optional[str]
    ):
        """Property 3.5: ECR Public succeeds regardless of credential_arn presence.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.6**

        For any pull-through cache creation request where upstream_registry is
        'ecr-public', the request SHALL succeed regardless of whether credential_arn
        is provided or None.
        """
        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'ecr-public',
            'upstreamRegistryUrl': 'public.ecr.aws',
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='ecr-public',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert the request succeeded
        assert result['success'] is True, (
            f'Expected success=True for ecr-public with credential_arn={credential_arn}, '
            f'got: {result}'
        )
        mock_client.create_pull_through_cache_rule.assert_called_once()

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(data=st.data())
    async def test_ecr_public_without_credentials_proceeds_to_api(self, data):
        """Property 3.6: ECR Public without credentials proceeds to API call.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.6**

        For any pull-through cache creation request where upstream_registry is
        'ecr-public' and credential_arn is None, the request SHALL proceed to make
        the ECR API call (not be rejected at validation).
        """
        # Generate optional prefix
        ecr_prefix = data.draw(
            st.one_of(
                st.none(),
                st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',  # pragma: allowlist secret
                    min_size=1,
                    max_size=20,
                ),
            )
        )

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': ecr_prefix or 'ecr-public',
            'upstreamRegistryUrl': 'public.ecr.aws',
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='ecr-public',
                ecr_repository_prefix=ecr_prefix,
                credential_arn=None,
            )

        # Assert the API was called (validation passed)
        mock_client.create_pull_through_cache_rule.assert_called_once()
        assert result['success'] is True

    # =========================================================================
    # Property 3.7: Comprehensive registry type and credential combinations
    # =========================================================================

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        registry_type=st.sampled_from(['quay', 'ecr-public']),
        has_credentials=st.booleans(),
    )
    async def test_non_docker_hub_registries_accept_any_credential_state(
        self, registry_type: str, has_credentials: bool
    ):
        """Property 3.7: Non-Docker Hub registries accept any credential state.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.6**

        For any pull-through cache creation request where upstream_registry is
        'quay' or 'ecr-public', the request SHALL succeed regardless of whether
        credentials are provided or not.
        """
        credential_arn = (
            'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-creds'
            if has_credentials
            else None
        )

        expected_urls = {
            'quay': 'quay.io',
            'ecr-public': 'public.ecr.aws',
        }

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock successful pull-through cache rule creation
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': registry_type,
            'upstreamRegistryUrl': expected_urls[registry_type],
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }

        # Mock registry policy operations
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}

        # Mock repository creation template operations
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry=registry_type,
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert the request succeeded
        assert result['success'] is True, (
            f'Expected success=True for {registry_type} with '
            f'has_credentials={has_credentials}, got: {result}'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        ecr_prefix=st.one_of(
            st.none(),
            st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',  # pragma: allowlist secret
                min_size=1,
                max_size=20,
            ),
        )
    )
    async def test_docker_hub_credential_requirement_independent_of_prefix(
        self, ecr_prefix: Optional[str]
    ):
        """Property 3.8: Docker Hub credential requirement is independent of prefix.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.5**

        For any pull-through cache creation request where upstream_registry is
        'docker-hub' and credential_arn is None, the request SHALL be rejected
        regardless of what ecr_repository_prefix is specified.
        """
        mock_ctx = AsyncMock()

        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='docker-hub',
            ecr_repository_prefix=ecr_prefix,
            credential_arn=None,
        )

        # Assert the request was rejected
        assert result['success'] is False, (
            f'Expected success=False for docker-hub without credentials with prefix={ecr_prefix}'
        )
        assert 'credential' in result['message'].lower(), (
            f'Expected error message to mention credentials for prefix={ecr_prefix}'
        )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        registry_type=st.sampled_from(['docker-hub', 'quay', 'ecr-public']),
        credential_arn=optional_credential_arn_strategy,
    )
    async def test_credential_validation_by_registry_type(
        self, registry_type: str, credential_arn: Optional[str]
    ):
        """Property 3.9: Credential validation depends on registry type.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.5, 4.6**

        For any combination of registry type and credential presence:
        - docker-hub + no credentials → rejected
        - docker-hub + credentials → accepted
        - quay + any → accepted
        - ecr-public + any → accepted
        """
        expected_urls = {
            'docker-hub': 'registry-1.docker.io',
            'quay': 'quay.io',
            'ecr-public': 'public.ecr.aws',
        }

        # Determine expected outcome
        should_be_rejected = registry_type == 'docker-hub' and credential_arn is None

        if should_be_rejected:
            # No need to mock ECR client - validation should fail first
            mock_ctx = AsyncMock()

            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry=registry_type,
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

            assert result['success'] is False, (
                f'Expected rejection for {registry_type} without credentials'
            )
            assert 'credential' in result['message'].lower()
        else:
            # Create mock ECR client for successful cases
            mock_client = _create_mock_ecr_client()

            mock_client.create_pull_through_cache_rule.return_value = {
                'ecrRepositoryPrefix': registry_type,
                'upstreamRegistryUrl': expected_urls[registry_type],
                'credentialArn': credential_arn,
                'createdAt': datetime.now(timezone.utc),
            }

            mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
                {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
                'GetRegistryPolicy',
            )
            mock_client.put_registry_policy.return_value = {}
            mock_client.create_repository_creation_template.return_value = {}

            mock_ctx = AsyncMock()

            with patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_client,
            ):
                result = await create_pull_through_cache_for_healthomics(
                    ctx=mock_ctx,
                    upstream_registry=registry_type,
                    ecr_repository_prefix=None,
                    credential_arn=credential_arn,
                )

            assert result['success'] is True, (
                f'Expected success for {registry_type} with credential_arn={credential_arn}'
            )

    # =========================================================================
    # Property 3.10: Error message quality for Docker Hub credential requirement
    # =========================================================================

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(data=st.data())
    async def test_docker_hub_rejection_message_is_informative(self, data):
        """Property 3.10: Docker Hub rejection message is informative.

        Feature: ecr-container-tools, Property 3: Credential Requirement by Registry Type
        **Validates: Requirements 4.5**

        When docker-hub is used without credentials, the error message SHALL
        be informative and mention both Docker Hub and Secrets Manager.
        """
        mock_ctx = AsyncMock()

        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='docker-hub',
            ecr_repository_prefix=None,
            credential_arn=None,
        )

        assert result['success'] is False
        message = result['message'].lower()

        # Message should be informative
        assert 'credential' in message, 'Error message should mention credentials'
        assert 'docker' in message or 'required' in message, (
            'Error message should indicate requirement'
        )
        assert 'secrets manager' in message or 'arn' in message, (
            'Error message should mention Secrets Manager or ARN'
        )


# =============================================================================
# Unit Tests for create_pull_through_cache_for_healthomics
# Feature: ecr-container-tools
# Task 9.4: Write unit tests for create_pull_through_cache_for_healthomics
# Requirements: 4.1, 4.5, 4.7, 4.8
# =============================================================================


class TestCreatePullThroughCacheForHealthOmicsUnit:
    """Unit tests for create_pull_through_cache_for_healthomics function.

    These tests cover:
    1. Successful creation for each registry type (docker-hub, quay, ecr-public)
    2. Docker Hub credential requirement validation
    3. Existing rule handling (PullThroughCacheRuleAlreadyExistsException)
    4. Permission application errors (registry policy update failure, template creation failure)
    5. Invalid registry type handling
    6. Error handling (AccessDeniedException, InvalidParameterException, LimitExceededException)
    7. Custom prefix handling
    8. Response structure validation

    **Validates: Requirements 4.1, 4.5, 4.7, 4.8**
    """

    # =========================================================================
    # Test 1: Successful creation for each registry type
    # =========================================================================

    @pytest.mark.asyncio
    async def test_successful_creation_docker_hub(self):
        """Test successful creation for Docker Hub registry.

        **Validates: Requirement 4.1** - Accept upstream registry type and credential ARN
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'docker-hub',
            'upstreamRegistryUrl': 'registry-1.docker.io',
            'credentialArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-creds',
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='docker-hub',
                ecr_repository_prefix=None,
                credential_arn='arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-creds',
            )

        # Assert
        assert result['success'] is True
        assert result['rule'] is not None
        assert result['rule']['ecr_repository_prefix'] == 'docker-hub'
        assert result['rule']['upstream_registry_url'] == 'registry-1.docker.io'
        assert result['registry_policy_updated'] is True
        assert result['repository_template_created'] is True
        mock_client.create_pull_through_cache_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_creation_quay(self):
        """Test successful creation for Quay.io registry.

        **Validates: Requirement 4.1** - Accept upstream registry type
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['rule'] is not None
        assert result['rule']['ecr_repository_prefix'] == 'quay'
        assert result['rule']['upstream_registry_url'] == 'quay.io'
        assert result['registry_policy_updated'] is True
        assert result['repository_template_created'] is True

    @pytest.mark.asyncio
    async def test_successful_creation_ecr_public(self):
        """Test successful creation for ECR Public registry.

        **Validates: Requirement 4.1** - Accept upstream registry type
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'ecr-public',
            'upstreamRegistryUrl': 'public.ecr.aws',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='ecr-public',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['rule'] is not None
        assert result['rule']['ecr_repository_prefix'] == 'ecr-public'
        assert result['rule']['upstream_registry_url'] == 'public.ecr.aws'
        assert result['registry_policy_updated'] is True
        assert result['repository_template_created'] is True

    # =========================================================================
    # Test 2: Docker Hub credential requirement validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_docker_hub_requires_credential_arn(self):
        """Test that Docker Hub requires credential ARN.

        **Validates: Requirement 4.5** - Docker Hub SHALL require credential ARN
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act - No need to mock ECR client, validation should fail first
        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='docker-hub',
            ecr_repository_prefix=None,
            credential_arn=None,
        )

        # Assert
        assert result['success'] is False
        assert result['rule'] is None
        assert result['registry_policy_updated'] is False
        assert result['repository_template_created'] is False
        assert 'credential' in result['message'].lower()
        assert 'docker' in result['message'].lower() or 'required' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_docker_hub_with_credential_arn_succeeds(self):
        """Test that Docker Hub with credential ARN succeeds.

        **Validates: Requirement 4.5** - Docker Hub with credentials should succeed
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        credential_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:docker-creds'
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'docker-hub',
            'upstreamRegistryUrl': 'registry-1.docker.io',
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='docker-hub',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert
        assert result['success'] is True
        assert result['rule'] is not None
        assert result['rule']['credential_arn'] == credential_arn

    # =========================================================================
    # Test 3: Existing rule handling (PullThroughCacheRuleAlreadyExistsException)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_existing_rule_handling(self):
        """Test handling when pull-through cache rule already exists.

        **Validates: Requirement 4.7** - Return informative message for existing rule
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'PullThroughCacheRuleAlreadyExistsException',
                    'Message': 'Rule already exists',
                }
            },
            'CreatePullThroughCacheRule',
        )
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'quay',
                    'upstreamRegistryUrl': 'quay.io',
                    'credentialArn': None,
                    'createdAt': datetime.now(timezone.utc),
                }
            ]
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['rule'] is not None
        assert 'already exists' in result['message'].lower()
        # Should still update permissions
        assert result['registry_policy_updated'] is True
        assert result['repository_template_created'] is True

    @pytest.mark.asyncio
    async def test_existing_rule_with_failed_describe(self):
        """Test handling when rule exists but describe fails.

        **Validates: Requirement 4.7** - Handle existing rule gracefully
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'PullThroughCacheRuleAlreadyExistsException',
                    'Message': 'Rule already exists',
                }
            },
            'CreatePullThroughCacheRule',
        )
        mock_client.describe_pull_through_cache_rules.side_effect = Exception('Describe failed')
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='ecr-public',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert - Should still succeed with default values
        assert result['success'] is True
        assert result['rule'] is not None

    # =========================================================================
    # Test 4: Permission application errors
    # =========================================================================

    @pytest.mark.asyncio
    async def test_registry_policy_update_failure(self):
        """Test handling when registry policy update fails.

        **Validates: Requirement 4.8** - Return detailed error for permission failures
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'PutRegistryPolicy',
        )
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True  # Rule was created
        assert result['registry_policy_updated'] is False
        assert result['repository_template_created'] is True
        assert (
            'registry policy' in result['message'].lower() or 'failed' in result['message'].lower()
        )

    @pytest.mark.asyncio
    async def test_repository_template_creation_failure(self):
        """Test handling when repository template creation fails.

        **Validates: Requirement 4.8** - Return detailed error for permission failures
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'CreateRepositoryCreationTemplate',
            )
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True  # Rule was created
        assert result['registry_policy_updated'] is True
        assert result['repository_template_created'] is False
        assert 'template' in result['message'].lower() or 'failed' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_both_permission_updates_fail(self):
        """Test handling when both registry policy and template creation fail.

        **Validates: Requirement 4.8** - Return detailed error for permission failures
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.side_effect = Exception('Policy update failed')
        mock_client.create_repository_creation_template.side_effect = Exception(
            'Template creation failed'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True  # Rule was created
        assert result['registry_policy_updated'] is False
        assert result['repository_template_created'] is False
        assert 'warning' in result['message'].lower() or 'failed' in result['message'].lower()

    # =========================================================================
    # Test 5: Invalid registry type handling
    # =========================================================================

    @pytest.mark.asyncio
    async def test_invalid_registry_type(self):
        """Test handling of invalid registry type.

        **Validates: Requirement 4.1** - Validate upstream registry type
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='invalid-registry',
            ecr_repository_prefix=None,
            credential_arn=None,
        )

        # Assert
        assert result['success'] is False
        assert result['rule'] is None
        assert 'invalid' in result['message'].lower()
        assert 'docker-hub' in result['message'].lower() or 'quay' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_empty_registry_type(self):
        """Test handling of empty registry type.

        **Validates: Requirement 4.1** - Validate upstream registry type
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='',
            ecr_repository_prefix=None,
            credential_arn=None,
        )

        # Assert
        assert result['success'] is False
        assert result['rule'] is None
        assert 'invalid' in result['message'].lower()

    # =========================================================================
    # Test 6: Error handling (AccessDeniedException, InvalidParameterException, etc.)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_access_denied_exception(self):
        """Test handling of AccessDeniedException.

        **Validates: Requirement 4.8** - Return detailed error for permission failures
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform ecr:CreatePullThroughCacheRule',
                }
            },
            'CreatePullThroughCacheRule',
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is False
        assert 'access denied' in result['message'].lower()
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_parameter_exception(self):
        """Test handling of InvalidParameterException.

        **Validates: Requirement 4.8** - Return detailed error
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'InvalidParameterException',
                    'Message': 'Invalid parameter: prefix contains invalid characters',
                }
            },
            'CreatePullThroughCacheRule',
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix='invalid/prefix!@#',
                credential_arn=None,
            )

        # Assert
        assert result['success'] is False
        assert 'invalid parameter' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_limit_exceeded_exception(self):
        """Test handling of LimitExceededException.

        **Validates: Requirement 4.8** - Return detailed error
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'LimitExceededException',
                    'Message': 'Maximum number of pull-through cache rules exceeded',
                }
            },
            'CreatePullThroughCacheRule',
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is False
        assert 'limit exceeded' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_generic_client_error(self):
        """Test handling of generic ClientError.

        **Validates: Requirement 4.8** - Return detailed error
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ServiceException',
                    'Message': 'Internal service error',
                }
            },
            'CreatePullThroughCacheRule',
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is False
        assert 'error' in result['message'].lower()
        mock_ctx.error.assert_called_once()

    # =========================================================================
    # Test 7: Custom prefix handling
    # =========================================================================

    @pytest.mark.asyncio
    async def test_custom_prefix_used(self):
        """Test that custom prefix is used when provided.

        **Validates: Requirement 4.1** - Accept optional ECR repository prefix
        """
        # Arrange
        custom_prefix = 'my-custom-prefix'
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': custom_prefix,
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=custom_prefix,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['rule']['ecr_repository_prefix'] == custom_prefix
        # Verify the custom prefix was passed to the API
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs['ecrRepositoryPrefix'] == custom_prefix

    @pytest.mark.asyncio
    async def test_default_prefix_used_when_not_provided(self):
        """Test that default prefix is used when not provided.

        **Validates: Requirement 4.1** - Default to registry type name
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        # Verify the default prefix was used
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs['ecrRepositoryPrefix'] == 'quay'

    # =========================================================================
    # Test 8: Response structure validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_response_structure_on_success(self):
        """Test that successful response has correct structure.

        **Validates: Requirement 4.1** - Return created rule details
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        created_at = datetime.now(timezone.utc)
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': created_at,
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert - Check all required fields are present
        assert 'success' in result
        assert 'rule' in result
        assert 'registry_policy_updated' in result
        assert 'repository_template_created' in result
        assert 'message' in result

        # Check rule structure
        rule = result['rule']
        assert rule is not None
        assert 'ecr_repository_prefix' in rule
        assert 'upstream_registry_url' in rule
        assert 'credential_arn' in rule
        assert 'healthomics_usable' in rule
        assert 'registry_permission_granted' in rule
        assert 'repository_template_exists' in rule
        assert 'repository_template_permission_granted' in rule

    @pytest.mark.asyncio
    async def test_response_structure_on_failure(self):
        """Test that failure response has correct structure.

        **Validates: Requirement 4.8** - Return detailed error
        """
        # Arrange
        mock_ctx = AsyncMock()

        # Act - Invalid registry type causes early failure
        result = await create_pull_through_cache_for_healthomics(
            ctx=mock_ctx,
            upstream_registry='invalid',
            ecr_repository_prefix=None,
            credential_arn=None,
        )

        # Assert - Check all required fields are present
        assert 'success' in result
        assert result['success'] is False
        assert 'rule' in result
        assert result['rule'] is None
        assert 'registry_policy_updated' in result
        assert result['registry_policy_updated'] is False
        assert 'repository_template_created' in result
        assert result['repository_template_created'] is False
        assert 'message' in result
        assert len(result['message']) > 0

    @pytest.mark.asyncio
    async def test_healthomics_usable_flag_when_all_permissions_succeed(self):
        """Test that healthomics_usable is True when all permissions are configured.

        **Validates: Requirement 4.1** - Return confirmation of HealthOmics permissions
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['rule']['healthomics_usable'] is True
        assert result['rule']['registry_permission_granted'] is True
        assert result['rule']['repository_template_exists'] is True
        assert result['rule']['repository_template_permission_granted'] is True

    @pytest.mark.asyncio
    async def test_healthomics_usable_flag_when_permissions_fail(self):
        """Test that healthomics_usable is False when permissions fail.

        **Validates: Requirement 4.8** - Indicate permission status
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.side_effect = Exception('Policy update failed')
        mock_client.create_repository_creation_template.side_effect = Exception('Template failed')

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True  # Rule was created
        assert result['rule']['healthomics_usable'] is False
        assert result['rule']['registry_permission_granted'] is False
        assert result['rule']['repository_template_exists'] is False

    # =========================================================================
    # Additional edge case tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_existing_registry_policy_updated(self):
        """Test that existing registry policy is updated correctly.

        **Validates: Requirement 4.1** - Update registry permissions policy
        """
        # Arrange
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'ExistingStatement',
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                    'Action': ['ecr:GetAuthorizationToken'],
                    'Resource': '*',
                }
            ],
        }
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(existing_policy)}
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['registry_policy_updated'] is True
        # Verify put_registry_policy was called
        mock_client.put_registry_policy.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_already_exists_updated(self):
        """Test that existing template is updated correctly.

        **Validates: Requirement 4.1** - Create/update repository creation template
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': None,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        # Template already exists
        mock_client.create_repository_creation_template.side_effect = (
            botocore.exceptions.ClientError(
                {
                    'Error': {
                        'Code': 'TemplateAlreadyExistsException',
                        'Message': 'Template exists',
                    }
                },
                'CreateRepositoryCreationTemplate',
            )
        )
        mock_client.update_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is True
        assert result['repository_template_created'] is True
        mock_client.update_repository_creation_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_quay_with_optional_credentials(self):
        """Test Quay.io with optional credentials provided.

        **Validates: Requirement 4.1** - Quay.io accepts optional credentials
        """
        # Arrange
        credential_arn = 'arn:aws:secretsmanager:us-east-1:123456789012:secret:quay-creds'
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.return_value = {
            'ecrRepositoryPrefix': 'quay',
            'upstreamRegistryUrl': 'quay.io',
            'credentialArn': credential_arn,
            'createdAt': datetime.now(timezone.utc),
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.put_registry_policy.return_value = {}
        mock_client.create_repository_creation_template.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=credential_arn,
            )

        # Assert
        assert result['success'] is True
        assert result['rule']['credential_arn'] == credential_arn
        # Verify credentials were passed to API
        call_kwargs = mock_client.create_pull_through_cache_rule.call_args[1]
        assert call_kwargs['credentialArn'] == credential_arn

    @pytest.mark.asyncio
    async def test_botocore_error_handling(self):
        """Test handling of BotoCoreError.

        **Validates: Requirement 4.8** - Return detailed error
        """
        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.create_pull_through_cache_rule.side_effect = (
            botocore.exceptions.BotoCoreError()
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await create_pull_through_cache_for_healthomics(
                ctx=mock_ctx,
                upstream_registry='quay',
                ecr_repository_prefix=None,
                credential_arn=None,
            )

        # Assert
        assert result['success'] is False
        assert 'aws error' in result['message'].lower() or 'error' in result['message'].lower()
        mock_ctx.error.assert_called_once()


# =============================================================================
# Property 5: Validation Issue Remediation
# Feature: ecr-container-tools, Property 5: Validation Issue Remediation
# Validates: Requirements 5.5
# =============================================================================


# Hypothesis Strategies for Validation Scenarios
# Strategy for generating validation severity levels
severity_strategy = st.sampled_from(['error', 'warning', 'info'])

# Strategy for generating validation component types
component_strategy = st.sampled_from(
    ['registry_policy', 'repository_template', 'pull_through_cache']
)

# Strategy for generating ECR repository prefixes
ecr_prefix_strategy = st.sampled_from(['docker-hub', 'quay', 'ecr-public', 'custom-prefix'])

# Strategy for generating upstream registry URLs
upstream_url_strategy = st.sampled_from(
    [
        'registry-1.docker.io',
        'quay.io',
        'public.ecr.aws',
    ]
)


@st.composite
def pull_through_cache_rule_strategy(draw) -> Dict[str, Any]:
    """Generate a valid pull-through cache rule for testing."""
    prefix = draw(ecr_prefix_strategy)
    url = draw(upstream_url_strategy)
    return {
        'ecrRepositoryPrefix': prefix,
        'upstreamRegistryUrl': url,
        'credentialArn': draw(
            st.one_of(
                st.none(), st.just('arn:aws:secretsmanager:us-east-1:123456789012:secret:creds')
            )
        ),
        'createdAt': datetime.now(timezone.utc),
    }


@st.composite
def registry_policy_scenario_strategy(draw) -> Dict[str, Any]:
    """Generate a registry policy scenario for validation testing.

    Returns a dict with:
    - has_policy: Whether a registry policy exists
    - has_healthomics_principal: Whether the policy includes HealthOmics principal
    - has_required_actions: Whether the policy includes required actions
    - policy_text: The policy JSON string or None
    """
    has_policy = draw(st.booleans())

    if not has_policy:
        return {
            'has_policy': False,
            'has_healthomics_principal': False,
            'has_required_actions': False,
            'policy_text': None,
        }

    has_healthomics_principal = draw(st.booleans())
    has_required_actions = draw(st.booleans()) if has_healthomics_principal else False

    if has_healthomics_principal and has_required_actions:
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
    elif has_healthomics_principal:
        # Has principal but missing some actions
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository'],  # Missing BatchImportUpstreamImage
                    'Resource': '*',
                }
            ],
        }
    else:
        # Policy exists but no HealthOmics principal
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'OtherAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'lambda.amazonaws.com'},
                    'Action': ['ecr:GetDownloadUrlForLayer'],
                    'Resource': '*',
                }
            ],
        }

    return {
        'has_policy': True,
        'has_healthomics_principal': has_healthomics_principal,
        'has_required_actions': has_required_actions,
        'policy_text': json.dumps(policy),
    }


@st.composite
def repository_template_scenario_strategy(draw) -> Dict[str, Any]:
    """Generate a repository template scenario for validation testing.

    Returns a dict with:
    - template_exists: Whether a template exists
    - has_policy: Whether the template has a policy
    - has_healthomics_principal: Whether the policy includes HealthOmics principal
    - has_required_actions: Whether the policy includes required actions
    - policy_text: The policy JSON string or None
    """
    template_exists = draw(st.booleans())

    if not template_exists:
        return {
            'template_exists': False,
            'has_policy': False,
            'has_healthomics_principal': False,
            'has_required_actions': False,
            'policy_text': None,
        }

    has_policy = draw(st.booleans())

    if not has_policy:
        return {
            'template_exists': True,
            'has_policy': False,
            'has_healthomics_principal': False,
            'has_required_actions': False,
            'policy_text': None,
        }

    has_healthomics_principal = draw(st.booleans())
    has_required_actions = draw(st.booleans()) if has_healthomics_principal else False

    if has_healthomics_principal and has_required_actions:
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
    elif has_healthomics_principal:
        # Has principal but missing some actions
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage'],  # Missing GetDownloadUrlForLayer
                }
            ],
        }
    else:
        # Policy exists but no HealthOmics principal
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'OtherAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'lambda.amazonaws.com'},
                    'Action': ['ecr:GetDownloadUrlForLayer'],
                }
            ],
        }

    return {
        'template_exists': True,
        'has_policy': True,
        'has_healthomics_principal': has_healthomics_principal,
        'has_required_actions': has_required_actions,
        'policy_text': json.dumps(policy),
    }


@st.composite
def validation_scenario_strategy(draw) -> Dict[str, Any]:
    """Generate a complete validation scenario combining PTC rules, registry policy, and templates.

    This strategy generates scenarios that will produce various validation issues
    to test that all issues have non-empty remediation fields.
    """
    # Generate 0-3 pull-through cache rules
    num_rules = draw(st.integers(min_value=0, max_value=3))
    ptc_rules = [draw(pull_through_cache_rule_strategy()) for _ in range(num_rules)]

    # Generate registry policy scenario
    registry_scenario = draw(registry_policy_scenario_strategy())

    # Generate template scenarios for each prefix
    template_scenarios = {}
    for rule in ptc_rules:
        prefix = rule['ecrRepositoryPrefix']
        template_scenarios[prefix] = draw(repository_template_scenario_strategy())

    return {
        'ptc_rules': ptc_rules,
        'registry_scenario': registry_scenario,
        'template_scenarios': template_scenarios,
    }


class TestValidationIssueRemediation:
    """Property 5: Validation Issue Remediation.

    **Validates: Requirements 5.5**

    *For any* validation issue detected during configuration validation, the issue
    object SHALL contain a non-empty `remediation` field with actionable guidance.
    """

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(scenario=validation_scenario_strategy())
    async def test_all_validation_issues_have_non_empty_remediation(
        self, scenario: Dict[str, Any]
    ):
        """Property 5.1: All validation issues have non-empty remediation fields.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        For any validation issue detected during configuration validation,
        the issue object SHALL contain a non-empty `remediation` field.
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        ptc_rules = scenario['ptc_rules']
        registry_scenario = scenario['registry_scenario']
        template_scenarios = scenario['template_scenarios']

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock describe_pull_through_cache_rules
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': ptc_rules,
        }

        # Mock get_registry_policy based on scenario
        if registry_scenario['has_policy']:
            mock_client.get_registry_policy.return_value = {
                'policyText': registry_scenario['policy_text']
            }
        else:
            mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
                {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
                'GetRegistryPolicy',
            )

        # Mock describe_repository_creation_templates based on scenarios
        def mock_describe_templates(prefixes):
            if not prefixes:
                return {'repositoryCreationTemplates': []}

            prefix = prefixes[0]
            template_scenario = template_scenarios.get(prefix, {})

            if not template_scenario.get('template_exists', False):
                raise botocore.exceptions.ClientError(
                    {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                    'DescribeRepositoryCreationTemplates',
                )

            template = {
                'prefix': prefix,
                'description': f'Template for {prefix}',
            }
            if template_scenario.get('has_policy', False):
                template['repositoryPolicy'] = template_scenario['policy_text']

            return {'repositoryCreationTemplates': [template]}

        mock_client.describe_repository_creation_templates.side_effect = mock_describe_templates

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Verify all issues have non-empty remediation fields
        issues = result.get('issues', [])
        for issue in issues:
            assert 'remediation' in issue, f'Issue missing remediation field: {issue}'
            assert issue['remediation'] is not None, f'Issue has None remediation: {issue}'
            assert isinstance(issue['remediation'], str), (
                f'Issue remediation is not a string: {issue}'
            )
            assert len(issue['remediation'].strip()) > 0, f'Issue has empty remediation: {issue}'

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(scenario=validation_scenario_strategy())
    async def test_remediation_contains_actionable_guidance(self, scenario: Dict[str, Any]):
        """Property 5.2: Remediation fields contain actionable guidance.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        For any validation issue, the remediation field SHALL contain actionable
        guidance (indicated by containing action words or specific instructions).
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        ptc_rules = scenario['ptc_rules']
        registry_scenario = scenario['registry_scenario']
        template_scenarios = scenario['template_scenarios']

        # Create mock ECR client
        mock_client = _create_mock_ecr_client()

        # Mock describe_pull_through_cache_rules
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': ptc_rules,
        }

        # Mock get_registry_policy based on scenario
        if registry_scenario['has_policy']:
            mock_client.get_registry_policy.return_value = {
                'policyText': registry_scenario['policy_text']
            }
        else:
            mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
                {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
                'GetRegistryPolicy',
            )

        # Mock describe_repository_creation_templates based on scenarios
        def mock_describe_templates(prefixes):
            if not prefixes:
                return {'repositoryCreationTemplates': []}

            prefix = prefixes[0]
            template_scenario = template_scenarios.get(prefix, {})

            if not template_scenario.get('template_exists', False):
                raise botocore.exceptions.ClientError(
                    {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                    'DescribeRepositoryCreationTemplates',
                )

            template = {
                'prefix': prefix,
                'description': f'Template for {prefix}',
            }
            if template_scenario.get('has_policy', False):
                template['repositoryPolicy'] = template_scenario['policy_text']

            return {'repositoryCreationTemplates': [template]}

        mock_client.describe_repository_creation_templates.side_effect = mock_describe_templates

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Verify remediation contains actionable guidance
        # Actionable guidance typically contains action verbs or specific instructions
        action_indicators = [
            'create',
            'update',
            'add',
            'grant',
            'configure',
            'use',
            'ensure',
            'include',
            'set',
            'apply',
            'modify',
            'check',
            'verify',
            'run',
            'no action required',
            'ready',
            'valid',
        ]

        issues = result.get('issues', [])
        for issue in issues:
            remediation = issue.get('remediation', '').lower()
            has_actionable_content = any(
                indicator in remediation for indicator in action_indicators
            )
            assert has_actionable_content, (
                f'Remediation does not contain actionable guidance: "{issue["remediation"]}"'
            )

    @pytest.mark.asyncio
    async def test_no_ptc_rules_issue_has_remediation(self):
        """Property 5.3: Info issue for no PTC rules has remediation.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        When no pull-through cache rules exist, the info issue SHALL have
        a non-empty remediation field with guidance on creating rules.
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Create mock ECR client with no PTC rules
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [],
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Should have an info issue about no PTC rules
        issues = result.get('issues', [])
        assert len(issues) >= 1, 'Expected at least one issue for no PTC rules'

        # Find the info issue about no PTC rules
        no_rules_issue = None
        for issue in issues:
            if (
                issue.get('severity') == 'info'
                and 'no pull-through cache' in issue.get('message', '').lower()
            ):
                no_rules_issue = issue
                break

        assert no_rules_issue is not None, 'Expected info issue about no PTC rules'
        assert no_rules_issue['remediation'] is not None, 'Remediation should not be None'
        assert len(no_rules_issue['remediation'].strip()) > 0, 'Remediation should not be empty'
        assert 'create' in no_rules_issue['remediation'].lower(), (
            'Remediation should mention creating rules'
        )

    @pytest.mark.asyncio
    async def test_missing_registry_policy_issue_has_remediation(self):
        """Property 5.4: Error issue for missing registry policy has remediation.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        When registry policy is missing, the error issue SHALL have a non-empty
        remediation field with guidance on creating the policy.
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Create mock ECR client with PTC rules but no registry policy
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Find the error issue about missing registry policy
        issues = result.get('issues', [])
        registry_policy_issue = None
        for issue in issues:
            if issue.get('component') == 'registry_policy' and issue.get('severity') == 'error':
                registry_policy_issue = issue
                break

        assert registry_policy_issue is not None, 'Expected error issue about registry policy'
        assert registry_policy_issue['remediation'] is not None, 'Remediation should not be None'
        assert len(registry_policy_issue['remediation'].strip()) > 0, (
            'Remediation should not be empty'
        )

    @pytest.mark.asyncio
    async def test_missing_template_issue_has_remediation(self):
        """Property 5.5: Error issue for missing template has remediation.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        When repository creation template is missing, the error issue SHALL have
        a non-empty remediation field with guidance on creating the template.
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Create mock ECR client with PTC rules, valid registry policy, but no template
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }
        # Valid registry policy
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}
        # No template
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Find the error issue about missing template
        issues = result.get('issues', [])
        template_issue = None
        for issue in issues:
            if (
                issue.get('component') == 'repository_template'
                and issue.get('severity') == 'error'
            ):
                template_issue = issue
                break

        assert template_issue is not None, 'Expected error issue about repository template'
        assert template_issue['remediation'] is not None, 'Remediation should not be None'
        assert len(template_issue['remediation'].strip()) > 0, 'Remediation should not be empty'

    @pytest.mark.asyncio
    async def test_valid_config_info_issue_has_remediation(self):
        """Property 5.6: Info issue for valid config has remediation.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        When configuration is valid, the info issue SHALL have a non-empty
        remediation field (even if it says 'no action required').
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Create mock ECR client with fully valid configuration
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }
        # Valid registry policy
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}
        # Valid template with correct permissions
        template_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'description': 'Template for docker-hub',
                    'repositoryPolicy': json.dumps(template_policy),
                }
            ],
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Should be valid
        assert result['valid'] is True, 'Configuration should be valid'

        # All issues (including info) should have remediation
        issues = result.get('issues', [])
        for issue in issues:
            assert issue['remediation'] is not None, (
                f'Issue remediation should not be None: {issue}'
            )
            assert len(issue['remediation'].strip()) > 0, (
                f'Issue remediation should not be empty: {issue}'
            )

    @pytest.mark.asyncio
    @settings(max_examples=100)
    @given(
        num_rules=st.integers(min_value=1, max_value=5),
        registry_has_policy=st.booleans(),
        registry_has_permissions=st.booleans(),
    )
    async def test_remediation_mentions_healthomics_for_permission_issues(
        self,
        num_rules: int,
        registry_has_policy: bool,
        registry_has_permissions: bool,
    ):
        """Property 5.7: Permission-related remediation mentions HealthOmics.

        Feature: ecr-container-tools, Property 5: Validation Issue Remediation
        **Validates: Requirements 5.5**

        For any permission-related validation issue, the remediation SHALL
        mention HealthOmics or the HealthOmics principal to provide context.
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Generate PTC rules
        ptc_rules = []
        prefixes = ['docker-hub', 'quay', 'ecr-public', 'custom-1', 'custom-2']
        for i in range(num_rules):
            ptc_rules.append(
                {
                    'ecrRepositoryPrefix': prefixes[i % len(prefixes)],
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            )

        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': ptc_rules,
        }

        # Configure registry policy based on parameters
        if registry_has_policy:
            if registry_has_permissions:
                policy = {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'omics.amazonaws.com'},
                            'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                            'Resource': '*',
                        }
                    ],
                }
            else:
                policy = {
                    'Version': '2012-10-17',
                    'Statement': [
                        {
                            'Effect': 'Allow',
                            'Principal': {'Service': 'lambda.amazonaws.com'},
                            'Action': ['ecr:GetDownloadUrlForLayer'],
                            'Resource': '*',
                        }
                    ],
                }
            mock_client.get_registry_policy.return_value = {'policyText': json.dumps(policy)}
        else:
            mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
                {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
                'GetRegistryPolicy',
            )

        # No templates for simplicity
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Check that permission-related issues mention HealthOmics
        issues = result.get('issues', [])
        for issue in issues:
            if issue.get('severity') == 'error':
                remediation_lower = issue['remediation'].lower()
                # Permission issues should mention HealthOmics or omics.amazonaws.com
                mentions_healthomics = (
                    'healthomics' in remediation_lower
                    or 'omics.amazonaws.com' in remediation_lower
                )
                assert mentions_healthomics, (
                    f'Permission-related remediation should mention HealthOmics: "{issue["remediation"]}"'
                )


# =============================================================================
# Unit Tests for validate_healthomics_ecr_config
# Feature: ecr-container-tools
# Task 10.3: Write unit tests for validate_healthomics_ecr_config
# Requirements: 5.1, 5.5, 5.6
# =============================================================================


class TestValidateHealthomicsECRConfigUnit:
    """Unit tests for validate_healthomics_ecr_config function.

    These tests cover:
    1. Fully valid configuration (all checks pass)
    2. Missing registry policy
    3. Missing repository templates
    4. Incorrect template permissions
    5. No pull-through cache rules
    6. Error handling

    **Validates: Requirements 5.1, 5.5, 5.6**
    """

    @pytest.mark.asyncio
    async def test_fully_valid_configuration(self):
        """Test validation of a fully valid ECR configuration.

        **Validates: Requirement 5.6** - Return overall validity status
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange - Create a fully valid configuration
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }

        # Registry policy grants HealthOmics access
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Repository template exists with correct permissions
        template_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'description': 'Template for docker-hub',
                    'repositoryPolicy': json.dumps(template_policy),
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is True
        assert result['pull_through_caches_checked'] == 1
        # Should have an info message about valid configuration
        info_issues = [i for i in result['issues'] if i['severity'] == 'info']
        assert len(info_issues) >= 1

    @pytest.mark.asyncio
    async def test_missing_registry_policy(self):
        """Test validation when registry policy is missing.

        **Validates: Requirement 5.2** - Check registry permissions policy
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }

        # No registry policy
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )

        # No template
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is False
        # Should have an error about missing registry policy
        registry_errors = [
            i
            for i in result['issues']
            if i['severity'] == 'error' and i['component'] == 'registry_policy'
        ]
        assert len(registry_errors) >= 1
        assert 'remediation' in registry_errors[0]
        assert len(registry_errors[0]['remediation']) > 0

    @pytest.mark.asyncio
    async def test_missing_repository_templates(self):
        """Test validation when repository templates are missing.

        **Validates: Requirement 5.3** - Check repository creation templates
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                },
                {
                    'ecrRepositoryPrefix': 'quay',
                    'upstreamRegistryUrl': 'quay.io',
                    'createdAt': datetime.now(timezone.utc),
                },
            ],
        }

        # Registry policy exists and is valid
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # No templates exist
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is False
        # Should have errors about missing templates for both prefixes
        template_errors = [
            i
            for i in result['issues']
            if i['severity'] == 'error' and i['component'] == 'repository_template'
        ]
        assert len(template_errors) == 2
        for error in template_errors:
            assert 'remediation' in error
            assert len(error['remediation']) > 0

    @pytest.mark.asyncio
    async def test_incorrect_template_permissions(self):
        """Test validation when template has incorrect permissions.

        **Validates: Requirement 5.4** - Verify template permissions
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }

        # Registry policy exists and is valid
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Template exists but with incomplete permissions (missing GetDownloadUrlForLayer)
        template_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'PartialAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage'],  # Missing GetDownloadUrlForLayer
                }
            ],
        }
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'description': 'Template for docker-hub',
                    'repositoryPolicy': json.dumps(template_policy),
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is False
        # Should have an error about incorrect template permissions
        template_errors = [
            i
            for i in result['issues']
            if i['severity'] == 'error' and i['component'] == 'repository_template'
        ]
        assert len(template_errors) >= 1
        # Error should mention missing permissions
        assert (
            'missing' in template_errors[0]['message'].lower()
            or 'permission' in template_errors[0]['message'].lower()
        )
        assert 'remediation' in template_errors[0]
        assert len(template_errors[0]['remediation']) > 0

    @pytest.mark.asyncio
    async def test_no_pull_through_cache_rules(self):
        """Test validation when no pull-through cache rules exist.

        **Validates: Requirement 5.1** - List all pull-through cache rules
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # No PTC rules
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is True  # No rules means nothing to validate
        assert result['pull_through_caches_checked'] == 0
        # Should have an info issue about no PTC rules
        info_issues = [
            i
            for i in result['issues']
            if i['severity'] == 'info' and 'no pull-through cache' in i['message'].lower()
        ]
        assert len(info_issues) >= 1
        assert 'remediation' in info_issues[0]
        assert len(info_issues[0]['remediation']) > 0

    @pytest.mark.asyncio
    async def test_access_denied_error(self):
        """Test handling of AccessDeniedException.

        **Validates: Requirement 5.6** - Handle errors gracefully
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
                'DescribePullThroughCacheRules',
            )
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()
        error_message = mock_ctx.error.call_args[0][0]
        assert 'Access denied' in error_message

    @pytest.mark.asyncio
    async def test_botocore_error_handling(self):
        """Test handling of BotoCoreError.

        **Validates: Requirement 5.6** - Handle errors gracefully
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()
        mock_client.describe_pull_through_cache_rules.side_effect = (
            botocore.exceptions.BotoCoreError()
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.BotoCoreError):
                await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Verify error was reported to context
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_ptc_rules_validation(self):
        """Test validation with multiple pull-through cache rules.

        **Validates: Requirement 5.1** - List all pull-through cache rules
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # Multiple PTC rules
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                },
                {
                    'ecrRepositoryPrefix': 'quay',
                    'upstreamRegistryUrl': 'quay.io',
                    'createdAt': datetime.now(timezone.utc),
                },
                {
                    'ecrRepositoryPrefix': 'ecr-public',
                    'upstreamRegistryUrl': 'public.ecr.aws',
                    'createdAt': datetime.now(timezone.utc),
                },
            ],
        }

        # Registry policy exists and is valid
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Templates exist for all prefixes
        template_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }

        def mock_describe_templates(prefixes):
            prefix = prefixes[0]
            return {
                'repositoryCreationTemplates': [
                    {
                        'prefix': prefix,
                        'description': f'Template for {prefix}',
                        'repositoryPolicy': json.dumps(template_policy),
                    }
                ],
            }

        mock_client.describe_repository_creation_templates.side_effect = mock_describe_templates

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is True
        assert result['pull_through_caches_checked'] == 3

    @pytest.mark.asyncio
    async def test_registry_policy_missing_actions(self):
        """Test validation when registry policy is missing required actions.

        **Validates: Requirement 5.2** - Check registry permissions policy
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }

        # Registry policy exists but missing BatchImportUpstreamImage
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'PartialAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository'],  # Missing BatchImportUpstreamImage
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Template exists
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is False
        # Should have an error about missing registry policy actions
        registry_errors = [
            i
            for i in result['issues']
            if i['severity'] == 'error' and i['component'] == 'registry_policy'
        ]
        assert len(registry_errors) >= 1
        assert 'missing' in registry_errors[0]['message'].lower()

    @pytest.mark.asyncio
    async def test_template_without_policy(self):
        """Test validation when template exists but has no policy.

        **Validates: Requirement 5.4** - Verify template permissions
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                }
            ],
        }

        # Registry policy exists and is valid
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Template exists but has no repositoryPolicy
        mock_client.describe_repository_creation_templates.return_value = {
            'repositoryCreationTemplates': [
                {
                    'prefix': 'docker-hub',
                    'description': 'Template for docker-hub',
                    # No repositoryPolicy field
                }
            ],
        }

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is False
        # Should have an error about template without policy
        template_errors = [
            i
            for i in result['issues']
            if i['severity'] == 'error' and i['component'] == 'repository_template'
        ]
        assert len(template_errors) >= 1

    @pytest.mark.asyncio
    async def test_all_issues_have_remediation(self):
        """Test that all validation issues have non-empty remediation fields.

        **Validates: Requirement 5.5** - Provide remediation steps
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange - Create a configuration with multiple issues
        mock_client = _create_mock_ecr_client()

        # PTC rules exist
        mock_client.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {
                    'ecrRepositoryPrefix': 'docker-hub',
                    'upstreamRegistryUrl': 'registry-1.docker.io',
                    'createdAt': datetime.now(timezone.utc),
                },
                {
                    'ecrRepositoryPrefix': 'quay',
                    'upstreamRegistryUrl': 'quay.io',
                    'createdAt': datetime.now(timezone.utc),
                },
            ],
        }

        # No registry policy
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RegistryPolicyNotFoundException', 'Message': 'Not found'}},
            'GetRegistryPolicy',
        )

        # No templates
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(
                {'Error': {'Code': 'TemplateNotFoundException', 'Message': 'Not found'}},
                'DescribeRepositoryCreationTemplates',
            )
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert - All issues should have non-empty remediation
        for issue in result['issues']:
            assert 'remediation' in issue, f'Issue missing remediation: {issue}'
            assert issue['remediation'] is not None, f'Issue has None remediation: {issue}'
            assert len(issue['remediation'].strip()) > 0, f'Issue has empty remediation: {issue}'

    @pytest.mark.asyncio
    async def test_pagination_of_ptc_rules(self):
        """Test that pagination is handled when listing PTC rules.

        **Validates: Requirement 5.1** - List all pull-through cache rules
        """
        from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
            validate_healthomics_ecr_config,
        )

        # Arrange
        mock_client = _create_mock_ecr_client()

        # Simulate paginated response
        call_count = [0]

        def mock_describe_ptc_rules(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    'pullThroughCacheRules': [
                        {
                            'ecrRepositoryPrefix': 'docker-hub',
                            'upstreamRegistryUrl': 'registry-1.docker.io',
                            'createdAt': datetime.now(timezone.utc),
                        }
                    ],
                    'nextToken': 'page2',
                }
            else:
                return {
                    'pullThroughCacheRules': [
                        {
                            'ecrRepositoryPrefix': 'quay',
                            'upstreamRegistryUrl': 'quay.io',
                            'createdAt': datetime.now(timezone.utc),
                        }
                    ],
                }

        mock_client.describe_pull_through_cache_rules.side_effect = mock_describe_ptc_rules

        # Registry policy exists and is valid
        registry_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:CreateRepository', 'ecr:BatchImportUpstreamImage'],
                    'Resource': '*',
                }
            ],
        }
        mock_client.get_registry_policy.return_value = {'policyText': json.dumps(registry_policy)}

        # Templates exist
        template_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                }
            ],
        }

        def mock_describe_templates(prefixes):
            return {
                'repositoryCreationTemplates': [
                    {
                        'prefix': prefixes[0],
                        'description': f'Template for {prefixes[0]}',
                        'repositoryPolicy': json.dumps(template_policy),
                    }
                ],
            }

        mock_client.describe_repository_creation_templates.side_effect = mock_describe_templates

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await validate_healthomics_ecr_config(ctx=mock_ctx)

        # Assert
        assert result['valid'] is True
        assert result['pull_through_caches_checked'] == 2
        # Should have called describe_pull_through_cache_rules twice
        assert mock_client.describe_pull_through_cache_rules.call_count == 2


# =============================================================================
# Unit Tests for grant_healthomics_repository_access
# Feature: ecr-container-tools
# =============================================================================


class TestGrantHealthOmicsRepositoryAccessUnit:
    """Unit tests for grant_healthomics_repository_access function.

    These tests cover:
    1. Granting access to a repository with no existing policy
    2. Updating an existing policy to add HealthOmics access
    3. Repository already has HealthOmics access (no changes needed)
    4. Repository not found error handling
    5. Access denied error handling
    6. Input validation (empty repository name)
    """

    @pytest.mark.asyncio
    async def test_grant_access_creates_new_policy(self):
        """Test that a new policy is created when none exists."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        # No existing policy
        error_response = {
            'Error': {
                'Code': 'RepositoryPolicyNotFoundException',
                'Message': 'Repository policy does not exist',
            }
        }
        mock_client.get_repository_policy.side_effect = [
            botocore.exceptions.ClientError(error_response, 'GetRepositoryPolicy'),
            # Second call after policy is set - return the new policy
            {
                'policyText': json.dumps(
                    {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Sid': 'HealthOmicsAccess',
                                'Effect': 'Allow',
                                'Principal': {'Service': 'omics.amazonaws.com'},
                                'Action': [
                                    'ecr:BatchGetImage',
                                    'ecr:GetDownloadUrlForLayer',
                                ],
                            }
                        ],
                    }
                )
            },
        ]
        mock_client.set_repository_policy.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        # Assert
        assert result['success'] is True
        assert result['repository_name'] == 'my-repo'
        assert result['policy_created'] is True
        assert result['policy_updated'] is False
        assert result['previous_healthomics_accessible'] == 'not_accessible'
        assert result['current_healthomics_accessible'] == 'accessible'
        assert 'created' in result['message'].lower()

        # Verify set_repository_policy was called
        mock_client.set_repository_policy.assert_called_once()
        call_kwargs = mock_client.set_repository_policy.call_args[1]
        assert call_kwargs['repositoryName'] == 'my-repo'
        policy = json.loads(call_kwargs['policyText'])
        assert any(
            stmt.get('Principal', {}).get('Service') == 'omics.amazonaws.com'
            for stmt in policy['Statement']
        )

    @pytest.mark.asyncio
    async def test_grant_access_updates_existing_policy(self):
        """Test that an existing policy is updated to add HealthOmics access."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        # Existing policy without HealthOmics access
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'OtherAccess',
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                    'Action': ['ecr:GetDownloadUrlForLayer'],
                }
            ],
        }
        mock_client.get_repository_policy.side_effect = [
            {'policyText': json.dumps(existing_policy)},
            # Second call after policy is set
            {
                'policyText': json.dumps(
                    {
                        'Version': '2012-10-17',
                        'Statement': [
                            existing_policy['Statement'][0],
                            {
                                'Sid': 'HealthOmicsAccess',
                                'Effect': 'Allow',
                                'Principal': {'Service': 'omics.amazonaws.com'},
                                'Action': [
                                    'ecr:BatchGetImage',
                                    'ecr:GetDownloadUrlForLayer',
                                ],
                            },
                        ],
                    }
                )
            },
        ]
        mock_client.set_repository_policy.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        # Assert
        assert result['success'] is True
        assert result['policy_created'] is False
        assert result['policy_updated'] is True
        assert result['previous_healthomics_accessible'] == 'not_accessible'
        assert 'updated' in result['message'].lower()

        # Verify existing statements are preserved
        call_kwargs = mock_client.set_repository_policy.call_args[1]
        policy = json.loads(call_kwargs['policyText'])
        assert len(policy['Statement']) == 2
        # Check that original statement is preserved
        assert any(stmt.get('Sid') == 'OtherAccess' for stmt in policy['Statement'])

    @pytest.mark.asyncio
    async def test_grant_access_already_accessible(self):
        """Test that no changes are made when repository already has HealthOmics access."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        # Policy already grants HealthOmics access (default from _create_mock_ecr_client)

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        # Assert
        assert result['success'] is True
        assert result['policy_created'] is False
        assert result['policy_updated'] is False
        assert result['previous_healthomics_accessible'] == 'accessible'
        assert result['current_healthomics_accessible'] == 'accessible'
        assert 'already' in result['message'].lower()

        # Verify set_repository_policy was NOT called
        mock_client.set_repository_policy.assert_not_called()

    @pytest.mark.asyncio
    async def test_grant_access_repository_not_found(self):
        """Test error handling when repository does not exist."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository not found',
            }
        }
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRepositoryPolicy'
        )

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='nonexistent-repo',
            )

        # Assert
        assert result['success'] is False
        assert 'not found' in result['message'].lower()
        mock_ctx.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_grant_access_access_denied(self):
        """Test error handling when access is denied to set policy."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        # No existing policy
        policy_not_found = {
            'Error': {
                'Code': 'RepositoryPolicyNotFoundException',
                'Message': 'Repository policy does not exist',
            }
        }
        mock_client.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            policy_not_found, 'GetRepositoryPolicy'
        )
        # Access denied when trying to set policy
        access_denied = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.set_repository_policy.side_effect = botocore.exceptions.ClientError(
            access_denied, 'SetRepositoryPolicy'
        )

        mock_ctx = AsyncMock()

        # Act & Assert
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                await grant_healthomics_repository_access(
                    ctx=mock_ctx,
                    repository_name='my-repo',
                )

        mock_ctx.error.assert_called_once()
        assert 'SetRepositoryPolicy' in mock_ctx.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_grant_access_empty_repository_name(self):
        """Test validation error for empty repository name."""
        # Arrange
        mock_ctx = AsyncMock()

        # Act
        result = await grant_healthomics_repository_access(
            ctx=mock_ctx,
            repository_name='',
        )

        # Assert
        assert result['success'] is False
        assert 'required' in result['message'].lower() or 'empty' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_grant_access_replaces_existing_healthomics_statement(self):
        """Test that existing HealthOmics statements are replaced, not duplicated."""
        # Arrange
        mock_client = _create_mock_ecr_client()
        # Existing policy with partial HealthOmics access (missing one action)
        existing_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'OldHealthOmicsAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': ['ecr:BatchGetImage'],  # Missing GetDownloadUrlForLayer
                }
            ],
        }
        mock_client.get_repository_policy.side_effect = [
            {'policyText': json.dumps(existing_policy)},
            # Second call after policy is set
            {
                'policyText': json.dumps(
                    {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Sid': 'HealthOmicsAccess',
                                'Effect': 'Allow',
                                'Principal': {'Service': 'omics.amazonaws.com'},
                                'Action': [
                                    'ecr:BatchGetImage',
                                    'ecr:GetDownloadUrlForLayer',
                                ],
                            }
                        ],
                    }
                )
            },
        ]
        mock_client.set_repository_policy.return_value = {}

        mock_ctx = AsyncMock()

        # Act
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await grant_healthomics_repository_access(
                ctx=mock_ctx,
                repository_name='my-repo',
            )

        # Assert
        assert result['success'] is True
        assert result['policy_updated'] is True

        # Verify only one HealthOmics statement exists (old one replaced)
        call_kwargs = mock_client.set_repository_policy.call_args[1]
        policy = json.loads(call_kwargs['policyText'])
        healthomics_statements = [
            stmt
            for stmt in policy['Statement']
            if stmt.get('Principal', {}).get('Service') == 'omics.amazonaws.com'
        ]
        assert len(healthomics_statements) == 1
        # Verify it has both required actions
        assert 'ecr:BatchGetImage' in healthomics_statements[0]['Action']
        assert 'ecr:GetDownloadUrlForLayer' in healthomics_statements[0]['Action']
