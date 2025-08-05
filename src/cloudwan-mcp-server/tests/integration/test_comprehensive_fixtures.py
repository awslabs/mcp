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

"""Comprehensive tests using advanced fixtures following AWS Labs patterns."""

import json
import time

# Import our fixtures
from unittest.mock import Mock, patch

import pytest

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_routes,
    discover_vpcs,
    list_core_networks,
    validate_cloudwan_policy,
)


class TestTopologyFixtureIntegration:
    """Test integration with topology fixtures."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_enterprise_hub_spoke_topology(self, enterprise_hub_spoke_topology) -> None:
        """Test enterprise hub-and-spoke topology processing."""
        topology = enterprise_hub_spoke_topology

        assert topology["topology_type"] == "hub_spoke"
        assert len(topology["regions"]) == 5
        assert len(topology["core_networks"]) == 5

        # Test with mock responses using topology data
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()

            # Use topology data for mock responses
            mock_client.list_core_networks.return_value = {"CoreNetworks": topology["core_networks"]}
            mock_get_client.return_value = mock_client

            result = await list_core_networks()
            parsed = json.loads(result)

            assert parsed["success"] is True
            assert parsed["total_count"] == len(topology["core_networks"])
            assert len(parsed["core_networks"]) == 5

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_mesh_topology_processing(self, full_mesh_topology) -> None:
        """Test full mesh topology processing."""
        topology = full_mesh_topology

        assert topology["topology_type"] == "full_mesh"
        assert len(topology["regions"]) == 4

        # Should have full mesh peering connections: n*(n-1)/2
        expected_connections = 4 * 3 // 2  # 6 connections
        assert len(topology["peering_connections"]) == expected_connections

        # Test VPC discovery with topology data
        for region in topology["regions"]:
            region_vpcs = topology["vpc_attachments"][region]

            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()
                mock_client.describe_vpcs.return_value = {"Vpcs": region_vpcs}
                mock_get_client.return_value = mock_client

                result = await discover_vpcs(region=region)
                parsed = json.loads(result)

                assert parsed["success"] is True
                assert parsed["region"] == region
                assert len(parsed["vpcs"]) == len(region_vpcs)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_hierarchical_topology_validation(self, hierarchical_topology) -> None:
        """Test hierarchical topology validation."""
        topology = hierarchical_topology

        assert topology["topology_type"] == "hierarchical"
        assert topology["levels"] == 3
        assert topology["branches_per_level"] == 4

        # Validate hierarchy structure
        root_node = topology["hierarchy"]
        assert root_node["level"] == 1
        assert root_node["parent_id"] is None
        assert len(root_node["children"]) == 4

        # Test that all core networks are present
        expected_networks = 1 + 4 + 16  # Level 1 + Level 2 + Level 3
        assert len(topology["core_networks"]) == expected_networks

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_random_topology_adaptability(self, random_network_topology) -> None:
        """Test adaptability with randomly generated topologies."""
        topology = random_network_topology

        # Should handle any topology type
        assert topology["topology_type"] in ["hub_spoke", "full_mesh", "hierarchical"]
        assert "global_network" in topology
        assert topology["global_network"]["State"] == "AVAILABLE"

        # Basic structure validation regardless of type
        if topology["topology_type"] == "hub_spoke":
            assert "regions" in topology
            assert "vpc_attachments" in topology
        elif topology["topology_type"] == "full_mesh":
            assert "peering_connections" in topology
            assert len(topology["peering_connections"]) > 0
        else:  # hierarchical
            assert "hierarchy" in topology
            assert "levels" in topology


class TestPolicyFixtureValidation:
    """Test policy fixtures validation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_enterprise_policy_validation(self, enterprise_policy) -> None:
        """Test enterprise policy fixture validation."""
        policy = enterprise_policy

        # Basic policy structure validation
        assert policy["version"] == "2021.12"
        assert "core-network-configuration" in policy
        assert "segments" in policy
        assert "segment-actions" in policy
        assert "attachment-policies" in policy

        # Validate policy with our function
        result = await validate_cloudwan_policy(policy)
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert "overall_status" in parsed
        assert parsed["policy_version"] == "2021.12"

        # Should have comprehensive validation results
        validation_results = parsed["validation_results"]
        assert len(validation_results) >= 4  # At least version, core-config, segments, actions

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_security_policy_compliance(self, security_policy) -> None:
        """Test security policy fixture compliance."""
        policy = security_policy

        # Validate security requirements
        assert len(policy["segments"]) == 4
        security_segments = ["pci-compliant", "hipaa-compliant", "sox-compliant", "security-tools"]

        for segment in policy["segments"]:
            assert segment["name"] in security_segments
            if segment["name"] != "security-tools":
                # Compliance segments should require acceptance and isolation
                assert segment["require-attachment-acceptance"] is True
                assert segment["isolate-attachments"] is True

        # Test policy validation
        result = await validate_cloudwan_policy(policy)
        parsed = json.loads(result)

        assert parsed["success"] is True

        # Verify security-specific validation
        response_text = json.dumps(parsed)
        assert "pci-compliant" in response_text
        assert "hipaa-compliant" in response_text

    @pytest.mark.integration
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_policy_fixture_performance(self, enterprise_policy) -> None:
        """Test policy fixture processing performance."""
        policy = enterprise_policy

        # Should handle large enterprise policy efficiently
        start_time = time.time()
        result = await validate_cloudwan_policy(policy)
        processing_time = time.time() - start_time

        parsed = json.loads(result)
        assert parsed["success"] is True

        # Performance requirements
        assert processing_time < 10.0, f"Enterprise policy validation took {processing_time:.2f}s"

        # Policy should have realistic enterprise scale
        assert len(policy["segments"]) == 10
        assert len(policy["attachment-policies"]) == 50


