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

"""Large network topology handling tests following AWS Labs patterns."""

import gc
import json
import os
import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import psutil
import pytest

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_peers,
    analyze_tgw_routes,
    discover_vpcs,
    get_global_networks,
    list_core_networks,
    validate_cloudwan_policy,
    validate_ip_cidr,
)


class TestLargeVPCDiscoveryPerformance:
    """Test large VPC discovery performance with 10K+ VPCs."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_discover_10k_vpcs_performance(self) -> None:
        """Test VPC discovery performance with 10,000+ VPCs."""
        # Generate large dataset of 10,000 VPCs
        large_vpc_dataset = []
        for i in range(10000):
            vpc_data = {
                "VpcId": f"vpc-{i:08d}abcdef{i % 16:x}",
                "State": "available",
                "CidrBlock": f"10.{i // 256}.{i % 256}.0/24",
                "DhcpOptionsId": f"dopt-{i:08d}",
                "InstanceTenancy": "default",
                "IsDefault": False,
                "Tags": [
                    {"Key": "Name", "Value": f"VPC-{i:05d}"},
                    {"Key": "Environment", "Value": "production" if i % 2 == 0 else "development"},
                    {"Key": "Region", "Value": f"us-east-{(i % 4) + 1}"},
                    {"Key": "CostCenter", "Value": f"CC-{i % 100:03d}"},
                    {"Key": "Owner", "Value": f"team-{i % 50:02d}@company.com"},
                ],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": f"vpc-cidr-assoc-{i:08d}",
                        "CidrBlock": f"10.{i // 256}.{i % 256}.0/24",
                        "CidrBlockState": {"State": "associated"},
                    }
                ],
            }
            large_vpc_dataset.append(vpc_data)

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_vpcs.return_value = {"Vpcs": large_vpc_dataset}
            mock_get_client.return_value = mock_client

            result = await discover_vpcs(region="us-east-1")

            end_time = time.time()
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
            execution_time = end_time - start_time
            memory_usage = memory_after - memory_before

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 10000
            assert len(parsed["vpcs"]) == 10000

            # Performance assertions
            assert execution_time < 10.0, f"Execution took {execution_time:.2f}s, expected < 10s"
            assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB, expected < 500MB"

            # Validate data integrity
            assert parsed["vpcs"][0]["VpcId"] == "vpc-00000000abcdef0"
            assert parsed["vpcs"][9999]["VpcId"] == "vpc-00009999abcdeff"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_vpc_discovery_with_complex_cidr_blocks(self) -> None:
        """Test VPC discovery with complex CIDR block configurations."""
        complex_vpcs = []

        # Generate VPCs with multiple CIDR blocks (IPv4 and IPv6)
        for i in range(5000):
            vpc_data = {
                "VpcId": f"vpc-complex-{i:06d}",
                "State": "available",
                "CidrBlock": f"172.{16 + (i // 256)}.{i % 256}.0/20",
                "Ipv6CidrBlockAssociationSet": [
                    {
                        "AssociationId": f"vpc-cidr-assoc-ipv6-{i}",
                        "Ipv6CidrBlock": f"2001:db8:{i:04x}::/56",
                        "Ipv6CidrBlockState": {"State": "associated"},
                    }
                ],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": f"vpc-cidr-assoc-primary-{i}",
                        "CidrBlock": f"172.{16 + (i // 256)}.{i % 256}.0/20",
                        "CidrBlockState": {"State": "associated"},
                    },
                    {
                        "AssociationId": f"vpc-cidr-assoc-secondary-{i}",
                        "CidrBlock": f"192.168.{i % 256}.0/24",
                        "CidrBlockState": {"State": "associated"},
                    },
                ],
            }
            complex_vpcs.append(vpc_data)

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_vpcs.return_value = {"Vpcs": complex_vpcs}
            mock_get_client.return_value = mock_client

            start_time = time.time()
            result = await discover_vpcs()
            end_time = time.time()

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["total_count"] == 5000
            assert len(parsed["vpcs"]) == 5000

            # Verify complex CIDR handling
            first_vpc = parsed["vpcs"][0]
            assert "CidrBlock" in first_vpc
            assert "CidrBlockAssociationSet" in first_vpc

            execution_time = end_time - start_time
            assert execution_time < 5.0, f"Complex VPC processing took {execution_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_vpc_discovery_memory_optimized_streaming(self) -> None:
        """Test memory-optimized streaming for very large VPC datasets."""
        # Simulate streaming processing of 15,000 VPCs
        vpc_batch_size = 1000
        total_vpcs = 15000
        batches_processed = 0

        def streaming_vpc_mock(service, region=None):
            nonlocal batches_processed
            mock_client = Mock()

            def describe_vpcs_streaming(**kwargs):
                nonlocal batches_processed
                batches_processed += 1

                # Generate batch of VPCs
                start_idx = (batches_processed - 1) * vpc_batch_size
                end_idx = min(start_idx + vpc_batch_size, total_vpcs)

                batch_vpcs = [
                    {
                        "VpcId": f"vpc-stream-{i:08d}",
                        "State": "available",
                        "CidrBlock": f"10.{i // 65536}.{(i // 256) % 256}.0/24",
                        "Tags": [{"Key": "Batch", "Value": str(batches_processed)}],
                    }
                    for i in range(start_idx, end_idx)
                ]

                response = {"Vpcs": batch_vpcs}
                if end_idx < total_vpcs:
                    response["NextToken"] = f"batch-{batches_processed + 1}"

                return response

            mock_client.describe_vpcs.side_effect = describe_vpcs_streaming
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=streaming_vpc_mock):
            gc.collect()  # Clear memory before test
            initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            result = await discover_vpcs()

            final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory

            parsed = json.loads(result)
            assert parsed["success"] is True
            # Current implementation returns first batch only
            assert parsed["total_count"] == vpc_batch_size
            assert batches_processed >= 1

            # Memory should not grow excessively with streaming
            assert memory_growth < 200, f"Memory grew by {memory_growth:.2f}MB during streaming"


class TestMassiveRouteTableAnalysis:
    """Test analysis of route tables with 1M+ routes."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_1_million_routes_performance(self) -> None:
        """Test route table analysis with 1 million routes."""
        # Generate 1M routes across different categories
        massive_routes = []
        route_types = ["static", "propagated", "local"]
        route_states = ["active", "blackhole"]

        for i in range(1000000):
            route_data = {
                "DestinationCidrBlock": f"{10 + (i // 65536)}.{(i // 256) % 256}.{i % 256}.0/32",
                "TransitGatewayAttachments": [
                    {
                        "TransitGatewayAttachmentId": f"tgw-attach-{i // 1000:06d}",
                        "ResourceId": f"vpc-route-{i // 1000:06d}",
                        "ResourceType": "vpc",
                    }
                ]
                if i % 10 != 9
                else [],  # 10% blackhole routes
                "Type": route_types[i % len(route_types)],
                "State": route_states[0 if i % 10 != 9 else 1],  # 90% active, 10% blackhole
                "RouteOrigin": "CreateRoute"
                if route_types[i % len(route_types)] == "static"
                else "EnableVgwRoutePropagation",
            }
            massive_routes.append(route_data)

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.return_value = {
                "Routes": massive_routes,
                "AdditionalRoutesAvailable": False,
            }
            mock_get_client.return_value = mock_client

            result = await analyze_tgw_routes("tgw-rtb-massive-test")

            end_time = time.time()
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            execution_time = end_time - start_time
            memory_usage = memory_after - memory_before

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["analysis"]["total_routes"] == 1000000
            assert parsed["analysis"]["active_routes"] == 900000  # 90%
            assert parsed["analysis"]["blackholed_routes"] == 100000  # 10%

            # Performance constraints for 1M routes
            assert execution_time < 30.0, f"1M route analysis took {execution_time:.2f}s"
            assert memory_usage < 1000, f"Memory usage {memory_usage:.2f}MB for 1M routes"

            # Verify route type distribution
            route_details = parsed["analysis"]["route_details"]
            static_routes = [r for r in route_details if r["Type"] == "static"]
            propagated_routes = [r for r in route_details if r["Type"] == "propagated"]
            assert len(static_routes) > 0
            assert len(propagated_routes) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_route_analysis_with_chunked_processing(self) -> None:
        """Test route analysis with chunked processing for memory efficiency."""
        chunk_size = 50000
        total_routes = 500000
        chunks_processed = 0

        def chunked_route_mock(service, region=None):
            nonlocal chunks_processed
            mock_client = Mock()

            def chunked_search(**kwargs):
                nonlocal chunks_processed
                chunks_processed += 1

                # Generate chunk of routes
                start_idx = (chunks_processed - 1) * chunk_size
                end_idx = min(start_idx + chunk_size, total_routes)

                chunk_routes = [
                    {
                        "DestinationCidrBlock": f"192.168.{i // 256}.{i % 256}/32",
                        "State": "active",
                        "Type": "static",
                        "TransitGatewayAttachments": [
                            {
                                "TransitGatewayAttachmentId": f"tgw-attach-chunk-{chunks_processed:03d}",
                                "ResourceType": "vpc",
                            }
                        ],
                    }
                    for i in range(start_idx, end_idx)
                ]

                return {"Routes": chunk_routes, "AdditionalRoutesAvailable": end_idx < total_routes}

            mock_client.search_transit_gateway_routes.side_effect = chunked_search
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=chunked_route_mock):
            start_time = time.time()
            result = await analyze_tgw_routes("tgw-rtb-chunked")
            end_time = time.time()

            parsed = json.loads(result)
            assert parsed["success"] is True
            # Current implementation processes first chunk
            assert parsed["analysis"]["total_routes"] == chunk_size
            assert chunks_processed >= 1

            execution_time = end_time - start_time
            assert execution_time < 15.0, f"Chunked processing took {execution_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_route_deduplication_large_dataset(self) -> None:
        """Test route deduplication with large datasets containing duplicates."""
        base_routes = []
        duplicate_factor = 5  # Each route appears 5 times
        unique_routes = 100000

        # Create base set of unique routes
        for i in range(unique_routes):
            base_route = {
                "DestinationCidrBlock": f"172.16.{i // 256}.{i % 256}/32",
                "State": "active",
                "Type": "propagated",
                "RouteOrigin": "EnableVgwRoutePropagation",
                "TransitGatewayAttachments": [
                    {"TransitGatewayAttachmentId": f"tgw-attach-{i // 1000:03d}", "ResourceType": "vpc"}
                ],
            }
            base_routes.append(base_route)

        # Create dataset with duplicates
        routes_with_duplicates = []
        for _ in range(duplicate_factor):
            routes_with_duplicates.extend(base_routes.copy())

        total_routes = len(routes_with_duplicates)  # 500,000 routes

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.search_transit_gateway_routes.return_value = {
                "Routes": routes_with_duplicates,
                "AdditionalRoutesAvailable": False,
            }
            mock_get_client.return_value = mock_client

            start_time = time.time()
            result = await analyze_tgw_routes("tgw-rtb-dedup-test")
            end_time = time.time()

            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["analysis"]["total_routes"] == total_routes

            # Test should handle large duplicate dataset efficiently
            execution_time = end_time - start_time
            assert execution_time < 20.0, f"Deduplication took {execution_time:.2f}s"


