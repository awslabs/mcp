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

"""Which warehouses exist, asked of the control plane rather than of a warehouse."""

import asyncio
import time
from awslabs.redshift_mcp_server.clients import ACCESS_DENIED, client_manager
from awslabs.redshift_mcp_server.consts import CLUSTER_RESOLVE_TTL
from awslabs.redshift_mcp_server.models import RedshiftCluster
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError


# Identifier to the moment it was resolved and what it resolved to. Bounded by the number of
# clusters in the account, not by anything a caller chooses.
_resolved: dict[str, tuple[float, RedshiftCluster]] = {}


def _fetch_provisioned_clusters() -> list[dict]:
    """Page through every provisioned cluster.

    Synchronous, and called through asyncio.to_thread: boto3 blocks, and client construction
    on first use blocks for seconds, which would stall every other call on the event loop.

    Returns:
        The raw DescribeClusters entries.
    """
    paginator = client_manager.redshift_client().get_paginator('describe_clusters')
    return [cluster for page in paginator.paginate() for cluster in page.get('Clusters', [])]


def _fetch_serverless_workgroups() -> list[tuple[dict, dict]]:
    """Page through every serverless workgroup and fetch each one's detail.

    Synchronous, and called through asyncio.to_thread, for the same reason as its provisioned
    counterpart. The detail call is per workgroup, so this blocks for longer still.

    Returns:
        Pairs of the ListWorkgroups entry and its GetWorkgroup detail.
    """
    serverless_client = client_manager.redshift_serverless_client()
    paginator = serverless_client.get_paginator('list_workgroups')
    return [
        (
            workgroup,
            serverless_client.get_workgroup(workgroupName=workgroup['workgroupName'])['workgroup'],
        )
        for page in paginator.paginate()
        for workgroup in page.get('workgroups', [])
    ]


def _provisioned_cluster(cluster: dict) -> RedshiftCluster:
    """Map one DescribeClusters entry onto the model.

    Args:
        cluster: One entry from DescribeClusters.

    Returns:
        The cluster as this server reports it.
    """
    return RedshiftCluster(
        identifier=cluster['ClusterIdentifier'],
        type='provisioned',
        # Lowercased here and in the serverless mapper. The two APIs disagree on case -
        # 'available' against 'AVAILABLE' - and a caller told that only an available cluster can
        # be queried would compare against one of them and silently drop every cluster of the
        # other kind.
        status=cluster['ClusterStatus'].lower(),
        database_name=cluster.get('DBName', 'dev'),
        endpoint=cluster.get('Endpoint', {}).get('Address'),
        port=cluster.get('Endpoint', {}).get('Port'),
        vpc_id=cluster.get('VpcId'),
        node_type=cluster.get('NodeType'),
        number_of_nodes=cluster.get('NumberOfNodes'),
        creation_time=cluster.get('ClusterCreateTime'),
        master_username=cluster.get('MasterUsername'),
        publicly_accessible=cluster.get('PubliclyAccessible'),
        encrypted=cluster.get('Encrypted'),
        tags={tag['Key']: tag['Value'] for tag in cluster.get('Tags', [])},
    )


def _serverless_cluster(workgroup: dict, detail: dict) -> RedshiftCluster:
    """Map one ListWorkgroups entry and its GetWorkgroup detail onto the model.

    Args:
        workgroup: One entry from ListWorkgroups.
        detail: The GetWorkgroup response for that workgroup.

    Returns:
        The workgroup as this server reports it, in the same shape as a provisioned cluster.
    """
    endpoint = detail.get('endpoint', {})

    return RedshiftCluster(
        identifier=workgroup['workgroupName'],
        type='serverless',
        status=workgroup['status'].lower(),  # Lowercased, per _provisioned_cluster.
        # Serverless always exposes the built-in 'dev' database. Reporting the namespace's
        # configured default would require redshift-serverless:GetNamespace; callers can pass an
        # explicit database_name to the other tools instead.
        database_name='dev',
        endpoint=endpoint.get('address'),
        port=endpoint.get('port'),
        # The workgroup's VPC endpoints carry the real VPC. Reported from subnetIds[0] before,
        # this field answered with a subnet id under the name vpc_id, and disagreed with the
        # provisioned mapper about what it holds.
        vpc_id=next(
            (vpce['vpcId'] for vpce in endpoint.get('vpcEndpoints', []) if vpce.get('vpcId')),
            None,
        ),
        node_type=None,  # Not applicable for serverless
        number_of_nodes=None,  # Not applicable for serverless
        creation_time=workgroup.get('creationDate'),
        master_username=None,  # Serverless uses IAM
        publicly_accessible=detail.get('publiclyAccessible'),
        encrypted=True,  # Serverless is always encrypted
        tags={tag['key']: tag['value'] for tag in detail.get('tags', [])},
    )


