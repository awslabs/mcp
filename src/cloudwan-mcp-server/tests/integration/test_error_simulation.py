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

"""Error response simulation and edge case testing following AWS Labs patterns."""

import json
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

from awslabs.cloudwan_mcp_server.server import (
    list_core_networks, get_global_networks, get_core_network_policy,
    get_core_network_change_set, discover_vpcs, trace_network_path,
    validate_ip_cidr, analyze_tgw_routes, analyze_tgw_peers,
    validate_cloudwan_policy, manage_tgw_routes, analyze_segment_routes
)


class TestThrottlingExceptionScenarios:
    """Test comprehensive ThrottlingException waterfall scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_throttling_exception_exponential_backoff(self):
        """Test ThrottlingException with exponential backoff simulation."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ThrottlingException',
                        'Message': 'Rate exceeded',
                        'RetryAfterSeconds': '5'
                    },
                    'ResponseMetadata': {
                        'RequestId': 'req-throttle-123456789',
                        'HTTPStatusCode': 429,
                        'RetryAttempts': 3
                    }
                },
                'ListCoreNetworks'
            )
            mock_get_client.return_value = mock_client
            
            result = await list_core_networks()
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ThrottlingException'
            assert 'Rate exceeded' in parsed['error']
            assert 'req-throttle-123456789' in parsed.get('request_id', '')

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_throttling_cascade_across_services(self):
        """Test throttling cascade affecting multiple AWS services."""
        def throttle_side_effect(service, region=None):
            mock_client = Mock()
            if service == 'networkmanager':
                mock_client.list_core_networks.side_effect = ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': 'NetworkManager throttled'}},
                    'ListCoreNetworks'
                )
            elif service == 'ec2':
                mock_client.describe_vpcs.side_effect = ClientError(
                    {'Error': {'Code': 'RequestLimitExceeded', 'Message': 'EC2 throttled'}},
                    'DescribeVpcs'
                )
            return mock_client

        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=throttle_side_effect):
            # Test throttling across multiple services
            nm_result = await list_core_networks()
            vpc_result = await discover_vpcs()
            
            nm_parsed = json.loads(nm_result)
            vpc_parsed = json.loads(vpc_result)
            
            assert nm_parsed['success'] is False
            assert nm_parsed['error_code'] == 'ThrottlingException'
            assert vpc_parsed['success'] is False
            assert vpc_parsed['error_code'] == 'RequestLimitExceeded'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_throttling_with_burst_capacity_exhaustion(self):
        """Test throttling after burst capacity exhaustion."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ThrottlingException',
                        'Message': 'Too Many Requests - burst capacity exhausted',
                        'Type': 'Client'
                    },
                    'ResponseMetadata': {
                        'HTTPHeaders': {
                            'x-amzn-requestid': 'burst-exhausted-123',
                            'retry-after': '30'
                        }
                    }
                },
                'GetCoreNetworkPolicy'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_core_network_policy('core-network-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ThrottlingException'
            assert 'burst capacity exhausted' in parsed['error']


class TestResourceNotFoundScenarios:
    """Test comprehensive ResourceNotFoundException permutations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_core_network_not_found_cascade(self):
        """Test ResourceNotFoundException cascading through dependent operations."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Core network core-network-nonexistent does not exist',
                        'ResourceType': 'CoreNetwork',
                        'ResourceId': 'core-network-nonexistent'
                    }
                },
                'GetCoreNetworkPolicy'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_core_network_policy('core-network-nonexistent')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ResourceNotFoundException'
            assert 'core-network-nonexistent does not exist' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_global_network_not_found_with_dependencies(self):
        """Test global network not found affecting dependent resources."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.describe_global_networks.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Global network global-network-123 was not found',
                        'ResourceArn': 'arn:aws:networkmanager::123456789012:global-network/global-network-123'
                    }
                },
                'DescribeGlobalNetworks'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_global_networks()
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ResourceNotFoundException'
            assert 'global-network-123 was not found' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transit_gateway_attachment_not_found(self):
        """Test transit gateway attachment not found with detailed error context."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'InvalidTransitGatewayAttachmentID.NotFound',
                        'Message': 'The transitGatewayAttachment ID tgw-attach-invalid does not exist',
                        'InvalidParameter': 'TransitGatewayAttachmentId'
                    }
                },
                'DescribeTransitGatewayPeeringAttachments'
            )
            mock_get_client.return_value = mock_client
            
            result = await analyze_tgw_peers('tgw-attach-invalid')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'InvalidTransitGatewayAttachmentID.NotFound'
            assert 'tgw-attach-invalid does not exist' in parsed['error']


class TestInvalidParameterValueScenarios:
    """Test comprehensive InvalidParameterValue edge cases."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_cidr_format_variations(self):
        """Test various invalid CIDR format scenarios."""
        invalid_cidrs = [
            '256.256.256.256/24',  # Invalid IP octets
            '192.168.1.0/33',      # Invalid subnet mask
            '10.0.0.0/-1',         # Negative subnet mask
            '172.16.0.0/ab',       # Non-numeric subnet mask
            'not-an-ip/16',        # Non-IP format
            '192.168.1.1/24/extra' # Extra components
        ]
        
        for invalid_cidr in invalid_cidrs:
            result = await validate_ip_cidr('validate_cidr', cidr=invalid_cidr)
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert 'validate_ip_cidr failed:' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_region_parameter(self):
        """Test invalid region parameter handling."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.list_core_networks.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'InvalidParameterValue',
                        'Message': 'Invalid region: invalid-region-1234',
                        'ParameterName': 'Region',
                        'ParameterValue': 'invalid-region-1234'
                    }
                },
                'ListCoreNetworks'
            )
            mock_get_client.return_value = mock_client
            
            result = await list_core_networks(region='invalid-region-1234')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'InvalidParameterValue'
            assert 'invalid-region-1234' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_ip_address_formats(self):
        """Test various invalid IP address format scenarios."""
        invalid_ips = [
            '999.999.999.999',     # Out of range octets
            '192.168.1',           # Incomplete IP
            '192.168.1.1.1',       # Too many octets
            'not.an.ip.address',   # Non-numeric octets
            '192.168.01.001',      # Leading zeros
            '192.168.1.-1'         # Negative octet
        ]
        
        for invalid_ip in invalid_ips:
            result = await validate_ip_cidr('validate_ip', ip=invalid_ip)
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert 'validate_ip_cidr failed:' in parsed['error']


class TestDependencyViolationScenarios:
    """Test comprehensive DependencyViolation chained failure scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_core_network_policy_dependency_violation(self):
        """Test core network policy update with dependency violations."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'DependencyViolation',
                        'Message': 'Cannot modify policy while change set is pending execution',
                        'DependentResource': 'CoreNetworkChangeSet',
                        'DependentResourceId': 'change-set-12345'
                    }
                },
                'GetCoreNetworkPolicy'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_core_network_policy('core-network-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'DependencyViolation'
            assert 'change set is pending execution' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_attachment_deletion_dependency_violation(self):
        """Test attachment deletion blocked by route table dependencies."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'DependencyViolation',
                        'Message': 'Cannot analyze routes while attachment deletion is in progress',
                        'ConflictingOperation': 'DeleteTransitGatewayVpcAttachment',
                        'ConflictingResourceId': 'tgw-attach-dependency-123'
                    }
                },
                'SearchTransitGatewayRoutes'
            )
            mock_get_client.return_value = mock_client
            
            result = await analyze_tgw_routes('tgw-rtb-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'DependencyViolation'
            assert 'attachment deletion is in progress' in parsed['error']


class TestInvalidPolicyDocumentScenarios:
    """Test comprehensive InvalidPolicyDocumentException variations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_malformed_policy_json_structure(self):
        """Test malformed policy document JSON structure validation."""
        malformed_policies = [
            {'version': '2021.12'},  # Missing core-network-configuration
            {
                'version': '2021.12',
                'core-network-configuration': {
                    'asn-ranges': []  # Empty ASN ranges
                }
            },
            {
                'version': 'invalid-version',  # Invalid version
                'core-network-configuration': {
                    'asn-ranges': ['64512-64555']
                }
            }
        ]
        
        for policy in malformed_policies:
            result = await validate_cloudwan_policy(policy)
            
            parsed = json.loads(result)
            assert parsed['success'] is True  # Function succeeds but validation fails
            assert parsed['overall_status'] == 'invalid'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_policy_syntax_errors(self):
        """Test policy document syntax error detection."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'InvalidPolicyDocumentException',
                        'Message': 'Policy document contains syntax errors at line 15',
                        'PolicyErrors': [
                            {
                                'ErrorCode': 'InvalidSegmentName',
                                'ErrorMessage': 'Segment name contains invalid characters',
                                'LineNumber': 15
                            }
                        ]
                    }
                },
                'GetCoreNetworkPolicy'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_core_network_policy('core-network-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'InvalidPolicyDocumentException'
            assert 'syntax errors at line 15' in parsed['error']


class TestConcurrentModificationScenarios:
    """Test comprehensive ConcurrentModification simulation scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_policy_modification(self):
        """Test concurrent policy modification detection."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ConcurrentModificationException',
                        'Message': 'Policy is being modified by another operation',
                        'ConflictingOperationId': 'op-12345',
                        'ConflictingOperationType': 'UpdateCoreNetworkPolicy'
                    }
                },
                'GetCoreNetworkPolicy'
            )
            mock_get_client.return_value = mock_client
            
            result = await get_core_network_policy('core-network-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ConcurrentModificationException'
            assert 'modified by another operation' in parsed['error']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_route_table_modification(self):
        """Test concurrent route table modification scenarios."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.side_effect = ClientError(
                {
                    'Error': {
                        'Code': 'ConcurrentModificationException',
                        'Message': 'Route table is being modified concurrently',
                        'LastModifiedTime': '2024-01-15T10:30:45Z',
                        'ModifyingUser': 'arn:aws:iam::123456789012:user/network-admin'
                    }
                },
                'SearchTransitGatewayRoutes'
            )
            mock_get_client.return_value = mock_client
            
            result = await analyze_tgw_routes('tgw-rtb-123')
            
            parsed = json.loads(result)
            assert parsed['success'] is False
            assert parsed['error_code'] == 'ConcurrentModificationException'
            assert 'being modified concurrently' in parsed['error']


class TestCrossServiceErrorPropagation:
    """Test comprehensive cross-service error propagation scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_networkmanager_to_ec2_error_propagation(self):
        """Test error propagation from NetworkManager to EC2 service calls."""
        call_count = 0
        
        def progressive_failure(service, region=None):
            nonlocal call_count
            call_count += 1
            mock_client = Mock()
            
            if service == 'networkmanager' and call_count == 1:
                # First call succeeds
                mock_client.list_core_networks.return_value = {'CoreNetworks': []}
            elif service == 'ec2' and call_count == 2:
                # Second call fails, propagating error
                mock_client.describe_vpcs.side_effect = ClientError(
                    {
                        'Error': {
                            'Code': 'ServiceUnavailableException',
                            'Message': 'EC2 service temporarily unavailable due to NetworkManager dependency failure'
                        }
                    },
                    'DescribeVpcs'
                )
            
            return mock_client
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=progressive_failure):
            # First call should succeed
            nm_result = await list_core_networks()
            nm_parsed = json.loads(nm_result)
            assert nm_parsed['success'] is True
            
            # Second call should fail with propagated error
            vpc_result = await discover_vpcs()
            vpc_parsed = json.loads(vpc_result)
            assert vpc_parsed['success'] is False
            assert vpc_parsed['error_code'] == 'ServiceUnavailableException'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_authentication_error_propagation(self):
        """Test authentication error propagation across multiple service calls."""
        auth_error = ClientError(
            {
                'Error': {
                    'Code': 'UnauthorizedOperation',
                    'Message': 'You are not authorized to perform this operation. Contact account administrator',
                    'AuthorizationFailureType': 'InsufficientPermissions'
                }
            },
            'UnauthorizedOperation'
        )
        
        def auth_failure_factory(service, region=None):
            mock_client = Mock()
            if service == 'networkmanager':
                mock_client.list_core_networks.side_effect = auth_error
                mock_client.describe_global_networks.side_effect = auth_error
            elif service == 'ec2':
                mock_client.describe_vpcs.side_effect = auth_error
                mock_client.search_transit_gateway_routes.side_effect = auth_error
            return mock_client
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=auth_failure_factory):
            # Test multiple operations fail with same auth error
            operations = [
                list_core_networks(),
                get_global_networks(),
                discover_vpcs(),
                analyze_tgw_routes('tgw-rtb-123')
            ]
            
            results = await asyncio.gather(*operations, return_exceptions=True)
            
            for result in results:
                assert not isinstance(result, Exception)
                parsed = json.loads(result)
                assert parsed['success'] is False
                assert parsed['error_code'] == 'UnauthorizedOperation'
                assert 'not authorized to perform this operation' in parsed['error']


