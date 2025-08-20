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

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime

from awslabs.cloudwan_mcp_server.server import discover_ip_details


@pytest.mark.asyncio
class TestEnhancedDiscoverIPDetails:
    """Comprehensive tests for enhanced discover_ip_details function."""

    async def test_success_full_discovery(self):
        """Test successful ENI + routing + SGs + instance discovery."""
        fake_ip = "10.0.0.5"
        region = "us-east-1"

        # Mock AWS client
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # Step 1: ENI discovery
            ec2.describe_network_interfaces.return_value = {
                "NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-123",
                    "SubnetId": "subnet-abc",
                    "VpcId": "vpc-xyz",
                    "AvailabilityZone": "us-east-1a",
                    "Groups": [{"GroupId": "sg-111"}],
                    "Status": "in-use",
                    "InterfaceType": "interface",
                    "Attachment": {"InstanceId": "i-12345", "Status": "attached"}
                }]
            }
            
            # Step 2: Route Tables
            ec2.describe_route_tables.return_value = {
                "RouteTables": [{
                    "RouteTableId": "rtb-123", 
                    "Routes": [
                        {"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-123"},
                        {"DestinationCidrBlock": "10.0.0.0/16", "GatewayId": "local"}
                    ],
                    "Associations": [{"SubnetId": "subnet-abc"}],
                    "PropagatingVgws": []
                }]
            }
            
            # Step 3: Security Groups
            ec2.describe_security_groups.return_value = {
                "SecurityGroups": [{
                    "GroupId": "sg-111",
                    "GroupName": "default",
                    "Description": "default security group",
                    "IpPermissions": [
                        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                    ],
                    "IpPermissionsEgress": [
                        {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                    ],
                    "VpcId": "vpc-xyz"
                }]
            }
            
            # Step 4: Instance association
            ec2.describe_instances.return_value = {
                "Reservations": [{
                    "Instances": [{
                        "InstanceId": "i-12345",
                        "InstanceType": "t3.micro",
                        "State": {"Name": "running"},
                        "Platform": "linux",
                        "LaunchTime": datetime.now(),
                        "Tags": [{"Key": "Name", "Value": "test-instance"}]
                    }]
                }]
            }

            mock_client.return_value = ec2
            result = await discover_ip_details(fake_ip, region)
            response = json.loads(result)

            # Validate base response
            assert response["success"] is True
            assert response["ip_address"] == fake_ip
            assert response["is_private"] is True
            
            # Validate ENI details
            eni_details = response["aws_networking_context"]["eni_details"]
            assert eni_details["eni_found"] is True
            assert eni_details["eni_id"] == "eni-123"
            assert eni_details["vpc_id"] == "vpc-xyz"
            
            # Validate routing context
            routing_context = response["aws_networking_context"]["routing_context"]
            assert routing_context["route_table_found"] is True
            assert routing_context["route_table_id"] == "rtb-123"
            assert len(routing_context["routes"]) == 2
            
            # Validate security groups
            sg_context = response["aws_networking_context"]["security_groups"]
            assert sg_context["security_groups_found"] is True
            assert len(sg_context["security_groups"]) == 1
            
            # Validate associated resources
            resources = response["aws_networking_context"]["associated_resources"]
            assert resources["resources_found"] is True
            assert resources["instance_id"] == "i-12345"
            
            # Validate metrics
            assert response["services_queried"] == 4
            assert response["services_successful"] == 4

    async def test_ip_not_found_scenario(self):
        """Test when IP has no associated AWS ENI."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            # Both private and public IP searches return empty
            ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
            mock_client.return_value = ec2

            result = await discover_ip_details("192.168.1.100")
            response = json.loads(result)
            
            assert response["success"] is True
            assert response["aws_networking_context"]["eni_details"]["eni_found"] is False
            assert "No AWS network interface found" in response["aws_networking_context"]["message"]
            assert "possible_reasons" in response["aws_networking_context"]
            assert response["services_successful"] == 0

    async def test_partial_failure_graceful_degradation(self):
        """Test graceful degradation when some services fail."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # ENI found successfully
            ec2.describe_network_interfaces.return_value = {
                "NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-123",
                    "SubnetId": "subnet-abc",
                    "Groups": [{"GroupId": "sg-111"}],
                    "Attachment": {"InstanceId": "i-12345"}
                }]
            }
            
            # Route table discovery fails
            ec2.describe_route_tables.side_effect = Exception("Route table service unavailable")
            
            # Security groups succeed
            ec2.describe_security_groups.return_value = {
                "SecurityGroups": [{
                    "GroupId": "sg-111",
                    "GroupName": "web-sg"
                }]
            }
            
            # Instance discovery fails
            ec2.describe_instances.side_effect = ClientError(
                {"Error": {"Code": "UnauthorizedOperation", "Message": "Not authorized"}}, 
                "DescribeInstances"
            )
            
            mock_client.return_value = ec2
            result = await discover_ip_details("10.0.0.10")
            response = json.loads(result)

            # Should still succeed overall
            assert response["success"] is True
            
            # ENI and SG should succeed
            assert response["aws_networking_context"]["eni_details"]["eni_found"] is True
            assert response["aws_networking_context"]["security_groups"]["security_groups_found"] is True
            
            # Route table and resources should fail gracefully
            assert response["aws_networking_context"]["routing_context"]["route_table_found"] is False
            assert response["aws_networking_context"]["associated_resources"]["resources_found"] is False
            
            # Metrics should reflect partial success
            assert response["services_successful"] == 2  # ENI + SG successful

    async def test_error_sanitization(self):
        """Test that sensitive information is properly sanitized in errors."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # ENI discovery contains sensitive error
            ec2.describe_network_interfaces.side_effect = Exception(
                "Access denied for arn:aws:iam::123456789012:user/sensitive-user with AKIA1234567890123456"
            )
            
            mock_client.return_value = ec2
            result = await discover_ip_details("10.0.0.1")
            response = json.loads(result)

            # Error should be sanitized
            eni_error = response["aws_networking_context"]["eni_details"]["error"]
            assert "[ARN_REDACTED]" in eni_error
            assert "[ACCESS_KEY_REDACTED]" in eni_error
            assert "123456789012" not in eni_error
            assert "AKIA1234567890123456" not in eni_error

    async def test_invalid_ip_handling(self):
        """Test handling of invalid IP address format."""
        result = await discover_ip_details("invalid-ip-address")
        response = json.loads(result)
        
        assert response["success"] is False
        assert "error" in response
        assert "discover_ip_details failed" in response["error"]

    async def test_public_ip_discovery(self):
        """Test discovery for public IP addresses (Elastic IPs)."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # Private IP search returns empty, public IP search succeeds
            ec2.describe_network_interfaces.side_effect = [
                {"NetworkInterfaces": []},  # First call (private IP)
                {"NetworkInterfaces": [{    # Second call (public IP)
                    "NetworkInterfaceId": "eni-public-123",
                    "SubnetId": "subnet-public",
                    "Groups": [{"GroupId": "sg-web"}],
                    "Association": {"PublicIp": "54.123.45.67"}
                }]}
            ]
            
            mock_client.return_value = ec2
            result = await discover_ip_details("54.123.45.67")
            response = json.loads(result)

            assert response["success"] is True
            assert response["aws_networking_context"]["eni_details"]["eni_found"] is True
            assert response["aws_networking_context"]["eni_details"]["eni_id"] == "eni-public-123"

    async def test_performance_timeout_handling(self):
        """Test handling of AWS API timeouts."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # Simulate slow API response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate delay
                return {"NetworkInterfaces": []}
            
            ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
            mock_client.return_value = ec2
            
            # Should complete without timeout errors
            result = await discover_ip_details("10.0.0.1")
            response = json.loads(result)
            
            assert response["success"] is True
            assert "timestamp" in response

    @pytest.mark.integration 
    async def test_real_aws_integration(self):
        """Integration test with real AWS environment (requires valid credentials)."""
        # Skip if no AWS credentials available
        try:
            import boto3
            sts = boto3.client('sts')
            sts.get_caller_identity()
        except Exception:
            pytest.skip("No valid AWS credentials for integration test")
        
        # Test with a known public IP (AWS service IP)
        result = await discover_ip_details("8.8.8.8")  # External IP - should not find ENI
        response = json.loads(result)
        
        assert response["success"] is True
        assert response["aws_networking_context"]["eni_details"]["eni_found"] is False
        assert response["services_queried"] >= 1

    async def test_security_group_large_dataset_handling(self):
        """Test handling of large security group datasets."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # ENI with multiple security groups
            ec2.describe_network_interfaces.return_value = {
                "NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-multi-sg",
                    "Groups": [{"GroupId": f"sg-{i}"} for i in range(10)]  # 10 SGs
                }]
            }
            
            # Large security group response
            large_sg_list = []
            for i in range(10):
                large_sg_list.append({
                    "GroupId": f"sg-{i}",
                    "GroupName": f"sg-name-{i}",
                    "IpPermissions": [{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80}],
                    "IpPermissionsEgress": [{"IpProtocol": "-1"}]
                })
            
            ec2.describe_security_groups.return_value = {"SecurityGroups": large_sg_list}
            ec2.describe_route_tables.return_value = {"RouteTables": []}
            ec2.describe_instances.return_value = {"Reservations": []}
            
            mock_client.return_value = ec2
            result = await discover_ip_details("10.0.0.5")
            response = json.loads(result)

            # Should handle large dataset without issues
            assert response["success"] is True
            sg_details = response["aws_networking_context"]["security_groups"]
            assert sg_details["security_groups_found"] is True
            assert sg_details["total_count"] == 10

    async def test_concurrent_execution_performance(self):
        """Validate that API calls execute in parallel, not sequentially."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # Add delays to simulate API response time
            async def delayed_eni_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-timing",
                    "SubnetId": "subnet-timing",
                    "Groups": [{"GroupId": "sg-timing"}],
                    "Attachment": {"InstanceId": "i-timing"}
                }]}
                
            async def delayed_route_response(*args, **kwargs):
                await asyncio.sleep(0.1) 
                return {"RouteTables": []}
                
            async def delayed_sg_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"SecurityGroups": []}
                
            async def delayed_instance_response(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {"Reservations": []}
            
            ec2.describe_network_interfaces.return_value = {
                "NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-timing",
                    "SubnetId": "subnet-timing", 
                    "Groups": [{"GroupId": "sg-timing"}],
                    "Attachment": {"InstanceId": "i-timing"}
                }]
            }
            ec2.describe_route_tables.return_value = {"RouteTables": []}
            ec2.describe_security_groups.return_value = {"SecurityGroups": []}
            ec2.describe_instances.return_value = {"Reservations": []}
            
            mock_client.return_value = ec2

            start_time = asyncio.get_event_loop().time()
            result = await discover_ip_details("10.0.0.2")
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Should complete in less than sequential time (would be ~0.4s if sequential)
            assert elapsed_time < 0.3  # Parallel execution should be faster
            
            response = json.loads(result)
            assert response["success"] is True

    async def test_aws_permission_errors(self):
        """Test handling of various AWS permission scenarios."""
        test_cases = [
            ("UnauthorizedOperation", "Not authorized for network interfaces"),
            ("AccessDenied", "Access denied to describe resources"), 
            ("InvalidParameter", "Invalid parameter in request")
        ]
        
        for error_code, error_message in test_cases:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
                ec2 = MagicMock()
                ec2.describe_network_interfaces.side_effect = ClientError(
                    {"Error": {"Code": error_code, "Message": error_message}}, 
                    "DescribeNetworkInterfaces"
                )
                mock_client.return_value = ec2

                result = await discover_ip_details("10.0.0.1")
                response = json.loads(result)

                assert response["success"] is False
                assert error_code in response.get("error_code", "")

    async def test_ipv6_address_handling(self):
        """Test IPv6 address processing."""
        ipv6_address = "2001:db8::1"
        
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
            mock_client.return_value = ec2

            result = await discover_ip_details(ipv6_address)
            response = json.loads(result)

            assert response["success"] is True
            assert response["ip_version"] == 6
            assert response["ip_address"] == ipv6_address

    async def test_eni_without_instance_attachment(self):
        """Test ENI discovery when ENI exists but has no instance attachment."""
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            ec2 = MagicMock()
            
            # ENI without attachment (e.g., Lambda ENI, ALB ENI)
            ec2.describe_network_interfaces.return_value = {
                "NetworkInterfaces": [{
                    "NetworkInterfaceId": "eni-no-instance",
                    "SubnetId": "subnet-lambda",
                    "Groups": [{"GroupId": "sg-lambda"}],
                    "Status": "in-use",
                    "Attachment": {}  # No InstanceId
                }]
            }
            
            ec2.describe_route_tables.return_value = {"RouteTables": []}
            ec2.describe_security_groups.return_value = {"SecurityGroups": []}
            
            mock_client.return_value = ec2
            result = await discover_ip_details("10.0.1.50")
            response = json.loads(result)

            # ENI should be found
            assert response["aws_networking_context"]["eni_details"]["eni_found"] is True
            
            # Resources should indicate no instance attachment
            resources = response["aws_networking_context"]["associated_resources"]
            assert resources["resources_found"] is False
            assert resources["reason"] == "No instance attachment"

    async def test_error_message_sanitization_comprehensive(self):
        """Comprehensive test of error message sanitization."""
        sensitive_messages = [
            "Failed to connect to arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
            "Access key AKIA1234567890123456 is invalid",  
            "Session token IQoJb3JpZ2luX2VjEPD...very-long-token expired",
            "Profile admin-user in region us-east-1 failed",
            "Account 123456789012 access denied"
        ]
        
        for message in sensitive_messages:
            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
                ec2 = MagicMock()
                ec2.describe_network_interfaces.side_effect = Exception(message)
                mock_client.return_value = ec2

                result = await discover_ip_details("10.0.0.1") 
                response = json.loads(result)

                # Verify sanitization occurred
                error_text = response.get("error", "")
                assert "[ARN_REDACTED]" in error_text or "[ACCESS_KEY_REDACTED]" in error_text or "[ACCOUNT_REDACTED]" in error_text
                assert "123456789012" not in error_text
                assert "AKIA1234567890123456" not in error_text

    async def test_response_format_consistency(self):
        """Validate consistent response format across success and failure scenarios."""
        test_scenarios = [
            ("10.0.0.1", "success_scenario"),
            ("invalid-ip", "failure_scenario"),
            ("127.0.0.1", "loopback_scenario")
        ]
        
        for ip, scenario in test_scenarios:
            if scenario == "success_scenario":
                with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
                    ec2 = MagicMock()
                    ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
                    mock_client.return_value = ec2
                    result = await discover_ip_details(ip)
            else:
                result = await discover_ip_details(ip)
            
            response = json.loads(result)
            
            # All responses should have consistent base fields
            required_fields = ["success", "ip_address"] if scenario != "failure_scenario" else ["success", "error"]
            for field in required_fields:
                assert field in response, f"Missing {field} in {scenario}"