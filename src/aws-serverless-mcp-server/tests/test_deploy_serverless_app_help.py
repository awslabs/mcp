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
"""Tests for the deploy_serverless_app_help module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.guidance.deploy_serverless_app_help import (
    ApplicationType,
    DeployServerlessAppHelpTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestDeployServerlessAppHelp:
    """Tests for the deploy_serverless_app_help function."""

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_event_driven(self):
        """Test getting deployment help for event-driven applications."""
        # Call the function with event-driven application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.EVENT_DRIVEN
        )

        # Verify the result
        assert 'content' in result

        content = result['content']
        assert isinstance(content, list)
        assert len(content) > 0

        # Verify each step has required fields
        for step in content:
            assert 'step' in step
            assert 'prompt' in step
            assert isinstance(step['step'], int)
            assert isinstance(step['prompt'], str)
            assert len(step['prompt']) > 0

        # Check that steps are sequential
        for i, step in enumerate(content):
            assert step['step'] == i + 1

        # Check that event-driven specific content is included
        all_prompts = ' '.join([step['prompt'] for step in content])
        assert 'event source mapping' in all_prompts.lower() or 'esm' in all_prompts.lower()

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_backend(self):
        """Test getting deployment help for backend applications."""
        # Call the function with backend application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.BACKEND
        )

        # Verify the result
        assert 'content' in result

        content = result['content']
        assert isinstance(content, list)
        assert len(content) > 0

        # Verify each step has required fields
        for step in content:
            assert 'step' in step
            assert 'prompt' in step
            assert isinstance(step['step'], int)
            assert isinstance(step['prompt'], str)
            assert len(step['prompt']) > 0

        # Check that backend-specific content is included
        all_prompts = ' '.join([step['prompt'] for step in content])
        assert (
            'api gateway' in all_prompts.lower() or 'lambda function urls' in all_prompts.lower()
        )

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_fullstack(self):
        """Test getting deployment help for fullstack applications."""
        # Call the function with fullstack application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.FULLSTACK
        )

        # Verify the result
        assert 'content' in result

        content = result['content']
        assert isinstance(content, list)
        assert len(content) > 0

        # Verify each step has required fields
        for step in content:
            assert 'step' in step
            assert 'prompt' in step
            assert isinstance(step['step'], int)
            assert isinstance(step['prompt'], str)
            assert len(step['prompt']) > 0

        # Check that fullstack-specific content is included
        all_prompts = ' '.join([step['prompt'] for step in content])
        assert ('frontend' in all_prompts.lower() and 'backend' in all_prompts.lower()) or (
            's3' in all_prompts.lower() and 'cloudfront' in all_prompts.lower()
        )

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_step_structure(self):
        """Test the structure of deployment steps."""
        # Test with backend application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.BACKEND
        )

        # Verify deployment steps structure
        assert 'content' in result

        content = result['content']
        assert isinstance(content, list)
        assert len(content) >= 6  # Should have at least 6 steps based on implementation

        # Check each step has proper structure
        for i, step in enumerate(content):
            assert isinstance(step, dict)
            assert 'step' in step
            assert 'prompt' in step

            # Step number should be sequential
            assert step['step'] == i + 1

            # Prompt should be meaningful
            assert isinstance(step['prompt'], str)
            assert len(step['prompt']) > 20  # Should have substantial content

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_application_types_coverage(self):
        """Test that all application types are properly handled."""
        application_types = [
            ApplicationType.EVENT_DRIVEN,
            ApplicationType.BACKEND,
            ApplicationType.FULLSTACK,
        ]

        for app_type in application_types:
            # Call the function
            result = await DeployServerlessAppHelpTool(
                MagicMock()
            ).deploy_serverless_app_help_tool(AsyncMock(), app_type.value)

            # Verify the result
            assert 'content' in result

            content = result['content']
            assert isinstance(content, list)
            assert len(content) > 0

            # Verify all steps have required structure
            for step in content:
                assert 'step' in step
                assert 'prompt' in step
                assert isinstance(step['step'], int)
                assert isinstance(step['prompt'], str)

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_content_consistency(self):
        """Test that deployment help content is consistent across application types."""
        application_types = [
            ApplicationType.EVENT_DRIVEN,
            ApplicationType.BACKEND,
            ApplicationType.FULLSTACK,
        ]

        results = []
        for app_type in application_types:
            result = await DeployServerlessAppHelpTool(
                MagicMock()
            ).deploy_serverless_app_help_tool(AsyncMock(), app_type.value)
            content = result['content']
            results.append(content)

        # Check that all results have the same number of steps
        step_counts = [len(content) for content in results]
        assert all(count == step_counts[0] for count in step_counts), (
            'All application types should have the same number of steps'
        )

        # Check that step numbers are consistent
        for content in results:
            for i, step in enumerate(content):
                assert step['step'] == i + 1

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_sam_integration(self):
        """Test that deployment help properly integrates SAM CLI guidance."""
        # Test with event-driven application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.EVENT_DRIVEN
        )

        # Verify SAM CLI is mentioned in the help
        assert 'content' in result

        content = result['content']

        # Check deployment steps mention SAM
        all_prompts = ' '.join([step['prompt'] for step in content])

        sam_keywords = ['sam_init', 'sam_build', 'sam_deploy', 'sam']
        assert any(keyword in all_prompts.lower() for keyword in sam_keywords)

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_lambda_web_adapter_mention(self):
        """Test that Lambda Web Adapter is mentioned for web frameworks."""
        # Test with backend application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.BACKEND
        )

        # Verify Lambda Web Adapter is mentioned
        assert 'content' in result

        content = result['content']

        # Check that Lambda Web Adapter is mentioned
        all_prompts = ' '.join([step['prompt'] for step in content])
        assert 'lambda web adapter' in all_prompts.lower()

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_iac_guidance(self):
        """Test that IaC guidance is included."""
        # Test with fullstack application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.FULLSTACK
        )

        # Verify IaC guidance is included
        assert 'content' in result

        content = result['content']

        # Check that IaC tools are mentioned
        all_prompts = ' '.join([step['prompt'] for step in content])
        iac_keywords = ['infrastructure as code', 'iac', 'cloudformation', 'cdk', 'sam']
        assert any(keyword in all_prompts.lower() for keyword in iac_keywords)

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_deployment_artifacts(self):
        """Test that deployment artifact guidance is included."""
        # Test with backend application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.BACKEND
        )

        # Verify deployment artifact guidance is included
        assert 'content' in result

        content = result['content']

        # Check that deployment artifacts are mentioned
        all_prompts = ' '.join([step['prompt'] for step in content])
        artifact_keywords = ['zip', 's3', 'container image', 'ecr', 'deployment package']
        assert any(keyword in all_prompts.lower() for keyword in artifact_keywords)

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_step_order(self):
        """Test that deployment steps are in logical order."""
        # Test with event-driven application type
        result = await DeployServerlessAppHelpTool(MagicMock()).deploy_serverless_app_help_tool(
            AsyncMock(), ApplicationType.EVENT_DRIVEN
        )

        # Verify step order makes sense
        assert 'content' in result

        content = result['content']

        # Check that steps follow logical order
        step_prompts = [step['prompt'].lower() for step in content]

        # First step should be about initialization/setup
        assert any(
            keyword in step_prompts[0] for keyword in ['init', 'generate', 'handler', 'structure']
        )

        # Later steps should be about building and deployment
        later_steps = ' '.join(step_prompts[-2:])
        assert any(keyword in later_steps for keyword in ['build', 'deploy', 'package'])