async def discover_clusters(denied_sink: set[str] | None = None) -> list[RedshiftCluster]:
    """Discover all Redshift clusters and serverless workgroups.

    Best-effort only against a denial: a half IAM refuses is skipped and whatever the other
    half found is returned, and both refused is an error. Any other failure of either half -
    throttling, a validation error, anything that is not a ClientError - propagates even when
    the other half would have succeeded.

    Args:
        denied_sink: Filled with 'provisioned' or 'serverless' for each half IAM refused, so a
            caller can tell a cluster that does not exist from one this account cannot list.

    Returns:
        List of RedshiftCluster models.

    Raises:
        ToolError: If IAM denied both provisioned and serverless discovery.
    """
    clusters = []
    provisioned_error = None
    serverless_error = None

    try:
        logger.debug('Discovering provisioned Redshift clusters')

        provisioned_count = 0
        for cluster in await asyncio.to_thread(_fetch_provisioned_clusters):
            clusters.append(_provisioned_cluster(cluster))
            provisioned_count += 1

        # Counted rather than measured off `clusters`, which was only right while this half ran
        # first.
        logger.info(f'Found {provisioned_count} provisioned clusters')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in ACCESS_DENIED:
            raise
        provisioned_error = e
        if denied_sink is not None:
            denied_sink.add('provisioned')
        logger.warning(f'Skipping provisioned; IAM lacks permission: {e}')

    try:
        logger.debug('Discovering Redshift Serverless workgroups')

        serverless_count = 0
        for workgroup, detail in await asyncio.to_thread(_fetch_serverless_workgroups):
            clusters.append(_serverless_cluster(workgroup, detail))
            serverless_count += 1

        logger.info(f'Found {serverless_count} serverless workgroups')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in ACCESS_DENIED:
            raise
        serverless_error = e
        if denied_sink is not None:
            denied_sink.add('serverless')
        logger.warning(f'Skipping serverless; IAM lacks permission: {e}')

    if provisioned_error and serverless_error:
        msg = (
            'Unable to discover any Redshift clusters: IAM lacks both redshift and '
            f'redshift-serverless permissions. Provisioned: {provisioned_error}; '
            f'Serverless: {serverless_error}'
        )
        logger.error(msg)
        raise ToolError(msg)

    logger.info(f'Total clusters discovered: {len(clusters)}')
    return clusters


async def resolve_cluster(cluster_identifier: str) -> RedshiftCluster:
    """Resolve a cluster identifier to its discovered cluster.

    Cached for CLUSTER_RESOLVE_TTL seconds. Every statement resolves, and discovery costs a
    DescribeClusters, a ListWorkgroups and a GetWorkgroup per workgroup - eleven times over in
    one review_cluster. Staleness is safe: a resolve needs the identifier and the type, which do
    not change while a cluster lives.

    Args:
        cluster_identifier: The cluster identifier to resolve.

    Returns:
        The matching RedshiftCluster model.

    Raises:
        ToolError: If no discovered cluster carries that identifier.
    """
    cached = _resolved.get(cluster_identifier)
    if cached is not None and time.monotonic() - cached[0] < CLUSTER_RESOLVE_TTL:
        return cached[1]

    denied: set[str] = set()
    discovered = await discover_clusters(denied_sink=denied)

    # Every entry is cached, not just the one asked for, since the call that found them has
    # already been paid for. A miss caches nothing, so a cluster that appears later is found on
    # the next resolve rather than after this expires.
    now = time.monotonic()
    for cluster in discovered:
        _resolved[cluster.identifier] = (now, cluster)

    for cluster in discovered:
        if cluster.identifier == cluster_identifier:
            return cluster

    # A half of discovery IAM refused leaves its clusters out of this list and out of
    # list_clusters alike, so "not found" would name the wrong cause and send the caller to a
    # tool that omits it too.
    hidden = (
        f' Listing {" and ".join(sorted(denied))} clusters was denied, so one of that kind is '
        f'absent here and from list_clusters; grant the listing permission to address it.'
        if denied
        else ''
    )

    raise ToolError(
        f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster '
        f'identifiers.{hidden}'
    )
