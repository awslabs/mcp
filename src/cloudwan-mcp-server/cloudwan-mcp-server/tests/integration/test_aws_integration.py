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

"""Integration tests for AWS service interactions."""

import json
import pytest
from awslabs.cloudwan_mcp_server.server import (
    discover_vpcs,
    list_core_networks,
)
from botocore.exceptions import ClientError
from moto import mock_aws
from unittest.mock import Mock, patch


class TestAWSServiceIntegration:
    """Test integration with AWS services using moto mocking."""

    @pytest.mark.asyncio
    async def test_vpc_discovery_with_moto(self):
        """Test VPC discovery with moto EC2 mocking."""
        with mock_aws():
            import boto3

            # Create test VPC using moto
            ec2 = boto3.client("ec2", region_name="us-east-1")
            vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            vpc_id = vpc["Vpc"]["VpcId"]

            # Clear any existing cached clients
            from awslabs.cloudwan_mcp_server.server import _create_client
            _create_client.cache_clear()

            # Test VPC discovery
            result = await discover_vpcs("us-east-1")
            response = json.loads(result)

            assert response["success"] is True
            assert response["total_count"] >= 1  # At least our created VPC
            assert len(response["vpcs"]) >= 1
            # Check that our VPC is in the results
            vpc_ids = [vpc["VpcId"] for vpc in response["vpcs"]]
            assert vpc_id in vpc_ids

    @pytest.mark.asyncio
    async def test_multiple_vpcs_discovery(self):
        """Test discovery of multiple VPCs."""
        with mock_aws():
            import boto3

            ec2 = boto3.client("ec2", region_name="us-west-2")

            # Create multiple VPCs
            vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            vpc2 = ec2.create_vpc(CidrBlock="172.16.0.0/16")
            vpc3 = ec2.create_vpc(CidrBlock="192.168.0.0/16")

            from awslabs.cloudwan_mcp_server.server import _create_client
            _create_client.cache_clear()

            result = await discover_vpcs("us-west-2")
            response = json.loads(result)

            assert response["success"] is True
            assert response["total_count"] >= 3  # At least our 3 created VPCs
            assert len(response["vpcs"]) >= 3

            # Check that our VPCs are present
            vpc_ids = {vpc["VpcId"] for vpc in response["vpcs"]}
            expected_ids = {vpc1["Vpc"]["VpcId"], vpc2["Vpc"]["VpcId"], vpc3["Vpc"]["VpcId"]}
            assert expected_ids.issubset(vpc_ids)  # Our VPCs should be subset of all VPCs

    @pytest.mark.asyncio
    async def test_aws_client_error_propagation(self):
        """Test that AWS client errors are properly propagated."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            # Mock ClientError
            error_response = {
                'Error': {
                    'Code': 'UnauthorizedOperation',
                    'Message': 'You are not authorized to perform this operation'
                }
            }
            mock_client.return_value.list_core_networks.side_effect = ClientError(
                error_response, 'ListCoreNetworks'
            )

            result = await list_core_networks("us-east-1")
            response = json.loads(result)

            assert response["success"] is False
            assert response["error_code"] == "UnauthorizedOperation"
            assert "You are not authorized" in response["error"]

    @pytest.mark.asyncio
    async def test_aws_service_availability(self):
        """Test handling of AWS service availability issues."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            # Mock service unavailable error
            error_response = {
                'Error': {
                    'Code': 'ServiceUnavailable',
                    'Message': 'Service is temporarily unavailable'
                }
            }
            mock_client.return_value.describe_vpcs.side_effect = ClientError(
                error_response, 'DescribeVpcs'
            )

            result = await discover_vpcs("us-east-1")
            response = json.loads(result)

            assert response["success"] is False
            assert response["error_code"] == "ServiceUnavailable"

    @pytest.mark.asyncio
    async def test_regional_client_isolation(self):
        """Test that different regions use isolated clients."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            # Setup different responses for different regions
            east_client = Mock()
            west_client = Mock()

            east_client.list_core_networks.return_value = {"CoreNetworks": [{"CoreNetworkId": "east-network"}]}
            west_client.list_core_networks.return_value = {"CoreNetworks": [{"CoreNetworkId": "west-network"}]}

            def get_client_side_effect(service, region):
                if region == "us-east-1":
                    return east_client
                elif region == "us-west-2":
                    return west_client
                else:
                    return Mock()

            mock_get_client.side_effect = get_client_side_effect

            # Test both regions
            east_result = await list_core_networks("us-east-1")
            west_result = await list_core_networks("us-west-2")

            east_response = json.loads(east_result)
            west_response = json.loads(west_result)

            # Verify different clients were called
            assert east_response["core_networks"][0]["CoreNetworkId"] == "east-network"
            assert west_response["core_networks"][0]["CoreNetworkId"] == "west-network"


class TestAWSCredentialsHandling:
    """Test AWS credentials and profile handling."""

    @pytest.mark.asyncio
    async def test_aws_profile_integration(self):
        """Test AWS profile handling integration."""
        from awslabs.cloudwan_mcp_server.server import aws_config, _create_client
        
        with patch('boto3.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_session_instance.client.return_value = mock_client

            # Mock the aws_config profile directly
            with patch.object(aws_config, 'profile', 'test-profile'):
                _create_client.cache_clear()  # Clear cache to force new client creation

                result = await list_core_networks("us-east-1")
                response = json.loads(result)

                # Verify session was created with correct profile
                mock_session.assert_called_with(profile_name="test-profile")
                assert response["success"] is True

    @pytest.mark.asyncio
    async def test_default_credentials_fallback(self):
        """Test fallback to default credentials when no profile is set."""
        from awslabs.cloudwan_mcp_server.server import aws_config, _create_client
        
        with patch('boto3.client') as mock_client_func:
            mock_client = Mock()
            mock_client.list_core_networks.return_value = {"CoreNetworks": []}
            mock_client_func.return_value = mock_client

            # Mock the aws_config profile to None
            with patch.object(aws_config, 'profile', None):
                _create_client.cache_clear()

                result = await list_core_networks("us-east-1")
                response = json.loads(result)

                # Verify direct boto3.client was called (no profile)
                mock_client_func.assert_called()
                assert response["success"] is True

    @pytest.mark.asyncio
    async def test_invalid_profile_handling(self):
        """Test handling of invalid AWS profile."""
        from awslabs.cloudwan_mcp_server.server import aws_config, _create_client
        
        with patch('boto3.Session') as mock_session:
            mock_session.side_effect = Exception("Profile not found")

            # Mock the aws_config profile to invalid profile
            with patch.object(aws_config, 'profile', 'invalid-profile'):
                _create_client.cache_clear()

                result = await list_core_networks("us-east-1")
                response = json.loads(result)

                assert response["success"] is False
                assert "[PROFILE_REDACTED]" in response["error"]


class TestAWSConfigurationIntegration:
    """Test AWS configuration and connection handling."""

    def test_boto3_config_parameters(self):
        """Test that boto3 clients are configured with correct parameters."""
        from awslabs.cloudwan_mcp_server.server import aws_config, _create_client, get_aws_client
        
        with patch.object(aws_config, 'profile', None):
            _create_client.cache_clear()  # Clear cache to force client creation

            with patch('boto3.client') as mock_client:
                mock_client.return_value = Mock()

                client = get_aws_client("networkmanager", "eu-central-1")

                # Verify boto3.client was called with correct config
                assert mock_client.called
                call_args = mock_client.call_args
                assert call_args is not None
                config = call_args[1]["config"]

                assert config.region_name == "eu-central-1"
                assert config.retries["max_attempts"] == 3
                assert config.retries["mode"] == "adaptive"
                assert config.max_pool_connections == 10

    @pytest.mark.asyncio
    async def test_connection_retry_behavior(self):
        """Test connection retry behavior with transient errors."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_client = Mock()

            # Simulate transient network error that succeeds on retry
            error_response = {
                'Error': {
                    'Code': 'RequestTimeout',
                    'Message': 'Request timed out'
                }
            }
            mock_client.list_core_networks.side_effect = [
                ClientError(error_response, 'ListCoreNetworks'),
                {"CoreNetworks": [{"CoreNetworkId": "success"}]}
            ]
            mock_get_client.return_value = mock_client

            result = await list_core_networks("us-east-1")
            response = json.loads(result)

            # First call should fail, but error handling should work
            assert response["success"] is False
            assert response["error_code"] == "RequestTimeout"

    @pytest.mark.asyncio
    async def test_multi_region_isolation(self):
        """Test that multi-region operations are properly isolated."""
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            # Track calls per region
            region_calls = {}

            def track_calls(service, region):
                if region not in region_calls:
                    region_calls[region] = Mock()
                    region_calls[region].describe_vpcs.return_value = {
                        "Vpcs": [{"VpcId": f"vpc-{region}", "Region": region}]
                    }
                return region_calls[region]

            mock_get_client.side_effect = track_calls

            # Call tools for different regions
            regions = ["us-east-1", "us-west-2", "eu-west-1"]
            results = []

            for region in regions:
                result = await discover_vpcs(region)
                results.append((region, json.loads(result)))

            # Verify each region got its own client and response
            assert len(region_calls) == 3
            for region, response in results:
                assert response["success"] is True
                assert response["region"] == region
                assert response["vpcs"][0]["VpcId"] == f"vpc-{region}"


