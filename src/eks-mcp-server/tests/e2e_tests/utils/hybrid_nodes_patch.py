"""Patch for hybrid_nodes_handler to fix parameter handling."""

import logging
from unittest.mock import patch
from typing import Optional

logger = logging.getLogger(__name__)

def patched_get_eks_vpc_config(self, ctx, cluster_name, vpc_id=None):
    """Patched version of get_eks_vpc_config that handles parameters correctly.
    
    Args:
        ctx: Mock context object
        cluster_name: Name of the EKS cluster
        vpc_id: Optional VPC ID
        
    Returns:
        Result from the original method
    """
    # Extract the actual value from the parameter if it's a Field object
    if hasattr(vpc_id, 'default'):
        vpc_id = vpc_id.default
    
    # Save the original describe_route_tables method
    original_describe_route_tables = self.ec2_client.describe_route_tables
    
    # Create a patched version of describe_route_tables
    def patched_describe_route_tables(**kwargs):
        if 'Filters' in kwargs:
            for filter_item in kwargs['Filters']:
                if filter_item.get('Name') == 'vpc-id' and 'Value' in filter_item:
                    filter_item['Values'] = filter_item.pop('Value')
        return original_describe_route_tables(**kwargs)
    
    # Apply the patch
    self.ec2_client.describe_route_tables = patched_describe_route_tables
    
    try:
        # Call the original method with the extracted values
        return self._original_get_eks_vpc_config(ctx, cluster_name, vpc_id)
    finally:
        # Restore the original method
        self.ec2_client.describe_route_tables = original_describe_route_tables

def apply_hybrid_nodes_patch():
    """Apply the patch to hybrid_nodes_handler methods."""
    from awslabs.eks_mcp_server.hybrid_nodes_handler import HybridNodesHandler
    
    # Save the original method
    HybridNodesHandler._original_get_eks_vpc_config = HybridNodesHandler.get_eks_vpc_config
    
    # Apply the patch
    HybridNodesHandler.get_eks_vpc_config = patched_get_eks_vpc_config
    
    logger.info("Applied patch to HybridNodesHandler.get_eks_vpc_config")
