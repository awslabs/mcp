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

"""Tests for clone_container_to_ecr and related functions.

Feature: ecr-container-clone
"""

import botocore
import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
    CODEBUILD_PROJECT_NAME,
    PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES,
    _find_matching_pull_through_cache,
    _get_or_create_codebuild_project,
    _parse_container_image_reference,
    clone_container_to_ecr,
)
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Tests for _parse_container_image_reference
# =============================================================================


class TestParseContainerImageReference:
    """Tests for the _parse_container_image_reference helper function."""

    def test_simple_image_name_becomes_library_image(self):
        """Test that 'ubuntu' becomes 'registry-1.docker.io/library/ubuntu:latest'."""
        result = _parse_container_image_reference('ubuntu')
        assert result['registry'] == 'registry-1.docker.io'
        assert result['repository'] == 'library/ubuntu'
        assert result['tag'] == 'latest'
        assert result['digest'] is None

    def test_simple_image_with_tag(self):
        """Test that 'ubuntu:22.04' parses correctly."""
        result = _parse_container_image_reference('ubuntu:22.04')
        assert result['registry'] == 'registry-1.docker.io'
        assert result['repository'] == 'library/ubuntu'
        assert result['tag'] == '22.04'
        assert result['digest'] is None

    def test_org_image_becomes_docker_hub(self):
        """Test that 'myorg/myimage:v1' becomes Docker Hub image."""
        result = _parse_container_image_reference('myorg/myimage:v1')
        assert result['registry'] == 'registry-1.docker.io'
        assert result['repository'] == 'myorg/myimage'
        assert result['tag'] == 'v1'
        assert result['digest'] is None

    def test_quay_io_image(self):
        """Test that 'quay.io/biocontainers/samtools:1.17' parses correctly."""
        result = _parse_container_image_reference('quay.io/biocontainers/samtools:1.17')
        assert result['registry'] == 'quay.io'
        assert result['repository'] == 'biocontainers/samtools'
        assert result['tag'] == '1.17'
        assert result['digest'] is None

    def test_ecr_public_image(self):
        """Test that 'public.ecr.aws/lts/ubuntu:22.04' parses correctly."""
        result = _parse_container_image_reference('public.ecr.aws/lts/ubuntu:22.04')
        assert result['registry'] == 'public.ecr.aws'
        assert result['repository'] == 'lts/ubuntu'
        assert result['tag'] == '22.04'
        assert result['digest'] is None

    def test_ghcr_io_image(self):
        """Test that 'ghcr.io/owner/repo:tag' parses correctly."""
        result = _parse_container_image_reference('ghcr.io/owner/repo:tag')
        assert result['registry'] == 'ghcr.io'
        assert result['repository'] == 'owner/repo'
        assert result['tag'] == 'tag'

    def test_image_with_digest(self):
        """Test that image with digest parses correctly."""
        digest = 'sha256:abc123def456'
        result = _parse_container_image_reference(f'ubuntu@{digest}')
        assert result['registry'] == 'registry-1.docker.io'
        assert result['repository'] == 'library/ubuntu'
        assert result['tag'] is None
        assert result['digest'] == digest

    def test_docker_io_normalized_to_registry_1(self):
        """Test that docker.io is normalized to registry-1.docker.io."""
        result = _parse_container_image_reference('docker.io/library/ubuntu:latest')
        assert result['registry'] == 'registry-1.docker.io'
        assert result['repository'] == 'library/ubuntu'
        assert result['tag'] == 'latest'

    def test_full_reference_constructed_correctly_with_tag(self):
        """Test that full_reference is constructed correctly with tag."""
        result = _parse_container_image_reference('ubuntu:22.04')
        assert result['full_reference'] == 'registry-1.docker.io/library/ubuntu:22.04'

    def test_full_reference_constructed_correctly_with_digest(self):
        """Test that full_reference is constructed correctly with digest."""
        digest = 'sha256:abc123'
        result = _parse_container_image_reference(f'ubuntu@{digest}')
        assert result['full_reference'] == f'registry-1.docker.io/library/ubuntu@{digest}'

    def test_wave_seqera_io_image(self):
        """Test that wave.seqera.io images parse correctly."""
        result = _parse_container_image_reference('wave.seqera.io/wt/abc123:latest')
        assert result['registry'] == 'wave.seqera.io'
        assert result['repository'] == 'wt/abc123'
        assert result['tag'] == 'latest'

    def test_nested_repository_path(self):
        """Test parsing image with nested repository path."""
        result = _parse_container_image_reference('quay.io/org/sub/image:v1')
        assert result['registry'] == 'quay.io'
        assert result['repository'] == 'org/sub/image'
        assert result['tag'] == 'v1'


