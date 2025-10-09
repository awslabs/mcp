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
"""Tests for the esm_diagnosis module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.poller.esm_diagnosis import (
    EsmDiagnosisTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestEsmDiagnosisTool:
    """Test getting the diagnosis and resolution steps."""

    @pytest.fixture
    def esm_diagnosis_tool(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mock_mcp = MagicMock()
        return EsmDiagnosisTool(mock_mcp)

    async def test_esm_kafka_diagnosis_tool(self, esm_diagnosis_tool):
        """Test getting the self diagnosis steps."""
        result = await esm_diagnosis_tool.esm_kafka_diagnosis_tool(AsyncMock())

        # Basic assertions
        assert isinstance(result, dict)
        assert 'diagnosis' in result
        assert 'issues' in result['diagnosis']
        assert 'timeout_indicators' in result['diagnosis']
        assert 'resolutions' in result['diagnosis']
        assert 'next_actions' in result['diagnosis']

        # Verify the response contains all expected timeout indicator categories
        timeout_indicators = result['diagnosis']['timeout_indicators']
        expected_categories = [
            'pre-broker-timeout',
            'post-broker-timeout',
            'lambda-unreachable',
            'on-failure-destination-unreachable',
            'sts-unreachable',
        ]

        for category in expected_categories:
            assert category in timeout_indicators
            assert isinstance(timeout_indicators[category], list)
            assert len(timeout_indicators[category]) > 0

        # Verify next actions reference the resolution tool
        for action in result['diagnosis']['next_actions']:
            assert 'esm_kafka_resolution_tool' in action

    @pytest.mark.parametrize(
        'issue_type',
        [
            'pre-broker-timeout',
            'post-broker-timeout',
            'lambda-unreachable',
            'on-failure-destination-unreachable',
            'sts-unreachable',
            'others',
            None,  # Test with None to see default behavior
        ],
    )
    async def test_esm_kafka_resolution_tool(self, esm_diagnosis_tool, issue_type):
        """Test getting the resolution steps."""
        result = await esm_diagnosis_tool.esm_kafka_resolution_tool(
            AsyncMock(),
            issue_type=issue_type,
        )

        # Basic assertions
        assert isinstance(result, dict)
        assert 'response' in result
        assert 'issues' in result['response']
        assert 'resolutions' in result['response']

        # Verify the response contains appropriate resolutions based on the issue type
        if issue_type == 'pre-broker-timeout':
            assert any(
                'security groups' in res.lower()
                for res in result['response']['resolutions']['steps']
            )
            assert 'rules' in result['response']['resolutions']
        elif issue_type == 'post-broker-timeout':
            assert any(
                'broker status' in res.lower()
                for res in result['response']['resolutions']['steps']
            )
        elif issue_type == 'lambda-unreachable':
            assert any(
                'has sufficient permissions' in res.lower()
                for res in result['response']['resolutions']['steps']
            )
            assert 'rules' in result['response']['resolutions']
        elif issue_type == 'on-failure-destination-unreachable':
            assert any('sns' in res.lower() for res in result['response']['resolutions']['steps'])
        elif issue_type == 'sts-unreachable':
            assert any(
                'sts vpc endpoint' in res.lower()
                for res in result['response']['resolutions']['steps']
            )
        else:
            assert any(
                'please refer to' in res.lower()
                for res in result['response']['resolutions']['steps']
            )
