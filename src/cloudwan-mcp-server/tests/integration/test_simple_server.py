#!/usr/bin/env python3
"""
Simplified CloudWAN MCP Server for Claude Code compatibility testing.

This is a minimal version based on the working core-mcp-server pattern.
"""

import sys
from mcp.server.fastmcp import FastMCP
from typing import List, TypedDict
import asyncio
import boto3
import json

class ContentItem(TypedDict):
    type: str
    text: str

class McpResponse(TypedDict, total=False):
    content: List[ContentItem]
    isError: bool

# Create FastMCP server with minimal configuration
mcp = FastMCP(
    'CloudWAN MCP server for AWS CloudWAN network analysis',
    dependencies=[
        'boto3',
    ],
)

@mcp.tool(name='get_global_networks')
async def get_global_networks() -> str:
    """Get AWS CloudWAN Global Networks.
    
    Lists all CloudWAN Global Networks in your AWS account.
    """
    try:
        # Simple implementation for testing
        import boto3
        import os
        
        # Get AWS session
        profile = os.getenv('AWS_PROFILE')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
        
        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()
            
        client = session.client('networkmanager', region_name=region)
        
        # Get global networks
        response = client.describe_global_networks()
        global_networks = response.get('GlobalNetworks', [])
        
        if not global_networks:
            return "No CloudWAN Global Networks found in your account."
        
        result = f"Found {len(global_networks)} CloudWAN Global Network(s):\n\n"
        
        for i, gn in enumerate(global_networks, 1):
            result += f"{i}. Global Network ID: {gn.get('GlobalNetworkId', 'N/A')}\n"
            result += f"   State: {gn.get('State', 'N/A')}\n"
            result += f"   Description: {gn.get('Description', 'No description')}\n"
            result += f"   Created: {gn.get('CreatedAt', 'N/A')}\n"
            
            # Tags
            tags = gn.get('Tags', [])
            if tags:
                tag_str = ', '.join([f"{t.get('Key')}={t.get('Value')}" for t in tags[:3]])
                result += f"   Tags: {tag_str}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving global networks: {str(e)}"

@mcp.tool(name='list_core_networks') 
async def list_core_networks() -> str:
    """List AWS CloudWAN Core Networks.
    
    Lists all CloudWAN Core Networks associated with Global Networks.
    """
    try:
        import boto3
        import os
        
        # Get AWS session
        profile = os.getenv('AWS_PROFILE')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
        
        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()
            
        client = session.client('networkmanager', region_name=region)
        
        # Get core networks
        response = client.describe_core_networks()
        core_networks = response.get('CoreNetworks', [])
        
        if not core_networks:
            return "No CloudWAN Core Networks found in your account."
        
        result = f"Found {len(core_networks)} CloudWAN Core Network(s):\n\n"
        
        for i, cn in enumerate(core_networks, 1):
            result += f"{i}. Core Network ID: {cn.get('CoreNetworkId', 'N/A')}\n"
            result += f"   State: {cn.get('State', 'N/A')}\n"
            result += f"   Global Network: {cn.get('GlobalNetworkId', 'N/A')}\n"
            result += f"   Policy Version: {cn.get('PolicyVersionId', 'N/A')}\n"
            result += f"   Created: {cn.get('CreatedAt', 'N/A')}\n"
            
            # Tags
            tags = cn.get('Tags', [])
            if tags:
                tag_str = ', '.join([f"{t.get('Key')}={t.get('Value')}" for t in tags[:3]])
                result += f"   Tags: {tag_str}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving core networks: {str(e)}"

def main() -> None:
    """Run the simplified CloudWAN MCP server."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("Server shutdown requested")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()