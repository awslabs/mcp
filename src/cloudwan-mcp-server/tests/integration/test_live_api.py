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

"""Live API tests against real AWS CloudWAN infrastructure following AWS Labs patterns."""

import json
import os
import time

import pytest

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_peers,
    analyze_tgw_routes,
    aws_config_manager,
    discover_vpcs,
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
    validate_ip_cidr,
)


@pytest.fixture(scope="session")
def live_aws_credentials():
    """Ensure AWS credentials are available for live tests."""
    required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(f"Missing required AWS credentials: {', '.join(missing_vars)}")

    return {
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "session_token": os.getenv("AWS_SESSION_TOKEN"),
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    }


@pytest.fixture(scope="session")
def live_test_resources():
    """Define live test resources that should exist in the test account."""
    return {
        # These should be created manually in the test AWS account
        "test_regions": ["us-east-1", "us-west-2"],
        "expected_vpcs": {
            "us-east-1": 1,  # At least 1 VPC expected in us-east-1
            "us-west-2": 0,  # May have 0 VPCs in us-west-2
        },
    }


class TestLiveCoreNetworkOperations:
    """Test live CloudWAN Core Network operations."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_core_network_listing(self, live_aws_credentials, live_test_resources) -> None:
        """Test against real AWS CloudWAN API."""
        start_time = time.time()

        for region in live_test_resources["test_regions"]:
            try:
                result = await list_core_networks(region=region)
                parsed = json.loads(result)

                # Should succeed or fail gracefully
                assert isinstance(parsed, dict)
                assert "success" in parsed
                assert "region" in parsed
                assert parsed["region"] == region

                if parsed["success"]:
                    assert "core_networks" in parsed
                    assert "total_count" in parsed
                    assert isinstance(parsed["core_networks"], list)

                    # Validate core network structure if any exist
                    for network in parsed["core_networks"]:
                        assert "CoreNetworkId" in network
                        assert "State" in network
                        assert network["State"] in ["AVAILABLE", "CREATING", "UPDATING", "DELETING"]

                else:
                    # If failed, should have error information
                    assert "error" in parsed
                    assert "error_code" in parsed

            except Exception as e:
                pytest.fail(f"Unexpected error in live core network test for {region}: {e}")

        execution_time = time.time() - start_time
        assert execution_time < 30.0, f"Live core network test took {execution_time:.2f}s"

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_global_network_discovery(self, live_aws_credentials, live_test_resources) -> None:
        """Test live global network discovery."""
        for region in live_test_resources["test_regions"]:
            result = await get_global_networks(region=region)
            parsed = json.loads(result)

            assert isinstance(parsed, dict)
            assert "success" in parsed

            if parsed["success"]:
                assert "global_networks" in parsed
                assert "total_count" in parsed
                assert isinstance(parsed["global_networks"], list)

                # Validate global network structure
                for network in parsed["global_networks"]:
                    assert "GlobalNetworkId" in network
                    if "State" in network:
                        assert network["State"] in ["PENDING", "AVAILABLE", "DELETING", "UPDATING"]
            else:
                # Common expected errors for regions without CloudWAN
                expected_errors = ["AccessDenied", "UnauthorizedOperation", "OptInRequired"]
                assert any(error in parsed.get("error", "") for error in expected_errors)

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_core_network_policy_retrieval(self, live_aws_credentials) -> None:
        """Test live core network policy retrieval."""
        # First get available core networks
        result = await list_core_networks()
        parsed = json.loads(result)

        if parsed["success"] and parsed["total_count"] > 0:
            # Test policy retrieval for first available core network
            core_network_id = parsed["core_networks"][0]["CoreNetworkId"]

            policy_result = await get_core_network_policy(core_network_id)
            policy_parsed = json.loads(policy_result)

            if policy_parsed["success"]:
                # Validate policy structure
                assert "policy_document" in policy_parsed
                assert "policy_version_id" in policy_parsed
                assert "core_network_id" in policy_parsed

                # Parse and validate policy document
                policy_doc = json.loads(policy_parsed["policy_document"])
                assert "version" in policy_doc
                assert policy_doc["version"] in ["2021.12", "2022.02"]
            else:
                # Policy retrieval may fail if no policy exists
                assert "error" in policy_parsed
        else:
            pytest.skip("No core networks available for policy testing")

    @pytest.mark.live
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_live_multi_region_consistency(self, live_aws_credentials, live_test_resources) -> None:
        """Test cross-region consistency of CloudWAN resources."""
        region_results = {}

        # Test multiple regions simultaneously
        for region in live_test_resources["test_regions"]:
            core_networks_result = await list_core_networks(region=region)
            global_networks_result = await get_global_networks(region=region)

            region_results[region] = {
                "core_networks": json.loads(core_networks_result),
                "global_networks": json.loads(global_networks_result),
            }

        # Analyze cross-region consistency
        for region, results in region_results.items():
            assert isinstance(results["core_networks"], dict)
            assert isinstance(results["global_networks"], dict)

            # Global networks should be consistent across regions (they're global resources)
            if results["global_networks"]["success"]:
                global_network_ids = [gn["GlobalNetworkId"] for gn in results["global_networks"]["global_networks"]]

                # Store for cross-region comparison
                if not hasattr(test_live_multi_region_consistency, "global_networks_ref"):
                    test_live_multi_region_consistency.global_networks_ref = global_network_ids
                else:
                    # Global networks should be the same across regions
                    ref_ids = set(test_live_multi_region_consistency.global_networks_ref)
                    current_ids = set(global_network_ids)
                    # Allow for some differences due to eventual consistency
                    assert len(ref_ids.symmetric_difference(current_ids)) <= 1


class TestLiveVPCOperations:
    """Test live VPC operations."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_vpc_discovery(self, live_aws_credentials, live_test_resources) -> None:
        """Test VPC discovery against live AWS account."""
        for region in live_test_resources["test_regions"]:
            result = await discover_vpcs(region=region)
            parsed = json.loads(result)

            assert isinstance(parsed, dict)
            assert "success" in parsed
            assert "region" in parsed
            assert parsed["region"] == region

            if parsed["success"]:
                assert "vpcs" in parsed
                assert "total_count" in parsed
                assert isinstance(parsed["vpcs"], list)

                expected_count = live_test_resources["expected_vpcs"][region]
                if expected_count > 0:
                    assert parsed["total_count"] >= expected_count, (
                        f"Expected at least {expected_count} VPCs in {region}"
                    )

                # Validate VPC structure
                for vpc in parsed["vpcs"]:
                    assert "VpcId" in vpc
                    assert vpc["VpcId"].startswith("vpc-")
                    assert "State" in vpc
                    assert vpc["State"] in ["pending", "available", "terminating"]
                    assert "CidrBlock" in vpc
            else:
                # Should fail gracefully with proper error information
                assert "error" in parsed
                assert "error_code" in parsed

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_vpc_filtering(self, live_aws_credentials) -> None:
        """Test VPC discovery with filtering in live environment."""
        result = await discover_vpcs()
        parsed = json.loads(result)

        if parsed["success"] and parsed["total_count"] > 0:
            # Test that VPCs have expected attributes for filtering
            for vpc in parsed["vpcs"]:
                assert "VpcId" in vpc
                assert "State" in vpc
                assert "CidrBlock" in vpc

                # VpcId should be valid format
                assert len(vpc["VpcId"]) >= 12  # vpc- + 8-17 chars
                assert vpc["VpcId"].startswith("vpc-")

                # State should be valid
                valid_states = ["pending", "available", "terminating"]
                assert vpc["State"] in valid_states

                # CIDR should be valid format (basic check)
                cidr = vpc["CidrBlock"]
                assert "/" in cidr
                assert len(cidr.split("/")) == 2
        else:
            pytest.skip("No VPCs available for filtering test")


