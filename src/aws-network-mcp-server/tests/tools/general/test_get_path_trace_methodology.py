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

"""Test cases for the get_path_trace_methodology tool."""

from awslabs.aws_network_mcp_server.tools.general.get_path_trace_methodology import (
    get_path_trace_methodology,
)


class TestGetPathTraceMethodology:
    """Test cases for get_path_trace_methodology function."""

    async def test_get_path_trace_methodology_returns_valid_response(self):
        """Test that methodology returns proper structure."""
        result = await get_path_trace_methodology()

        # Verify response structure matches actual implementation
        assert isinstance(result, dict)
        assert 'methodology' in result
        assert 'step_by_step_process' in result
        assert 'service_specific_guidance' in result
        assert 'common_failure_patterns' in result
        assert 'critical_best_practices' in result

        # Verify content is not empty
        assert len(result['methodology']) > 0
        assert len(result['step_by_step_process']) > 0
        assert len(result['service_specific_guidance']) > 0
        assert len(result['common_failure_patterns']) > 0
        assert len(result['critical_best_practices']) > 0

    async def test_methodology_contains_expected_sections(self):
        """Test that methodology contains expected sections."""
        result = await get_path_trace_methodology()

        methodology = result['methodology']

        # Check for key sections in methodology
        assert 'DISCOVER' in methodology['mandatory_sequence'][0]
        assert 'ROUTE' in methodology['mandatory_sequence'][1]
        assert 'SECURE' in methodology['mandatory_sequence'][2]
        assert 'VERIFY' in methodology['mandatory_sequence'][3]
        assert 'DIAGNOSE' in methodology['mandatory_sequence'][4]

        # Check step by step process has 5 steps
        steps = result['step_by_step_process']
        assert isinstance(steps, dict)
        assert len(steps) == 5  # Should have exactly 5 main steps

        # Check each step exists
        assert 'step_1_discovery' in steps
        assert 'step_2_routing_analysis' in steps
        assert 'step_3_security_analysis' in steps
        assert 'step_4_verification' in steps
        assert 'step_5_diagnosis' in steps

    async def test_service_specific_guidance_structure(self):
        """Test service specific guidance structure."""
        result = await get_path_trace_methodology()

        guidance = result['service_specific_guidance']
        assert isinstance(guidance, dict)

        # Should have guidance for main services
        assert 'cloud_wan' in guidance
        assert 'transit_gateway' in guidance
        assert 'vpc_networking' in guidance

    async def test_common_failure_patterns_structure(self):
        """Test common failure patterns structure."""
        result = await get_path_trace_methodology()

        patterns = result['common_failure_patterns']
        assert isinstance(patterns, dict)

        # Should include common networking failure patterns
        assert 'asymmetric_routing' in patterns
        assert 'ephemeral_ports' in patterns
        assert 'firewall_inspection' in patterns

    async def test_methodology_is_deterministic(self):
        """Test that methodology returns consistent results."""
        result1 = await get_path_trace_methodology()
        result2 = await get_path_trace_methodology()

        # Results should be identical since it's static methodology
        assert result1 == result2

    async def test_methodology_security_considerations(self):
        """Test that methodology includes security considerations."""
        result = await get_path_trace_methodology()

        methodology_text = str(result)

        # Should mention security-related concepts
        assert 'security' in methodology_text.lower()

        # Should reference security groups or NACLs
        assert 'security group' in methodology_text.lower() or 'nacl' in methodology_text.lower()

        # Should mention access denied scenarios which are security-related
        assert (
            'access_denied' in methodology_text.lower() or 'authorized' in methodology_text.lower()
        )

    async def test_methodology_contains_tool_references(self):
        """Test that methodology references actual tool functions."""
        result = await get_path_trace_methodology()

        methodology_text = str(result)

        # Should reference key tools
        assert 'find_ip_address' in methodology_text
        assert 'get_eni_details' in methodology_text
        assert 'get_vpc_network_details' in methodology_text

    async def test_workflow_steps_completeness(self):
        """Test that workflow steps cover complete troubleshooting process."""
        result = await get_path_trace_methodology()

        steps = result['step_by_step_process']
        step_names = list(steps.keys())

        # Should cover end-to-end process with 5 specific steps
        assert 'step_1_discovery' in step_names
        assert 'step_2_routing_analysis' in step_names
        assert 'step_3_security_analysis' in step_names
        assert 'step_4_verification' in step_names
        assert 'step_5_diagnosis' in step_names

    async def test_methodology_no_sensitive_data(self):
        """Test that methodology doesn't expose sensitive information."""
        result = await get_path_trace_methodology()

        methodology_text = str(result).lower()

        # Should not contain any credentials, keys, or sensitive data
        sensitive_patterns = [
            'aws_access_key',
            'aws_secret',
            'password',
            'token',
            'credential',
            'arn:aws:iam::',
            'account-id',
            'secret-key',
        ]

        for pattern in sensitive_patterns:
            assert pattern not in methodology_text, (
                f'Found potentially sensitive pattern: {pattern}'
            )
