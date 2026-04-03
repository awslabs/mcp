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

"""Tests for pull-through cache initiation functionality.

Feature: ecr-container-tools
Tests the ability to initiate pull-through cache when a container is not found
but the repository is a PullThroughCache accessible to HealthOmics.
"""

import botocore
import botocore.exceptions
import json
import pytest
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_ECR_PREFIXES
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
    _check_pull_through_cache_healthomics_usability,
    check_container_availability,
)
from awslabs.aws_healthomics_mcp_server.utils.ecr_utils import (
    get_pull_through_cache_rule_for_repository,
    initiate_pull_through_cache,
)
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Helper Functions
# =============================================================================


def _create_mock_ptc_rules_response(prefixes: list) -> dict:
    """Create a mock response for describe_pull_through_cache_rules with given prefixes."""
    return {
        'pullThroughCacheRules': [
            {'ecrRepositoryPrefix': prefix, 'upstreamRegistryUrl': f'https://{prefix}.io'}
            for prefix in prefixes
        ]
    }


def _create_healthomics_registry_policy() -> str:
    """Create a registry policy that grants HealthOmics access."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsPullThroughCacheAccess',
                    'Effect': 'Allow',
                    'Principal': {'Service': 'omics.amazonaws.com'},
                    'Action': [
                        'ecr:CreateRepository',
                        'ecr:BatchImportUpstreamImage',
                    ],
                    'Resource': '*',
                }
            ],
        }
    )


def _create_healthomics_repository_policy() -> str:
    """Create a repository policy that grants HealthOmics access."""
    return json.dumps(
        {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'HealthOmicsImagePullAccess',
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


def _create_mock_ecr_client_with_healthomics_access() -> MagicMock:
    """Create a mock ECR client configured for HealthOmics access."""
    mock_client = MagicMock()

    # Configure PTC rules
    mock_client.describe_pull_through_cache_rules.return_value = _create_mock_ptc_rules_response(
        list(DEFAULT_ECR_PREFIXES.values())
    )

    # Configure registry policy
    mock_client.get_registry_policy.return_value = {
        'policyText': _create_healthomics_registry_policy()
    }

    # Configure repository creation template
    mock_client.describe_repository_creation_templates.return_value = {
        'repositoryCreationTemplates': [
            {
                'prefix': 'docker-hub',
                'repositoryPolicy': _create_healthomics_repository_policy(),
            }
        ]
    }

    # Configure repository policy
    mock_client.get_repository_policy.return_value = {
        'policyText': _create_healthomics_repository_policy()
    }

    return mock_client


# =============================================================================
# Tests for get_pull_through_cache_rule_for_repository
# =============================================================================


class TestGetPullThroughCacheRuleForRepository:
    """Tests for the get_pull_through_cache_rule_for_repository utility function."""

    def test_finds_matching_rule(self):
        """Test that a matching rule is found for a repository name."""
        ptc_rules = [
            {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'registry-1.docker.io'},
            {'ecrRepositoryPrefix': 'quay', 'upstreamRegistryUrl': 'quay.io'},
        ]

        result = get_pull_through_cache_rule_for_repository('docker-hub/library/ubuntu', ptc_rules)

        assert result is not None
        assert result['ecrRepositoryPrefix'] == 'docker-hub'

    def test_returns_none_for_no_match(self):
        """Test that None is returned when no rule matches."""
        ptc_rules = [
            {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'registry-1.docker.io'},
        ]

        result = get_pull_through_cache_rule_for_repository('my-custom-repo', ptc_rules)

        assert result is None

    def test_returns_none_for_empty_rules(self):
        """Test that None is returned when rules list is empty."""
        result = get_pull_through_cache_rule_for_repository('docker-hub/library/ubuntu', [])

        assert result is None

    def test_prefix_must_be_followed_by_slash(self):
        """Test that prefix must be followed by a slash to match."""
        ptc_rules = [
            {'ecrRepositoryPrefix': 'docker-hub', 'upstreamRegistryUrl': 'registry-1.docker.io'},
        ]

        # Should not match - no slash after prefix
        result = get_pull_through_cache_rule_for_repository('docker-hub-extra', ptc_rules)
        assert result is None

        # Should match - has slash after prefix
        result = get_pull_through_cache_rule_for_repository('docker-hub/image', ptc_rules)
        assert result is not None


# =============================================================================
# Tests for initiate_pull_through_cache
# =============================================================================


class TestInitiatePullThroughCache:
    """Tests for the initiate_pull_through_cache utility function."""

    def test_successful_pull_through(self):
        """Test successful pull-through cache initiation."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                        'imageTag': 'latest',
                    },
                    'imageManifest': '{}',
                }
            ],
            'failures': [],
        }

        success, message, image_details = initiate_pull_through_cache(
            mock_client,
            'docker-hub/library/ubuntu',
            image_tag='latest',
        )

        assert success is True
        assert 'successfully' in message.lower()
        assert image_details is not None
        assert image_details['imageDigest'] == 'sha256:abc123'
        assert image_details['imageTag'] == 'latest'

    def test_image_not_found_in_upstream(self):
        """Test when image is not found in upstream registry."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [
                {
                    'imageId': {'imageTag': 'nonexistent'},
                    'failureCode': 'ImageNotFound',
                    'failureReason': 'Image not found in upstream registry',
                }
            ],
        }

        success, message, image_details = initiate_pull_through_cache(
            mock_client,
            'docker-hub/library/nonexistent',
            image_tag='nonexistent',
        )

        assert success is False
        assert 'not found' in message.lower()
        assert image_details is None

    def test_repository_not_found_exception(self):
        """Test when repository does not exist."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository not found',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, image_details = initiate_pull_through_cache(
            mock_client,
            'docker-hub/library/ubuntu',
            image_tag='latest',
        )

        assert success is False
        assert 'repository' in message.lower()
        assert image_details is None

    def test_access_denied_exception(self):
        """Test when access is denied."""
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied',
            }
        }
        mock_client.batch_get_image.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetImage'
        )

        success, message, image_details = initiate_pull_through_cache(
            mock_client,
            'docker-hub/library/ubuntu',
            image_tag='latest',
        )

        assert success is False
        assert 'access denied' in message.lower()
        assert image_details is None

    def test_with_image_digest(self):
        """Test pull-through with image digest instead of tag."""
        mock_client = MagicMock()
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                    },
                    'imageManifest': '{}',
                }
            ],
            'failures': [],
        }

        success, message, image_details = initiate_pull_through_cache(
            mock_client,
            'docker-hub/library/ubuntu',
            image_digest='sha256:abc123',
        )

        assert success is True
        assert image_details is not None
        assert image_details['imageDigest'] == 'sha256:abc123'

        # Verify batch_get_image was called with digest
        call_args = mock_client.batch_get_image.call_args
        assert call_args[1]['imageIds'][0] == {'imageDigest': 'sha256:abc123'}