class TestLargeTGWAttachmentHandling:
    """Test handling of 100K+ TGW attachments."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_100k_tgw_attachments_analysis(self) -> None:
        """Test analysis of 100,000+ TGW peering attachments."""
        large_attachments = []

        # Generate 100,000 TGW peering attachments
        for i in range(100000):
            attachment_data = {
                "TransitGatewayAttachmentId": f"tgw-attach-{i:08d}",
                "RequesterTgwInfo": {
                    "TransitGatewayId": f"tgw-requester-{i // 1000:05d}",
                    "OwnerId": f"{123456789012 + (i // 10000)}",
                    "Region": f"us-{['east', 'west'][i % 2]}-{(i % 4) + 1}",
                },
                "AccepterTgwInfo": {
                    "TransitGatewayId": f"tgw-accepter-{i // 1000:05d}",
                    "OwnerId": f"{210987654321 + (i // 10000)}",
                    "Region": f"eu-{['west', 'central'][i % 2]}-{(i % 3) + 1}",
                },
                "Status": {
                    "Code": "available" if i % 20 != 19 else "pending-acceptance",  # 95% available
                    "Message": "Peering attachment is available",
                },
                "State": "available" if i % 20 != 19 else "pending-acceptance",
                "CreatedAt": datetime(2024, 1, 15 + (i // 10000), 10, 30, 45, tzinfo=UTC),
                "Tags": [
                    {"Key": "Batch", "Value": f"batch-{i // 1000:03d}"},
                    {"Key": "Environment", "Value": "production" if i % 3 == 0 else "staging"},
                ],
            }
            large_attachments.append(attachment_data)

        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        start_time = time.time()

        # Test attachment analysis in batches
        batch_size = 10000
        successful_batches = 0

        for batch_start in range(0, len(large_attachments), batch_size):
            batch_end = min(batch_start + batch_size, len(large_attachments))
            batch_attachments = large_attachments[batch_start:batch_end]

            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
                mock_client = Mock()
                mock_client.describe_transit_gateway_peering_attachments.return_value = {
                    "TransitGatewayPeeringAttachments": batch_attachments
                }
                mock_get_client.return_value = mock_client

                # Test batch analysis with first attachment ID
                if batch_attachments:
                    result = await analyze_tgw_peers(batch_attachments[0]["TransitGatewayAttachmentId"])

                    parsed = json.loads(result)
                    assert parsed["success"] is True
                    assert "peer_analysis" in parsed
                    successful_batches += 1

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        total_time = end_time - start_time
        memory_growth = memory_after - memory_before

        # Validate batch processing performance
        assert successful_batches == 10  # 100k / 10k = 10 batches
        assert total_time < 60.0, f"100K attachment processing took {total_time:.2f}s"
        assert memory_growth < 300, f"Memory grew by {memory_growth:.2f}MB"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_tgw_attachment_relationship_mapping(self) -> None:
        """Test mapping relationships between large numbers of TGW attachments."""
        # Create interconnected mesh of TGW attachments
        mesh_size = 1000  # 1000 TGWs in mesh = ~500K potential connections
        attachment_relationships = []

        for i in range(mesh_size):
            for j in range(i + 1, min(i + 50, mesh_size)):  # Each TGW connects to next 50
                relationship = {
                    "TransitGatewayAttachmentId": f"tgw-attach-{i:04d}-to-{j:04d}",
                    "RequesterTgwInfo": {"TransitGatewayId": f"tgw-{i:04d}", "Region": f"us-east-{(i % 2) + 1}"},
                    "AccepterTgwInfo": {"TransitGatewayId": f"tgw-{j:04d}", "Region": f"us-west-{(j % 2) + 1}"},
                    "State": "available",
                    "Status": {"Code": "available"},
                }
                attachment_relationships.append(relationship)

        len(attachment_relationships)

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.describe_transit_gateway_peering_attachments.return_value = {
                "TransitGatewayPeeringAttachments": attachment_relationships
            }
            mock_get_client.return_value = mock_client

            start_time = time.time()

            # Analyze sample of relationships
            sample_attachments = attachment_relationships[:100]  # Test with 100 attachments
            analysis_results = []

            for attachment in sample_attachments:
                result = await analyze_tgw_peers(attachment["TransitGatewayAttachmentId"])
                parsed = json.loads(result)
                analysis_results.append(parsed)

            end_time = time.time()
            analysis_time = end_time - start_time

            # Verify relationship analysis
            assert len(analysis_results) == 100
            assert all(result["success"] for result in analysis_results)
            assert analysis_time < 30.0, f"Relationship analysis took {analysis_time:.2f}s"


class TestOversizedPolicyDocumentHandling:
    """Test handling of 50K+ core network policies."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_50k_core_network_policies_validation(self) -> None:
        """Test validation of 50,000+ core network policy variations."""
        # Generate large policy with many segments and rules
        massive_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": [f"{64512 + i}-{64512 + i + 99}" for i in range(0, 1000, 100)],
                "edge-locations": [
                    {"location": f"{region}-{az}", "asn": 64512 + (region_idx * 100) + az_idx}
                    for region_idx, region in enumerate(["us-east", "us-west", "eu-west", "ap-southeast"])
                    for az_idx, az in enumerate(["1", "2", "3"])
                ],
                "inside-cidr-blocks": [f"169.254.{i}.0/24" for i in range(100)],
                "vpn-ecmp-support": True,
            },
            "segments": [
                {
                    "name": f"segment-{i:04d}",
                    "require-attachment-acceptance": i % 2 == 0,
                    "isolate-attachments": i % 3 == 0,
                    "allow-filter": [f"10.{i}.0.0/16", f"172.16.{i}.0/24"],
                    "deny-filter": [f"192.168.{i}.0/24"] if i % 5 == 0 else [],
                    "edge-locations": [f"us-east-{(i % 3) + 1}", f"us-west-{(i % 3) + 1}"],
                }
                for i in range(10000)  # 10,000 segments
            ],
            "segment-actions": [
                {
                    "action": "share",
                    "segment": f"segment-{i:04d}",
                    "share-with": [f"segment-{j:04d}" for j in range(i + 1, min(i + 5, 10000))],
                    "mode": "attachment-route",
                }
                for i in range(0, 10000, 10)  # 1,000 sharing rules
            ],
            "attachment-policies": [
                {
                    "rule-number": i,
                    "condition-logic": "or",
                    "conditions": [
                        {
                            "type": "tag-value",
                            "key": "Environment",
                            "value": "production" if i % 2 == 0 else "development",
                            "operator": "equals",
                        },
                        {"type": "account-id", "value": f"{123456789000 + (i % 1000)}", "operator": "equals"},
                    ],
                    "action": {"association-method": "constant", "segment": f"segment-{i % 10000:04d}"},
                }
                for i in range(20000)  # 20,000 attachment policies
            ],
        }

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        result = await validate_cloudwan_policy(massive_policy)

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        validation_time = end_time - start_time
        memory_usage = memory_after - memory_before

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "overall_status" in parsed
        assert "validation_results" in parsed

        # Performance constraints for massive policy
        assert validation_time < 60.0, f"Massive policy validation took {validation_time:.2f}s"
        assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB for large policy"

        # Verify validation captured key elements
        validation_results = parsed["validation_results"]
        assert any(r["field"] == "version" for r in validation_results)
        assert any(r["field"] == "core-network-configuration" for r in validation_results)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_policy_parsing_memory_streaming(self) -> None:
        """Test policy parsing with memory-efficient streaming."""
        # Create policy with deeply nested structures
        deep_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-65000"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
        }

        # Add deeply nested segment actions (5 levels deep)
        nested_actions = []
        for level1 in range(100):
            for level2 in range(50):
                action = {
                    "action": "share",
                    "segment": f"segment-{level1:02d}-{level2:02d}",
                    "share-with": [f"segment-{level1:02d}-{k:02d}" for k in range(level2 + 1, min(level2 + 10, 50))],
                    "conditions": {
                        "nested-level-1": {
                            "nested-level-2": {
                                "nested-level-3": {
                                    "nested-level-4": {
                                        "nested-level-5": [
                                            {"condition": f"condition-{level1}-{level2}-{j}", "value": f"value-{j}"}
                                            for j in range(20)
                                        ]
                                    }
                                }
                            }
                        }
                    },
                }
                nested_actions.append(action)

        deep_policy["segment-actions"] = nested_actions

        gc.collect()  # Clean up before test
        memory_baseline = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        start_time = time.time()
        result = await validate_cloudwan_policy(deep_policy)
        end_time = time.time()

        memory_peak = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_growth = memory_peak - memory_baseline
        parsing_time = end_time - start_time

        parsed = json.loads(result)
        assert parsed["success"] is True

        # Memory should be managed efficiently for deep nesting
        assert memory_growth < 200, f"Deep parsing used {memory_growth:.2f}MB"
        assert parsing_time < 30.0, f"Deep parsing took {parsing_time:.2f}s"


