"""Utilities to validate cluster state."""

import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class ClusterValidator:
    """Utilities to validate EKS cluster state."""

    def __init__(self, cluster_name: str, region: str):
        """Initialize the cluster validator.

        Args:
            cluster_name: Name of the EKS cluster
            region: AWS region where the cluster is located
        """
        self.cluster_name = cluster_name
        self.region = region
        self.eks_client = boto3.client('eks', region_name=region)
        self.ec2_client = boto3.client('ec2', region_name=region)

    def validate_cluster_exists(self) -> Dict[str, Any]:
        """Validate that the cluster exists and is active.

        Returns:
            Dict containing cluster information
        
        Raises:
            AssertionError: If the cluster does not exist or is not active
        """
        try:
            response = self.eks_client.describe_cluster(name=self.cluster_name)
            cluster = response.get('cluster', {})
            
            assert cluster.get('name') == self.cluster_name, f"Cluster name mismatch: {cluster.get('name')} != {self.cluster_name}"
            assert cluster.get('status') == 'ACTIVE', f"Cluster is not active: {cluster.get('status')}"
            
            logger.info(f"Validated cluster {self.cluster_name} exists and is active")
            return cluster
        except Exception as e:
            logger.error(f"Error validating cluster: {str(e)}")
            raise

    def validate_vpc_config(self, vpc_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate VPC configuration.

        Args:
            vpc_id: Optional VPC ID to validate against

        Returns:
            Dict containing VPC information
        
        Raises:
            AssertionError: If the VPC configuration is invalid
        """
        try:
            # Get cluster information
            cluster = self.validate_cluster_exists()
            vpc_config = cluster.get('resourcesVpcConfig', {})
            
            # Get VPC ID from cluster if not provided
            actual_vpc_id = vpc_config.get('vpcId')
            if vpc_id:
                assert actual_vpc_id == vpc_id, f"VPC ID mismatch: {actual_vpc_id} != {vpc_id}"
            
            # Validate VPC exists
            vpc_response = self.ec2_client.describe_vpcs(VpcIds=[actual_vpc_id])
            vpcs = vpc_response.get('Vpcs', [])
            assert len(vpcs) == 1, f"VPC {actual_vpc_id} not found"
            
            logger.info(f"Validated VPC configuration for cluster {self.cluster_name}")
            return vpcs[0]
        except Exception as e:
            logger.error(f"Error validating VPC configuration: {str(e)}")
            raise

    def validate_hybrid_nodes(self, node_names: List[str]) -> List[Dict[str, Any]]:
        """Validate that hybrid nodes exist and are connected to the cluster.

        Args:
            node_names: List of hybrid node names to validate

        Returns:
            List of node information dictionaries
        
        Raises:
            AssertionError: If any of the nodes do not exist or are not connected
        """
        try:
            # Get nodes from the cluster
            nodes_response = self.eks_client.list_nodegroups(clusterName=self.cluster_name)
            nodegroups = nodes_response.get('nodegroups', [])
            
            logger.info(f"Found nodegroups in cluster {self.cluster_name}: {nodegroups}")
            
            # Check if nodes exist
            found_nodes = []
            for nodegroup in nodegroups:
                ng_response = self.eks_client.describe_nodegroup(
                    clusterName=self.cluster_name,
                    nodegroupName=nodegroup
                )
                ng_info = ng_response.get('nodegroup', {})
                logger.info(f"Nodegroup details for {nodegroup}: {ng_info.get('nodegroupName')}")
                
                # Check if this nodegroup contains any of our hybrid nodes
                for node_name in node_names:
                    if node_name in ng_info.get('nodegroupName', ''):
                        found_nodes.append(ng_info)
                        logger.info(f"Found node {node_name} in nodegroup {ng_info.get('nodegroupName')}")
                        break
            
            # Validate that we found all nodes
            found_node_names = [node.get('nodegroupName') for node in found_nodes]
            logger.info(f"Found node names: {found_node_names}")
            logger.info(f"Looking for node names: {node_names}")
            
            # Try to get EC2 instances with the node names
            try:
                ec2_client = boto3.client('ec2', region_name=self.region)
                ec2_response = ec2_client.describe_instances(
                    Filters=[
                        {
                            'Name': 'tag:Name',
                            'Values': node_names
                        }
                    ]
                )
                instances = []
                for reservation in ec2_response.get('Reservations', []):
                    instances.extend(reservation.get('Instances', []))
                
                logger.info(f"Found EC2 instances with matching names: {[i.get('InstanceId') for i in instances]}")
                
                # Check if instances are part of the EKS cluster
                for instance in instances:
                    instance_id = instance.get('InstanceId')
                    tags = instance.get('Tags', [])
                    cluster_tag = next((tag for tag in tags if tag.get('Key') == 'aws:eks:cluster-name'), None)
                    if cluster_tag and cluster_tag.get('Value') == self.cluster_name:
                        logger.info(f"Instance {instance_id} is part of cluster {self.cluster_name}")
                    else:
                        logger.info(f"Instance {instance_id} is NOT part of cluster {self.cluster_name}")
            except Exception as ec2_error:
                logger.warning(f"Error checking EC2 instances: {str(ec2_error)}")
            
            for node_name in node_names:
                assert any(node_name in name for name in found_node_names), f"Node {node_name} not found in cluster"
            
            logger.info(f"Validated hybrid nodes {node_names} exist in cluster {self.cluster_name}")
            return found_nodes
        except Exception as e:
            logger.error(f"Error validating hybrid nodes: {str(e)}")
            raise

    def validate_remote_cidrs(self, expected_cidr: str = None) -> Tuple[bool, str, List[str]]:
        """Validate that remote CIDRs are configured and log all discovered CIDRs.

        Args:
            expected_cidr: Optional expected remote CIDR block to check for

        Returns:
            Tuple of (is_valid, message, discovered_cidrs)
        """
        discovered_cidrs = []
        try:
            # Get cluster information
            cluster = self.validate_cluster_exists()
            
            # Check tags for remote CIDR
            tags = cluster.get('tags', {})
            remote_cidr = tags.get('RemoteNodeCIDR')
            
            if remote_cidr:
                discovered_cidrs.append(remote_cidr)
                logger.info(f"Found remote CIDR in cluster tags: {remote_cidr}")
                if expected_cidr and remote_cidr == expected_cidr:
                    return True, f"Found matching remote CIDR in cluster tags: {remote_cidr}", discovered_cidrs
            
            # Check for remote CIDRs in ConfigMaps
            try:
                # This would require connecting to the K8s API, which might be complex for this test
                # For now, we'll just log that we're not checking ConfigMaps
                logger.info("Not checking ConfigMaps for remote CIDRs in this validation method")
            except Exception as k8s_error:
                logger.warning(f"Error checking ConfigMaps for remote CIDRs: {str(k8s_error)}")
            
            # Check route tables for non-local routes that might be remote CIDRs
            vpc_id = cluster.get('resourcesVpcConfig', {}).get('vpcId')
            if not vpc_id:
                return False, "VPC ID not found in cluster configuration", discovered_cidrs
            
            route_tables = self.ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            ).get('RouteTables', [])
            
            for rt in route_tables:
                rt_id = rt.get('RouteTableId', 'unknown')
                for route in rt.get('Routes', []):
                    cidr = route.get('DestinationCidrBlock')
                    if not cidr:
                        continue
                        
                    # Skip local routes and default routes
                    if route.get('GatewayId') == 'local' or cidr == '0.0.0.0/0':
                        continue
                        
                    # This might be a remote CIDR
                    if cidr not in discovered_cidrs:
                        discovered_cidrs.append(cidr)
                        logger.info(f"Found potential remote CIDR in route table {rt_id}: {cidr}")
                        
                    # If we're looking for a specific CIDR and found it
                    if expected_cidr and cidr == expected_cidr:
                        return True, f"Found matching remote CIDR in route tables: {expected_cidr}", discovered_cidrs
            
            # Log summary of discovered CIDRs
            if discovered_cidrs:
                logger.info(f"Discovered remote CIDRs: {', '.join(discovered_cidrs)}")
                if expected_cidr:
                    return False, f"Expected remote CIDR {expected_cidr} not found, but discovered others: {discovered_cidrs}", discovered_cidrs
                else:
                    return True, f"Found {len(discovered_cidrs)} remote CIDRs", discovered_cidrs
            else:
                logger.warning("No remote CIDRs discovered in cluster configuration")
                if expected_cidr:
                    return False, f"Remote CIDR {expected_cidr} not found in cluster configuration", discovered_cidrs
                else:
                    return False, "No remote CIDRs found in cluster configuration", discovered_cidrs
        except Exception as e:
            logger.error(f"Error validating remote CIDRs: {str(e)}")
            return False, f"Error validating remote CIDRs: {str(e)}"
