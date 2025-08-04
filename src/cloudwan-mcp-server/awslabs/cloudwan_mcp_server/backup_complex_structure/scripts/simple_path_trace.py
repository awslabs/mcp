#!/usr/bin/env python3
"""
Simple Network Path Tracing Script using foundation script patterns.

This script traces network paths between source and destination IPs using
the proven patterns from existing foundation scripts.
"""

import boto3
import json
import ipaddress
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Package-based imports - no need to modify path when using uvx

# Set required environment variables for this customer environment
os.environ["AWS_PROFILE"] = "taylaand+customer-cloudwan-Admin"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
os.environ["AWS_ENDPOINT_URL_NETWORKMANAGER"] = "https://networkmanageromega.us-west-2.amazonaws.com"


console = Console()


class SimpleNetworkTracer:
    """Simple network path tracer using foundation script patterns."""
    
    def __init__(self):
        """Initialize the tracer."""
        # Print current environment setup
        aws_profile = os.environ.get("AWS_PROFILE")
        aws_region = os.environ.get("AWS_REGION")
        custom_endpoint = os.environ.get("AWS_ENDPOINT_URL_NETWORKMANAGER")
        
        console.print(f"✨ Using AWS profile: {aws_profile}", style="yellow")
        console.print(f"✨ Using AWS region: {aws_region}", style="yellow")
        console.print(f"✨ Using custom Network Manager endpoint: {custom_endpoint}", style="yellow")
        
        self.session = boto3.Session()
        
        # Regions for EC2 discovery (search in eu-west-1 and eu-west-2)
        self.regions = ["eu-west-1", "eu-west-2"]
        
        console.print("🔍 Simple Network Path Tracer initialized", style="green")
        console.print(f"Configured regions: {', '.join(self.regions)}", style="blue")
    
    def find_ip_in_region(self, region: str, ip_address: str) -> dict:
        """Find IP address context in a specific region."""
        try:
            ec2_client = self.session.client('ec2', region_name=region)
            
            # Search for ENIs with this private IP
            response = ec2_client.describe_network_interfaces(
                Filters=[
                    {"Name": "private-ip-address", "Values": [ip_address]}
                ]
            )
            
            if response.get("NetworkInterfaces"):
                eni = response["NetworkInterfaces"][0]
                
                # Get VPC and subnet info
                vpc_id = eni.get("VpcId")
                subnet_id = eni.get("SubnetId")
                
                # Get route tables for this subnet
                route_tables = self.get_route_tables_for_subnet(ec2_client, subnet_id)
                
                # Get VPC details
                vpc_info = self.get_vpc_details(ec2_client, vpc_id)
                
                # Get CloudWAN segment information
                segment_info = self.get_cloudwan_segment_for_vpc(vpc_id, region)
                
                return {
                    "found": True,
                    "region": region,
                    "vpc_id": vpc_id,
                    "subnet_id": subnet_id,
                    "eni_id": eni.get("NetworkInterfaceId"),
                    "availability_zone": eni.get("AvailabilityZone"),
                    "description": eni.get("Description", ""),
                    "status": eni.get("Status"),
                    "route_tables": route_tables,
                    "vpc_info": vpc_info,
                    "segment_info": segment_info
                }
            
            return {"found": False, "region": region}
            
        except Exception as e:
            console.print(f"❌ Error searching for IP {ip_address} in region {region}: {e}", style="red")
            return {"found": False, "region": region, "error": str(e)}
    
    def get_vpc_details(self, ec2_client, vpc_id: str) -> dict:
        """Get VPC details."""
        try:
            response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
            if response.get("Vpcs"):
                vpc = response["Vpcs"][0]
                return {
                    "cidr_block": vpc.get("CidrBlock"),
                    "state": vpc.get("State"),
                    "is_default": vpc.get("IsDefault", False),
                    "tags": {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])}
                }
        except Exception as e:
            console.print(f"Warning: Could not get VPC details for {vpc_id}: {e}", style="yellow")
        
        return {}
    
    def get_cloudwan_segment_for_vpc(self, vpc_id: str, region: str) -> dict:
        """Find which CloudWAN segment a VPC belongs to."""
        try:
            # Use the session which has the custom endpoint configured
            # NetworkManager API is always in us-west-2 for this environment
            nm_client = self.session.client('networkmanager', region_name='us-west-2')
            
            # First, get all core networks
            core_networks_response = nm_client.list_core_networks()
            
            for core_network in core_networks_response.get("CoreNetworks", []):
                core_network_id = core_network.get("CoreNetworkId")
                
                try:
                    # Get VPC attachments for this core network
                    attachments_response = nm_client.list_attachments(
                        CoreNetworkId=core_network_id,
                        AttachmentType="VPC"
                    )
                    
                    # Check if our VPC is attached
                    for attachment in attachments_response.get("Attachments", []):
                        if (attachment.get("ResourceArn", "").endswith(f"/{vpc_id}") and 
                            attachment.get("EdgeLocation") == region):
                            
                            # Get segment name from attachment
                            segment_name = attachment.get("SegmentName", "Unknown")
                            attachment_id = attachment.get("AttachmentId")
                            state = attachment.get("State")
                            
                            return {
                                "segment_name": segment_name,
                                "core_network_id": core_network_id,
                                "attachment_id": attachment_id,
                                "state": state,
                                "edge_location": region,
                                "found": True
                            }
                
                except Exception as e:
                    console.print(f"Warning: Could not get attachments for core network {core_network_id}: {e}", style="yellow")
                    continue
            
            return {"found": False, "segment_name": "Not Attached", "core_network_id": None}
            
        except Exception as e:
            console.print(f"Warning: Could not discover CloudWAN segment for VPC {vpc_id}: {e}", style="yellow")
            return {"found": False, "segment_name": "Unknown", "core_network_id": None}
    
    def get_route_tables_for_subnet(self, ec2_client, subnet_id: str) -> list:
        """Get route tables associated with a subnet."""
        try:
            # Get route tables associated with the subnet
            response = ec2_client.describe_route_tables(
                Filters=[
                    {"Name": "association.subnet-id", "Values": [subnet_id]}
                ]
            )
            
            route_tables = []
            for rt in response.get("RouteTables", []):
                routes = []
                for route in rt.get("Routes", []):
                    target = (route.get("GatewayId") or 
                             route.get("TransitGatewayId") or 
                             route.get("NetworkInterfaceId") or 
                             route.get("VpcPeeringConnectionId") or
                             route.get("NatGatewayId") or
                             "local")
                    
                    routes.append({
                        "destination_cidr": route.get("DestinationCidrBlock", ""),
                        "target": target,
                        "state": route.get("State"),
                        "origin": route.get("Origin")
                    })
                
                route_tables.append({
                    "route_table_id": rt.get("RouteTableId"),
                    "routes": routes,
                    "main": any(assoc.get("Main", False) for assoc in rt.get("Associations", []))
                })
            
            return route_tables
            
        except Exception as e:
            console.print(f"Warning: Could not get route tables for subnet {subnet_id}: {e}", style="yellow")
            return []
    
    def find_ip_context(self, ip_address: str) -> dict:
        """Find IP context across all regions."""
        console.print(f"🔍 Searching for IP {ip_address} across regions: {', '.join(self.regions)}")
        
        # Search across regions concurrently
        with ThreadPoolExecutor(max_workers=len(self.regions)) as executor:
            future_to_region = {
                executor.submit(self.find_ip_in_region, region, ip_address): region 
                for region in self.regions
            }
            
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    result = future.result()
                    if result.get("found"):
                        console.print(f"✅ Found IP {ip_address} in region {region}", style="green")
                        return result
                except Exception as e:
                    console.print(f"❌ Error in region {region}: {e}", style="red")
        
        console.print(f"❌ IP {ip_address} not found in any region", style="red")
        return {"found": False}
    
    def find_matching_routes(self, destination_ip: str, route_tables: list) -> list:
        """Find routes that match the destination IP."""
        matching_routes = []
        dest_ip = ipaddress.ip_address(destination_ip)
        
        for rt in route_tables:
            for route in rt.get("routes", []):
                dest_cidr = route.get("destination_cidr", "")
                if dest_cidr and dest_cidr != "0.0.0.0/0":
                    try:
                        network = ipaddress.ip_network(dest_cidr, strict=False)
                        if dest_ip in network:
                            matching_routes.append({
                                "route_table_id": rt.get("route_table_id"),
                                "destination_cidr": dest_cidr,
                                "target": route.get("target"),
                                "state": route.get("state"),
                                "origin": route.get("origin"),
                                "prefix_length": network.prefixlen,
                                "is_main_table": rt.get("main", False)
                            })
                    except ValueError:
                        continue
        
        # Sort by most specific (longest prefix)
        matching_routes.sort(key=lambda x: x.get("prefix_length", 0), reverse=True)
        return matching_routes
    
    def discover_core_networks(self) -> list:
        """Discover Core Networks using Network Manager."""
        try:
            # Use the session which has the custom endpoint configured
            # NetworkManager API is always in us-west-2 for this environment
            nm_client = self.session.client('networkmanager', region_name='us-west-2')
            
            console.print("🔍 Discovering Core Networks...")
            response = nm_client.list_core_networks()
            
            core_networks = []
            for cn in response.get("CoreNetworks", []):
                core_networks.append({
                    "core_network_id": cn.get("CoreNetworkId"),
                    "global_network_id": cn.get("GlobalNetworkId"),
                    "state": cn.get("State"),
                    "description": cn.get("Description", ""),
                    "policy_version_id": cn.get("PolicyVersionId")
                })
            
            console.print(f"✅ Found {len(core_networks)} Core Networks", style="green")
            return core_networks
            
        except Exception as e:
            console.print(f"❌ Core Network discovery failed: {e}", style="red")
            return []
    
    def analyze_transit_gateways_in_region(self, region: str) -> dict:
        """Analyze Transit Gateways in a specific region."""
        try:
            ec2_client = self.session.client('ec2', region_name=region)
            
            # Get Transit Gateways
            response = ec2_client.describe_transit_gateways()
            tgws = response.get("TransitGateways", [])
            
            tgw_analysis = []
            for tgw in tgws:
                tgw_id = tgw.get("TransitGatewayId")
                
                # Get TGW name from tags
                tgw_name = tgw_id
                for tag in tgw.get("Tags", []):
                    if tag.get("Key", "").lower() == "name":
                        tgw_name = tag.get("Value", tgw_id)
                        break
                
                # Get peering attachments
                peering_response = ec2_client.describe_transit_gateway_peering_attachments(
                    Filters=[{"Name": "transit-gateway-id", "Values": [tgw_id]}]
                )
                peering_count = len(peering_response.get("TransitGatewayPeeringAttachments", []))
                
                tgw_analysis.append({
                    "transit_gateway_id": tgw_id,
                    "name": tgw_name,
                    "state": tgw.get("State"),
                    "asn": tgw.get("Options", {}).get("AmazonSideAsn"),
                    "peering_connections": peering_count,
                    "region": region
                })
            
            return {
                "region": region,
                "transit_gateways": tgw_analysis,
                "count": len(tgw_analysis)
            }
            
        except Exception as e:
            console.print(f"❌ TGW analysis failed in region {region}: {e}", style="red")
            return {"region": region, "transit_gateways": [], "count": 0, "error": str(e)}
    
    def trace_path(self, source_ip: str, destination_ip: str) -> dict:
        """Trace network path between two IPs."""
        console.print(Panel.fit(
            f"🚀 Network Path Trace\n"
            f"Source: {source_ip}\nDestination: {destination_ip}",
            title="Path Tracing",
            style="blue"
        ))
        
        # Step 1: Find IP contexts
        source_context = self.find_ip_context(source_ip)
        destination_context = self.find_ip_context(destination_ip)
        
        # Step 2: Discover Core Networks
        core_networks = self.discover_core_networks()
        
        # Step 3: Analyze TGWs in relevant regions
        regions = set([source_context.get("region"), destination_context.get("region")])
        regions = [r for r in regions if r]  # Remove None values
        
        tgw_analysis = {}
        for region in regions:
            tgw_analysis[region] = self.analyze_transit_gateways_in_region(region)
        
        # Step 4: Find routing
        routing_analysis = {}
        if source_context.get("found") and source_context.get("route_tables"):
            matching_routes = self.find_matching_routes(destination_ip, source_context["route_tables"])
            routing_analysis = {
                "matching_routes": matching_routes,
                "route_count": len(matching_routes)
            }
        
        # Compile results
        analysis = {
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "source_context": source_context,
            "destination_context": destination_context,
            "core_networks": core_networks,
            "transit_gateway_analysis": tgw_analysis,
            "routing_analysis": routing_analysis
        }
        
        return analysis
    
    def display_results(self, analysis: dict):
        """Display the path analysis results with rich formatting."""
        source_ctx = analysis["source_context"]
        dest_ctx = analysis["destination_context"]
        
        # Summary table
        summary_table = Table(title="Path Trace Summary", box=box.ROUNDED)
        summary_table.add_column("Attribute", style="cyan")
        summary_table.add_column("Source", style="green")
        summary_table.add_column("Destination", style="yellow")
        
        summary_table.add_row("IP Address", analysis["source_ip"], analysis["destination_ip"])
        summary_table.add_row(
            "Status", 
            "✅ Found" if source_ctx.get("found") else "❌ Not Found",
            "✅ Found" if dest_ctx.get("found") else "❌ Not Found"
        )
        
        if source_ctx.get("found"):
            summary_table.add_row("Region", source_ctx.get("region", "N/A"), dest_ctx.get("region", "N/A") if dest_ctx.get("found") else "N/A")
            summary_table.add_row("VPC", source_ctx.get("vpc_id", "N/A"), dest_ctx.get("vpc_id", "N/A") if dest_ctx.get("found") else "N/A")
            summary_table.add_row("Subnet", source_ctx.get("subnet_id", "N/A"), dest_ctx.get("subnet_id", "N/A") if dest_ctx.get("found") else "N/A")
            
            # Add CloudWAN segment information
            source_segment = source_ctx.get("segment_info", {}).get("segment_name", "Unknown")
            dest_segment = dest_ctx.get("segment_info", {}).get("segment_name", "Unknown") if dest_ctx.get("found") else "N/A"
            summary_table.add_row("CloudWAN Segment", source_segment, dest_segment)
        
        console.print(summary_table)
        console.print()
        
        # Routing analysis
        routing = analysis.get("routing_analysis", {})
        if routing.get("matching_routes"):
            route_table = Table(title="Matching Routes (Most Specific First)", box=box.ROUNDED)
            route_table.add_column("Destination CIDR", style="cyan")
            route_table.add_column("Target", style="green")
            route_table.add_column("State", style="yellow")
            route_table.add_column("Origin", style="magenta")
            route_table.add_column("Route Table", style="blue")
            
            for route in routing["matching_routes"][:10]:  # Show top 10
                route_table.add_row(
                    route.get("destination_cidr", ""),
                    route.get("target", ""),
                    route.get("state", ""),
                    route.get("origin", ""), 
                    route.get("route_table_id", "")
                )
            
            console.print(route_table)
            console.print()
        
        # Core Networks
        core_networks = analysis.get("core_networks", [])
        if core_networks:
            cn_table = Table(title="Core Networks", box=box.ROUNDED)
            cn_table.add_column("Core Network ID", style="cyan")
            cn_table.add_column("Global Network ID", style="green")
            cn_table.add_column("State", style="yellow")
            cn_table.add_column("Description", style="magenta")
            
            for cn in core_networks:
                cn_table.add_row(
                    cn.get("core_network_id", ""),
                    cn.get("global_network_id", ""),
                    cn.get("state", ""),
                    cn.get("description", "")
                )
            
            console.print(cn_table)
            console.print()
        
        # Transit Gateway analysis
        tgw_analysis = analysis.get("transit_gateway_analysis", {})
        if tgw_analysis:
            for region, data in tgw_analysis.items():
                if data.get("transit_gateways"):
                    tgw_table = Table(title=f"Transit Gateways - {region}", box=box.ROUNDED)
                    tgw_table.add_column("TGW ID", style="cyan")
                    tgw_table.add_column("Name", style="green")
                    tgw_table.add_column("State", style="yellow")
                    tgw_table.add_column("ASN", style="magenta")
                    tgw_table.add_column("Peering Connections", style="blue")
                    
                    for tgw in data["transit_gateways"]:
                        tgw_table.add_row(
                            tgw.get("transit_gateway_id", ""),
                            tgw.get("name", ""),
                            tgw.get("state", ""),
                            str(tgw.get("asn", "")),
                            str(tgw.get("peering_connections", 0))
                        )
                    
                    console.print(tgw_table)
                    console.print()
        
        # Path analysis summary
        self.display_path_summary(analysis)
    
    def display_path_summary(self, analysis: dict):
        """Display path analysis summary."""
        source_ctx = analysis["source_context"]
        dest_ctx = analysis["destination_context"]
        routing = analysis.get("routing_analysis", {})
        
        summary_lines = []
        
        # Connectivity status
        if source_ctx.get("found") and dest_ctx.get("found"):
            if source_ctx.get("vpc_id") == dest_ctx.get("vpc_id"):
                summary_lines.append("🔗 Path Type: Intra-VPC communication")
            elif source_ctx.get("region") == dest_ctx.get("region"):
                summary_lines.append("🔗 Path Type: Inter-VPC, same region")
            else:
                summary_lines.append("🔗 Path Type: Inter-VPC, cross-region")
            
            # Add CloudWAN segment analysis
            source_segment = source_ctx.get("segment_info", {}).get("segment_name", "Unknown")
            dest_segment = dest_ctx.get("segment_info", {}).get("segment_name", "Unknown")
            
            if source_segment != "Unknown" and dest_segment != "Unknown":
                if source_segment == dest_segment:
                    summary_lines.append(f"🔷 CloudWAN: Intra-segment communication ({source_segment})")
                else:
                    summary_lines.append(f"🔷 CloudWAN: Inter-segment communication ({source_segment} → {dest_segment})")
            elif source_segment != "Unknown" or dest_segment != "Unknown":
                if source_segment != "Unknown":
                    summary_lines.append(f"🔷 CloudWAN: Source in {source_segment} segment")
                if dest_segment != "Unknown":
                    summary_lines.append(f"🔷 CloudWAN: Destination in {dest_segment} segment")
        else:
            summary_lines.append("❌ Cannot determine path - IP(s) not found")
        
        # Routing analysis
        if routing.get("matching_routes"):
            best_route = routing["matching_routes"][0]
            target = best_route.get("target", "")
            
            if target.startswith("tgw-"):
                summary_lines.append("🚇 Transit Gateway routing detected")
            elif target.startswith("igw-"):
                summary_lines.append("🌐 Internet Gateway routing detected")
            elif target.startswith("nat-"):
                summary_lines.append("🔀 NAT Gateway routing detected")
            elif target == "local":
                summary_lines.append("🏠 Local VPC routing")
            
            summary_lines.append(f"📋 Best matching route: {best_route.get('destination_cidr')} -> {target}")
        
        # Recommendations
        recommendations = []
        if not source_ctx.get("found"):
            recommendations.append("Verify source IP address is correct and accessible")
        if not dest_ctx.get("found"):
            recommendations.append("Verify destination IP address is correct and accessible")
        
        if routing.get("matching_routes"):
            best_route = routing["matching_routes"][0]
            if best_route.get("target", "").startswith("tgw-"):
                recommendations.append("Check Transit Gateway route tables and security groups")
        
        if recommendations:
            summary_lines.append("\n💡 Recommendations:")
            for rec in recommendations:
                summary_lines.append(f"   • {rec}")
        
        if summary_lines:
            console.print(Panel(
                "\n".join(summary_lines),
                title="Path Analysis Summary",
                style="green"
            ))


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Simple Network Path Tracing")
    parser.add_argument("--source", required=True, help="Source IP address")
    parser.add_argument("--destination", required=True, help="Destination IP address")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    tracer = SimpleNetworkTracer()
    analysis = tracer.trace_path(args.source, args.destination)
    
    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    else:
        tracer.display_results(analysis)


if __name__ == "__main__":
    main()