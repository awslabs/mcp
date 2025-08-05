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

"""Advanced test fixtures for AWS CloudWAN MCP Server testing following AWS Labs patterns."""

import random
from datetime import UTC, datetime
from typing import Any

import pytest


class NetworkTopologyFixtures:
    """Generate complex network topology fixtures for testing."""

    @staticmethod
    def generate_enterprise_hub_spoke_topology(regions: int = 5, spokes_per_region: int = 10) -> dict[str, Any]:
        """Generate enterprise hub-and-spoke network topology."""
        topology = {
            "topology_type": "hub_spoke",
            "regions": [],
            "global_network": {
                "GlobalNetworkId": "global-network-enterprise-hub-spoke",
                "Description": "Enterprise hub-and-spoke topology",
                "State": "AVAILABLE",
            },
            "core_networks": [],
            "transit_gateways": {},
            "vpc_attachments": {},
            "peering_connections": [],
        }

        region_names = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"][:regions]

        for i, region in enumerate(region_names):
            topology["regions"].append(region)

            # Create core network per region
            core_network = {
                "CoreNetworkId": f"core-network-{region}",
                "GlobalNetworkId": topology["global_network"]["GlobalNetworkId"],
                "State": "AVAILABLE",
                "Description": f"Core network for {region}",
                "PolicyVersionId": "1",
                "Region": region,
                "Segments": ["production", "staging", "development"],
            }
            topology["core_networks"].append(core_network)

            # Create hub TGW for region
            hub_tgw = {
                "TransitGatewayId": f"tgw-hub-{region}",
                "State": "available",
                "Description": f"Hub transit gateway for {region}",
                "AmazonSideAsn": 64512 + i,
                "DefaultRouteTableId": f"tgw-rtb-hub-{region}",
                "RouteTableIds": [f"tgw-rtb-hub-{region}", f"tgw-rtb-spoke-{region}"],
            }
            topology["transit_gateways"][region] = [hub_tgw]

            # Create spoke VPCs and TGWs
            region_vpcs = []
            for spoke_idx in range(spokes_per_region):
                spoke_vpc = {
                    "VpcId": f"vpc-spoke-{region}-{spoke_idx:03d}",
                    "State": "available",
                    "CidrBlock": f"10.{i * 50 + spoke_idx}.0.0/16",
                    "Region": region,
                    "Tags": [
                        {"Key": "Name", "Value": f"Spoke VPC {spoke_idx} - {region}"},
                        {"Key": "Environment", "Value": ["production", "staging", "development"][spoke_idx % 3]},
                        {"Key": "Workload", "Value": f"workload-{spoke_idx:03d}"},
                        {"Key": "CostCenter", "Value": f"cc-{spoke_idx % 10:03d}"},
                    ],
                }
                region_vpcs.append(spoke_vpc)

            topology["vpc_attachments"][region] = region_vpcs

            # Create cross-region peering connections
            if i > 0:
                # Peer with previous region (creating a chain)
                prev_region = region_names[i - 1]
                peering = {
                    "TransitGatewayPeeringAttachmentId": f"tgw-attach-peer-{prev_region}-{region}",
                    "RequesterTgwInfo": {
                        "TransitGatewayId": f"tgw-hub-{prev_region}",
                        "Region": prev_region,
                        "OwnerId": "123456789012",
                    },
                    "AccepterTgwInfo": {
                        "TransitGatewayId": f"tgw-hub-{region}",
                        "Region": region,
                        "OwnerId": "123456789012",
                    },
                    "State": "available",
                    "Status": {"Code": "available"},
                }
                topology["peering_connections"].append(peering)

        return topology

    @staticmethod
    def generate_mesh_topology(regions: int = 4, vpcs_per_region: int = 8) -> dict[str, Any]:
        """Generate full mesh network topology."""
        topology = {
            "topology_type": "full_mesh",
            "regions": [],
            "global_network": {
                "GlobalNetworkId": "global-network-full-mesh",
                "Description": "Full mesh network topology",
                "State": "AVAILABLE",
            },
            "core_networks": [],
            "transit_gateways": {},
            "vpc_attachments": {},
            "peering_connections": [],
        }

        region_names = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"][:regions]

        for i, region in enumerate(region_names):
            topology["regions"].append(region)

            # Create core network
            core_network = {
                "CoreNetworkId": f"core-network-mesh-{region}",
                "GlobalNetworkId": topology["global_network"]["GlobalNetworkId"],
                "State": "AVAILABLE",
                "PolicyVersionId": "2",
                "Region": region,
                "Segments": ["shared", "isolated", "dmz"],
            }
            topology["core_networks"].append(core_network)

            # Create TGW
            tgw = {
                "TransitGatewayId": f"tgw-mesh-{region}",
                "State": "available",
                "AmazonSideAsn": 65000 + i,
                "DefaultRouteTableId": f"tgw-rtb-mesh-{region}",
                "PropagationDefaultRouteTableId": f"tgw-rtb-prop-{region}",
                "AssociationDefaultRouteTableId": f"tgw-rtb-assoc-{region}",
            }
            topology["transit_gateways"][region] = [tgw]

            # Create VPCs with different patterns
            region_vpcs = []
            for vpc_idx in range(vpcs_per_region):
                vpc = {
                    "VpcId": f"vpc-mesh-{region}-{vpc_idx:03d}",
                    "State": "available",
                    "CidrBlock": f"172.{16 + i}.{vpc_idx}.0/24",
                    "Region": region,
                    "Tags": [
                        {"Key": "Name", "Value": f"Mesh VPC {vpc_idx} - {region}"},
                        {"Key": "Segment", "Value": ["shared", "isolated", "dmz"][vpc_idx % 3]},
                        {"Key": "Tier", "Value": ["web", "app", "db"][vpc_idx % 3]},
                    ],
                }
                region_vpcs.append(vpc)
            topology["vpc_attachments"][region] = region_vpcs

        # Create full mesh peering connections
        for i, region1 in enumerate(region_names):
            for j, region2 in enumerate(region_names):
                if i < j:  # Avoid duplicate connections
                    peering = {
                        "TransitGatewayPeeringAttachmentId": f"tgw-attach-mesh-{region1}-{region2}",
                        "RequesterTgwInfo": {
                            "TransitGatewayId": f"tgw-mesh-{region1}",
                            "Region": region1,
                            "OwnerId": "123456789012",
                        },
                        "AccepterTgwInfo": {
                            "TransitGatewayId": f"tgw-mesh-{region2}",
                            "Region": region2,
                            "OwnerId": "123456789012",
                        },
                        "State": "available",
                        "Status": {"Code": "available"},
                    }
                    topology["peering_connections"].append(peering)

        return topology

    @staticmethod
    def generate_hierarchical_topology(levels: int = 3, branches_per_level: int = 4) -> dict[str, Any]:
        """Generate hierarchical network topology."""
        topology = {
            "topology_type": "hierarchical",
            "levels": levels,
            "branches_per_level": branches_per_level,
            "global_network": {
                "GlobalNetworkId": "global-network-hierarchical",
                "Description": "Hierarchical network topology",
                "State": "AVAILABLE",
            },
            "hierarchy": {},
            "core_networks": [],
            "routing_policies": [],
        }

        def create_hierarchical_node(level: int, parent_id: str = None, branch_idx: int = 0):
            if level > levels:
                return None

            node_id = f"level-{level}-branch-{branch_idx:03d}"
            if parent_id:
                node_id = f"{parent_id}-{node_id}"

            node = {
                "node_id": node_id,
                "level": level,
                "parent_id": parent_id,
                "core_network_id": f"core-network-{node_id}",
                "children": [],
                "vpcs": [],
            }

            # Create core network for this node
            core_network = {
                "CoreNetworkId": node["core_network_id"],
                "GlobalNetworkId": topology["global_network"]["GlobalNetworkId"],
                "State": "AVAILABLE",
                "Level": level,
                "ParentCoreNetworkId": f"core-network-{parent_id}" if parent_id else None,
                "PolicyVersionId": str(level),
            }
            topology["core_networks"].append(core_network)

            # Create VPCs for this level
            vpcs_at_level = max(1, 2 ** (levels - level))  # More VPCs at lower levels
            for vpc_idx in range(vpcs_at_level):
                vpc = {
                    "VpcId": f"vpc-{node_id}-{vpc_idx:03d}",
                    "State": "available",
                    "CidrBlock": f"10.{level}.{branch_idx * 10 + vpc_idx}.0/24",
                    "Level": level,
                    "NodeId": node_id,
                }
                node["vpcs"].append(vpc)

            # Create child nodes
            if level < levels:
                for child_idx in range(branches_per_level):
                    child = create_hierarchical_node(level + 1, node_id, child_idx)
                    if child:
                        node["children"].append(child)

            return node

        # Build hierarchy starting from root
        topology["hierarchy"] = create_hierarchical_node(1)

        return topology