class TestPerformanceDatasetIntegration:
    """Test integration with performance datasets."""

    @pytest.mark.integration
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_large_route_dataset_processing(self, large_route_dataset) -> None:
        """Test large route dataset processing."""
        routes = large_route_dataset

        assert len(routes) == 100000

        # Test route analysis with large dataset
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            # Use a subset for testing to avoid timeout
            test_routes = routes[:1000]  # First 1000 routes
            mock_client.search_transit_gateway_routes.return_value = {
                "Routes": test_routes,
                "AdditionalRoutesAvailable": False,
            }
            mock_get_client.return_value = mock_client

            start_time = time.time()
            result = await analyze_tgw_routes("tgw-rtb-performance-test")
            processing_time = time.time() - start_time

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["analysis"]["total_routes"] == 1000

            # Should process efficiently
            assert processing_time < 5.0, f"Route processing took {processing_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_large_vpc_dataset_discovery(self, large_vpc_dataset) -> None:
        """Test large VPC dataset discovery."""
        vpcs = large_vpc_dataset

        assert len(vpcs) == 10000

        # Test VPC discovery with large dataset
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            # Use a subset for testing
            test_vpcs = vpcs[:500]  # First 500 VPCs
            mock_client.describe_vpcs.return_value = {"Vpcs": test_vpcs}
            mock_get_client.return_value = mock_client

            start_time = time.time()
            result = await discover_vpcs()
            processing_time = time.time() - start_time

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 500

            # Should discover efficiently
            assert processing_time < 3.0, f"VPC discovery took {processing_time:.2f}s"

            # Validate data integrity
            assert all("VpcId" in vpc for vpc in parsed["vpcs"])
            assert all(vpc["State"] == "available" for vpc in parsed["vpcs"])


