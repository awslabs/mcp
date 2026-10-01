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


# The last discovery that answered for both types: when it ran, and every cluster and workgroup it
# found. `resolve_cluster` answers from it until it is CLUSTER_RESOLVE_TTL old, and each such
# discovery replaces it, `list_clusters`' included. One a denial cut short clears it.
_discovered: tuple[float, list[RedshiftCluster]] | None = None


def _fetch_provisioned_clusters() -> list[dict]:
    """Page through every provisioned cluster.

    Synchronous, and called through asyncio.to_thread: boto3 blocks, and client construction
    on first use blocks for seconds, which would stall every other call on the event loop.

    Returns:
        The raw DescribeClusters entries.
    """
    paginator = client_manager.redshift_client().get_paginator('describe_clusters')
    return [cluster for page in paginator.paginate() for cluster in page.get('Clusters', [])]


def _fetch_serverless_workgroups() -> list[tuple[dict, list[dict]]]:
    """Page through every serverless workgroup and fetch each one's tags.

    Synchronous, and called through asyncio.to_thread, for the same reason as its provisioned
    counterpart. One further call per workgroup, so this blocks for longer still.

    ListWorkgroups answers with the same Workgroup shape GetWorkgroup does, every member
    included, so the detail call this used to make per workgroup added nothing. It also could not
    fail safely: a workgroup deleted between the two answers ResourceNotFoundException, which is
    not a denial, so it failed all of discovery - and with it every statement on every healthy
    provisioned cluster, once the stored discovery had expired.

    Returns:
        Pairs of the ListWorkgroups entry and its tags.
    """
    serverless_client = client_manager.redshift_serverless_client()
    paginator = serverless_client.get_paginator('list_workgroups')

    # Tags are asked for by themselves because the Workgroup shape has no member for them, where
    # DescribeClusters carries a provisioned cluster's inline.
    tags_warned = False
    workgroups: list[tuple[dict, list[dict]]] = []

    for page in paginator.paginate():
        for workgroup in page.get('workgroups', []):
            arn = workgroup.get('workgroupArn')
            tags: list[dict] = []
            # Tags are keyed by ARN, so there is nothing to ask for without one.
            if arn is not None:
                try:
                    tags = serverless_client.list_tags_for_resource(resourceArn=arn).get(
                        'tags', []
                    )
                except Exception as e:  # noqa: BLE001 - see below
                    # Best effort against every failure, not a denial alone: tags are the one field
                    # this carries, and raising costs the whole cluster list.
                    if not tags_warned:
                        # What is suppressed after the first failure is the warning, not the call.
                        # Suppressing the call instead let a denial scoped to one ARN - an
                        # ordinary least-privilege policy - report every workgroup the principal
                        # can read as untagged.
                        tags_warned = True
                        logger.warning(
                            'Reporting a serverless workgroup as untagged; '
                            f'redshift-serverless:ListTagsForResource failed: {e}'
                        )

            workgroups.append((workgroup, tags))

    return workgroups


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
        # other type.
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