# =============================================================================
# Tests for _find_matching_pull_through_cache
# =============================================================================


class TestFindMatchingPullThroughCache:
    """Tests for the _find_matching_pull_through_cache helper function."""

    def test_exact_match(self):
        """Test finding exact registry match."""
        rules = [
            {'upstreamRegistryUrl': 'quay.io', 'ecrRepositoryPrefix': 'quay'},
        ]
        result = _find_matching_pull_through_cache('quay.io', rules)
        assert result is not None
        assert result['ecrRepositoryPrefix'] == 'quay'

    def test_docker_io_matches_registry_1(self):
        """Test that docker.io matches registry-1.docker.io."""
        rules = [
            {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'},
        ]
        result = _find_matching_pull_through_cache('docker.io', rules)
        assert result is not None
        assert result['ecrRepositoryPrefix'] == 'docker'

    def test_registry_1_matches_docker_io(self):
        """Test that registry-1.docker.io matches docker.io rule."""
        rules = [
            {'upstreamRegistryUrl': 'docker.io', 'ecrRepositoryPrefix': 'docker'},
        ]
        result = _find_matching_pull_through_cache('registry-1.docker.io', rules)
        assert result is not None
        assert result['ecrRepositoryPrefix'] == 'docker'

    def test_no_match_returns_none(self):
        """Test that no match returns None."""
        rules = [
            {'upstreamRegistryUrl': 'quay.io', 'ecrRepositoryPrefix': 'quay'},
        ]
        result = _find_matching_pull_through_cache('ghcr.io', rules)
        assert result is None

    def test_empty_rules_returns_none(self):
        """Test that empty rules list returns None."""
        result = _find_matching_pull_through_cache('quay.io', [])
        assert result is None

    def test_multiple_rules_finds_correct_one(self):
        """Test finding correct rule among multiple."""
        rules = [
            {'upstreamRegistryUrl': 'quay.io', 'ecrRepositoryPrefix': 'quay'},
            {'upstreamRegistryUrl': 'ghcr.io', 'ecrRepositoryPrefix': 'ghcr'},
            {'upstreamRegistryUrl': 'public.ecr.aws', 'ecrRepositoryPrefix': 'ecr-public'},
        ]
        result = _find_matching_pull_through_cache('ghcr.io', rules)
        assert result is not None
        assert result['ecrRepositoryPrefix'] == 'ghcr'


# =============================================================================
# Tests for _get_or_create_codebuild_project
# =============================================================================


class TestGetOrCreateCodeBuildProject:
    """Tests for the _get_or_create_codebuild_project helper function."""

    def test_project_exists_returns_name(self):
        """Test that existing project returns project name without creating."""
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_iam = MagicMock()

        result = _get_or_create_codebuild_project(
            mock_codebuild, mock_iam, '123456789012', 'us-east-1'
        )

        assert result == CODEBUILD_PROJECT_NAME
        mock_codebuild.create_project.assert_not_called()
        mock_iam.create_role.assert_not_called()

    def test_project_not_exists_creates_role_and_project(self):
        """Test that missing project creates IAM role and CodeBuild project."""
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {'projects': []}
        mock_codebuild.create_project.return_value = {}

        mock_iam = MagicMock()
        mock_iam.exceptions.NoSuchEntityException = Exception
        mock_iam.get_role.side_effect = mock_iam.exceptions.NoSuchEntityException()
        mock_iam.create_role.return_value = {}
        mock_iam.put_role_policy.return_value = {}

        with patch('time.sleep'):
            result = _get_or_create_codebuild_project(
                mock_codebuild, mock_iam, '123456789012', 'us-east-1'
            )

        assert result == CODEBUILD_PROJECT_NAME
        mock_iam.create_role.assert_called_once()
        mock_iam.put_role_policy.assert_called_once()
        mock_codebuild.create_project.assert_called_once()

    def test_role_exists_skips_role_creation(self):
        """Test that existing IAM role skips role creation."""
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {'projects': []}
        mock_codebuild.create_project.return_value = {}

        mock_iam = MagicMock()
        mock_iam.get_role.return_value = {'Role': {'Arn': 'arn:aws:iam::123:role/test'}}

        result = _get_or_create_codebuild_project(
            mock_codebuild, mock_iam, '123456789012', 'us-east-1'
        )

        assert result == CODEBUILD_PROJECT_NAME
        mock_iam.create_role.assert_not_called()
        mock_codebuild.create_project.assert_called_once()

    def test_client_error_not_resource_not_found_raises(self):
        """Test that non-ResourceNotFoundException errors are raised."""
        mock_codebuild = MagicMock()
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_codebuild.batch_get_projects.side_effect = botocore.exceptions.ClientError(
            error_response, 'BatchGetProjects'
        )
        mock_iam = MagicMock()

        with pytest.raises(botocore.exceptions.ClientError):
            _get_or_create_codebuild_project(mock_codebuild, mock_iam, '123456789012', 'us-east-1')


# =============================================================================
# Tests for _copy_image_via_codebuild
# =============================================================================


class TestCopyImageViaCodeBuild:
    """Tests for the _copy_image_via_codebuild async function."""

    @pytest.mark.asyncio
    async def test_successful_build_returns_digest(self):
        """Test successful CodeBuild returns image digest."""
        mock_ctx = AsyncMock()
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        mock_codebuild.batch_get_builds.return_value = {'builds': [{'buildStatus': 'SUCCEEDED'}]}

        mock_ecr = MagicMock()
        mock_ecr.describe_images.return_value = {
            'imageDetails': [{'imageDigest': 'sha256:abc123'}]
        }

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
                _copy_image_via_codebuild,
            )

            result = await _copy_image_via_codebuild(
                ctx=mock_ctx,
                source_image='ubuntu:latest',
                target_repo='my-repo',
                target_tag='latest',
                account_id='123456789012',
                region='us-east-1',
            )

        assert result['success'] is True
        assert result['digest'] == 'sha256:abc123'

    @pytest.mark.asyncio
    async def test_build_failed_returns_error(self):
        """Test failed CodeBuild returns error message."""
        mock_ctx = AsyncMock()
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        mock_codebuild.batch_get_builds.return_value = {
            'builds': [
                {
                    'buildStatus': 'FAILED',
                    'phases': [
                        {'phaseStatus': 'FAILED', 'contexts': [{'message': 'Docker pull failed'}]}
                    ],
                }
            ]
        }

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
                _copy_image_via_codebuild,
            )

            result = await _copy_image_via_codebuild(
                ctx=mock_ctx,
                source_image='ubuntu:latest',
                target_repo='my-repo',
                target_tag='latest',
                account_id='123456789012',
                region='us-east-1',
            )

        assert result['success'] is False
        assert 'FAILED' in result['message']
        assert 'Docker pull failed' in result['message']