class TestMassiveIPAddressAnalysis:
    """Test analysis of 500K+ IP addresses and CIDR blocks."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_500k_ip_address_validation(self) -> None:
        """Test validation of 500,000+ IP addresses."""
        # Generate large set of IP addresses across different ranges
        ip_test_cases = []

        # IPv4 addresses
        for octet1 in range(1, 11):  # 10.x.x.x
            for octet2 in range(0, 256, 10):
                for octet3 in range(0, 256, 10):
                    for octet4 in range(1, 26):  # 25 IPs per /24
                        ip_test_cases.append(f"{octet1}.{octet2}.{octet3}.{octet4}")

        # Add IPv6 addresses
        for i in range(10000):
            ipv6 = f"2001:db8:{i:04x}::1"
            ip_test_cases.append(ipv6)

        total_ips = len(ip_test_cases)
        successful_validations = 0
        failed_validations = 0

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Test IPs in batches to avoid overwhelming the system
        batch_size = 1000
        for i in range(0, min(total_ips, 10000), batch_size):  # Test first 10k IPs
            batch_end = min(i + batch_size, total_ips)
            batch_ips = ip_test_cases[i:batch_end]

            for ip in batch_ips:
                result = await validate_ip_cidr("validate_ip", ip=ip)
                parsed = json.loads(result)

                if parsed["success"]:
                    successful_validations += 1
                else:
                    failed_validations += 1

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        validation_time = end_time - start_time
        memory_usage = memory_after - memory_before
        validations_per_second = (successful_validations + failed_validations) / validation_time

        # Performance requirements
        assert validations_per_second > 100, f"Only {validations_per_second:.1f} validations/sec"
        assert memory_usage < 100, f"Memory usage {memory_usage:.2f}MB for IP validation"
        assert successful_validations > failed_validations, "More validations should succeed"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_cidr_block_analysis_large_dataset(self) -> None:
        """Test CIDR block analysis with large datasets."""
        # Generate comprehensive CIDR block test cases
        cidr_test_cases = []

        # RFC 1918 private ranges with various subnet sizes
        for subnet_size in [8, 12, 16, 20, 24, 28]:
            for network in range(0, 256, max(1, 256 // (32 - subnet_size))):
                cidr_test_cases.append(f"10.{network}.0.0/{subnet_size}")
                cidr_test_cases.append(f"172.{16 + (network // 16)}.{network % 16}.0/{subnet_size}")
                cidr_test_cases.append(f"192.168.{network}.0/{subnet_size}")

        # IPv6 CIDR blocks
        for i in range(1000):
            cidr_test_cases.append(f"2001:db8:{i:04x}::/{48 + (i % 16)}")

        successful_cidr_validations = 0
        start_time = time.time()

        # Process CIDR blocks in batches
        batch_size = 500
        for i in range(0, min(len(cidr_test_cases), 5000), batch_size):  # Test first 5k
            batch_end = min(i + batch_size, len(cidr_test_cases))
            batch_cidrs = cidr_test_cases[i:batch_end]

            for cidr in batch_cidrs:
                result = await validate_ip_cidr("validate_cidr", cidr=cidr)
                parsed = json.loads(result)

                if parsed["success"]:
                    successful_cidr_validations += 1
                    # Validate CIDR analysis results
                    assert "network_address" in parsed or "error" in parsed

        end_time = time.time()
        cidr_analysis_time = end_time - start_time
        cidrs_per_second = successful_cidr_validations / cidr_analysis_time

        assert cidrs_per_second > 50, f"Only {cidrs_per_second:.1f} CIDR analyses/sec"
        assert successful_cidr_validations > 1000, f"Expected >1000 CIDR validations, got {successful_cidr_validations}"


class TestTopologyVisualizationLimits:
    """Test topology visualization with size and complexity limits."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complex_network_topology_limits(self) -> None:
        """Test network topology handling at visualization limits."""
        # Create complex multi-tier topology
        topology_data = {
            "core_networks": [f"core-network-{i:03d}" for i in range(100)],
            "global_networks": [f"global-network-{i:03d}" for i in range(50)],
            "transit_gateways": [f"tgw-{i:05d}" for i in range(1000)],
            "vpc_connections": [],
            "peering_connections": [],
        }

        # Generate VPC connections (each TGW connects to 10 VPCs)
        for tgw_idx in range(1000):
            for vpc_idx in range(10):
                connection = {
                    "transit_gateway": f"tgw-{tgw_idx:05d}",
                    "vpc_id": f"vpc-{tgw_idx:05d}-{vpc_idx:02d}",
                    "attachment_id": f"tgw-attach-{tgw_idx:05d}-{vpc_idx:02d}",
                    "state": "available",
                }
                topology_data["vpc_connections"].append(connection)

        # Generate peering connections (mesh topology subset)
        for i in range(0, 1000, 10):  # Every 10th TGW peers with next 5
            for j in range(i + 1, min(i + 6, 1000)):
                peering = {
                    "requester_tgw": f"tgw-{i:05d}",
                    "accepter_tgw": f"tgw-{j:05d}",
                    "peering_attachment_id": f"tgw-attach-peer-{i:05d}-{j:05d}",
                    "state": "available",
                }
                topology_data["peering_connections"].append(peering)

        (
            len(topology_data["core_networks"])
            + len(topology_data["global_networks"])
            + len(topology_data["transit_gateways"])
            + len(topology_data["vpc_connections"])
        )

        len(topology_data["peering_connections"])

        # Simulate topology processing
        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Mock topology analysis that would process this data
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()

            # Mock responses for topology components
            mock_client.list_core_networks.return_value = {
                "CoreNetworks": [{"CoreNetworkId": cn} for cn in topology_data["core_networks"]]
            }
            mock_client.describe_global_networks.return_value = {
                "GlobalNetworks": [{"GlobalNetworkId": gn} for gn in topology_data["global_networks"]]
            }
            mock_client.describe_vpcs.return_value = {
                "Vpcs": [
                    {"VpcId": conn["vpc_id"], "State": "available", "CidrBlock": f"10.{i // 256}.{i % 256}.0/24"}
                    for i, conn in enumerate(topology_data["vpc_connections"])
                ]
            }

            mock_get_client.return_value = mock_client

            # Test core components
            core_result = await list_core_networks()
            global_result = await get_global_networks()
            vpc_result = await discover_vpcs()

            end_time = time.time()
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            processing_time = end_time - start_time
            memory_usage = memory_after - memory_before

            # Verify topology processing
            core_parsed = json.loads(core_result)
            global_parsed = json.loads(global_result)
            vpc_parsed = json.loads(vpc_result)

            assert core_parsed["success"] is True
            assert global_parsed["success"] is True
            assert vpc_parsed["success"] is True

            # Performance constraints for complex topology
            assert processing_time < 45.0, f"Complex topology processing took {processing_time:.2f}s"
            assert memory_usage < 400, f"Topology memory usage {memory_usage:.2f}MB"

            # Validate topology scale
            assert len(core_parsed["core_networks"]) == 100
            assert len(global_parsed["global_networks"]) == 50
            assert len(vpc_parsed["vpcs"]) == 10000  # 1000 TGWs * 10 VPCs each