class PolicyFixtures:
    """Generate complex CloudWAN policy fixtures."""

    @staticmethod
    def generate_enterprise_policy(segments: int = 10, rules: int = 50) -> dict[str, Any]:
        """Generate enterprise-grade CloudWAN policy."""
        policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": [f"{64512 + i * 100}-{64512 + (i + 1) * 100 - 1}" for i in range(5)],
                "edge-locations": [],
                "inside-cidr-blocks": ["169.254.0.0/16"],
                "vpn-ecmp-support": True,
            },
            "segments": [],
            "segment-actions": [],
            "attachment-policies": [],
        }

        # Generate edge locations for major AWS regions
        aws_regions = [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-central-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
        ]

        for i, region in enumerate(aws_regions):
            edge_location = {"location": region, "asn": 64512 + i * 10, "inside-cidr-blocks": [f"169.254.{i}.0/24"]}
            policy["core-network-configuration"]["edge-locations"].append(edge_location)

        # Generate segments with enterprise patterns
        segment_types = [
            {"name": "production", "isolation": False, "acceptance": False},
            {"name": "staging", "isolation": True, "acceptance": True},
            {"name": "development", "isolation": True, "acceptance": True},
            {"name": "shared-services", "isolation": False, "acceptance": False},
            {"name": "dmz", "isolation": True, "acceptance": True},
            {"name": "management", "isolation": True, "acceptance": True},
        ]

        for i in range(segments):
            base_segment = segment_types[i % len(segment_types)]
            segment = {
                "name": f"{base_segment['name']}-{i // len(segment_types) + 1:02d}",
                "description": f"Enterprise segment for {base_segment['name']} workloads instance {i + 1}",
                "require-attachment-acceptance": base_segment["acceptance"],
                "isolate-attachments": base_segment["isolation"],
                "allow-filter": [f"10.{i}.0.0/16", f"172.{16 + i}.0.0/12"],
                "deny-filter": ["192.168.0.0/16"] if base_segment["isolation"] else [],
                "edge-locations": aws_regions[: (i % 5) + 1],  # Varying edge location coverage
            }
            policy["segments"].append(segment)

        # Generate segment actions (sharing rules)
        for i in range(segments):
            segment_name = policy["segments"][i]["name"]

            # Create sharing rules based on segment type
            if "production" in segment_name:
                # Production segments share with shared-services
                shared_segments = [s["name"] for s in policy["segments"] if "shared-services" in s["name"]]
            elif "shared-services" in segment_name:
                # Shared services can be accessed by all
                shared_segments = [s["name"] for s in policy["segments"] if s["name"] != segment_name][:5]
            else:
                # Other segments share within their type
                shared_segments = [
                    s["name"]
                    for s in policy["segments"]
                    if s["name"] != segment_name and s["name"].split("-")[0] == segment_name.split("-")[0]
                ][:3]

            if shared_segments:
                segment_action = {
                    "action": "share",
                    "segment": segment_name,
                    "share-with": shared_segments,
                    "mode": "attachment-route",
                }
                policy["segment-actions"].append(segment_action)

        # Generate attachment policies
        for i in range(rules):
            rule = {
                "rule-number": i + 1,
                "description": f"Enterprise attachment rule {i + 1}",
                "condition-logic": "and" if i % 2 == 0 else "or",
                "conditions": [
                    {
                        "type": "tag-value",
                        "key": "Environment",
                        "value": ["production", "staging", "development"][i % 3],
                        "operator": "equals",
                    },
                    {"type": "account-id", "value": f"{123456789000 + (i % 50)}", "operator": "equals"},
                    {"type": "tag-exists", "key": "CostCenter", "operator": "exists"},
                ],
                "action": {
                    "association-method": "constant",
                    "segment": policy["segments"][i % len(policy["segments"])]["name"],
                    "require-acceptance": i % 4 == 0,  # 25% require acceptance
                },
            }
            policy["attachment-policies"].append(rule)

        return policy

    @staticmethod
    def generate_security_focused_policy() -> dict[str, Any]:
        """Generate security-focused CloudWAN policy with strict isolation."""
        policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555", "65000-65010"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}, {"location": "us-west-2", "asn": 64513}],
                "inside-cidr-blocks": ["169.254.0.0/16"],
            },
            "segments": [
                {
                    "name": "pci-compliant",
                    "description": "PCI DSS compliant segment with strict isolation",
                    "require-attachment-acceptance": True,
                    "isolate-attachments": True,
                    "allow-filter": ["10.1.0.0/16"],
                    "deny-filter": ["0.0.0.0/0"],  # Deny all by default
                    "edge-locations": ["us-east-1"],
                },
                {
                    "name": "hipaa-compliant",
                    "description": "HIPAA compliant segment for healthcare data",
                    "require-attachment-acceptance": True,
                    "isolate-attachments": True,
                    "allow-filter": ["10.2.0.0/16"],
                    "deny-filter": ["192.168.0.0/16", "172.16.0.0/12"],
                    "edge-locations": ["us-east-1"],
                },
                {
                    "name": "sox-compliant",
                    "description": "SOX compliant segment for financial data",
                    "require-attachment-acceptance": True,
                    "isolate-attachments": True,
                    "allow-filter": ["10.3.0.0/16"],
                    "deny-filter": ["0.0.0.0/0"],
                    "edge-locations": ["us-east-1", "us-west-2"],
                },
                {
                    "name": "security-tools",
                    "description": "Security tools and monitoring segment",
                    "require-attachment-acceptance": True,
                    "isolate-attachments": False,
                    "allow-filter": ["10.10.0.0/16"],
                    "edge-locations": ["us-east-1", "us-west-2"],
                },
            ],
            "segment-actions": [
                {
                    "action": "share",
                    "segment": "security-tools",
                    "share-with": ["pci-compliant", "hipaa-compliant", "sox-compliant"],
                    "mode": "single-route",
                }
            ],
            "attachment-policies": [
                {
                    "rule-number": 1,
                    "description": "PCI compliant resources",
                    "condition-logic": "and",
                    "conditions": [
                        {"type": "tag-value", "key": "Compliance", "value": "PCI", "operator": "equals"},
                        {"type": "tag-value", "key": "DataClassification", "value": "Restricted", "operator": "equals"},
                    ],
                    "action": {
                        "association-method": "constant",
                        "segment": "pci-compliant",
                        "require-acceptance": True,
                    },
                },
                {
                    "rule-number": 2,
                    "description": "HIPAA compliant resources",
                    "condition-logic": "and",
                    "conditions": [
                        {"type": "tag-value", "key": "Compliance", "value": "HIPAA", "operator": "equals"},
                        {"type": "tag-value", "key": "DataType", "value": "PHI", "operator": "equals"},
                    ],
                    "action": {
                        "association-method": "constant",
                        "segment": "hipaa-compliant",
                        "require-acceptance": True,
                    },
                },
            ],
        }

        return policy