class TestMultiRegionConfigurationIntegration:
    """Test multi-region configuration integration."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_global_deployment_configuration(self, global_deployment_config) -> None:
        """Test global deployment configuration."""
        config = global_deployment_config

        assert config["deployment_type"] == "global"
        assert config["primary_region"] == "us-east-1"
        assert len(config["secondary_regions"]) == 3

        # Test each region configuration
        for region_name, region_config in config["regions"].items():
            assert region_config["region_name"] == region_name
            assert len(region_config["availability_zones"]) == 3
            assert len(region_config["core_networks"]) == 1
            assert len(region_config["transit_gateways"]) == 1

            # Primary region should have more VPCs
            if region_config["is_primary"]:
                assert len(region_config["vpcs"]) == 5
            else:
                assert len(region_config["vpcs"]) == 3

        # Test cross-region connections
        assert len(config["cross_region_connections"]) == len(config["secondary_regions"])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_disaster_recovery_configuration(self, disaster_recovery_config) -> None:
        """Test disaster recovery configuration."""
        config = disaster_recovery_config

        assert config["deployment_type"] == "disaster_recovery"
        assert config["primary_site"]["region"] == "us-east-1"
        assert config["dr_site"]["region"] == "us-west-2"

        # Validate DR requirements
        assert config["primary_site"]["rto"] == 300  # 5 minutes
        assert config["primary_site"]["rpo"] == 900  # 15 minutes
        assert config["dr_site"]["rto"] == 600  # 10 minutes

        # Test replication configuration
        assert config["replication"]["method"] == "async"
        assert config["replication"]["frequency"] == 300

        # Validate resources for both sites
        for site_name in ["primary_site", "dr_site"]:
            site = config[site_name]
            assert "resources" in site
            assert len(site["resources"]["core_networks"]) == 1
            assert len(site["resources"]["transit_gateways"]) == 1
            assert len(site["resources"]["vpcs"]) == 3  # One per AZ

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_region_consistency_validation(self, global_deployment_config) -> None:
        """Test multi-region consistency validation."""
        config = global_deployment_config

        # Test that global resources are consistent across regions
        global_network_id = None
        for region_name, region_config in config["regions"].items():
            core_network = region_config["core_networks"][0]

            if global_network_id is None:
                global_network_id = core_network["GlobalNetworkId"]
            else:
                # All core networks should reference same global network
                assert core_network["GlobalNetworkId"] == global_network_id

        # Test mock responses for consistency
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()

            for region_name, region_config in config["regions"].items():
                # Mock core networks response
                mock_client.list_core_networks.return_value = {"CoreNetworks": region_config["core_networks"]}
                mock_get_client.return_value = mock_client

                result = await list_core_networks(region=region_name)
                parsed = json.loads(result)

                assert parsed["success"] is True
                assert parsed["region"] == region_name
                assert len(parsed["core_networks"]) == 1


class TestFixtureScalabilityValidation:
    """Test fixture scalability and limits."""

    @pytest.mark.integration
    @pytest.mark.slowtest
    @pytest.mark.asyncio
    async def test_fixture_memory_efficiency(self, enterprise_hub_spoke_topology, enterprise_policy) -> None:
        """Test fixture memory efficiency."""
        import gc
        import os

        import psutil

        # Measure memory before
        gc.collect()
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Process topology and policy
        topology = enterprise_hub_spoke_topology
        policy = enterprise_policy

        # Validate complex structures
        assert len(topology["regions"]) == 5
        assert len(topology["peering_connections"]) == 4  # Chain connections
        assert len(policy["segments"]) == 10
        assert len(policy["attachment-policies"]) == 50

        # Test policy validation
        result = await validate_cloudwan_policy(policy)
        parsed = json.loads(result)
        assert parsed["success"] is True

        # Measure memory after
        gc.collect()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = memory_after - memory_before

        # Memory growth should be reasonable
        assert memory_growth < 100, f"Memory grew by {memory_growth:.2f}MB processing fixtures"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fixture_data_integrity(self, full_mesh_topology, security_policy) -> None:
        """Test fixture data integrity."""
        topology = full_mesh_topology
        policy = security_policy

        # Validate topology data integrity
        for region in topology["regions"]:
            # Each region should have consistent data
            assert region in topology["vpc_attachments"]
            assert region in topology["transit_gateways"]

            vpcs = topology["vpc_attachments"][region]
            for vpc in vpcs:
                assert vpc["Region"] == region
                assert vpc["State"] == "available"
                assert "VpcId" in vpc
                assert "CidrBlock" in vpc

        # Validate policy data integrity
        for segment in policy["segments"]:
            assert "name" in segment
            assert "require-attachment-acceptance" in segment
            assert "isolate-attachments" in segment
            if "allow-filter" in segment:
                # CIDR blocks should be valid format
                for cidr in segment["allow-filter"]:
                    assert "/" in cidr
                    parts = cidr.split("/")
                    assert len(parts) == 2
                    assert parts[1].isdigit()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fixture_edge_cases(self, hierarchical_topology) -> None:
        """Test fixture edge cases and boundary conditions."""
        topology = hierarchical_topology

        # Test hierarchy edge cases
        root = topology["hierarchy"]

        def validate_hierarchy_node(node, expected_level) -> None:
            assert node["level"] == expected_level
            assert len(node["vpcs"]) > 0  # Every node should have VPCs

            # Test parent-child relationships
            for child in node["children"]:
                assert child["parent_id"] == node["node_id"]
                assert child["level"] == expected_level + 1
                validate_hierarchy_node(child, expected_level + 1)

        validate_hierarchy_node(root, 1)

        # Test that all core networks have valid IDs
        for core_network in topology["core_networks"]:
            assert "CoreNetworkId" in core_network
            assert core_network["CoreNetworkId"].startswith("core-network-")
            assert core_network["State"] == "AVAILABLE"
            assert "Level" in core_network
            assert 1 <= core_network["Level"] <= topology["levels"]
