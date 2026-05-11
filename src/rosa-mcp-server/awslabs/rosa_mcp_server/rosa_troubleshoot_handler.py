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

"""ROSA troubleshooting handler providing diagnostics and guidance.

Includes a troubleshooting knowledge base, VPC configuration retrieval,
and metrics guidance for monitoring ROSA clusters.
"""

import boto3
import json
from awslabs.rosa_mcp_server.ocm_client import OCMClient
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


TROUBLESHOOT_KB = [
    {
        'keywords': ['pod', 'pending', 'stuck', 'not starting'],
        'title': 'Pod stuck in Pending state',
        'solution': (
            'Check node capacity (rosa_get_nodes), check if machine pool has enough replicas, '
            'verify resource requests/limits, check for taints preventing scheduling.'
        ),
    },
    {
        'keywords': ['node', 'notready', 'not ready', 'unhealthy'],
        'title': 'Node NotReady',
        'solution': (
            'Check node pool status (rosa_list_machinepools), verify AWS instance health in '
            'EC2 console, check cluster operators (rosa_get_cluster_operators), review CloudWatch metrics.'
        ),
    },
    {
        'keywords': ['operator', 'degraded', 'unavailable'],
        'title': 'Cluster operator degraded',
        'solution': (
            'Run rosa_get_cluster_operators to identify degraded operators. Check operator pod logs. '
            'Common causes: DNS issues, certificate expiry, storage problems.'
        ),
    },
    {
        'keywords': ['ingress', 'route', 'not accessible', '503', '504', 'timeout'],
        'title': 'Application not accessible via Route/Ingress',
        'solution': (
            'Verify ingress controller (rosa_list_ingresses), check Route status, verify service '
            'endpoints exist, check network policies, verify DNS propagation.'
        ),
    },
    {
        'keywords': ['authentication', 'login', 'forbidden', '401', '403', 'oauth'],
        'title': 'Authentication/Authorization issues',
        'solution': (
            'Check IDPs (rosa_list_idps), verify user group membership (rosa_list_users), '
            'check RBAC roles, verify OAuth server operator status.'
        ),
    },
    {
        'keywords': ['upgrade', 'failed', 'stuck', 'version'],
        'title': 'Cluster upgrade issues',
        'solution': (
            'Check upgrade policy status, review install logs (rosa_get_install_logs), '
            'verify all operators are available before upgrade, check version gate agreements.'
        ),
    },
    {
        'keywords': ['storage', 'pvc', 'pending', 'bound', 'ebs', 'volume'],
        'title': 'Storage/PVC issues',
        'solution': (
            'Check StorageClass exists, verify EBS CSI operator (rosa_get_cluster_operators), '
            'check AWS service quotas for EBS volumes, verify node IAM role has EBS permissions.'
        ),
    },
    {
        'keywords': ['network', 'dns', 'connectivity', 'timeout', 'connection refused'],
        'title': 'Network connectivity issues',
        'solution': (
            'Check cluster network type (OVNKubernetes), verify VPC config (rosa_get_vpc_config), '
            'check security groups, verify NAT gateway for private subnets, check NetworkPolicies.'
        ),
    },
    {
        'keywords': ['scaling', 'autoscaler', 'not scaling', 'capacity'],
        'title': 'Autoscaling not working',
        'solution': (
            'Check autoscaler config (rosa_get_autoscaler), verify machine pool has autoscaling '
            'enabled with min/max, check if max nodes reached, review cluster autoscaler logs.'
        ),
    },
    {
        'keywords': ['certificate', 'tls', 'ssl', 'expired', 'cert'],
        'title': 'TLS/Certificate issues',
        'solution': (
            'Check ingress controller certificates, verify cert-manager operator if installed, '
            'check default wildcard certificate validity, review router pods.'
        ),
    },
    {
        'keywords': ['image', 'pull', 'imagepullbackoff', 'registry', 'ecr'],
        'title': 'Image pull failures',
        'solution': (
            'Verify image exists in registry, check pull secrets (oc get secret), for ECR: '
            'verify IAM role has ecr:GetAuthorizationToken, check network access to registry.'
        ),
    },
    {
        'keywords': ['oom', 'memory', 'killed', 'evicted', 'resource'],
        'title': 'Pod OOMKilled or evicted',
        'solution': (
            'Check pod resource requests/limits, review node memory usage (rosa_get_cluster_metrics), '
            'consider increasing machine pool instance type or adding more nodes.'
        ),
    },
]


