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

"""Tests for create_container_registry_map tool."""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.tools.ecr_tools import create_container_registry_map
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, patch


class TestCreateContainerRegistryMap:
    """Tests for the create_container_registry_map function."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MCP context."""
        return AsyncMock()

    @pytest.fixture
    def tool_wrapper(self):
        """Create a test wrapper for the tool."""
        return MCPToolTestWrapper(create_container_registry_map)

    @pytest.fixture
    def mock_ptc_rules_response(self):
        """Create a mock response for list_pull_through_cache_rules with usable caches."""
        return {
            'rules': [
                {
                    'ecr_repository_prefix': 'docker-hub',
                    'upstream_registry_url': 'registry-1.docker.io',
                    'healthomics_usable': True,
                    'registry_permission_granted': True,
                    'repository_template_exists': True,
                    'repository_template_permission_granted': True,
                },
                {
                    'ecr_repository_prefix': 'quay',
                    'upstream_registry_url': 'quay.io',
                    'healthomics_usable': True,
                    'registry_permission_granted': True,
                    'repository_template_exists': True,
                    'repository_template_permission_granted': True,
                },
                {
                    'ecr_repository_prefix': 'ecr-public',
                    'upstream_registry_url': 'public.ecr.aws',
                    'healthomics_usable': False,  # Not usable
                    'registry_permission_granted': False,
                    'repository_template_exists': False,
                    'repository_template_permission_granted': False,
                },
            ],
            'next_token': None,
        }

    @pytest.mark.asyncio
    async def test_basic_registry_map_creation(
        self, mock_ctx, tool_wrapper, mock_ptc_rules_response
    ):
        """Test basic container registry map creation with discovered caches."""
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=mock_ptc_rules_response,
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
            result = await tool_wrapper.call(ctx=mock_ctx)

        assert result['success'] is True
        assert result['account_id'] == '123456789012'
        assert result['region'] == 'us-east-1'
        assert result['discovered_healthomics_usable_caches'] == 2

        container_map = result['container_registry_map']
        assert 'registryMappings' in container_map
        assert len(container_map['registryMappings']) == 2

        # Verify the mappings are correct
        mappings = {
            m['upstreamRegistryUrl']: m['ecrRepositoryPrefix']
            for m in container_map['registryMappings']
        }
        assert mappings['registry-1.docker.io'] == 'docker-hub'
        assert mappings['quay.io'] == 'quay'
        # ecr-public should NOT be included (not healthomics_usable)
        assert 'public.ecr.aws' not in mappings

    @pytest.mark.asyncio
    async def test_explicit_account_and_region(
        self, mock_ctx, tool_wrapper, mock_ptc_rules_response
    ):
        """Test with explicitly provided account ID and region."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
            new_callable=AsyncMock,
            return_value=mock_ptc_rules_response,
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                ecr_account_id='987654321098',
                ecr_region='eu-west-1',
            )

        assert result['success'] is True
        assert result['account_id'] == '987654321098'
        assert result['region'] == 'eu-west-1'

    @pytest.mark.asyncio
    async def test_skip_pull_through_cache_discovery(self, mock_ctx, tool_wrapper):
        """Test with pull-through cache discovery disabled."""
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                include_pull_through_caches=False,
            )

        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0
        assert result['container_registry_map'] == {}

    @pytest.mark.asyncio
    async def test_additional_registry_mappings(
        self, mock_ctx, tool_wrapper, mock_ptc_rules_response
    ):
        """Test adding additional registry mappings."""
        additional_mappings = [
            {
                'upstreamRegistryUrl': 'ghcr.io',
                'ecrRepositoryPrefix': 'github',
            },
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=mock_ptc_rules_response,
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
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                additional_registry_mappings=additional_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']
        assert len(container_map['registryMappings']) == 3

        mappings = {
            m['upstreamRegistryUrl']: m['ecrRepositoryPrefix']
            for m in container_map['registryMappings']
        }
        assert mappings['ghcr.io'] == 'github'

    @pytest.mark.asyncio
    async def test_additional_mapping_overrides_discovered(
        self, mock_ctx, tool_wrapper, mock_ptc_rules_response
    ):
        """Test that additional mappings override discovered ones."""
        additional_mappings = [
            {
                'upstreamRegistryUrl': 'registry-1.docker.io',
                'ecrRepositoryPrefix': 'my-custom-docker-hub',
            },
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=mock_ptc_rules_response,
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
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                additional_registry_mappings=additional_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']

        mappings = {
            m['upstreamRegistryUrl']: m['ecrRepositoryPrefix']
            for m in container_map['registryMappings']
        }
        # Should use the user-provided prefix, not the discovered one
        assert mappings['registry-1.docker.io'] == 'my-custom-docker-hub'

    @pytest.mark.asyncio
    async def test_image_mappings(self, mock_ctx, tool_wrapper):
        """Test with image mappings."""
        image_mappings = [
            {
                'sourceImage': 'broadinstitute/gatk:4.6.0.2',
                'destinationImage': '123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/broadinstitute/gatk:latest',
            },
            {
                'sourceImage': 'ubuntu:20.04',
                'destinationImage': '123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/ubuntu:20.04',
            },
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                include_pull_through_caches=False,
                image_mappings=image_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']
        assert 'imageMappings' in container_map
        assert len(container_map['imageMappings']) == 2
        assert container_map['imageMappings'][0]['sourceImage'] == 'broadinstitute/gatk:4.6.0.2'

    @pytest.mark.asyncio
    async def test_combined_registry_and_image_mappings(
        self, mock_ctx, tool_wrapper, mock_ptc_rules_response
    ):
        """Test with both registry and image mappings."""
        image_mappings = [
            {
                'sourceImage': 'ubuntu',
                'destinationImage': '123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/ubuntu:20.04',
            },
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=mock_ptc_rules_response,
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
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                image_mappings=image_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']
        assert 'registryMappings' in container_map
        assert 'imageMappings' in container_map
        assert len(container_map['registryMappings']) == 2
        assert len(container_map['imageMappings']) == 1

    @pytest.mark.asyncio
    async def test_json_output_format(self, mock_ctx, tool_wrapper, mock_ptc_rules_response):
        """Test that JSON output is valid and properly formatted."""
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=mock_ptc_rules_response,
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
            result = await tool_wrapper.call(ctx=mock_ctx)

        # Verify JSON output is valid
        json_output = result['json_output']
        parsed = json.loads(json_output)
        assert parsed == result['container_registry_map']

        # Verify it's pretty-printed (has indentation)
        assert '\n' in json_output
        assert '    ' in json_output

    @pytest.mark.asyncio
    async def test_invalid_additional_mapping_skipped(self, mock_ctx, tool_wrapper):
        """Test that invalid additional mappings are skipped."""
        additional_mappings = [
            {'upstreamRegistryUrl': 'valid.io', 'ecrRepositoryPrefix': 'valid'},
            {'upstreamRegistryUrl': 'missing-prefix.io'},  # Missing ecrRepositoryPrefix
            {'ecrRepositoryPrefix': 'missing-url'},  # Missing upstreamRegistryUrl
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                include_pull_through_caches=False,
                additional_registry_mappings=additional_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']
        # Only the valid mapping should be included
        assert len(container_map['registryMappings']) == 1
        assert container_map['registryMappings'][0]['upstreamRegistryUrl'] == 'valid.io'

    @pytest.mark.asyncio
    async def test_invalid_image_mapping_skipped(self, mock_ctx, tool_wrapper):
        """Test that invalid image mappings are skipped."""
        image_mappings = [
            {'sourceImage': 'valid:tag', 'destinationImage': 'dest:tag'},
            {'sourceImage': 'missing-dest'},  # Missing destinationImage
            {'destinationImage': 'missing-source'},  # Missing sourceImage
        ]

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                include_pull_through_caches=False,
                image_mappings=image_mappings,
            )

        assert result['success'] is True
        container_map = result['container_registry_map']
        # Only the valid mapping should be included
        assert len(container_map['imageMappings']) == 1
        assert container_map['imageMappings'][0]['sourceImage'] == 'valid:tag'

    @pytest.mark.asyncio
    async def test_no_usable_caches_returns_empty_mappings(self, mock_ctx, tool_wrapper):
        """Test when no HealthOmics-usable caches are found."""
        ptc_response = {
            'rules': [
                {
                    'ecr_repository_prefix': 'docker-hub',
                    'upstream_registry_url': 'registry-1.docker.io',
                    'healthomics_usable': False,
                },
            ],
            'next_token': None,
        }

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=ptc_response,
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
            result = await tool_wrapper.call(ctx=mock_ctx)

        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0
        assert result['container_registry_map'] == {}

    @pytest.mark.asyncio
    async def test_ptc_discovery_failure_continues(self, mock_ctx, tool_wrapper):
        """Test that failure to discover PTCs doesn't fail the whole operation."""
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                side_effect=Exception('Access denied'),
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
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                additional_registry_mappings=[
                    {'upstreamRegistryUrl': 'manual.io', 'ecrRepositoryPrefix': 'manual'},
                ],
            )

        # Should still succeed with manual mappings
        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0
        assert len(result['container_registry_map']['registryMappings']) == 1

    @pytest.mark.asyncio
    async def test_account_id_resolution_failure(self, mock_ctx, tool_wrapper):
        """Test handling of account ID resolution failure."""
        with patch(
            'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
            side_effect=Exception('STS access denied'),
        ):
            result = await tool_wrapper.call(ctx=mock_ctx)

        assert result['success'] is False
        assert 'Failed to get AWS account ID' in result['message']

    @pytest.mark.asyncio
    async def test_usage_hint_included(self, mock_ctx, tool_wrapper):
        """Test that usage hint is included in response."""
        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_account_id',
                return_value='123456789012',
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region',
                return_value='us-east-1',
            ),
        ):
            result = await tool_wrapper.call(
                ctx=mock_ctx,
                include_pull_through_caches=False,
            )

        assert 'usage_hint' in result
        assert 'container-registry-map.json' in result['usage_hint']

    @pytest.mark.asyncio
    async def test_empty_rules_list(self, mock_ctx, tool_wrapper):
        """Test with empty rules list from PTC discovery."""
        ptc_response = {'rules': [], 'next_token': None}

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.ecr_tools.list_pull_through_cache_rules',
                new_callable=AsyncMock,
                return_value=ptc_response,
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
            result = await tool_wrapper.call(ctx=mock_ctx)

        assert result['success'] is True
        assert result['discovered_healthomics_usable_caches'] == 0
        assert result['container_registry_map'] == {}