class TestLiveTransitGatewayOperations:
    """Test live Transit Gateway operations."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_tgw_route_analysis_error_handling(self, live_aws_credentials) -> None:
        """Test TGW route analysis error handling with invalid route table."""
        # Use invalid route table ID to test error handling
        invalid_route_table_id = "tgw-rtb-invalid123456789"

        result = await analyze_tgw_routes(invalid_route_table_id)
        parsed = json.loads(result)

        # Should handle invalid route table gracefully
        assert isinstance(parsed, dict)
        assert "success" in parsed
        assert parsed["success"] is False
        assert "error" in parsed
        assert "error_code" in parsed

        # Should return proper AWS error codes
        expected_errors = ["InvalidRouteTableID.NotFound", "InvalidRouteTableId.NotFound", "UnauthorizedOperation"]
        assert any(error in parsed["error_code"] for error in expected_errors)

    @pytest.mark.live
    @pytest.mark.skipif(os.getenv("SKIP_TGW_TESTS") == "1", reason="TGW resources not available")
    @pytest.mark.asyncio
    async def test_live_tgw_peer_analysis_error_handling(self, live_aws_credentials) -> None:
        """Test TGW peer analysis error handling."""
        # Use invalid peering attachment ID
        invalid_attachment_id = "tgw-attach-invalid123456789"

        result = await analyze_tgw_peers(invalid_attachment_id)
        parsed = json.loads(result)

        # Should handle invalid attachment ID gracefully
        assert isinstance(parsed, dict)
        assert "success" in parsed
        assert parsed["success"] is False
        assert "error" in parsed

        # Should not expose internal system information
        assert "traceback" not in parsed["error"].lower()
        assert "internal error" not in parsed["error"].lower()


class TestLiveNetworkUtilities:
    """Test live network utility operations."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_ip_validation(self, live_aws_credentials) -> None:
        """Test IP validation with various real-world IP patterns."""
        test_ips = [
            ("8.8.8.8", True),  # Google DNS
            ("1.1.1.1", True),  # Cloudflare DNS
            ("192.168.1.1", True),  # Private IP
            ("10.0.0.1", True),  # Private IP
            ("172.16.0.1", True),  # Private IP
            ("256.1.1.1", False),  # Invalid IP
            ("192.168.1", False),  # Incomplete IP
            ("invalid", False),  # Non-IP string
        ]

        for ip, expected_valid in test_ips:
            result = await validate_ip_cidr("validate_ip", ip=ip)
            parsed = json.loads(result)

            assert isinstance(parsed, dict)
            assert "success" in parsed

            if expected_valid:
                assert parsed["success"] is True
                assert "ip_address" in parsed
                assert parsed["ip_address"] == ip
                assert "version" in parsed
                assert parsed["version"] in [4, 6]
            else:
                # Invalid IPs should fail validation
                assert parsed["success"] is False
                assert "error" in parsed

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_cidr_validation(self, live_aws_credentials) -> None:
        """Test CIDR validation with real-world CIDR patterns."""
        test_cidrs = [
            ("192.168.0.0/24", True),  # Standard private CIDR
            ("10.0.0.0/8", True),  # Class A private
            ("172.16.0.0/12", True),  # Class B private
            ("0.0.0.0/0", True),  # Default route
            ("192.168.1.0/25", True),  # Subnet
            ("192.168.0.0/33", False),  # Invalid prefix length
            ("256.1.1.0/24", False),  # Invalid IP in CIDR
            ("192.168.1.0", False),  # Missing prefix
        ]

        for cidr, expected_valid in test_cidrs:
            result = await validate_ip_cidr("validate_cidr", cidr=cidr)
            parsed = json.loads(result)

            assert isinstance(parsed, dict)
            assert "success" in parsed

            if expected_valid:
                assert parsed["success"] is True
                assert "network" in parsed
                assert parsed["network"] == cidr
                assert "network_address" in parsed
                assert "num_addresses" in parsed
            else:
                # Invalid CIDRs should fail validation
                assert parsed["success"] is False
                assert "error" in parsed