METRICS_GUIDANCE = {
    'container_insights': {
        'namespace': 'ContainerInsights',
        'key_metrics': [
            {
                'name': 'cpu_usage_total',
                'description': 'Total CPU usage',
                'dimensions': ['ClusterName', 'Namespace', 'PodName'],
            },
            {
                'name': 'memory_usage',
                'description': 'Memory usage in bytes',
                'dimensions': ['ClusterName', 'Namespace', 'PodName'],
            },
            {
                'name': 'network_rx_bytes',
                'description': 'Network bytes received',
                'dimensions': ['ClusterName', 'PodName'],
            },
            {
                'name': 'network_tx_bytes',
                'description': 'Network bytes transmitted',
                'dimensions': ['ClusterName', 'PodName'],
            },
            {
                'name': 'node_cpu_utilization',
                'description': 'Node CPU utilization %',
                'dimensions': ['ClusterName', 'NodeName'],
            },
            {
                'name': 'node_memory_utilization',
                'description': 'Node memory utilization %',
                'dimensions': ['ClusterName', 'NodeName'],
            },
            {
                'name': 'pod_number_of_container_restarts',
                'description': 'Container restart count',
                'dimensions': ['ClusterName', 'Namespace', 'PodName'],
            },
        ],
    },
    'openshift_monitoring': {
        'description': 'OpenShift built-in Prometheus metrics (accessible via cluster monitoring)',
        'key_metrics': [
            'cluster:cpu_usage_cores:sum',
            'cluster:memory_usage_bytes:sum',
            'cluster:node_cpu:ratio',
            'etcd_server_has_leader',
            'apiserver_request_total',
            'alerts_firing',
        ],
    },
    'recommended_alarms': [
        {
            'metric': 'node_cpu_utilization',
            'threshold': '80%',
            'action': 'Scale machine pool',
        },
        {
            'metric': 'node_memory_utilization',
            'threshold': '85%',
            'action': 'Scale machine pool or increase instance type',
        },
        {
            'metric': 'pod_number_of_container_restarts',
            'threshold': '>5 in 10min',
            'action': 'Investigate pod health',
        },
    ],
}


