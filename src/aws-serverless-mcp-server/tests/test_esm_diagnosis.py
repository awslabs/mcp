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
from awslabs.aws_serverless_mcp_server.tools.esm.esm_diagnosis import (
    EsmDiagnosisTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestEsmDiagnosisTool:
    """Test getting the diagnosis and resolution steps."""

    @pytest.fixture
    def esm_diagnosis_tool(self):
        """Create a mock FastMCP and initialize the tool with the mock."""
        mock_mcp = MagicMock()
        return EsmDiagnosisTool(mock_mcp, allow_write=True)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'issue_type, kafka_type',
        [
            ('diagnosis', 'auto-detect'),
            ('diagnosis', 'msk'),
            ('diagnosis', 'self-managed'),
        ],
    )
    async def test_esm_kafka_troubleshoot_diagnosis(
        self, esm_diagnosis_tool, issue_type, kafka_type
    ):
        """Test getting the self diagnosis steps."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type=issue_type, kafka_type=kafka_type
        )

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
            'authentication-failed',
            'network-connectivity',
        ]

        for category in expected_categories:
            assert category in timeout_indicators
            assert isinstance(timeout_indicators[category], list)
            assert len(timeout_indicators[category]) > 0

        # Verify next actions reference the troubleshoot tool
        next_actions_text = ' '.join(result['diagnosis']['next_actions'])
        assert 'esm_kafka_troubleshoot' in next_actions_text

        # Verify important facts are included based on Kafka type
        important_facts = result['diagnosis']['important_facts']
        if kafka_type == 'msk':
            facts_text = ' '.join(important_facts)
            assert 'MSK' in facts_text or 'Amazon MSK' in facts_text
        elif kafka_type == 'self-managed':
            facts_text = ' '.join(important_facts)
            assert 'Self-Managed' in facts_text or 'self-managed' in facts_text

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'issue_type, kafka_type',
        [
            ('pre-broker-timeout', 'msk'),
            ('post-broker-timeout', 'self-managed'),
            ('lambda-unreachable', 'auto-detect'),
            ('on-failure-destination-unreachable', 'msk'),
            ('sts-unreachable', 'self-managed'),
            ('authentication-failed', 'msk'),
            ('network-connectivity', 'auto-detect'),
            ('others', 'auto-detect'),
        ],
    )
    async def test_esm_kafka_troubleshoot_resolution(
        self, esm_diagnosis_tool, issue_type, kafka_type
    ):
        """Test getting the resolution steps for specific issues."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(),
            issue_type=issue_type,
            kafka_type=kafka_type,
        )

        # Basic assertions
        assert isinstance(result, dict)

        # For specific issue types, we should get resolution steps
        if issue_type != 'diagnosis':
            # Should have either resolution steps or error handling
            # Check if response is nested under 'response' key
            if 'response' in result:
                response_data = result['response']
                assert (
                    'resolutions' in response_data
                    or 'steps' in response_data
                    or 'issues' in response_data
                )
            else:
                assert 'resolutions' in result or 'steps' in result or 'issues' in result

            # Verify the response contains appropriate resolutions based on the issue type
            response_text = str(result).lower()

            # Verify safety requirements are included
            assert (
                'critical safety requirements' in response_text or 'never deploy' in response_text
            )

            if issue_type == 'pre-broker-timeout':
                assert 'security group' in response_text or 'network' in response_text
                if kafka_type == 'msk':
                    assert 'msk' in response_text
                elif kafka_type == 'self-managed':
                    assert 'self-managed' in response_text or 'vpc configuration' in response_text

            elif issue_type == 'post-broker-timeout':
                assert 'broker' in response_text or 'kafka' in response_text

            elif issue_type == 'lambda-unreachable':
                assert (
                    'lambda' in response_text
                    or 'permission' in response_text
                    or 'vpc endpoint' in response_text
                )

            elif issue_type == 'on-failure-destination-unreachable':
                assert 'destination' in response_text or 'failure' in response_text

            elif issue_type == 'sts-unreachable':
                assert (
                    'sts' in response_text
                    or 'endpoint' in response_text
                    or 'role assumption' in response_text
                )

            elif issue_type == 'authentication-failed':
                assert (
                    'auth' in response_text
                    or 'credential' in response_text
                    or 'iam' in response_text
                )
                if kafka_type == 'msk':
                    assert 'iam authentication' in response_text or 'sasl/scram' in response_text
                elif kafka_type == 'self-managed':
                    assert 'sasl' in response_text or 'mtls' in response_text

            elif issue_type == 'network-connectivity':
                assert (
                    'network' in response_text
                    or 'connectivity' in response_text
                    or 'vpc' in response_text
                )

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_msk_specific_resolution(self, esm_diagnosis_tool):
        """Test MSK-specific resolution steps."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='pre-broker-timeout', kafka_type='msk'
        )

        # Should contain MSK-specific guidance
        response_text = str(result).lower()
        assert 'msk cluster security group' in response_text or 'msk' in response_text
        assert 'ports 9092-9098' in response_text or '9092' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_self_managed_specific_resolution(
        self, esm_diagnosis_tool
    ):
        """Test self-managed Kafka specific resolution steps."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='authentication-failed', kafka_type='self-managed'
        )

        # Should contain self-managed Kafka specific guidance
        response_text = str(result).lower()
        assert (
            'self-managed' in response_text or 'sasl' in response_text or 'mtls' in response_text
        )

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_safety_requirements(self, esm_diagnosis_tool):
        """Test that all resolution steps include safety requirements."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='network-connectivity', kafka_type='msk'
        )

        # Should include safety requirements
        response_text = str(result).lower()
        assert (
            'never deploy' in response_text
            or 'user confirmation' in response_text
            or 'critical safety' in response_text
        )

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_authentication_failed_msk(self, esm_diagnosis_tool):
        """Test authentication-failed issue type for MSK."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='authentication-failed', kafka_type='msk'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'authentication' in response_text
        assert 'msk' in response_text or 'iam' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_authentication_failed_self_managed(
        self, esm_diagnosis_tool
    ):
        """Test authentication-failed issue type for self-managed Kafka."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='authentication-failed', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'authentication' in response_text
        assert 'sasl' in response_text or 'self-managed' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_on_failure_destination_unreachable(
        self, esm_diagnosis_tool
    ):
        """Test on-failure-destination-unreachable issue type."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='on-failure-destination-unreachable', kafka_type='msk'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'failure' in response_text or 'destination' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_invalid_issue_type(self, esm_diagnosis_tool):
        """Test with invalid issue type to cover default case."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='invalid-issue-type', kafka_type='msk'
        )

        assert isinstance(result, dict)
        # Should still return some diagnostic information
        assert 'diagnostic' in str(result).lower() or 'troubleshoot' in str(result).lower()

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_template_generation_guidance(self, esm_diagnosis_tool):
        """Test that resolution steps include template generation guidance."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='pre-broker-timeout', kafka_type='msk'
        )

        # Should include guidance about SAM templates and deployment
        response_text = str(result).lower()
        assert 'sam template' in response_text or 'template' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_all_issue_types(self, esm_diagnosis_tool):
        """Test all issue types for comprehensive coverage."""
        issue_types = [
            'pre-broker-timeout',
            'post-broker-timeout',
            'lambda-unreachable',
            'on-failure-destination-unreachable',
            'sts-unreachable',
            'authentication-failed',
            'network-connectivity',
            'others',
        ]

        for issue_type in issue_types:
            result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
                AsyncMock(), issue_type=issue_type, kafka_type='msk'
            )

            assert isinstance(result, dict)
            # Each issue type should return resolution steps
            response_text = str(result).lower()
            assert 'resolution' in response_text or 'steps' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_all_kafka_types(self, esm_diagnosis_tool):
        """Test all Kafka types for comprehensive coverage."""
        kafka_types = ['msk', 'self-managed', 'auto-detect']

        for kafka_type in kafka_types:
            # Test diagnosis
            result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
                AsyncMock(), issue_type='diagnosis', kafka_type=kafka_type
            )

            assert isinstance(result, dict)
            assert 'diagnosis' in result

            # Test resolution
            result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
                AsyncMock(), issue_type='pre-broker-timeout', kafka_type=kafka_type
            )

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_default_parameters(self, esm_diagnosis_tool):
        """Test with default parameters."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(AsyncMock())

        assert isinstance(result, dict)
        # Default should be diagnosis mode
        assert 'diagnosis' in result or 'response' in result

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_none_parameters(self, esm_diagnosis_tool):
        """Test with None parameters to ensure proper handling."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type=None, kafka_type=None
        )

        assert isinstance(result, dict)
        # Should default to diagnosis mode or return response structure
        assert 'diagnosis' in result or 'response' in result

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_auto_detect_branches(self, esm_diagnosis_tool):
        """Test auto-detect branches for comprehensive coverage."""
        # Test authentication-failed with auto-detect
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='authentication-failed', kafka_type='auto-detect'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'general authentication failed' in response_text

        # Test lambda-unreachable with self-managed
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='lambda-unreachable', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'self-managed kafka lambda unreachable' in response_text

        # Test on-failure-destination-unreachable with self-managed
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='on-failure-destination-unreachable', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'self-managed kafka on-failure destination' in response_text

        # Test sts-unreachable with auto-detect
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='sts-unreachable', kafka_type='auto-detect'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'general sts unreachable' in response_text

        # Test others with self-managed
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='others', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'self-managed kafka documentation' in response_text

        # Test network-connectivity with self-managed to cover line 451-452
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='network-connectivity', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'self-managed kafka esm network connectivity' in response_text

        # Test on-failure-destination-unreachable with auto-detect to cover line 588
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='on-failure-destination-unreachable', kafka_type='auto-detect'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'general on-failure destination unreachable' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_diagnosis_msk(self, esm_diagnosis_tool):
        """Test diagnosis issue type for MSK."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='diagnosis', kafka_type='msk'
        )

        assert isinstance(result, dict)
        assert 'diagnosis' in result
        assert 'important_facts' in result['diagnosis']

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_diagnosis_self_managed(self, esm_diagnosis_tool):
        """Test diagnosis issue type for self-managed Kafka."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='diagnosis', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        assert 'diagnosis' in result
        assert 'important_facts' in result['diagnosis']

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_diagnosis_auto_detect(self, esm_diagnosis_tool):
        """Test diagnosis with auto-detect kafka type."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='diagnosis', kafka_type=None
        )

        assert isinstance(result, dict)
        assert 'diagnosis' in result
        assert 'important_facts' in result['diagnosis']

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_timeout_issues_msk(self, esm_diagnosis_tool):
        """Test timeout-issues resolution for MSK."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='timeout-issues', kafka_type='msk'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'timeout' in response_text or 'resolution' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_timeout_issues_self_managed(self, esm_diagnosis_tool):
        """Test timeout-issues resolution for self-managed Kafka."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='timeout-issues', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'timeout' in response_text or 'resolution' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_consumer_lag_msk(self, esm_diagnosis_tool):
        """Test consumer-lag resolution for MSK."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='consumer-lag', kafka_type='msk'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'consumer' in response_text or 'lag' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_consumer_lag_self_managed(self, esm_diagnosis_tool):
        """Test consumer-lag resolution for self-managed Kafka."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='consumer-lag', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'consumer' in response_text or 'lag' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_permission_denied_msk(self, esm_diagnosis_tool):
        """Test permission-denied resolution for MSK."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='permission-denied', kafka_type='msk'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'permission' in response_text or 'denied' in response_text

    @pytest.mark.asyncio
    async def test_esm_kafka_troubleshoot_permission_denied_self_managed(self, esm_diagnosis_tool):
        """Test permission-denied resolution for self-managed Kafka."""
        result = await esm_diagnosis_tool.esm_kafka_troubleshoot_tool(
            AsyncMock(), issue_type='permission-denied', kafka_type='self-managed'
        )

        assert isinstance(result, dict)
        response_text = str(result).lower()
        assert 'permission' in response_text or 'denied' in response_text