def _serverless_cluster(workgroup: dict, tags: list[dict]) -> RedshiftCluster:
    """Map one ListWorkgroups entry and its tags onto the model.

    Args:
        workgroup: One entry from ListWorkgroups, which carries the whole Workgroup shape.
        tags: The ListTagsForResource tags for that workgroup, empty if the call failed.

    Returns:
        The workgroup as this server reports it, in the same shape as a provisioned cluster.
    """
    endpoint = workgroup.get('endpoint', {})

    return RedshiftCluster(
        identifier=workgroup['workgroupName'],
        type='serverless',
        status=workgroup['status'].lower(),  # Lowercased, per _provisioned_cluster.
        # Serverless always exposes the built-in 'dev' database. Reporting the namespace's
        # configured default would require redshift-serverless:GetNamespace; callers can pass an
        # explicit database_name to the other tools instead.
        database_name='dev',
        endpoint=endpoint.get('address'),
        # The workgroup carries its own port too, which is the one a workgroup still creating its
        # endpoint has. Read from the endpoint alone, the port was reported absent while the
        # service was stating it.
        port=endpoint.get('port', workgroup.get('port')),
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
        publicly_accessible=workgroup.get('publiclyAccessible'),
        encrypted=True,  # Serverless is always encrypted
        tags={tag['key']: tag['value'] for tag in tags},
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
    global _discovered

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
        for workgroup, tags in await asyncio.to_thread(_fetch_serverless_workgroups):
            clusters.append(_serverless_cluster(workgroup, tags))
            serverless_count += 1

        logger.info(f'Found {serverless_count} serverless workgroups')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in ACCESS_DENIED:
            raise
        serverless_error = e
        if denied_sink is not None:
            denied_sink.add('serverless')
        logger.warning(f'Skipping serverless; IAM lacks permission: {e}')

    # Two discoveries that overlap can finish out of order and leave the older one stored, which
    # the TTL bounds; serialized instead, one stalled control-plane call held every other resolve
    # behind it.
    #
    # A discovery a denial cut short is not stored, because only a discovery knows what was
    # denied: stored, a refusal of the hidden type would blame the age of the lookup rather
    # than the denial. It clears the stored one instead, both halves denied included, so a
    # resolve sees what list_clusters sees: kept, the older one answered for the rest of its TTL,
    # and refused a cluster list_clusters had just shown.
    _discovered = None if provisioned_error or serverless_error else (time.monotonic(), clusters)

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


async def resolve_cluster(
    cluster_identifier: str, cluster_type: str, fresh: bool = False
) -> RedshiftCluster:
    """Resolve a cluster identifier and type to the discovered cluster.

    Answered from the last complete discovery until it is CLUSTER_RESOLVE_TTL old, because every
    statement resolves and a discovery costs a DescribeClusters, a ListWorkgroups and a
    ListTagsForResource per workgroup. Until then a cluster created, deleted or recreated as the
    other type goes unnoticed, and a refusal says how old the lookup is; `list_clusters`
    discovers every time and replaces it. Fields other than the identifier and the type, node
    type and status among them, are as old, so a caller that reads them passes `fresh`.

    A discovery a denial cut short is answered from, since a principal permanently denied one half
    has to keep working, but not stored: it clears the stored one, so every resolve discovers
    while the denial lasts.

    Args:
        cluster_identifier: The cluster identifier to resolve.
        cluster_type: `provisioned` or `serverless`.
        fresh: Discover even when the stored discovery would answer.

    Returns:
        The matching RedshiftCluster model.

    Raises:
        ToolError: If no discovered cluster of that type carries that identifier.
    """
    stored = _discovered
    if not fresh and stored is not None and time.monotonic() - stored[0] < CLUSTER_RESOLVE_TTL:
        clusters = stored[1]
        # A refusal from the stored discovery can be out of date: a cluster created since is not
        # in it. Said so, the caller looks again rather than taking the cluster for missing, or
        # moving to the other type a refusal names, which is a different warehouse.
        note = (
            f' Clusters were last looked up {int(time.monotonic() - stored[0])} seconds ago; '
            f'list_clusters looks again.'
        )
    else:
        denied: set[str] = set()
        clusters = await discover_clusters(denied_sink=denied)
        # A half of discovery IAM refused leaves its clusters out of this list and out of
        # list_clusters alike, so "not found" would name the wrong cause and send the caller to a
        # tool that omits it too. Only for the type the caller named: said of a provisioned
        # cluster with the serverless listing denied, it sent the caller to grant a permission
        # that could not help.
        note = (
            f' Listing {cluster_type} clusters was denied, so any of that type is absent here and '
            f'from list_clusters; grant the listing permission to address it.'
            if cluster_type in denied
            else ''
        )

    found = [cluster for cluster in clusters if cluster.identifier == cluster_identifier]
    for cluster in found:
        if cluster.type == cluster_type:
            return cluster

    if found:
        # Without `note`, a denial or an old lookup read as the cluster not existing, and named
        # the other type as what to use instead - a different warehouse holding its own data.
        raise ToolError(
            f'No {cluster_type} cluster named {cluster_identifier} was found. Found instead: a '
            f'{found[0].type} one.{note}'
        )

    raise ToolError(
        f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster '
        f'identifiers.{note}'
    )