class PerformanceTestDatasets:
    """Generate performance testing datasets."""

    @staticmethod
    def generate_large_route_dataset(route_count: int = 100000) -> list[dict[str, Any]]:
        """Generate large route dataset for performance testing."""
        routes = []

        route_types = ["static", "propagated", "local"]
        route_states = ["active", "blackhole"]

        for i in range(route_count):
            route = {
                "DestinationCidrBlock": f"{10 + (i // 65536)}.{(i // 256) % 256}.{i % 256}.0/32",
                "TransitGatewayAttachments": [
                    {
                        "TransitGatewayAttachmentId": f"tgw-attach-{i // 1000:06d}",
                        "ResourceId": f"vpc-{i // 1000:06d}",
                        "ResourceType": "vpc",
                    }
                ]
                if i % 10 != 9
                else [],  # 10% blackhole routes
                "Type": route_types[i % len(route_types)],
                "State": route_states[0 if i % 10 != 9 else 1],
                "RouteOrigin": "CreateRoute"
                if route_types[i % len(route_types)] == "static"
                else "EnableVgwRoutePropagation",
            }
            routes.append(route)

        return routes

    @staticmethod
    def generate_vpc_dataset(vpc_count: int = 10000) -> list[dict[str, Any]]:
        """Generate large VPC dataset for performance testing."""
        vpcs = []

        for i in range(vpc_count):
            vpc = {
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
                ],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": f"vpc-cidr-assoc-{i:08d}",
                        "CidrBlock": f"10.{i // 256}.{i % 256}.0/24",
                        "CidrBlockState": {"State": "associated"},
                    }
                ],
            }
            vpcs.append(vpc)

        return vpcs

    @staticmethod
    def generate_tgw_attachments_dataset(attachment_count: int = 50000) -> list[dict[str, Any]]:
        """Generate large TGW attachments dataset."""
        attachments = []

        for i in range(attachment_count):
            attachment = {
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
                    "Code": "available" if i % 20 != 19 else "pending-acceptance",
                    "Message": "Peering attachment is available",
                },
                "State": "available" if i % 20 != 19 else "pending-acceptance",
                "CreatedAt": datetime(2024, 1, 15 + (i // 10000), 10, 30, 45, tzinfo=UTC),
                "Tags": [
                    {"Key": "Batch", "Value": f"batch-{i // 1000:03d}"},
                    {"Key": "Environment", "Value": "production" if i % 3 == 0 else "staging"},
                ],
            }
            attachments.append(attachment)

        return attachments


class MultiRegionConfigurationFixtures:
    """Generate multi-region configuration fixtures."""

    @staticmethod
    def generate_global_deployment_config() -> dict[str, Any]:
        """Generate global multi-region deployment configuration."""
        config = {
            "deployment_type": "global",
            "primary_region": "us-east-1",
            "secondary_regions": ["us-west-2", "eu-west-1", "ap-southeast-1"],
            "disaster_recovery_region": "us-west-2",
            "regions": {},
        }

        all_regions = [config["primary_region"]] + config["secondary_regions"]

        for i, region in enumerate(all_regions):
            region_config = {
                "region_name": region,
                "is_primary": region == config["primary_region"],
                "availability_zones": [f"{region}a", f"{region}b", f"{region}c"],
                "core_networks": [
                    {
                        "CoreNetworkId": f"core-network-{region}",
                        "GlobalNetworkId": "global-network-worldwide",
                        "State": "AVAILABLE",
                        "PolicyVersionId": "1",
                    }
                ],
                "transit_gateways": [
                    {
                        "TransitGatewayId": f"tgw-{region}",
                        "State": "available",
                        "AmazonSideAsn": 64512 + i,
                        "DefaultRouteTableId": f"tgw-rtb-{region}",
                        "Description": f"Primary TGW for {region}",
                    }
                ],
                "vpcs": [],
                "route_tables": [
                    {
                        "RouteTableId": f"tgw-rtb-{region}",
                        "TransitGatewayId": f"tgw-{region}",
                        "State": "available",
                        "DefaultAssociationRouteTable": True,
                        "DefaultPropagationRouteTable": True,
                    }
                ],
            }

            # Generate VPCs per region
            vpcs_per_region = 5 if region == config["primary_region"] else 3
            for vpc_idx in range(vpcs_per_region):
                vpc = {
                    "VpcId": f"vpc-{region}-{vpc_idx:03d}",
                    "State": "available",
                    "CidrBlock": f"10.{i * 10 + vpc_idx}.0.0/16",
                    "Region": region,
                    "AvailabilityZone": region_config["availability_zones"][
                        vpc_idx % len(region_config["availability_zones"])
                    ],
                    "Tags": [
                        {"Key": "Name", "Value": f"Global VPC {vpc_idx} - {region}"},
                        {"Key": "Region", "Value": region},
                        {"Key": "Tier", "Value": ["web", "app", "db"][vpc_idx % 3]},
                    ],
                }
                region_config["vpcs"].append(vpc)

            config["regions"][region] = region_config

        # Add cross-region connections
        config["cross_region_connections"] = []
        primary = config["primary_region"]
        for secondary in config["secondary_regions"]:
            connection = {
                "ConnectionType": "TGWPeering",
                "RequesterRegion": primary,
                "AccepterRegion": secondary,
                "RequesterTGW": f"tgw-{primary}",
                "AccepterTGW": f"tgw-{secondary}",
                "State": "available",
            }
            config["cross_region_connections"].append(connection)

        return config

    @staticmethod
    def generate_disaster_recovery_config() -> dict[str, Any]:
        """Generate disaster recovery configuration."""
        config = {
            "deployment_type": "disaster_recovery",
            "primary_site": {
                "region": "us-east-1",
                "availability_zones": ["us-east-1a", "us-east-1b", "us-east-1c"],
                "rto": 300,  # 5 minutes
                "rpo": 900,  # 15 minutes
            },
            "dr_site": {
                "region": "us-west-2",
                "availability_zones": ["us-west-2a", "us-west-2b", "us-west-2c"],
                "rto": 600,  # 10 minutes
                "rpo": 3600,  # 1 hour
            },
            "replication": {
                "method": "async",
                "frequency": 300,  # 5 minutes
                "backup_retention": 30,  # 30 days
            },
            "failover_automation": {
                "enabled": True,
                "health_checks": ["core_network_connectivity", "transit_gateway_status", "vpc_routing_health"],
            },
        }

        # Generate resources for both sites
        for site_name, site_config in [("primary_site", config["primary_site"]), ("dr_site", config["dr_site"])]:
            region = site_config["region"]

            # Core network resources
            site_config["resources"] = {
                "core_networks": [
                    {
                        "CoreNetworkId": f"core-network-{region}-dr",
                        "GlobalNetworkId": "global-network-dr",
                        "State": "AVAILABLE",
                        "Description": f"DR core network for {region}",
                    }
                ],
                "transit_gateways": [
                    {
                        "TransitGatewayId": f"tgw-dr-{region}",
                        "State": "available",
                        "Description": f"DR transit gateway for {region}",
                        "AmazonSideAsn": 64512 if site_name == "primary_site" else 64513,
                    }
                ],
                "vpcs": [],
            }

            # Generate DR VPCs
            for i, az in enumerate(site_config["availability_zones"]):
                vpc = {
                    "VpcId": f"vpc-dr-{region}-{i:03d}",
                    "State": "available",
                    "CidrBlock": f"10.{100 if site_name == 'primary_site' else 200}.{i}.0/24",
                    "AvailabilityZone": az,
                    "Tags": [
                        {"Key": "Name", "Value": f"DR VPC {i} - {region}"},
                        {"Key": "DR-Site", "Value": site_name},
                        {"Key": "Criticality", "Value": "High"},
                    ],
                }
                site_config["resources"]["vpcs"].append(vpc)

        return config


# Pytest fixtures using the generator classes above


@pytest.fixture(scope="session")
def enterprise_hub_spoke_topology():
    """Fixture providing enterprise hub-and-spoke topology."""
    return NetworkTopologyFixtures.generate_enterprise_hub_spoke_topology(regions=5, spokes_per_region=10)


@pytest.fixture(scope="session")
def full_mesh_topology():
    """Fixture providing full mesh topology."""
    return NetworkTopologyFixtures.generate_mesh_topology(regions=4, vpcs_per_region=8)


@pytest.fixture(scope="session")
def hierarchical_topology():
    """Fixture providing hierarchical topology."""
    return NetworkTopologyFixtures.generate_hierarchical_topology(levels=3, branches_per_level=4)


@pytest.fixture(scope="session")
def enterprise_policy():
    """Fixture providing enterprise CloudWAN policy."""
    return PolicyFixtures.generate_enterprise_policy(segments=10, rules=50)


@pytest.fixture(scope="session")
def security_policy():
    """Fixture providing security-focused CloudWAN policy."""
    return PolicyFixtures.generate_security_focused_policy()


@pytest.fixture(scope="session")
def large_route_dataset():
    """Fixture providing large route dataset for performance testing."""
    return PerformanceTestDatasets.generate_large_route_dataset(route_count=100000)


@pytest.fixture(scope="session")
def large_vpc_dataset():
    """Fixture providing large VPC dataset for performance testing."""
    return PerformanceTestDatasets.generate_vpc_dataset(vpc_count=10000)


@pytest.fixture(scope="session")
def global_deployment_config():
    """Fixture providing global multi-region deployment configuration."""
    return MultiRegionConfigurationFixtures.generate_global_deployment_config()


@pytest.fixture(scope="session")
def disaster_recovery_config():
    """Fixture providing disaster recovery configuration."""
    return MultiRegionConfigurationFixtures.generate_disaster_recovery_config()


@pytest.fixture(scope="function")
def random_network_topology():
    """Fixture providing randomly generated network topology for each test."""
    topology_types = ["hub_spoke", "mesh", "hierarchical"]
    topology_type = random.choice(topology_types)

    if topology_type == "hub_spoke":
        return NetworkTopologyFixtures.generate_enterprise_hub_spoke_topology(
            regions=random.randint(2, 6), spokes_per_region=random.randint(3, 15)
        )
    elif topology_type == "mesh":
        return NetworkTopologyFixtures.generate_mesh_topology(
            regions=random.randint(2, 5), vpcs_per_region=random.randint(2, 10)
        )
    else:  # hierarchical
        return NetworkTopologyFixtures.generate_hierarchical_topology(
            levels=random.randint(2, 4), branches_per_level=random.randint(2, 6)
        )