# =============================================================================
# Tests for clone_container_to_ecr
# =============================================================================


class TestCloneContainerToECR:
    """Tests for the clone_container_to_ecr MCP tool."""

    @pytest.mark.asyncio
    async def test_empty_source_image_returns_error(self):
        """Test that empty source image returns error."""
        mock_ctx = AsyncMock()
        wrapper = MCPToolTestWrapper(clone_container_to_ecr)

        result = await wrapper.call(ctx=mock_ctx, source_image='')

        assert result['success'] is False
        assert 'required' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_whitespace_source_image_returns_error(self):
        """Test that whitespace-only source image returns error."""
        mock_ctx = AsyncMock()
        wrapper = MCPToolTestWrapper(clone_container_to_ecr)

        result = await wrapper.call(ctx=mock_ctx, source_image='   ')

        assert result['success'] is False
        assert 'required' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_failed_account_id_returns_error(self):
        """Test that failure to get account ID returns error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                side_effect=Exception('STS error'),
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        assert result['success'] is False
        assert 'account' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_pull_through_cache_success(self):
        """Test successful clone via pull-through cache."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'}
            ]
        }
        mock_ecr.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc123', 'imageTag': 'latest'}}]
        }
        mock_ecr.get_repository_policy.return_value = {'policyText': '{"Statement": []}'}
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        assert result['success'] is True
        assert result['used_pull_through_cache'] is True
        assert result['ecr_digest'] == 'sha256:abc123'
        assert 'docker/library/ubuntu' in result['ecr_uri']

    @pytest.mark.asyncio
    async def test_pull_through_cache_failure(self):
        """Test pull-through cache failure returns error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'}
            ]
        }
        mock_ecr.batch_get_image.return_value = {
            'images': [],
            'failures': [{'failureCode': 'ImageNotFound', 'failureReason': 'Image not found'}],
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        assert result['success'] is False
        assert 'ImageNotFound' in result['message']

    @pytest.mark.asyncio
    async def test_pull_through_cache_no_images(self):
        """Test pull-through cache returns no images."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'}
            ]
        }
        mock_ecr.batch_get_image.return_value = {'images': [], 'failures': []}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        assert result['success'] is False
        assert 'no images' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_no_ptc_supported_registry_suggests_creating(self):
        """Test no PTC for supported registry suggests creating one."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryNotFoundException'}}, 'DescribeRepositories'
        )
        mock_ecr.create_repository.return_value = {}
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        assert result['success'] is False
        assert result['repository_created'] is True
        assert 'CreatePullThroughCacheForHealthOmics' in result['message']

    @pytest.mark.asyncio
    async def test_no_ptc_unsupported_registry_uses_codebuild(self):
        """Test no PTC for unsupported registry uses CodeBuild."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryNotFoundException'}}, 'DescribeRepositories'
        )
        mock_ecr.create_repository.return_value = {}
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}
        mock_ecr.describe_images.return_value = {
            'imageDetails': [{'imageDigest': 'sha256:abc123'}]
        }

        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        mock_codebuild.batch_get_builds.return_value = {'builds': [{'buildStatus': 'SUCCEEDED'}]}

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert result['success'] is True
        assert result['used_codebuild'] is True
        assert result['used_pull_through_cache'] is False

    @pytest.mark.asyncio
    async def test_codebuild_failure_returns_manual_instructions(self):
        """Test CodeBuild failure returns manual push instructions."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.return_value = {'repositories': [{}]}
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}

        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        mock_codebuild.batch_get_builds.return_value = {
            'builds': [{'buildStatus': 'FAILED', 'phases': []}]
        }

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert result['success'] is False
        assert result['used_codebuild'] is False
        assert 'docker pull' in result['message']
        assert 'docker push' in result['message']

    @pytest.mark.asyncio
    async def test_access_denied_error(self):
        """Test AccessDeniedException returns proper error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'DescribeRepositories',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert result['success'] is False
        assert 'Access denied' in result['message']

    @pytest.mark.asyncio
    async def test_other_client_error(self):
        """Test other ClientError returns proper error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DescribeRepositories',
        )

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert result['success'] is False
        assert 'Rate exceeded' in result['message']

    @pytest.mark.asyncio
    async def test_botocore_error(self):
        """Test BotoCoreError returns proper error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.BotoCoreError()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert 'error' in result
        assert 'Error' in result['error']

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        """Test unexpected error returns proper error."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = RuntimeError('Unexpected')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx, source_image='wave.seqera.io/wt/abc123:latest'
            )

        assert 'error' in result
        assert 'Error' in result['error']

    @pytest.mark.asyncio
    async def test_pull_through_cache_with_digest(self):
        """Test pull-through cache with digest instead of tag."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'}
            ]
        }
        mock_ecr.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc123'}}]
        }
        mock_ecr.get_repository_policy.return_value = {'policyText': '{"Statement": []}'}
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu@sha256:originaldigest')

        assert result['success'] is True
        call_args = mock_ecr.batch_get_image.call_args
        assert 'imageDigest' in str(call_args)

    @pytest.mark.asyncio
    async def test_custom_target_repository_name(self):
        """Test custom target repository name is used."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryNotFoundException'}}, 'DescribeRepositories'
        )
        mock_ecr.create_repository.return_value = {}
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(
                ctx=mock_ctx,
                source_image='ubuntu:latest',
                target_repository_name='my-custom-repo',
            )

        assert 'my-custom-repo' in result['ecr_uri']


# =============================================================================
# Tests for PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES constant
# =============================================================================


class TestPullThroughCacheSupportedRegistries:
    """Tests for the PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES constant."""

    def test_docker_hub_supported(self):
        """Test Docker Hub registries are supported."""
        assert 'registry-1.docker.io' in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES
        assert 'docker.io' in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES

    def test_quay_supported(self):
        """Test Quay.io is supported."""
        assert 'quay.io' in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES

    def test_ecr_public_supported(self):
        """Test ECR Public is supported."""
        assert 'public.ecr.aws' in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES

    def test_ghcr_supported(self):
        """Test GitHub Container Registry is supported."""
        assert 'ghcr.io' in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES

    def test_wave_seqera_not_supported(self):
        """Test wave.seqera.io is NOT supported."""
        assert 'wave.seqera.io' not in PULL_THROUGH_CACHE_SUPPORTED_REGISTRIES


# =============================================================================
# Additional tests for edge cases and error paths
# =============================================================================


class TestCodeBuildEdgeCases:
    """Additional tests for CodeBuild edge cases."""

    @pytest.mark.asyncio
    async def test_build_with_empty_builds_response(self):
        """Test handling when batch_get_builds returns empty builds."""
        mock_ctx = AsyncMock()
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        # First call returns empty, then SUCCEEDED
        mock_codebuild.batch_get_builds.side_effect = [
            {'builds': []},
            {'builds': [{'buildStatus': 'SUCCEEDED'}]},
        ]

        mock_ecr = MagicMock()
        mock_ecr.describe_images.return_value = {
            'imageDetails': [{'imageDigest': 'sha256:abc123'}]
        }

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
                _copy_image_via_codebuild,
            )

            result = await _copy_image_via_codebuild(
                ctx=mock_ctx,
                source_image='ubuntu:latest',
                target_repo='my-repo',
                target_tag='latest',
                account_id='123456789012',
                region='us-east-1',
            )

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_build_with_stopped_status(self):
        """Test handling STOPPED build status."""
        mock_ctx = AsyncMock()
        mock_codebuild = MagicMock()
        mock_codebuild.batch_get_projects.return_value = {
            'projects': [{'name': CODEBUILD_PROJECT_NAME}]
        }
        mock_codebuild.start_build.return_value = {'build': {'id': 'build-123'}}
        mock_codebuild.batch_get_builds.return_value = {
            'builds': [{'buildStatus': 'STOPPED', 'phases': []}]
        }

        mock_iam = MagicMock()

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_codebuild_client',
                return_value=mock_codebuild,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_iam_client',
                return_value=mock_iam,
            ),
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import (
                _copy_image_via_codebuild,
            )

            result = await _copy_image_via_codebuild(
                ctx=mock_ctx,
                source_image='ubuntu:latest',
                target_repo='my-repo',
                target_tag='latest',
                account_id='123456789012',
                region='us-east-1',
            )

        assert result['success'] is False
        assert 'STOPPED' in result['message']


class TestCloneContainerEdgeCases:
    """Additional edge case tests for clone_container_to_ecr."""

    @pytest.mark.asyncio
    async def test_ptc_rules_check_exception_continues(self):
        """Test that exception checking PTC rules doesn't stop execution."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.side_effect = Exception('PTC check failed')
        mock_ecr.describe_repositories.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryNotFoundException'}}, 'DescribeRepositories'
        )
        mock_ecr.create_repository.return_value = {}
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        # Should continue even if PTC check fails
        assert result['repository_created'] is True

    @pytest.mark.asyncio
    async def test_grant_access_exception_continues(self):
        """Test that exception granting access doesn't stop execution."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {
            'pullThroughCacheRules': [
                {'upstreamRegistryUrl': 'registry-1.docker.io', 'ecrRepositoryPrefix': 'docker'}
            ]
        }
        mock_ecr.batch_get_image.return_value = {
            'images': [{'imageId': {'imageDigest': 'sha256:abc123', 'imageTag': 'latest'}}]
        }
        mock_ecr.get_repository_policy.side_effect = Exception('Policy check failed')

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        # Should succeed even if grant access fails
        assert result['success'] is True
        assert result['used_pull_through_cache'] is True

    @pytest.mark.asyncio
    async def test_repository_already_exists(self):
        """Test handling when repository already exists."""
        mock_ctx = AsyncMock()
        mock_ecr = MagicMock()
        mock_ecr.describe_pull_through_cache_rules.return_value = {'pullThroughCacheRules': []}
        mock_ecr.describe_repositories.return_value = {
            'repositories': [{'repositoryName': 'library-ubuntu'}]
        }
        mock_ecr.get_repository_policy.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'RepositoryPolicyNotFoundException'}}, 'GetRepositoryPolicy'
        )
        mock_ecr.set_repository_policy.return_value = {}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.get_ecr_client',
                return_value=mock_ecr,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            wrapper = MCPToolTestWrapper(clone_container_to_ecr)
            result = await wrapper.call(ctx=mock_ctx, source_image='ubuntu:latest')

        # Repository should not be created since it exists
        assert result['repository_created'] is False
