#!/usr/bin/env python3
"""
Enhanced path trace formatting functions for CloudWAN MCP.
"""

from typing import Dict, Any, List


def format_path_trace_result(result: Dict[str, Any]) -> str:
    """Format comprehensive path trace result."""
    if isinstance(result, str):
        try:
            import json
            result = json.loads(result)
        except:
            return f"📊 Path Trace Result:\n{result}"
    
    source_ip = result.get("source_ip", "N/A")
    dest_ip = result.get("destination_ip", "N/A")
    
    # Get context information
    source_ctx = result.get("source_context", {})
    dest_ctx = result.get("destination_context", {})
    
    # Build comprehensive path trace result
    formatted = f"""🛤️  **Path Trace: {source_ip} → {dest_ip}**
        
**Source Context:**
• Region: {source_ctx.get('region', 'N/A')}
• VPC: {source_ctx.get('vpc_id', 'N/A')}
• Subnet: {source_ctx.get('subnet_id', 'N/A')}
• Availability Zone: {source_ctx.get('availability_zone', 'N/A')}
• Status: {source_ctx.get('status', 'N/A')}
• CloudWAN Segment: {source_ctx.get('segment_info', {}).get('segment_name', 'N/A')}

**Destination Context:**
• Region: {dest_ctx.get('region', 'N/A')}
• VPC: {dest_ctx.get('vpc_id', 'N/A')}
• Subnet: {dest_ctx.get('subnet_id', 'N/A')}
• Availability Zone: {dest_ctx.get('availability_zone', 'N/A')}
• Status: {dest_ctx.get('status', 'N/A')}
• CloudWAN Segment: {dest_ctx.get('segment_info', {}).get('segment_name', 'N/A')}

**Core Networks:**
{format_core_networks(result.get('core_networks', []))}

**Transit Gateway Analysis:**
{format_tgw_analysis(result.get('transit_gateway_analysis', {}))}

**Routing Analysis:**
{format_routing_analysis(result.get('routing_analysis', {}))}
"""
    return formatted


def format_core_networks(core_networks: List[Dict[str, Any]]) -> str:
    """Format core networks information."""
    if not core_networks:
        return "• No core networks found"
    
    formatted_networks = []
    for i, network in enumerate(core_networks[:3]):  # Show first 3
        network_id = network.get('core_network_id', 'N/A')
        state = network.get('state', 'N/A')
        description = network.get('description', 'No description')
        formatted_networks.append(f"• Core Network {i+1}: {network_id} ({state}) - {description}")
    
    if len(core_networks) > 3:
        formatted_networks.append(f"• ... and {len(core_networks) - 3} more networks")
    
    return "\n".join(formatted_networks)


def format_tgw_analysis(tgw_analysis: Dict[str, Any]) -> str:
    """Format transit gateway analysis."""
    if not tgw_analysis:
        return "• No transit gateway analysis available"
    
    formatted_tgws = []
    for region, tgw_data in tgw_analysis.items():
        if isinstance(tgw_data, list) and tgw_data:
            tgw_count = len(tgw_data)
            formatted_tgws.append(f"• {region}: {tgw_count} Transit Gateway{'s' if tgw_count != 1 else ''}")
            
            # Show first TGW details
            first_tgw = tgw_data[0]
            if isinstance(first_tgw, dict):
                tgw_id = first_tgw.get('transit_gateway_id', 'N/A')
                state = first_tgw.get('state', 'N/A')
                formatted_tgws.append(f"  - {tgw_id} ({state})")
        else:
            formatted_tgws.append(f"• {region}: No transit gateways")
    
    return "\n".join(formatted_tgws) if formatted_tgws else "• No transit gateway data available"


def format_routing_analysis(routing_analysis: Dict[str, Any]) -> str:
    """Format routing analysis."""
    if not routing_analysis:
        return "• No routing analysis available"
    
    matching_routes = routing_analysis.get('matching_routes', [])
    route_count = routing_analysis.get('route_count', 0)
    
    if route_count == 0:
        return "• No matching routes found"
    
    formatted_routes = [f"• Found {route_count} matching route{'s' if route_count != 1 else ''}"]
    
    # Show first few routes
    for i, route in enumerate(matching_routes[:3]):
        if isinstance(route, dict):
            destination = route.get('destination_cidr_block', 'N/A')
            target = route.get('target', 'N/A')
            state = route.get('state', 'N/A')
            formatted_routes.append(f"  - Route {i+1}: {destination} → {target} ({state})")
    
    if len(matching_routes) > 3:
        formatted_routes.append(f"  - ... and {len(matching_routes) - 3} more routes")
    
    return "\n".join(formatted_routes)