class TestErrorRecoveryPatterns:
    """Test comprehensive error recovery pattern scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retry_after_temporary_failure(self):
        """Test retry patterns after temporary service failures."""
        retry_count = 0
        
        def temporary_failure_mock(service, region=None):
            nonlocal retry_count
            retry_count += 1
            mock_client = Mock()
            
            if retry_count <= 2:
                # First two calls fail
                mock_client.list_core_networks.side_effect = ClientError(
                    {
                        'Error': {
                            'Code': 'ServiceUnavailableException',
                            'Message': 'Service temporarily unavailable',
                            'RetryAfterSeconds': '1'
                        }
                    },
                    'ListCoreNetworks'
                )
            else:
                # Third call succeeds
                mock_client.list_core_networks.return_value = {
                    'CoreNetworks': [{'CoreNetworkId': 'core-network-recovery-test'}]
                }
            
            return mock_client
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=temporary_failure_mock):
            # First two attempts should fail
            result1 = await list_core_networks()
            result2 = await list_core_networks()
            result3 = await list_core_networks()
            
            parsed1 = json.loads(result1)
            parsed2 = json.loads(result2)
            parsed3 = json.loads(result3)
            
            assert parsed1['success'] is False
            assert parsed2['success'] is False
            assert parsed3['success'] is True
            assert parsed3['core_networks'][0]['CoreNetworkId'] == 'core-network-recovery-test'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern_simulation(self):
        """Test circuit breaker pattern for cascading failure prevention."""
        failure_count = 0
        
        def circuit_breaker_mock(service, region=None):
            nonlocal failure_count
            failure_count += 1
            mock_client = Mock()
            
            if failure_count <= 5:
                # First 5 calls fail rapidly
                mock_client.get_core_network_policy.side_effect = ClientError(
                    {
                        'Error': {
                            'Code': 'InternalFailure',
                            'Message': f'Internal service error #{failure_count}',
                            'CircuitBreakerState': 'OPEN' if failure_count >= 3 else 'CLOSED'
                        }
                    },
                    'GetCoreNetworkPolicy'
                )
            else:
                # After circuit breaker threshold, service recovers
                mock_client.get_core_network_policy.return_value = {
                    'CoreNetworkPolicy': {
                        'PolicyVersionId': '1',
                        'PolicyDocument': '{"version": "2021.12"}'
                    }
                }
            
            return mock_client
        
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=circuit_breaker_mock):
            results = []
            
            # Simulate multiple rapid-fire requests
            for i in range(7):
                result = await get_core_network_policy('core-network-123')
                results.append(json.loads(result))
            
            # First 5 should fail
            for i in range(5):
                assert results[i]['success'] is False
                assert results[i]['error_code'] == 'InternalFailure'
            
            # Later calls should succeed after circuit breaker recovery
            assert results[6]['success'] is True
            assert results[6]['policy_version_id'] == '1'


class TestErrorResponseFormatValidation:
    """Test error response format validation and compliance."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_aws_error_response_structure_compliance(self):
        """Test AWS error response structure compliance across all error types."""
        error_scenarios = [
            {
                'error_code': 'AccessDenied',
                'error_message': 'Access denied for resource',
                'operation': 'ListCoreNetworks'
            },
            {
                'error_code': 'ValidationException',
                'error_message': 'Validation failed for parameter',
                'operation': 'GetCoreNetworkPolicy'
            },
            {
                'error_code': 'InternalFailure',
                'error_message': 'Internal server error occurred',
                'operation': 'DescribeVpcs'
            }
        ]
        
        for scenario in error_scenarios:
            with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
                mock_client = Mock()
                error = ClientError(
                    {
                        'Error': {
                            'Code': scenario['error_code'],
                            'Message': scenario['error_message'],
                            'Type': 'Client' if scenario['error_code'] != 'InternalFailure' else 'Server'
                        },
                        'ResponseMetadata': {
                            'RequestId': f"req-{scenario['error_code']}-123",
                            'HTTPStatusCode': 403 if scenario['error_code'] == 'AccessDenied' else 400
                        }
                    },
                    scenario['operation']
                )
                
                mock_client.list_core_networks.side_effect = error
                mock_get_client.return_value = mock_client
                
                result = await list_core_networks()
                
                parsed = json.loads(result)
                assert parsed['success'] is False
                assert parsed['error_code'] == scenario['error_code']
                assert scenario['error_message'] in parsed['error']
                
                # Validate AWS Labs error response structure
                required_fields = ['success', 'error', 'error_code']
                for field in required_fields:
                    assert field in parsed, f"Missing required field: {field}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_message_localization_handling(self):
        """Test error message localization and internationalization handling."""
        localized_errors = [
            {
                'error_code': 'AccessDenied',
                'error_message': 'Accès refusé pour cette ressource',  # French
                'locale': 'fr-FR'
            },
            {
                'error_code': 'ValidationException',
                'error_message': 'パラメータの検証に失敗しました',  # Japanese
                'locale': 'ja-JP'
            }
        ]
        
        for error_scenario in localized_errors:
            with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
                mock_client = Mock()
                mock_client.list_core_networks.side_effect = ClientError(
                    {
                        'Error': {
                            'Code': error_scenario['error_code'],
                            'Message': error_scenario['error_message']
                        },
                        'ResponseMetadata': {
                            'HTTPHeaders': {
                                'content-language': error_scenario['locale']
                            }
                        }
                    },
                    'ListCoreNetworks'
                )
                mock_get_client.return_value = mock_client
                
                result = await list_core_networks()
                
                parsed = json.loads(result)
                assert parsed['success'] is False
                assert parsed['error_code'] == error_scenario['error_code']
                # Should handle non-ASCII characters properly
                assert error_scenario['error_message'] in parsed['error']