# =============================================================================
# Tests for _check_pull_through_cache_healthomics_usability
# =============================================================================


class TestCheckPullThroughCacheHealthOmicsUsability:
    """Tests for the _check_pull_through_cache_healthomics_usability helper function."""

    def test_usable_when_fully_configured(self):
        """Test that PTC is usable when fully configured for HealthOmics."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is True
        assert result['ptc_rule'] is not None

    def test_not_usable_when_no_registry_policy(self):
        """Test that PTC is not usable when registry policy is missing."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # Remove registry policy
        error_response = {
            'Error': {
                'Code': 'RegistryPolicyNotFoundException',
                'Message': 'Registry policy not found',
            }
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            error_response, 'GetRegistryPolicy'
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is False

    def test_not_usable_when_no_template(self):
        """Test that PTC is not usable when repository template is missing."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # Remove template
        error_response = {
            'Error': {
                'Code': 'TemplateNotFoundException',
                'Message': 'Template not found',
            }
        }
        mock_client.describe_repository_creation_templates.side_effect = (
            botocore.exceptions.ClientError(error_response, 'DescribeRepositoryCreationTemplates')
        )

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('docker-hub/library/ubuntu')

        assert result['is_ptc'] is True
        assert result['healthomics_usable'] is False

    def test_not_ptc_for_regular_repository(self):
        """Test that regular repositories are not identified as PTC."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = _check_pull_through_cache_healthomics_usability('my-custom-repo')

        assert result['is_ptc'] is False
        assert result['healthomics_usable'] is False


# =============================================================================
# Tests for check_container_availability with initiate_pull_through
# =============================================================================


class TestCheckContainerAvailabilityWithPullThroughInitiation:
    """Tests for check_container_availability with initiate_pull_through parameter."""

    @pytest.fixture
    def tool_wrapper(self):
        """Create a wrapper for the check_container_availability tool."""
        return MCPToolTestWrapper(check_container_availability)

    @pytest.mark.asyncio
    async def test_initiates_pull_through_on_image_not_found(self, tool_wrapper):
        """Test that pull-through is initiated when image is not found."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # First call to describe_images raises ImageNotFoundException
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # batch_get_image succeeds (pull-through works)
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                        'imageTag': 'latest',
                    },
                    'imageManifest': '{}',
                }
            ],
            'failures': [],
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                initiate_pull_through=True,
            )

        assert result['available'] is True
        assert result['pull_through_initiated'] is True
        assert result['image'] is not None
        assert result['image']['image_digest'] == 'sha256:abc123'

    @pytest.mark.asyncio
    async def test_initiates_pull_through_on_repository_not_found(self, tool_wrapper):
        """Test that pull-through is initiated when repository is not found."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # First call to describe_images raises RepositoryNotFoundException
        error_response = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': 'Repository not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # batch_get_image succeeds (pull-through creates repo and pulls image)
        mock_client.batch_get_image.return_value = {
            'images': [
                {
                    'imageId': {
                        'imageDigest': 'sha256:abc123',
                        'imageTag': 'latest',
                    },
                    'imageManifest': '{}',
                }
            ],
            'failures': [],
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                initiate_pull_through=True,
            )

        assert result['available'] is True
        assert result['pull_through_initiated'] is True

    @pytest.mark.asyncio
    async def test_no_pull_through_when_flag_is_false(self, tool_wrapper):
        """Test that pull-through is not initiated when flag is False."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images raises ImageNotFoundException
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

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                initiate_pull_through=False,
            )

        assert result['available'] is False
        assert result['pull_through_initiated'] is False
        # batch_get_image should not have been called
        mock_client.batch_get_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_pull_through_for_non_ptc_repository(self, tool_wrapper):
        """Test that pull-through is not initiated for non-PTC repositories."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images raises ImageNotFoundException
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

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='my-custom-repo',
                image_tag='latest',
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['is_pull_through_cache'] is False
        # batch_get_image should not have been called for non-PTC repo
        mock_client.batch_get_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_pull_through_when_healthomics_not_usable(self, tool_wrapper):
        """Test that pull-through is not initiated when HealthOmics cannot use PTC."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images raises ImageNotFoundException
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # Remove registry policy (makes PTC not usable by HealthOmics)
        registry_error = {
            'Error': {
                'Code': 'RegistryPolicyNotFoundException',
                'Message': 'Registry policy not found',
            }
        }
        mock_client.get_registry_policy.side_effect = botocore.exceptions.ClientError(
            registry_error, 'GetRegistryPolicy'
        )

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['pull_through_initiated'] is False
        assert 'not usable by HealthOmics' in result['pull_through_initiation_message']

    @pytest.mark.asyncio
    async def test_pull_through_failure_returns_not_available(self, tool_wrapper):
        """Test that failed pull-through returns not available."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images raises ImageNotFoundException
        error_response = {
            'Error': {
                'Code': 'ImageNotFoundException',
                'Message': 'Image not found',
            }
        }
        mock_client.describe_images.side_effect = botocore.exceptions.ClientError(
            error_response, 'DescribeImages'
        )

        # batch_get_image fails (image not in upstream)
        mock_client.batch_get_image.return_value = {
            'images': [],
            'failures': [
                {
                    'imageId': {'imageTag': 'nonexistent'},
                    'failureCode': 'ImageNotFound',
                    'failureReason': 'Image not found in upstream registry',
                }
            ],
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/nonexistent',
                image_tag='nonexistent',
                initiate_pull_through=True,
            )

        assert result['available'] is False
        assert result['pull_through_initiated'] is False
        assert 'not found' in result['pull_through_initiation_message'].lower()

    @pytest.mark.asyncio
    async def test_image_already_available_no_pull_through_needed(self, tool_wrapper):
        """Test that pull-through is not attempted when image is already available."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images succeeds (image exists)
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:existing123',
                    'imageSizeInBytes': 1024,
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
                initiate_pull_through=True,
            )

        assert result['available'] is True
        assert result['pull_through_initiated'] is False
        # batch_get_image should not have been called
        mock_client.batch_get_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_response_includes_pull_through_fields(self, tool_wrapper):
        """Test that response always includes pull_through fields."""
        mock_client = _create_mock_ecr_client_with_healthomics_access()

        # describe_images succeeds
        mock_client.describe_images.return_value = {
            'imageDetails': [
                {
                    'imageDigest': 'sha256:existing123',
                    'imageSizeInBytes': 1024,
                    'imageTags': ['latest'],
                }
            ]
        }

        mock_ctx = AsyncMock()

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
            return_value=mock_client,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                repository_name='docker-hub/library/ubuntu',
                image_tag='latest',
            )

        # These fields should always be present in the response
        assert 'pull_through_initiated' in result
        assert 'pull_through_initiation_message' in result
