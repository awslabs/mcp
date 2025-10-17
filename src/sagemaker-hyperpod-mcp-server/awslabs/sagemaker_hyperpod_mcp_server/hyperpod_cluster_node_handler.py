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

"""HyperPod cluster node handler for the HyperPod MCP Server."""

import os
from awslabs.sagemaker_hyperpod_mcp_server.aws_helper import AwsHelper
from awslabs.sagemaker_hyperpod_mcp_server.consts import (
    BATCH_DELETE_OPERATION,
    DESCRIBE_NODE_OPERATION,
    LIST_CLUSTERS_OPERATION,
    LIST_NODES_OPERATION,
    NODE_OPERATIONS,
    SUPPORTED_REGIONS,
    UPDATE_SOFTWARE_OPERATION,
)
from awslabs.sagemaker_hyperpod_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.sagemaker_hyperpod_mcp_server.models import (
    BatchDeleteClusterNodesError,
    BatchDeleteClusterNodesResponse,
    ClusterEbsVolumeConfig,
    ClusterInstancePlacement,
    ClusterInstanceStatusDetails,
    ClusterInstanceStorageConfig,
    ClusterLifeCycleConfig,
    ClusterNodeDetails,
    ClusterNodeSummary,
    ClusterSummary,
    DeploymentConfiguration,
    DescribeClusterNodeResponse,
    ListClusterNodesResponse,
    ListClustersResponse,
    UpdateClusterSoftwareInstanceGroupSpecification,
    UpdateClusterSoftwareResponse,
    VpcConfig,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field, validate_call
from typing import Any, List, Literal, Optional, Union


class HyperPodClusterNodeHandler:
    """Handler for HyperPod cluster node operations in the HyperPod MCP Server.

    This class provides tools for interacting with SageMaker HyperPod cluster nodes.
    """

    def __init__(
        self,
        mcp,
        allow_write: bool = False,
        allow_sensitive_data_access: bool = False,
    ):
        """Initialize the HyperPod cluster node handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # Register tools
        # temp workaround for update cluster, remove once update is fixed
        self.mcp.tool(name='describe_hp_cluster')(self.describe_hp_cluster)
        self.mcp.tool(name='update_hp_cluster')(self.update_hp_cluster)

        self.mcp.tool(name='manage_hyperpod_cluster_nodes')(self.manage_hyperpod_cluster_nodes)

    def get_sagemaker_client(
        self,
        ctx: Context,
        region_name: Optional[SUPPORTED_REGIONS] = None,
        profile_name: Optional[str] = None,
    ):
        """Get a SageMaker client for the specified region and profile.

        Args:
            ctx: The MCP context
            region_name: Optional AWS region name
            profile_name: Optional AWS profile name. Using the correct profile is important
                          for successful API calls, especially for SageMaker HyperPod operations.

        Returns:
            A boto3 SageMaker client
        """
        # Set AWS_PROFILE environment variable if profile_name is provided
        if profile_name:
            log_with_request_id(ctx, LogLevel.INFO, f'Using AWS profile: {profile_name}')
            os.environ['AWS_PROFILE'] = profile_name

        return AwsHelper.create_boto3_client('sagemaker', region_name=region_name)

    @validate_call
    async def manage_hyperpod_cluster_nodes(
        self,
        ctx: Context,
        operation: NODE_OPERATIONS = Field(
            description='Operation to perform: list_clusters, list_nodes, describe_node, update_software, or batch_delete. Choose "list_clusters" or "list_nodes" or "describe_node" for read-only operations when write access is disabled.',
        ),
        cluster_name: Optional[str] = Field(
            None,
            description='The name of the cluster. Required for all operations except "list_clusters".',
        ),
        node_id: Optional[str] = Field(
            None,
            description='The ID of the SageMaker HyperPod cluster node. Required for "describe_node" operation.',
        ),
        node_ids: Optional[List[str]] = Field(
            None,
            description='The list of node IDs to delete from the cluster. Required for "batch_delete" operation.',
        ),
        # Parameters for list_clusters operation
        max_results: Optional[int] = Field(
            10,
            description='The maximum number of results to return in the response. Default: 10. Used for "list_clusters" and "list_nodes" operations.',
            ge=1,
            le=100,
        ),
        next_token: Optional[str] = Field(
            None,
            description='If the response to a previous request was truncated, the response includes a NextToken. To retrieve the next set of results, use the token in the next request. Used for "list_clusters" and "list_nodes" operations.',
        ),
        name_contains: Optional[str] = Field(
            None,
            description='A filter that returns only clusters whose name contains the specified string. Used for "list_clusters" operation.',
        ),
        # Parameters for list_nodes operation
        creation_time_after: Optional[str] = Field(
            None,
            description='Filter for nodes/clusters created after the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00Z), date only (e.g., 2014-10-01), or Unix time in seconds. Used for "list_clusters" and "list_nodes" operations.',
        ),
        creation_time_before: Optional[str] = Field(
            None,
            description='Filter for nodes/clusters created before the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00Z), date only (e.g., 2014-10-01), or Unix time in seconds. Used for "list_clusters" and "list_nodes" operations.',
        ),
        instance_group_name_contains: Optional[str] = Field(
            None,
            description='Filter for nodes in instance groups whose name contains the specified string. Used for "list_nodes" operation.',
        ),
        sort_by: Optional[Literal['CREATION_TIME', 'NAME']] = Field(
            default='CREATION_TIME', description='The field to sort results by...'
        ),
        sort_order: Optional[Literal['Ascending', 'Descending']] = Field(
            default='Ascending',
            description='The sort order for results. The default is Ascending. Used for "list_clusters" and "list_nodes" operations.',
        ),
        training_plan_arn: Optional[str] = Field(
            None,
            description='The Amazon Resource Name (ARN) of the training plan to filter clusters by. Used for "list_clusters" operation.',
        ),
        # Parameters for update_software operation
        deployment_config: Optional[DeploymentConfiguration] = Field(
            None,
            description='The configuration to use when updating the AMI versions. Used for "update_software" operation.',
        ),
        instance_groups: Optional[List[UpdateClusterSoftwareInstanceGroupSpecification]] = Field(
            None,
            description='The array of instance groups for which to update AMI versions. Used for "update_software" operation.',
        ),
        # Common parameters
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> Union[
        ListClustersResponse,
        ListClusterNodesResponse,
        DescribeClusterNodeResponse,
        UpdateClusterSoftwareResponse,
        BatchDeleteClusterNodesResponse,
    ]:
        """Manage SageMaker HyperPod clusters and nodes with both read and write operations.

        This tool provides operations for managing SageMaker HyperPod clusters and nodes, including listing clusters,
        listing nodes, describing a specific node, updating cluster software, and deleting nodes. It serves as a consolidated
        interface for all cluster and node-related operations, simplifying the management of HyperPod resources.

        ## Operations
        - **list_clusters**: List SageMaker HyperPod clusters with options for pagination and filtering
        - **list_nodes**: List nodes in a SageMaker HyperPod cluster with options for pagination and filtering
        - **describe_node**: Get detailed information about a specific node in a SageMaker HyperPod cluster
        - **update_software**: Update the software for a SageMaker HyperPod cluster
        - **batch_delete**: Delete multiple nodes from a SageMaker HyperPod cluster in a single operation

        ## Response Information
        The response type varies based on the operation:
        - list_clusters: Returns ListClustersResponse with a list of clusters
        - list_nodes: Returns ListClusterNodesResponse with a list of nodes
        - describe_node: Returns DescribeClusterNodeResponse with detailed node information
        - update_software: Returns UpdateClusterSoftwareResponse with the cluster ARN
        - batch_delete: Returns BatchDeleteClusterNodesResponse with details of the deletion operation

        ## Important Notes
        - ALWAYS show the important notes for operations batch_delete and update_software BEFORE execute the operations
        - For update_software:
            The UpgradeClusterSoftware API call may impact your SageMaker HyperPod cluster uptime and availability. Plan accordingly to mitigate potential disruptions to your workloads
        - For batch_delete:
            - BEFORE running the tool, ALWAYS remind user all followings
            - To safeguard your work, back up your data to Amazon S3 or an FSx for Lustre file system before invoking
            the API on a worker node group. This will help prevent any potential data loss from the instance root volume.
            For more information about backup, see Use the backup script provided by SageMaker HyperPod:
            https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-backup-restore.html
            - If you want to invoke this API on an existing cluster, you'll first need to patch the cluster by running
            the UpdateClusterSoftware API. For more information about patching a cluster, see Update the SageMaker
            HyperPod platform software of a cluster:
            https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-hyperpod-update-software.html
            - Deleting nodes will permanently remove them from the cluster
            - This operation cannot be undone
            - Ensure you have selected the correct nodes before proceeding
            - This operation requires write access to be enabled for the handler

        ## Usage Tips
        - Use "list_clusters" operation to get an overview of all available clusters in a specified region
        - Use "list_nodes" operation to get an overview of all nodes in a specific cluster
        - Use "describe_node" operation to get detailed information about a specific node
        - Use "update_software" operation to update the software on all nodes or specific instance groups
        - Use "batch_delete" operation to delete multiple nodes in a single request
        - Specify region_name to operate on a cluster in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions

        ## Fallback Options:
        - If this tool fails, advise using AWS SageMaker CLI alternatives:
            - List clusters: `aws sagemaker list-clusters --region <cluster_region>`
            - List nodes: `aws sagemaker list-cluster-nodes --cluster-name <name> --region <cluster_region>`
            - Describe node: `aws sagemaker describe-cluster-node --cluster-name <name> --node-id <id> --region <cluster_region>`
            - Update software: `aws sagemaker update-cluster-software --cluster-name <name> --region <cluster_region>`
            - Delete nodes: `aws sagemaker batch-delete-cluster-nodes --cluster-name <name> --node-ids <ids> --region <cluster_region>`
        - Or, as another alternative: Advise using SageMaker HyperPod console for cluster and node management

        Args:
            ctx: MCP context
            operation: Operation to perform (list_clusters, list_nodes, describe_node, update_software, or batch_delete)
            cluster_name: The name of the cluster (required for all operations except list_clusters)
            node_id: The ID of the node (required for describe_node operation)
            node_ids: List of node IDs to delete (required for batch_delete operation)
            max_results: Maximum number of results to return (for list_clusters and list_nodes operations)
            next_token: Token for pagination (for list_clusters and list_nodes operations)
            name_contains: Filter clusters by name (for list_clusters operation)
            creation_time_after: Filter by creation time after (for list_clusters and list_nodes operations)
            creation_time_before: Filter by creation time before (for list_clusters and list_nodes operations)
            instance_group_name_contains: Filter by instance group name (for list_nodes operation)
            sort_by: Sort field (for list_clusters and list_nodes operations)
            sort_order: Sort order (for list_clusters and list_nodes operations)
            training_plan_arn: Filter clusters by training plan ARN (for list_clusters operation)
            deployment_config: Configuration for the update process (for update_software operation)
            instance_groups: Specific instance groups to update (for update_software operation)
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            Union[ListClustersResponse, ListClusterNodesResponse, DescribeClusterNodeResponse, UpdateClusterSoftwareResponse, BatchDeleteClusterNodesResponse]:
            Response specific to the operation performed
        """
        try:
            # Validate operation-specific required parameters
            if operation != 'list_clusters' and cluster_name is None:
                raise ValueError(
                    'cluster_name is required for all operations except list_clusters'
                )
            if operation == 'describe_node' and node_id is None:
                raise ValueError('node_id is required for describe_node operation')
            if operation == 'batch_delete' and (node_ids is None or len(node_ids) == 0):
                raise ValueError('node_ids is required for batch_delete operation')

            # Set default values for None parameters to satisfy type checker
            if max_results is None:
                max_results = 10

            # Check if write access is disabled and trying to perform a mutating operation
            if not self.allow_write and operation in [
                UPDATE_SOFTWARE_OPERATION,
                BATCH_DELETE_OPERATION,
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                # Return appropriate response type based on operation
                if operation == UPDATE_SOFTWARE_OPERATION:
                    return UpdateClusterSoftwareResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_arn='',
                    )
                elif operation == BATCH_DELETE_OPERATION:
                    # Ensure cluster_name is not None for the response
                    safe_cluster_name = cluster_name if cluster_name is not None else ''
                    return BatchDeleteClusterNodesResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        cluster_name=safe_cluster_name,
                        successful=[],
                        failed=None,
                    )

            # Dispatch to the appropriate operation handler
            if operation == LIST_CLUSTERS_OPERATION:
                return await self._list_hp_clusters(
                    ctx=ctx,
                    max_results=max_results,
                    next_token=next_token,
                    name_contains=name_contains,
                    creation_time_after=creation_time_after,
                    creation_time_before=creation_time_before,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    training_plan_arn=training_plan_arn,
                    region_name=region_name,
                    profile_name=profile_name,
                )
            elif operation == LIST_NODES_OPERATION:
                # Ensure cluster_name is not None
                if cluster_name is None:
                    raise ValueError('cluster_name is required for list_nodes operation')
                return await self._list_hp_cluster_nodes(
                    ctx=ctx,
                    cluster_name=cluster_name,
                    creation_time_after=creation_time_after,
                    creation_time_before=creation_time_before,
                    instance_group_name_contains=instance_group_name_contains,
                    max_results=max_results,
                    next_token=next_token,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    region_name=region_name,
                    profile_name=profile_name,
                )
            elif operation == DESCRIBE_NODE_OPERATION:
                # Ensure cluster_name and node_id are not None
                if cluster_name is None:
                    raise ValueError('cluster_name is required for describe_node operation')
                if node_id is None:
                    raise ValueError('node_id is required for describe_node operation')
                return await self._describe_hp_cluster_node(
                    ctx=ctx,
                    cluster_name=cluster_name,
                    node_id=node_id,
                    region_name=region_name,
                    profile_name=profile_name,
                )
            elif operation == UPDATE_SOFTWARE_OPERATION:
                # Ensure cluster_name is not None
                if cluster_name is None:
                    raise ValueError('cluster_name is required for update_software operation')
                return await self._update_hp_cluster_software(
                    ctx=ctx,
                    cluster_name=cluster_name,
                    deployment_config=deployment_config,
                    instance_groups=instance_groups,
                    region_name=region_name,
                    profile_name=profile_name,
                )
            elif operation == 'batch_delete':
                # Ensure cluster_name and node_ids are not None
                if cluster_name is None:
                    raise ValueError('cluster_name is required for batch_delete operation')
                if node_ids is None:
                    raise ValueError('node_ids is required for batch_delete operation')
                return await self._batch_delete_hp_cluster_nodes(
                    ctx=ctx,
                    cluster_name=cluster_name,
                    node_ids=node_ids,
                    region_name=region_name,
                    profile_name=profile_name,
                )
            else:
                error_message = f'Invalid operation: {operation}. Must be one of: {LIST_CLUSTERS_OPERATION}, {LIST_NODES_OPERATION}, {DESCRIBE_NODE_OPERATION}, {UPDATE_SOFTWARE_OPERATION}, {BATCH_DELETE_OPERATION}'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                # Default to ListClusterNodesResponse for invalid operations
                return ListClusterNodesResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    nodes=[],
                    next_token=None,
                )
        except ValueError as e:
            # Re-raise ValueError for parameter validation errors
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_hyperpod_cluster_nodes: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            # Default to ListClusterNodesResponse for general exceptions
            return ListClusterNodesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                nodes=[],
                next_token=None,
            )

    async def _list_hp_clusters(
        self,
        ctx: Context,
        max_results: int = Field(
            10,
            description='The maximum number of clusters to return in the response. Default: 10.',
            ge=1,
            le=100,
        ),
        next_token: Optional[str] = Field(
            None,
            description='If the response to a previous ListClusters request was truncated, the response includes a NextToken. To retrieve the next set of clusters, use the token in the next request.',
        ),
        name_contains: Optional[str] = Field(
            None,
            description='A filter that returns only clusters whose name contains the specified string.',
        ),
        creation_time_after: Optional[str] = Field(
            None,
            description='A filter that returns only clusters created after the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00.000Z), date only (e.g., 2014-10-01), or Unix time in seconds.',
        ),
        creation_time_before: Optional[str] = Field(
            None,
            description='A filter that returns only clusters created before the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00.000Z), date only (e.g., 2014-10-01), or Unix time in seconds.',
        ),
        sort_by: Optional[Literal['NAME', 'CREATION_TIME']] = Field(
            default='CREATION_TIME',
            description='The field to sort results by. The default is CREATION_TIME.',
        ),
        sort_order: Optional[Literal['Ascending', 'Descending']] = Field(
            default='Ascending',
            description='The sort order for results. The default is Ascending.',
        ),
        training_plan_arn: Optional[str] = Field(
            None,
            description='The Amazon Resource Name (ARN) of the training plan to filter clusters by.',
        ),
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> ListClustersResponse:
        """List SageMaker HyperPod clusters.

        This tool lists SageMaker HyperPod clusters with options for pagination and filtering.
        It returns information about each cluster including name, ARN, status, creation time,
        and training plan ARNs.

        ## Response Information
        The response includes a summary of each cluster with cluster name, ARN, status,
        creation time, and training plan ARNs.

        ## Usage Tips
        - Use max_results and next_token for pagination when there are many clusters
        - Use name_contains to filter clusters by name
        - Use creation_time_after and creation_time_before to filter by creation time, input should be formated to something like 2014-10-01T20:30:00.000Z, 2014-10-01T12:30:00.000-08:00, 2014-10-01, 1412195400
        - Use training_plan_arn to filter clusters by training plan
        - Use sort_by and sort_order to control the order of results
        - Specify region_name to list clusters in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions
          for SageMaker HyperPod operations

        Args:
            ctx: MCP context
            max_results: Maximum number of clusters to return (default: 10)
            next_token: Token for pagination (optional)
            name_contains: Filter clusters by name (optional)
            creation_time_after: Filter by creation time after as string (example format: 2014-10-01T20:30:00.000Z, 2014-10-01T12:30:00.000-08:00, 2014-10-01, 1412195400) (optional)
            creation_time_before: Filter by creation time before as string (example format: 2014-10-01T20:30:00.000Z, 2014-10-01T12:30:00.000-08:00, 2014-10-01, 1412195400) (optional)
            sort_by: Sort field (default: CREATION_TIME)
            sort_order: Sort order (default: Ascending)
            training_plan_arn: Filter clusters by training plan ARN (optional)
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            ListClustersResponse with list of clusters
        """
        try:
            # Get SageMaker client
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )

            # Prepare parameters for list_clusters API call
            params: dict[str, Any] = {}

            # Add parameters only if they are provided
            if max_results is not None:
                params['MaxResults'] = max_results
            if next_token is not None:
                params['NextToken'] = next_token
            if name_contains is not None:
                params['NameContains'] = name_contains
            if creation_time_after is not None:
                params['CreationTimeAfter'] = creation_time_after
            if creation_time_before is not None:
                params['CreationTimeBefore'] = creation_time_before
            if sort_by is not None:
                params['SortBy'] = sort_by
            if sort_order is not None:
                params['SortOrder'] = sort_order
            if training_plan_arn is not None:
                params['TrainingPlanArn'] = training_plan_arn

            # Call SageMaker API to list clusters
            log_with_request_id(
                ctx, LogLevel.INFO, f'Calling SageMaker list_clusters API with params: {params}'
            )
            try:
                response = sagemaker_client.list_clusters(**params)
                log_with_request_id(
                    ctx, LogLevel.INFO, f'SageMaker list_clusters API response: {response}'
                )
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.ERROR, f'SageMaker list_clusters API error: {str(e)}'
                )
                raise

            # Extract clusters from response
            clusters = []
            for cluster in response.get('ClusterSummaries', []):
                cluster_summary = ClusterSummary(
                    cluster_name=cluster.get('ClusterName', ''),
                    cluster_arn=cluster.get('ClusterArn', ''),
                    cluster_status=cluster.get('ClusterStatus', ''),
                    creation_time=str(cluster.get('CreationTime', '')),
                    training_plan_arns=cluster.get('TrainingPlanArns'),
                )
                clusters.append(cluster_summary)

            # Get next token for pagination
            next_token_response = response.get('NextToken')

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(clusters)} SageMaker HyperPod clusters',
            )

            # Return success response
            return ListClustersResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully listed {len(clusters)} SageMaker HyperPod clusters',
                    )
                ],
                clusters=clusters,
                next_token=next_token_response,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to list SageMaker HyperPod clusters: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return ListClustersResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                clusters=[],
                next_token=None,
            )

    async def describe_hp_cluster(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name of the cluster to describe.',
        ),
        region_name: SUPPORTED_REGIONS = Field(
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ):
        """Describe a SageMaker HyperPod cluster.

        Args:
            ctx: MCP context
            cluster_name: REQUIRED - Target cluster for describe cluster api
            region_name: REQUIRED - AWS region name
            profile_name: AWS profile name (optional)

        ## Fallback Options:
        - If this tool fails, advise using AWS SageMaker CLI option: `aws sagemaker describe-cluster --cluster-name <name> --region <cluster_region>`
        - Or as another alternative, advise checking directly in the SageMaker HyperPod console (Amazon SageMaker AI → HyperPod Clusters → Cluster Management → select cluster)

        Returns:
            describe cluster response
        """
        sagemaker_client = self.get_sagemaker_client(
            ctx, region_name=region_name, profile_name=profile_name
        )
        params = {'ClusterName': cluster_name}
        response = sagemaker_client.describe_cluster(**params)
        return response

    async def update_hp_cluster(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name of the cluster to update.',
        ),
        instance_groups: list = Field(
            ...,
            description='List of instance groups to update.',
        ),
        region_name: SUPPORTED_REGIONS = Field(
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ):
        """Update a SageMaker HyperPod clusters.

        Notes:
            - before using this tool, ensure you first have the most recent cluster instance group configurations by first calling the describe_hp_cluster tool first.
            - modify the instance group configuration based on user's request
            - important: Use "InstanceCount" (NOT "CurrentCount" or "TargetCount") for desired target count
            - pass the configuration back in the instance group parameter
            - example instance groups parameter
            "instance_groups": [
        ⋮        {
        ⋮          "OverrideVpcConfig": {
        ⋮            "SecurityGroupIds": [
        ⋮              "<>"
        ⋮            ],
        ⋮            "Subnets": [
        ⋮              "<>"
        ⋮            ]
        ⋮          },
        ⋮          "InstanceCount": <>,
        ⋮          "InstanceGroupName": "<>",
        ⋮          "InstanceStorageConfigs": [
        ⋮            {
        ⋮              "EbsVolumeConfig": {
        ⋮                "VolumeSizeInGB": <>
        ⋮              }
        ⋮            }
        ⋮          ],
        ⋮          "LifeCycleConfig": {
        ⋮            "SourceS3Uri": "<>",
        ⋮            "OnCreate": "<>"
        ⋮          },
        ⋮          "InstanceType": "<>",
        ⋮          "ThreadsPerCore": <>,
        ⋮          "ExecutionRole": "<>"
        ⋮        }
        ⋮      ],

        ## Fallback Options:
        - If this tool fails, advise using AWS SageMaker CLI option: `aws sagemaker update-cluster  --region <cluster_region>` with all appropriate parameters
        - Or as another alternative, advise making updates directly in the SageMaker HyperPod console (Amazon SageMaker AI → HyperPod Clusters → Cluster Management → select cluster → Edit)
        - To verify results: use CLI `aws sagemaker describe-cluster --cluster-name <name>` or directly verify in console

        Args:
            ctx: MCP context
            cluster_name: REQUIRED: cluster name to update
            instance_groups: REQUIRED: instance group configurations
            region_name: REQUIRED - AWS region name
            profile_name: AWS profile name (optional)

        Returns:
            update cluster response
        """
        if not self.allow_write:
            error_msg = 'Write access is not enabled for this handler. Cannot update cluster.'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return {'isError': True, 'errorMessage': error_msg}

        # First try-catch: Create SageMaker client and prepare parameters
        try:
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )
            params = {'ClusterName': cluster_name, 'InstanceGroups': instance_groups}
        except Exception as e:
            error_msg = f'Failed to prepare SageMaker client or parameters: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return {'isError': True, 'errorMessage': error_msg}

        # Second try-catch: Make the API call
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Calling SageMaker update_cluster API with params: {params}',
            )
            response = sagemaker_client.update_cluster(**params)
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'SageMaker update_cluster API response: {response}',
            )
        except Exception as e:
            error_msg = f'SageMaker update_cluster API error: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)
            return {'isError': True, 'errorMessage': error_msg}

        # Log success
        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Successfully updated SageMaker HyperPod cluster: {cluster_name}',
        )

        return response

    async def _describe_hp_cluster_node(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name of the cluster.',
        ),
        node_id: str = Field(
            ...,
            description='The ID of the SageMaker HyperPod cluster node.',
            min_length=1,
            max_length=256,
            pattern=r'i-[a-f0-9]{8}(?:[a-f0-9]{9})?',
        ),
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> DescribeClusterNodeResponse:
        """Describe a SageMaker HyperPod cluster node.

        This tool describes a specific node in a SageMaker HyperPod cluster.
        It returns detailed information about the node including instance group name, instance ID, instance status,
        instance type, launch time, last software update time, and other configuration details.

        ## Response Information
        The response includes detailed information about the node including:
        - Instance group name and ID
        - Instance status and type
        - Launch time and last software update time
        - Storage configurations
        - Network configurations
        - Placement information
        - And more

        ## Usage Tips
        - Use this tool to get detailed information about a specific node in a cluster
        - You need both the cluster name and node ID to identify the node
        - Specify region_name to describe a node in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions
          for SageMaker HyperPod operations

        Args:
            ctx: MCP context
            cluster_name: The name of the cluster
            node_id: The ID of the SageMaker HyperPod cluster node
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            DescribeClusterNodeResponse with node details
        """
        try:
            # Get SageMaker client
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )

            # Prepare parameters for describe_cluster_node API call
            params = {'ClusterName': cluster_name, 'NodeId': node_id}

            # Call SageMaker API to describe cluster node
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Calling SageMaker describe_cluster_node API with params: {params}',
            )
            try:
                response = sagemaker_client.describe_cluster_node(**params)
                log_with_request_id(
                    ctx, LogLevel.INFO, f'SageMaker describe_cluster_node API response: {response}'
                )
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.ERROR, f'SageMaker describe_cluster_node API error: {str(e)}'
                )
                raise

            # Extract node details from response
            node_details_data = response.get('NodeDetails', {})

            # Extract instance status details
            instance_status_data = node_details_data.get('InstanceStatus', {})
            instance_status_details = ClusterInstanceStatusDetails(
                status=instance_status_data.get(
                    'Status', 'Pending'
                ),  # Default to Pending if not provided
                message=instance_status_data.get('Message'),
            )

            # Process instance storage configs
            instance_storage_configs = []
            for storage_config in node_details_data.get('InstanceStorageConfigs', []):
                # Process EBS volume config
                ebs_volume_config = None
                if 'EbsVolumeConfig' in storage_config:
                    ebs_volume_config = ClusterEbsVolumeConfig(
                        volume_size_in_gb=storage_config['EbsVolumeConfig'].get('VolumeSizeInGb')
                    )

                # Create instance storage config
                instance_storage_config = ClusterInstanceStorageConfig(
                    ebs_volume_config=ebs_volume_config
                )
                instance_storage_configs.append(instance_storage_config)

            # Process life cycle config
            life_cycle_config = None
            if (
                'LifeCycleConfig' in node_details_data
                and node_details_data['LifeCycleConfig'].get('OnCreate')
                and node_details_data['LifeCycleConfig'].get('SourceS3Uri')
            ):
                life_cycle_config = ClusterLifeCycleConfig(
                    on_create=node_details_data['LifeCycleConfig'].get('OnCreate'),
                    source_s3_uri=node_details_data['LifeCycleConfig'].get('SourceS3Uri'),
                )

            # Process override VPC config
            override_vpc_config = None
            if 'OverrideVpcConfig' in node_details_data:
                override_vpc_config = VpcConfig(
                    security_group_ids=node_details_data['OverrideVpcConfig'].get(
                        'SecurityGroupIds'
                    ),
                    subnets=node_details_data['OverrideVpcConfig'].get('Subnets'),
                )

            # Process placement
            placement = None
            if 'Placement' in node_details_data:
                placement = ClusterInstancePlacement(
                    availability_zone=node_details_data['Placement'].get('AvailabilityZone'),
                    availability_zone_id=node_details_data['Placement'].get('AvailabilityZoneId'),
                )

            # Create node details
            node_details = ClusterNodeDetails(
                instance_group_name=node_details_data.get('InstanceGroupName', ''),
                instance_id=node_details_data.get('InstanceId', ''),
                instance_status=instance_status_details,
                instance_storage_configs=instance_storage_configs
                if instance_storage_configs
                else None,
                instance_type=node_details_data.get('InstanceType', ''),
                last_software_update_time=str(node_details_data.get('LastSoftwareUpdateTime'))
                if node_details_data.get('LastSoftwareUpdateTime')
                else None,
                launch_time=str(node_details_data.get('LaunchTime'))
                if node_details_data.get('LaunchTime')
                else None,
                life_cycle_config=life_cycle_config,
                override_vpc_config=override_vpc_config,
                placement=placement,
                private_dns_hostname=node_details_data.get('PrivateDnsHostname'),
                private_primary_ip=node_details_data.get('PrivatePrimaryIp'),
                private_primary_ipv6=node_details_data.get('PrivatePrimaryIpv6'),
                threads_per_core=node_details_data.get('ThreadsPerCore'),
            )

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully described SageMaker HyperPod cluster node: {node_id}',
            )

            # Return success response
            return DescribeClusterNodeResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully described SageMaker HyperPod cluster node: {node_id}',
                    )
                ],
                node_details=node_details,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to describe SageMaker HyperPod cluster node: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return DescribeClusterNodeResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                node_details=None,
            )

    async def _list_hp_cluster_nodes(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name of the cluster.',
        ),
        creation_time_after: Optional[str] = Field(
            None,
            description='Filter for nodes created after the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00Z), date only (e.g., 2014-10-01), or Unix time in seconds.',
        ),
        creation_time_before: Optional[str] = Field(
            None,
            description='Filter for nodes created before the specified time. Accepts formats: ISO 8601 (e.g., 2014-10-01T20:30:00Z), date only (e.g., 2014-10-01), or Unix time in seconds.',
        ),
        instance_group_name_contains: Optional[str] = Field(
            None,
            description='Filter for nodes in instance groups whose name contains the specified string.',
        ),
        max_results: int = Field(
            10,
            description='The maximum number of nodes to return in the response. Default: 10.',
            ge=1,
            le=100,
        ),
        next_token: Optional[str] = Field(
            None,
            description='If the response to a previous ListClusterNodes request was truncated, the response includes a NextToken. To retrieve the next set of nodes, use the token in the next request.',
        ),
        sort_by: Optional[Literal['CREATION_TIME', 'NAME']] = Field(
            default='CREATION_TIME',
            description='The field to sort results by. The default is CREATION_TIME.',
        ),
        sort_order: Optional[Literal['Ascending', 'Descending']] = Field(
            default='Ascending',
            description='The sort order for results. The default is Ascending.',
        ),
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> ListClusterNodesResponse:
        """List SageMaker HyperPod cluster nodes.

        This tool lists nodes in a SageMaker HyperPod cluster with options for pagination and filtering.
        It returns information about each node including instance group name, instance ID, instance status,
        instance type, launch time, and last software update time.

        ## Response Information
        The response includes a summary of each node with instance group name, instance ID, instance status,
        instance type, launch time, and last software update time.

        ## Usage Tips
        - Use max_results and next_token for pagination when there are many nodes
            - Use instance_group_name_contains to filter nodes by instance group name
        - Use creation_time_after and creation_time_before to filter by creation time
        - Use sort_by and sort_order to control the order of results
        - Specify region_name to list nodes in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions
          for SageMaker HyperPod operations

        Args:
            ctx: MCP context
            cluster_name: The name of the cluster
            creation_time_after: Filter by creation time after as string (optional)
            creation_time_before: Filter by creation time before as string (optional)
            instance_group_name_contains: Filter by instance group name (optional)
            max_results: Maximum number of nodes to return (default: 10)
            next_token: Token for pagination (optional)
            sort_by: Sort field (default: CREATION_TIME)
            sort_order: Sort order (default: Ascending)
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            ListClusterNodesResponse with list of nodes
        """
        try:
            # Get SageMaker client
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )

            # Prepare parameters for list_cluster_nodes API call
            params: dict[str, Any] = {'ClusterName': cluster_name}

            # Add parameters only if they are provided
            if max_results is not None:
                params['MaxResults'] = max_results
            if next_token is not None:
                params['NextToken'] = next_token
            if instance_group_name_contains is not None:
                params['InstanceGroupNameContains'] = instance_group_name_contains
            if creation_time_after is not None:
                params['CreationTimeAfter'] = creation_time_after
            if creation_time_before is not None:
                params['CreationTimeBefore'] = creation_time_before
            if sort_by is not None:
                params['SortBy'] = sort_by
            if sort_order is not None:
                params['SortOrder'] = sort_order

            # Call SageMaker API to list cluster nodes
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Calling SageMaker list_cluster_nodes API with params: {params}',
            )
            try:
                response = sagemaker_client.list_cluster_nodes(**params)
                log_with_request_id(
                    ctx, LogLevel.INFO, f'SageMaker list_cluster_nodes API response: {response}'
                )
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.ERROR, f'SageMaker list_cluster_nodes API error: {str(e)}'
                )
                raise

            # Extract nodes from response
            nodes = []
            for node in response.get('ClusterNodeSummaries', []):
                # Extract instance status details
                instance_status_data = node.get('InstanceStatus', {})
                instance_status_details = ClusterInstanceStatusDetails(
                    status=instance_status_data.get(
                        'Status', 'Pending'
                    ),  # Default to Pending if not provided
                    message=instance_status_data.get('Message'),
                )

                node_summary = ClusterNodeSummary(
                    instance_group_name=node.get('InstanceGroupName', ''),
                    instance_id=node.get('InstanceId', ''),
                    instance_status=instance_status_details,
                    instance_type=node.get('InstanceType', ''),
                    launch_time=str(node.get('LaunchTime', '')),
                    last_software_update_time=str(node.get('LastSoftwareUpdateTime', ''))
                    if node.get('LastSoftwareUpdateTime')
                    else None,
                )
                nodes.append(node_summary)

            # Get next token for pagination
            next_token_response = response.get('NextToken')

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully listed {len(nodes)} SageMaker HyperPod cluster nodes',
            )

            # Return success response
            return ListClusterNodesResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully listed {len(nodes)} SageMaker HyperPod cluster nodes',
                    )
                ],
                nodes=nodes,
                next_token=next_token_response,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to list SageMaker HyperPod cluster nodes: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return ListClusterNodesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                nodes=[],
                next_token=None,
            )

    async def _update_hp_cluster_software(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name or ARN of the SageMaker HyperPod cluster to update for security patching.',
            min_length=0,
            max_length=256,
            pattern=r'(arn:aws[a-z\-]*:sagemaker:[a-z0-9\-]*:[0-9]{12}:cluster/[a-z0-9]{12})|([a-zA-Z0-9](-*[a-zA-Z0-9]){0,62})',
        ),
        deployment_config: Optional[DeploymentConfiguration] = Field(
            None,
            description='The configuration to use when updating the AMI versions.',
        ),
        instance_groups: Optional[List[UpdateClusterSoftwareInstanceGroupSpecification]] = Field(
            None,
            description='The array of instance groups for which to update AMI versions.',
        ),
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> UpdateClusterSoftwareResponse:
        """Update the software for a SageMaker HyperPod cluster.

        This tool updates the software for a SageMaker HyperPod cluster.
        It initiates a software update for all nodes in the cluster.

        ## Response Information
        The response includes the ARN of the cluster being updated.

        ## Usage Tips
        - Use this tool to update the software on all nodes in a SageMaker HyperPod cluster
        - Specify instance_groups to update only specific instance groups in the cluster
        - Configure deployment_config to control how the update is performed:
          - Use auto_rollback_configuration to specify alarms that trigger rollback
          - Use rolling_update_policy to control batch sizes during updates
          - Use wait_interval_in_seconds to control the wait time between updates
        - The update process may take some time to complete
        - You can check the status of the update using the list_hp_cluster_nodes tool
        - Specify region_name to update a cluster in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions
          for SageMaker HyperPod operations

        Args:
            ctx: MCP context
            cluster_name: The name or ARN of the cluster to update
            deployment_config: Configuration for the update process (optional)
            instance_groups: Specific instance groups to update (optional)
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            UpdateClusterSoftwareResponse with cluster ARN
        """
        try:
            # Get SageMaker client
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )

            # Prepare parameters for update_cluster_software API call
            params: dict[str, Any] = {'ClusterName': cluster_name}

            # Add deployment configuration if provided
            if deployment_config:
                deployment_config_dict: dict[str, Any] = {}

                # Add auto rollback configuration if provided
                if deployment_config.auto_rollback_configuration:
                    auto_rollback_config = []
                    for alarm in deployment_config.auto_rollback_configuration:
                        auto_rollback_config.append({'AlarmName': alarm.alarm_name})
                    if auto_rollback_config:
                        deployment_config_dict['AutoRollbackConfiguration'] = auto_rollback_config

                # Add rolling update policy if provided
                if deployment_config.rolling_update_policy:
                    rolling_update_policy = {}

                    # Add maximum batch size if provided
                    if deployment_config.rolling_update_policy.maximum_batch_size:
                        maximum_batch_size = {
                            'Type': deployment_config.rolling_update_policy.maximum_batch_size.type,
                            'Value': deployment_config.rolling_update_policy.maximum_batch_size.value,
                        }
                        rolling_update_policy['MaximumBatchSize'] = maximum_batch_size

                    # Add rollback maximum batch size if provided
                    if deployment_config.rolling_update_policy.rollback_maximum_batch_size:
                        rollback_maximum_batch_size = {
                            'Type': deployment_config.rolling_update_policy.rollback_maximum_batch_size.type,
                            'Value': deployment_config.rolling_update_policy.rollback_maximum_batch_size.value,
                        }
                        rolling_update_policy['RollbackMaximumBatchSize'] = (
                            rollback_maximum_batch_size
                        )

                    if rolling_update_policy:
                        deployment_config_dict['RollingUpdatePolicy'] = rolling_update_policy

                # Add wait interval in seconds if provided
                if deployment_config.wait_interval_in_seconds is not None:
                    deployment_config_dict['WaitIntervalInSeconds'] = (
                        deployment_config.wait_interval_in_seconds
                    )

                # Add deployment config to params if not empty
                if deployment_config_dict:
                    params['DeploymentConfig'] = deployment_config_dict

            # Add instance groups if provided
            if instance_groups:
                instance_groups_list = []
                for group in instance_groups:
                    instance_groups_list.append({'InstanceGroupName': group.instance_group_name})
                if instance_groups_list:
                    params['InstanceGroups'] = instance_groups_list

            # Call SageMaker API to update cluster software
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Calling SageMaker update_cluster_software API with params: {params}',
            )
            try:
                response = sagemaker_client.update_cluster_software(**params)
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'SageMaker update_cluster_software API response: {response}',
                )
            except Exception as e:
                log_with_request_id(
                    ctx, LogLevel.ERROR, f'SageMaker update_cluster_software API error: {str(e)}'
                )
                raise

            # Extract cluster ARN from response
            cluster_arn = response.get('ClusterArn', '')

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully initiated software update for SageMaker HyperPod cluster: {cluster_name}',
            )

            # Return success response
            return UpdateClusterSoftwareResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully initiated software update for SageMaker HyperPod cluster: {cluster_name}',
                    )
                ],
                cluster_arn=cluster_arn,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to update software for SageMaker HyperPod cluster: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return UpdateClusterSoftwareResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                cluster_arn='',
            )

    async def _batch_delete_hp_cluster_nodes(
        self,
        ctx: Context,
        cluster_name: str = Field(
            ...,
            description='The name of the cluster.',
            min_length=0,
            max_length=256,
            pattern=r'(arn:aws[a-z\-]*:sagemaker:[a-z0-9\-]*:[0-9]{12}:cluster/[a-z0-9]{12})|([a-zA-Z0-9](-*[a-zA-Z0-9]){0,62})',
        ),
        node_ids: List[str] = Field(
            ...,
            description='The list of node IDs to delete from the cluster.',
            min_length=1,
            max_length=99,
        ),
        region_name: Optional[SUPPORTED_REGIONS] = Field(
            'us-east-1',
            description='AWS region name. Default is us-east-1.',
        ),
        profile_name: Optional[str] = Field(
            None,
            description='AWS profile name. If not provided, uses the default profile.',
        ),
    ) -> BatchDeleteClusterNodesResponse:
        """Delete multiple nodes from a SageMaker HyperPod cluster.

        This tool deletes multiple nodes from a SageMaker HyperPod cluster in a single operation.
        It returns information about the deleted nodes and any failures that occurred during deletion.

        ## Response Information
        The response includes the cluster name, a list of successfully deleted node IDs,
        and details about any failed node deletions.

        ## Note
        - For SageMaker HyperPod clusters using the Slurm workload manager, you cannot remove instances that are
          configured as Slurm controller nodes.
        - If you need to delete more than 99 instances, contact Support for assistance.

        ## Usage Tips
        - Use this tool to delete multiple nodes from a cluster in a single operation
        - You can delete up to 99 nodes in a single request
        - If some node deletions fail, the response will include details about the failures
        - Specify region_name to delete nodes in a specific region
        - Specify profile_name to use a specific AWS profile with appropriate permissions
          for SageMaker HyperPod operations

        Args:
            ctx: MCP context
            cluster_name: The name of the cluster
            node_ids: List of node IDs to delete from the cluster
            region_name: AWS region name (default: us-east-1)
            profile_name: AWS profile name (optional)

        Returns:
            BatchDeleteClusterNodesResponse with details of the deletion operation
        """
        try:
            # Get SageMaker client
            sagemaker_client = self.get_sagemaker_client(
                ctx, region_name=region_name, profile_name=profile_name
            )

            # Prepare parameters for batch_delete_cluster_nodes API call
            params = {'ClusterName': cluster_name, 'NodeIds': node_ids}

            # Call SageMaker API to batch delete cluster nodes
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Calling SageMaker batch_delete_cluster_nodes API with params: {params}',
            )
            try:
                response = sagemaker_client.batch_delete_cluster_nodes(**params)
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'SageMaker batch_delete_cluster_nodes API response: {response}',
                )
            except Exception as e:
                log_with_request_id(
                    ctx,
                    LogLevel.ERROR,
                    f'SageMaker batch_delete_cluster_nodes API error: {str(e)}',
                )
                raise

            # Extract successful and failed deletions from response
            successful_node_ids = response.get('Successful', [])
            failed_deletions = response.get('Failed', [])

            # Convert failed deletions to BatchDeleteClusterNodesError objects
            failed_deletions_list = []
            for failure in failed_deletions:
                failed_deletions_list.append(
                    BatchDeleteClusterNodesError(
                        code=failure.get('Code', ''),
                        message=failure.get('Message', ''),
                        node_id=failure.get('NodeId', ''),
                    )
                )

            # Log success
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Successfully deleted {len(successful_node_ids)} nodes from SageMaker HyperPod cluster: {cluster_name}',
            )
            if failed_deletions_list:
                log_with_request_id(
                    ctx,
                    LogLevel.WARNING,
                    f'Failed to delete {len(failed_deletions_list)} nodes from SageMaker HyperPod cluster: {cluster_name}',
                )

            # Return success response
            return BatchDeleteClusterNodesResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully deleted {len(successful_node_ids)} nodes from SageMaker HyperPod cluster: {cluster_name}. Failed deletions: {len(failed_deletions_list)}',
                    )
                ],
                cluster_name=cluster_name,
                successful=successful_node_ids,
                failed=failed_deletions_list if failed_deletions_list else None,
            )

        except Exception as e:
            # Log error
            error_msg = f'Failed to delete nodes from SageMaker HyperPod cluster: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            # Return error response
            return BatchDeleteClusterNodesResponse(
                isError=True,
                content=[TextContent(type='text', text=error_msg)],
                cluster_name=cluster_name,
                successful=[],
                failed=None,
            )