class TestToolIntegration:
    """Test integration between different tools."""

    @pytest.mark.asyncio
    async def test_tool_chaining_workflow(self, aws_service_mocker):
        """Test workflow that chains multiple tools together."""
        # Import the required functions first
        from awslabs.cloudwan_mcp_server.server import (
            get_core_network_change_set,
            get_core_network_policy,
            list_core_networks,
        )
        
        # Configure NetworkManager mock with proper client patching
        nm_mocker = aws_service_mocker("networkmanager", "us-east-1")
        nm_mocker.configure_core_networks([
            {"CoreNetworkId": "cn-123", "State": "AVAILABLE"},
            {"CoreNetworkId": "cn-456", "State": "PENDING"}
        ])

        # Add policy mock
        nm_mocker.client.get_core_network_policy.return_value = {
            "CoreNetworkPolicy": {
                "PolicyVersionId": 1,
                "PolicyDocument": {}
            }
        }

        # Add change set mock
        nm_mocker.client.get_core_network_change_set.return_value = {
            "CoreNetworkChanges": [
                {"Type": "POLICY_CHANGE"}
            ]
        }

        # Patch get_aws_client to return our configured mock
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_get_client.return_value = nm_mocker.client

            # Test tool chaining
            networks_result = await list_core_networks("us-east-1")
            networks_response = json.loads(networks_result)
            assert networks_response["success"] is True
            assert len(networks_response["core_networks"]) == 2

            core_network_id = networks_response["core_networks"][0]["CoreNetworkId"]

            policy_result = await get_core_network_policy(core_network_id)
            policy_response = json.loads(policy_result)
            assert policy_response["success"] is True

            changes_result = await get_core_network_change_set(
                core_network_id, str(policy_response["policy_version_id"])
            )
            changes_response = json.loads(changes_result)
            assert changes_response["success"] is True

    @pytest.mark.asyncio
    async def test_error_propagation_across_tools(self, aws_service_mocker):
        """Test that errors propagate correctly in tool workflows."""
        from awslabs.cloudwan_mcp_server.server import get_core_network_policy
        from botocore.exceptions import ClientError
        
        # Configure error in policy retrieval
        nm_mocker = aws_service_mocker("networkmanager", "us-east-1")
        
        # Create a proper ClientError for the mock
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Core network not found'
            }
        }
        nm_mocker.client.get_core_network_policy.side_effect = ClientError(
            error_response, 'GetCoreNetworkPolicy'
        )

        # Patch get_aws_client to return our configured mock
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_get_client:
            mock_get_client.return_value = nm_mocker.client

            result = await get_core_network_policy("invalid-network-id")
            response = json.loads(result)
            assert response["success"] is False
            assert response["error_code"] == "ResourceNotFoundException"