class RosaTroubleshootHandler:
    """Handler for ROSA troubleshooting, VPC config, and metrics guidance."""

    def __init__(
        self,
        mcp,
        ocm_client: Optional[OCMClient] = None,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the troubleshoot handler.

        Args:
            mcp: The FastMCP server instance.
            ocm_client: Shared OCM API client (needed for VPC config).
            allow_sensitive_data_access: Whether sensitive data access is permitted.
        """
        self.mcp = mcp
        self.ocm = ocm_client
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # These tools work without OCM
        self.mcp.tool(name='rosa_search_troubleshoot_guide')(self.rosa_search_troubleshoot_guide)
        self.mcp.tool(name='rosa_get_metrics_guidance')(self.rosa_get_metrics_guidance)

        # VPC config needs OCM to get cluster subnet info
        if ocm_client:
            self.mcp.tool(name='rosa_get_vpc_config')(self.rosa_get_vpc_config)

    async def rosa_search_troubleshoot_guide(
        self,
        ctx: Context,
        query: str,
    ) -> list[TextContent]:
        """Search the built-in troubleshooting knowledge base for ROSA/OpenShift issues.

        Args:
            ctx: MCP context.
            query: Search query describing the issue (e.g., "pod stuck pending").
        """
        query_lower = query.lower()
        query_words = query_lower.split()

        scored_results = []
        for entry in TROUBLESHOOT_KB:
            score = 0
            for keyword in entry['keywords']:
                keyword_lower = keyword.lower()
                # Exact keyword match in query
                if keyword_lower in query_lower:
                    score += 2
                # Partial word match
                elif any(word in keyword_lower or keyword_lower in word for word in query_words):
                    score += 1

            if score > 0:
                scored_results.append({
                    'title': entry['title'],
                    'solution': entry['solution'],
                    'relevance_score': score,
                })

        # Sort by relevance score descending
        scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)

        return [TextContent(
            type='text',
            text=json.dumps({
                'query': query,
                'results_count': len(scored_results),
                'results': scored_results,
            }, indent=2),
        )]

    async def rosa_get_metrics_guidance(
        self,
        ctx: Context,
    ) -> list[TextContent]:
        """Return metrics guidance for monitoring ROSA clusters.

        Provides a reference of key CloudWatch and OpenShift metrics, namespaces,
        dimensions, and recommended alarms.

        Args:
            ctx: MCP context.
        """
        return [TextContent(
            type='text',
            text=json.dumps(METRICS_GUIDANCE, indent=2),
        )]

    async def rosa_get_vpc_config(
        self,
        ctx: Context,
        cluster_id: str,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Get VPC configuration details for a ROSA cluster.

        Retrieves VPC, subnets, security groups, and NAT gateways associated
        with the cluster's infrastructure.

        Args:
            ctx: MCP context.
            cluster_id: The OCM cluster ID.
            region: AWS region. If omitted, uses default from environment or cluster region.
        """
        # Get cluster info from OCM to find subnet IDs
        cluster_info = await self.ocm.get_cluster(cluster_id)

        # Extract subnet IDs from cluster info
        aws_info = cluster_info.get('aws', {})
        subnet_ids = aws_info.get('subnet_ids', [])

        # Try to get region from cluster info if not provided
        cluster_region = region or cluster_info.get('region', {}).get('id')

        if not subnet_ids:
            # Try machine pools / node pools for subnet info
            try:
                is_hcp = cluster_info.get('hypershift', {}).get('enabled', False)
                if is_hcp:
                    pools = await self.ocm.list_node_pools(cluster_id)
                else:
                    pools = await self.ocm.list_machine_pools(cluster_id)

                for pool in pools.get('items', []):
                    pool_subnets = pool.get('subnet', '') or pool.get('aws_node_pool', {}).get('subnet_id', '')
                    if pool_subnets:
                        if isinstance(pool_subnets, list):
                            subnet_ids.extend(pool_subnets)
                        else:
                            subnet_ids.append(pool_subnets)
            except Exception:
                pass

        if not subnet_ids:
            return [TextContent(
                type='text',
                text=json.dumps({
                    'error': 'Could not determine subnet IDs for cluster. '
                             'Cluster may use a managed VPC without explicit subnet references.',
                    'cluster_id': cluster_id,
                }),
            )]

        try:
            kwargs = {}
            if cluster_region:
                kwargs['region_name'] = cluster_region

            ec2_client = boto3.client('ec2', **kwargs)

            # Describe subnets
            subnets_response = ec2_client.describe_subnets(SubnetIds=subnet_ids)
            subnets = subnets_response.get('Subnets', [])

            if not subnets:
                return [TextContent(
                    type='text',
                    text=json.dumps({'error': 'No subnets found for the provided IDs.'}),
                )]

            vpc_id = subnets[0]['VpcId']

            # Describe VPC
            vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
            vpc = vpc_response.get('Vpcs', [{}])[0]

            # Describe security groups in the VPC
            sg_response = ec2_client.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            security_groups = [
                {
                    'GroupId': sg['GroupId'],
                    'GroupName': sg['GroupName'],
                    'Description': sg.get('Description', ''),
                }
                for sg in sg_response.get('SecurityGroups', [])
            ]

            # Describe NAT gateways
            nat_response = ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            nat_gateways = [
                {
                    'NatGatewayId': nat['NatGatewayId'],
                    'State': nat['State'],
                    'SubnetId': nat.get('SubnetId', ''),
                    'ConnectivityType': nat.get('ConnectivityType', ''),
                }
                for nat in nat_response.get('NatGateways', [])
            ]

            # Describe route tables
            rt_response = ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            route_tables = [
                {
                    'RouteTableId': rt['RouteTableId'],
                    'Associations': [
                        a.get('SubnetId', 'main') for a in rt.get('Associations', [])
                    ],
                }
                for rt in rt_response.get('RouteTables', [])
            ]

            # Format subnet info
            subnet_info = []
            for s in subnets:
                # Determine if public by checking route table for internet gateway
                is_public = False
                for rt in rt_response.get('RouteTables', []):
                    assoc_subnets = [a.get('SubnetId') for a in rt.get('Associations', [])]
                    if s['SubnetId'] in assoc_subnets:
                        for route in rt.get('Routes', []):
                            if route.get('GatewayId', '').startswith('igw-'):
                                is_public = True
                                break

                subnet_info.append({
                    'SubnetId': s['SubnetId'],
                    'AvailabilityZone': s['AvailabilityZone'],
                    'CidrBlock': s['CidrBlock'],
                    'Public': is_public,
                    'MapPublicIpOnLaunch': s.get('MapPublicIpOnLaunch', False),
                    'AvailableIpAddressCount': s.get('AvailableIpAddressCount', 0),
                })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'cluster_id': cluster_id,
                    'vpc_id': vpc_id,
                    'vpc_cidr': vpc.get('CidrBlock', ''),
                    'subnets': subnet_info,
                    'security_groups': security_groups,
                    'nat_gateways': nat_gateways,
                    'route_tables': route_tables,
                }, indent=2, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error retrieving VPC configuration: {str(e)}',
            )]
