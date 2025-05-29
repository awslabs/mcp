# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the get_iac_guidance module."""

import json
import pytest
from awslabs.aws_serverless_mcp_server.models import GetIaCGuidanceRequest
from awslabs.aws_serverless_mcp_server.tools.guidance.get_iac_guidance import (
    ComparisonTable,
    IaCToolInfo,
    ToolSpecificGuidance,
    get_iac_guidance,
)


class TestIaCToolInfo:
    """Tests for the IaCToolInfo class."""

    def test_to_dict(self):
        """Test converting IaCToolInfo to dictionary."""
        tool_info = IaCToolInfo(
            name='Test Tool',
            description='A test tool',
            best_for=['Testing', 'Development'],
            pros=['Easy to use', 'Fast'],
            cons=['Limited features'],
            getting_started='Install and run',
            example_code="console.log('Hello, world!');",
        )

        result = tool_info.to_dict()

        assert result['name'] == 'Test Tool'
        assert result['description'] == 'A test tool'
        assert result['bestFor'] == ['Testing', 'Development']
        assert result['pros'] == ['Easy to use', 'Fast']
        assert result['cons'] == ['Limited features']
        assert result['gettingStarted'] == 'Install and run'
        assert result['exampleCode'] == "console.log('Hello, world!');"


class TestComparisonTable:
    """Tests for the ComparisonTable class."""

    def test_to_dict(self):
        """Test converting ComparisonTable to dictionary."""
        table = ComparisonTable(
            headers=['Feature', 'Tool A', 'Tool B'],
            rows=[{'tool': 'Language', 'cells': ['YAML', 'JSON']}],
        )

        result = table.to_dict()

        assert result['headers'] == ['Feature', 'Tool A', 'Tool B']
        assert len(result['rows']) == 1
        assert result['rows'][0]['tool'] == 'Language'
        assert result['rows'][0]['cells'] == ['YAML', 'JSON']


class TestToolSpecificGuidance:
    """Tests for the ToolSpecificGuidance class."""

    def test_to_dict(self):
        """Test converting ToolSpecificGuidance to dictionary."""
        guidance = ToolSpecificGuidance(
            title='Test Guidance',
            description='A test guidance',
            setup_steps=['Step 1', 'Step 2'],
            deployment_steps=['Deploy 1', 'Deploy 2'],
            common_commands=[{'command': 'test', 'description': 'Run tests'}],
        )

        result = guidance.to_dict()

        assert result['title'] == 'Test Guidance'
        assert result['description'] == 'A test guidance'
        assert result['setupSteps'] == ['Step 1', 'Step 2']
        assert result['deploymentSteps'] == ['Deploy 1', 'Deploy 2']
        assert len(result['commonCommands']) == 1
        assert result['commonCommands'][0]['command'] == 'test'
        assert result['commonCommands'][0]['description'] == 'Run tests'


class TestGetIaCGuidance:
    """Tests for the get_iac_guidance function."""

    @pytest.mark.asyncio
    async def test_get_iac_guidance_basic(self):
        """Test getting basic IaC guidance."""
        request = GetIaCGuidanceRequest(iac_tool='CloudFormation', include_examples=False)

        result = await get_iac_guidance(request)

        # Check basic structure
        assert 'title' in result
        assert 'overview' in result
        assert 'tools' in result
        assert 'comparisonTable' in result

        # Parse JSON strings
        tools = json.loads(result['tools'])
        comparison_table = json.loads(result['comparisonTable'])

        # Check tools
        assert len(tools) > 0
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'bestFor' in tool
            assert 'pros' in tool
            assert 'cons' in tool
            assert 'gettingStarted' in tool

        # Check comparison table
        assert 'headers' in comparison_table
        assert 'rows' in comparison_table
        assert len(comparison_table['headers']) > 0
        assert len(comparison_table['rows']) > 0

    @pytest.mark.asyncio
    async def test_get_iac_guidance_with_examples(self):
        """Test getting IaC guidance with examples."""
        request = GetIaCGuidanceRequest(iac_tool='CloudFormation', include_examples=True)

        result = await get_iac_guidance(request)

        # Parse JSON string
        tools = json.loads(result['tools'])

        # Check that examples are included
        for tool in tools:
            assert 'exampleCode' in tool
            assert tool['exampleCode'] != ''

    @pytest.mark.asyncio
    async def test_get_iac_guidance_without_examples(self):
        """Test getting IaC guidance without examples."""
        request = GetIaCGuidanceRequest(iac_tool='CloudFormation', include_examples=False)

        result = await get_iac_guidance(request)

        # Parse JSON string
        tools = json.loads(result['tools'])

        # Check that examples are not included or are empty
        for tool in tools:
            assert tool['exampleCode'] == ''

    @pytest.mark.asyncio
    async def test_get_iac_guidance_specific_tool_sam(self):
        """Test getting IaC guidance for SAM."""
        request = GetIaCGuidanceRequest(iac_tool='SAM', include_examples=False)

        result = await get_iac_guidance(request)

        # Check that tool-specific guidance is included
        assert 'toolSpecificGuidance' in result

        # Parse JSON string
        tool_specific_guidance = json.loads(result['toolSpecificGuidance'])
        assert tool_specific_guidance['title'] == 'AWS SAM Deployment Guide'

    @pytest.mark.asyncio
    async def test_get_iac_guidance_specific_tool_cdk(self):
        """Test getting IaC guidance for CDK."""
        request = GetIaCGuidanceRequest(iac_tool='CDK', include_examples=False)

        result = await get_iac_guidance(request)

        # Check that tool-specific guidance is included
        assert 'toolSpecificGuidance' in result

        # Parse JSON string
        tool_specific_guidance = json.loads(result['toolSpecificGuidance'])
        assert tool_specific_guidance['title'] == 'AWS CDK Deployment Guide'

    @pytest.mark.asyncio
    async def test_get_iac_guidance_specific_tool_cloudformation(self):
        """Test getting IaC guidance for CloudFormation."""
        request = GetIaCGuidanceRequest(iac_tool='CloudFormation', include_examples=True)

        result = await get_iac_guidance(request)

        # Check that tool-specific guidance is included
        assert 'toolSpecificGuidance' in result

        # Parse JSON string
        tool_specific_guidance = json.loads(result['toolSpecificGuidance'])
        assert tool_specific_guidance['title'] == 'AWS CloudFormation Deployment Guide'