class TestLiveConfigurationManagement:
    """Test live AWS configuration management."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_config_validation(self, live_aws_credentials) -> None:
        """Test AWS configuration validation against live credentials."""
        result = await aws_config_manager("validate_config")
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "success" in parsed

        if parsed["success"]:
            # Should validate successfully with live credentials
            assert "aws_config" in parsed
            assert "credentials_valid" in parsed
            assert parsed["credentials_valid"] is True

            # Should not expose actual credential values
            response_text = json.dumps(parsed)
            assert live_aws_credentials["access_key"] not in response_text
            assert live_aws_credentials["secret_key"] not in response_text
        else:
            # If validation fails, should provide helpful error
            assert "error" in parsed
            assert "error_code" in parsed

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_region_operations(self, live_aws_credentials, live_test_resources) -> None:
        """Test region switching with live AWS operations."""
        original_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        try:
            for test_region in live_test_resources["test_regions"]:
                # Switch to test region
                region_result = await aws_config_manager("set_region", region=test_region)
                region_parsed = json.loads(region_result)

                if region_parsed["success"]:
                    assert region_parsed["new_region"] == test_region

                    # Test operation in new region
                    vpc_result = await discover_vpcs(region=test_region)
                    vpc_parsed = json.loads(vpc_result)

                    assert "region" in vpc_parsed
                    assert vpc_parsed["region"] == test_region

        finally:
            # Restore original region
            await aws_config_manager("set_region", region=original_region)

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_live_current_config_retrieval(self, live_aws_credentials) -> None:
        """Test current configuration retrieval with live setup."""
        result = await aws_config_manager("get_current")
        parsed = json.loads(result)

        assert isinstance(parsed, dict)
        assert "success" in parsed

        if parsed["success"]:
            assert "current_config" in parsed
            config = parsed["current_config"]

            # Should have region information
            assert "region" in config
            assert isinstance(config["region"], str)
            assert len(config["region"]) > 0

            # Should have profile information (may be 'default')
            assert "profile" in config

            # Should not expose sensitive credentials
            response_text = json.dumps(parsed)
            assert "aws_access_key_id" not in response_text.lower()
            assert "aws_secret_access_key" not in response_text.lower()
        else:
            # Configuration retrieval should generally succeed
            pytest.fail(f"Config retrieval failed: {parsed.get('error', 'Unknown error')}")


class TestLivePerformanceMetrics:
    """Test performance metrics with live API calls."""

    @pytest.mark.live
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_live_api_response_times(self, live_aws_credentials, live_test_resources) -> None:
        """Test API response time performance with live calls."""
        performance_metrics = {"list_core_networks": [], "get_global_networks": [], "discover_vpcs": []}

        # Run each operation multiple times to get reliable metrics
        iterations = 3

        for i in range(iterations):
            # Test list_core_networks
            start_time = time.time()
            await list_core_networks()
            performance_metrics["list_core_networks"].append(time.time() - start_time)

            # Test get_global_networks
            start_time = time.time()
            await get_global_networks()
            performance_metrics["get_global_networks"].append(time.time() - start_time)

            # Test discover_vpcs
            start_time = time.time()
            await discover_vpcs()
            performance_metrics["discover_vpcs"].append(time.time() - start_time)

        # Analyze performance metrics
        for operation, times in performance_metrics.items():
            avg_time = sum(times) / len(times)
            max_time = max(times)

            # Performance assertions (adjust based on expected AWS API performance)
            assert avg_time < 5.0, f"{operation} average time {avg_time:.2f}s too high"
            assert max_time < 10.0, f"{operation} max time {max_time:.2f}s too high"

            print(f"{operation}: avg={avg_time:.3f}s, max={max_time:.3f}s")

    @pytest.mark.live
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_live_concurrent_operations(self, live_aws_credentials) -> None:
        """Test concurrent operations against live AWS APIs."""
        import asyncio

        concurrent_count = 5
        start_time = time.time()

        # Run operations concurrently
        tasks = []
        for i in range(concurrent_count):
            tasks.extend([list_core_networks(), get_global_networks(), discover_vpcs()])

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        successful_operations = 0
        for result in results:
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    if parsed.get("success", False):
                        successful_operations += 1
                except:
                    pass  # Skip malformed responses

        # Performance assertions
        assert successful_operations >= len(tasks) * 0.8, (
            f"Only {successful_operations}/{len(tasks)} operations succeeded"
        )
        assert total_time < 30.0, f"Concurrent operations took {total_time:.2f}s"

        operations_per_second = len(tasks) / total_time
        assert operations_per_second >= 1.0, f"Only {operations_per_second:.2f} ops/sec"

        print(
            f"Concurrent performance: {successful_operations}/{len(tasks)} successful, "
            f"{operations_per_second:.2f} ops/sec"
        )
