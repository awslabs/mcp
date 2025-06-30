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

"""EMREc2ClusterHandler for Data Processing MCP Server."""
import json
import os
import time
from awslabs.dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from awslabs.dataprocessing_mcp_server.models.emr_models import (
    CreateClusterResponse,
    DescribeClusterResponse,
    ModifyClusterResponse,
    ModifyClusterAttributesResponse,
    TerminateClustersResponse,
    ListClustersResponse,
    CreateSecurityConfigurationResponse,
    DeleteSecurityConfigurationResponse,
    DescribeSecurityConfigurationResponse,
    ListSecurityConfigurationsResponse,
)
from awslabs.dataprocessing_mcp_server.utils.consts import MCP_MANAGED_TAG_KEY, MCP_MANAGED_TAG_VALUE
from mcp.server.fastmcp import Context
from mcp.types import TextContent, Content
from pydantic import Field, BaseModel
from typing import Dict, List, Optional, Tuple, Union, cast, Any
from botocore.exceptions import ClientError, WaiterError


class EMREc2ClusterHandler:
    """Handler for Amazon EMR EC2 Cluster operations."""

    def __init__(
        self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False
    ):
        """Initialize the EMR EC2 Cluster handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.emr_client = AwsHelper.create_boto3_client("emr")

        # Register tools
        self.mcp.tool(name="manage_aws_emr_clusters")(self.manage_aws_emr_clusters)

    def _create_error_response(self, operation: str, error_message: str):
        """Create appropriate error response based on operation type."""
        content: List[Content] = [TextContent(type="text", text=error_message)]
        
        if operation == "create-cluster":
            return CreateClusterResponse(isError=True, content=content, cluster_id="", cluster_arn="", operation="create")
        elif operation == "describe-cluster":
            return DescribeClusterResponse(isError=True, content=content, cluster={})
        elif operation == "modify-cluster":
            return ModifyClusterResponse(isError=True, content=content, cluster_id="")
        elif operation == "modify-cluster-attributes":
            return ModifyClusterAttributesResponse(isError=True, content=content, cluster_id="")
        elif operation == "terminate-clusters":
            return TerminateClustersResponse(isError=True, content=content, cluster_ids=[])
        elif operation == "list-clusters":
            return ListClustersResponse(isError=True, content=content, clusters=[], count=0, marker="", operation="list")
        elif operation == "create-security-configuration":
            return CreateSecurityConfigurationResponse(isError=True, content=content, name="", creation_date_time="")
        elif operation == "delete-security-configuration":
            return DeleteSecurityConfigurationResponse(isError=True, content=content, name="")
        elif operation == "describe-security-configuration":
            return DescribeSecurityConfigurationResponse(isError=True, content=content, name="", security_configuration="", creation_date_time="")
        elif operation == "list-security-configurations":
            return ListSecurityConfigurationsResponse(isError=True, content=content, security_configurations=[], count=0, marker="", operation="list")
        else:
            return DescribeClusterResponse(isError=True, content=content, cluster={})

    async def manage_aws_emr_clusters(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description="Operation to perform: create-cluster, describe-cluster, modify-cluster, modify-cluster-attributes, terminate-clusters, list-clusters, create-security-configuration, delete-security-configuration, describe-security-configuration, list-security-configurations. Choose read-only operations when write access is disabled.",
        ),
        cluster_id: Optional[str] = Field(
            None,
            description="ID of the EMR cluster (required for describe-cluster, modify-cluster, modify-cluster-attributes).",
        ),
        cluster_ids: Optional[List[str]] = Field(
            None,
            description="List of EMR cluster IDs (required for terminate-clusters).",
        ),
        name: Optional[str] = Field(
            None,
            description="Name of the EMR cluster (required for create-cluster). Cannot contain <, >, $, |, or ` (backtick).",
        ),
        log_uri: Optional[str] = Field(
            None,
            description="The path to the Amazon S3 location where logs for the cluster are stored (optional for create-cluster).",
        ),
        log_encryption_kms_key_id: Optional[str] = Field(
            None,
            description="The KMS key used for encrypting log files. Available with EMR 5.30.0 and later, excluding EMR 6.0.0 (optional for create-cluster).",
        ),
        release_label: Optional[str] = Field(
            None,
            description="The Amazon EMR release label, which determines the version of open-source application packages installed on the cluster (required for create-cluster). Format: emr-x.x.x",
        ),
        applications: Optional[List[Dict[str, str]]] = Field(
            None,
            description='The applications to be installed on the cluster (optional for create-cluster). Example: [{"Name": "Hadoop"}, {"Name": "Spark"}]',
        ),
        instances: Optional[Dict[str, Any]] = Field(
            None,
            description="A specification of the number and type of Amazon EC2 instances (required for create-cluster). Must include instance groups or instance fleets configuration.",
        ),
        steps: Optional[List[Dict[str, Any]]] = Field(
            None,
            description="A list of steps to run on the cluster (optional for create-cluster). Each step contains Name, ActionOnFailure, and HadoopJarStep properties.",
        ),
        bootstrap_actions: Optional[List[Dict[str, Any]]] = Field(
            None,
            description="A list of bootstrap actions to run on the cluster (optional for create-cluster). Each action contains Name, ScriptBootstrapAction properties.",
        ),
        configurations: Optional[List[Dict[str, Any]]] = Field(
            None,
            description="A list of configurations to apply to the cluster (optional for create-cluster). Applies only to EMR releases 4.x and later.",
        ),
        visible_to_all_users: Optional[bool] = Field(
            None,
            description="Whether the cluster is visible to all IAM users of the AWS account (optional for create-cluster, default: true).",
        ),
        service_role: Optional[str] = Field(
            None,
            description="The IAM role that Amazon EMR assumes to access AWS resources on your behalf (optional for create-cluster).",
        ),
        job_flow_role: Optional[str] = Field(
            None,
            description="The IAM role for EC2 instances running the job flow (required for create-cluster when using temporary credentials).",
        ),
        security_configuration: Optional[str] = Field(
            None,
            description="The name of a security configuration to apply to the cluster (optional for create-cluster).",
        ),
        auto_scaling_role: Optional[str] = Field(
            None,
            description="An IAM role for automatic scaling policies (optional for create-cluster). Default role is EMR_AutoScaling_DefaultRole.",
        ),
        scale_down_behavior: Optional[str] = Field(
            None,
            description="The way that individual Amazon EC2 instances terminate when an automatic scale-in activity occurs (optional for create-cluster). Values: TERMINATE_AT_INSTANCE_HOUR, TERMINATE_AT_TASK_COMPLETION.",
        ),
        custom_ami_id: Optional[str] = Field(
            None,
            description="A custom Amazon Linux AMI for the cluster (optional for create-cluster). Available only in EMR releases 5.7.0 and later.",
        ),
        ebs_root_volume_size: Optional[int] = Field(
            None,
            description="The size, in GiB, of the EBS root device volume of the Linux AMI (optional for create-cluster). Available in EMR releases 4.x and later.",
        ),
        ebs_root_volume_iops: Optional[int] = Field(
            None,
            description="The IOPS of the EBS root device volume of the Linux AMI (optional for create-cluster). Available in EMR releases 6.15.0 and later.",
        ),
        ebs_root_volume_throughput: Optional[int] = Field(
            None,
            description="The throughput, in MiB/s, of the EBS root device volume of the Linux AMI (optional for create-cluster). Available in EMR releases 6.15.0 and later.",
        ),
        repo_upgrade_on_boot: Optional[str] = Field(
            None,
            description="Applies only when CustomAmiID is used. Specifies the type of updates that are applied from the Amazon Linux AMI package repositories when an instance boots (optional for create-cluster).",
        ),
        kerberos_attributes: Optional[Dict[str, Any]] = Field(
            None,
            description="Attributes for Kerberos configuration when Kerberos authentication is enabled (optional for create-cluster).",
        ),
        step_concurrency_level: Optional[int] = Field(
            None,
            description="The number of steps that can be executed concurrently (required for modify-cluster). Range: 1-256.",
        ),
        auto_terminate: Optional[bool] = Field(
            None,
            description="Whether the cluster should auto-terminate after completing steps (optional for modify-cluster-attributes).",
        ),
        termination_protected: Optional[bool] = Field(
            None,
            description="Whether the cluster is protected from termination (optional for modify-cluster-attributes).",
        ),
        unhealthy_node_replacement: Optional[bool] = Field(
            None,
            description="Whether Amazon EMR should gracefully replace Amazon EC2 core instances that have degraded within the cluster (optional for create-cluster).",
        ),
        os_release_label: Optional[str] = Field(
            None,
            description="The Amazon Linux release for the cluster (optional for create-cluster).",
        ),
        placement_groups: Optional[List[Dict[str, Any]]] = Field(
            None,
            description="Placement group configuration for the cluster (optional for create-cluster).",
        ),
        cluster_states: Optional[List[str]] = Field(
            None,
            description="The cluster state filters to apply when listing clusters (optional for list-clusters).",
        ),
        created_after: Optional[str] = Field(
            None,
            description="The creation date and time beginning value filter for listing clusters (optional for list-clusters).",
        ),
        created_before: Optional[str] = Field(
            None,
            description="The creation date and time end value filter for listing clusters (optional for list-clusters).",
        ),
        marker: Optional[str] = Field(
            None,
            description="The pagination token for list-clusters operation.",
        ),
        security_configuration_name: Optional[str] = Field(
            None,
            description="Name of the security configuration (required for create-security-configuration, delete-security-configuration, describe-security-configuration).",
        ),
        security_configuration_json: Optional[Dict[str, Any]] = Field(
            None,
            description="JSON format security configuration (required for create-security-configuration).",
        ),
    ) -> Union[
        CreateClusterResponse,
        DescribeClusterResponse,
        ModifyClusterResponse,
        ModifyClusterAttributesResponse,
        TerminateClustersResponse,
        ListClustersResponse,
        CreateSecurityConfigurationResponse,
        DeleteSecurityConfigurationResponse,
        DescribeSecurityConfigurationResponse,
        ListSecurityConfigurationsResponse,
    ]:
        """Manage AWS EMR EC2 clusters with comprehensive control over cluster lifecycle.

        This tool provides operations for managing Amazon EMR clusters running on EC2 instances,
        including creating, configuring, monitoring, modifying, and terminating clusters. It also
        supports security configuration management for EMR clusters.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-cluster, modify-cluster,
          modify-cluster-attributes, terminate-clusters, create-security-configuration, and
          delete-security-configuration operations
        - Appropriate AWS permissions for EMR cluster operations

        ## Operations
        - **create-cluster**: Create a new EMR cluster with specified configurations
        - **describe-cluster**: Get detailed information about a specific EMR cluster
        - **modify-cluster**: Modify the step concurrency level of a running cluster
        - **modify-cluster-attributes**: Modify auto-termination and termination protection settings
        - **terminate-clusters**: Terminate one or more EMR clusters
        - **list-clusters**: List all EMR clusters with optional filtering
        - **create-security-configuration**: Create a new EMR security configuration
        - **delete-security-configuration**: Delete an existing EMR security configuration
        - **describe-security-configuration**: Get details about a specific security configuration
        - **list-security-configurations**: List all available security configurations

        ## Example
        ```
        # Create a basic EMR cluster with Spark
        {
          "operation": "create-cluster",
          "name": "SparkCluster",
          "release_label": "emr-7.9.0",
          "applications": [{"Name": "Spark"}],
          "instances": {
            "InstanceGroups": [
              {
                "Name": "Master",
                "InstanceRole": "MASTER",
                "InstanceType": "m5.xlarge",
                "InstanceCount": 1
              },
              {
                "Name": "Core",
                "InstanceRole": "CORE",
                "InstanceType": "m5.xlarge",
                "InstanceCount": 2
              }
            ],
            "Ec2KeyName": "my-key-pair",
            "KeepJobFlowAliveWhenNoSteps": true
          }
        }
        ```

        ## Usage Tips
        - Use list-clusters to find cluster IDs before performing operations on specific clusters
        - Check cluster state before performing operations that require specific states
        - For large result sets, use pagination with marker parameter
        - When creating clusters, consider using security configurations for encryption and authentication

        Args:
            ctx: MCP context
            operation: Operation to perform
            cluster_id: ID of the EMR cluster
            cluster_ids: List of EMR cluster IDs
            name: Name of the EMR cluster
            log_uri: The path to the Amazon S3 location where logs for the cluster are stored
            release_label: The Amazon EMR release label
            applications: The applications to be installed on the cluster
            instances: A specification of the number and type of Amazon EC2 instances
            steps: A list of steps to run on the cluster
            bootstrap_actions: A list of bootstrap actions to run on the cluster
            configurations: A list of configurations to apply to the cluster
            visible_to_all_users: Whether the cluster is visible to all IAM users of the AWS account
            service_role: The IAM role that Amazon EMR assumes to access AWS resources on your behalf
            job_flow_role: The IAM role for EC2 instances running the job flow (required for create-cluster when using temporary credentials). Also known as the EC2 instance profile.
            security_configuration: The name of a security configuration to apply to the cluster
            auto_scaling_role: An IAM role for automatic scaling policies
            scale_down_behavior: The way that individual Amazon EC2 instances terminate when an automatic scale-in activity occurs
            custom_ami_id: A custom Amazon Linux AMI for the cluster
            ebs_root_volume_size: The size, in GiB, of the EBS root device volume of the Linux AMI
            repo_upgrade_on_boot: Specifies the type of updates that are applied from the Amazon Linux AMI package repositories when an instance boots
            kerberos_attributes: Attributes for Kerberos configuration when Kerberos authentication is enabled
            step_concurrency_level: The number of steps that can be executed concurrently
            auto_terminate: Whether the cluster should auto-terminate after completing steps
            termination_protected: Whether the cluster is protected from termination
            cluster_states: The cluster state filters to apply when listing clusters
            created_after: The creation date and time beginning value filter for listing clusters
            created_before: The creation date and time end value filter for listing clusters
            marker: The pagination token for list-clusters operation
            security_configuration_name: Name of the security configuration
            security_configuration_json: JSON format security configuration

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f"EMR EC2 Cluster Handler - Tool: manage_aws_emr_ec2_clusters - Operation: {operation}",
            )

            if not self.allow_write and operation in [
                "create-cluster",
                "modify-cluster",
                "modify-cluster-attributes",
                "terminate-clusters",
                "create-security-configuration",
                "delete-security-configuration",
            ]:
                error_message = (
                    f"Operation {operation} is not allowed without write access"
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response(operation, error_message)

            if operation == "create-cluster":
                # Check required parameters manually before proceeding
                missing_params = []
                if name is None:
                    missing_params.append("name")
                if release_label is None:
                    missing_params.append("release_label")
                if instances is None:
                    missing_params.append("instances")
                
                if missing_params:
                    error_message = "name, release_label, and instances are required for create-cluster operation"
                    return self._create_error_response(operation, error_message)

                # Prepare parameters
                params = {
                    "Name": name,
                    "ReleaseLabel": release_label,
                    "Instances": instances,
                }

                if log_uri is not None:
                    params["LogUri"] = log_uri

                if log_encryption_kms_key_id is not None:
                    params["LogEncryptionKmsKeyId"] = log_encryption_kms_key_id

                if applications is not None:
                    params["Applications"] = applications

                if steps is not None:
                    params["Steps"] = steps

                if bootstrap_actions is not None:
                    params["BootstrapActions"] = bootstrap_actions

                if configurations is not None:
                    params["Configurations"] = configurations

                if visible_to_all_users is not None:
                    params["VisibleToAllUsers"] = visible_to_all_users

                if service_role is not None:
                    params["ServiceRole"] = service_role

                if job_flow_role is not None:
                    params["JobFlowRole"] = job_flow_role

                if security_configuration is not None:
                    params["SecurityConfiguration"] = security_configuration

                if auto_scaling_role is not None:
                    params["AutoScalingRole"] = auto_scaling_role

                if scale_down_behavior is not None:
                    params["ScaleDownBehavior"] = scale_down_behavior

                if custom_ami_id is not None:
                    params["CustomAmiId"] = custom_ami_id

                if ebs_root_volume_size is not None:
                    params["EbsRootVolumeSize"] = ebs_root_volume_size

                if ebs_root_volume_iops is not None:
                    params["EbsRootVolumeIops"] = ebs_root_volume_iops

                if ebs_root_volume_throughput is not None:
                    params["EbsRootVolumeThroughput"] = ebs_root_volume_throughput

                if repo_upgrade_on_boot is not None:
                    params["RepoUpgradeOnBoot"] = repo_upgrade_on_boot

                if kerberos_attributes is not None:
                    params["KerberosAttributes"] = kerberos_attributes

                if unhealthy_node_replacement is not None:
                    params["UnhealthyNodeReplacement"] = unhealthy_node_replacement

                if os_release_label is not None:
                    params["OSReleaseLabel"] = os_release_label

                if placement_groups is not None:
                    params["PlacementGroups"] = placement_groups

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags("EMRCluster")
                aws_tags = [{'Key': key, 'Value': value} for key, value in resource_tags.items()]
                params["Tags"] = aws_tags

                # Create cluster
                response = self.emr_client.run_job_flow(**params)

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully created EMR cluster {name} with MCP management tags",
                    )
                ]
                return CreateClusterResponse(
                    isError=False,
                    content=content,
                    cluster_id=response.get("JobFlowId", ""),
                    cluster_arn=None,  # EMR doesn't return ARN in the create response
                )

            elif operation == "describe-cluster":
                if cluster_id is None:
                    error_message = "cluster_id is required for describe-cluster operation"
                    return self._create_error_response(operation, error_message)

                # Describe cluster
                response = self.emr_client.describe_cluster(ClusterId=cluster_id)

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully described EMR cluster {cluster_id}",
                    )
                ]
                return DescribeClusterResponse(
                    isError=False,
                    content=content,
                    cluster=response.get("Cluster", {}),
                )

            elif operation == "modify-cluster":
                if cluster_id is None:
                    error_message = "cluster_id is required for modify-cluster operation"
                    return self._create_error_response(operation, error_message)
                if step_concurrency_level is None:
                    error_message = "step_concurrency_level is required for modify-cluster operation"
                    return self._create_error_response(operation, error_message)

                # Modify cluster
                response = self.emr_client.modify_cluster(
                    ClusterId=cluster_id,
                    StepConcurrencyLevel=step_concurrency_level,
                )

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully modified EMR cluster {cluster_id}",
                    )
                ]
                return ModifyClusterResponse(
                    isError=False,
                    content=content,
                    cluster_id=cluster_id,
                    step_concurrency_level=response.get("StepConcurrencyLevel"),
                )

            elif operation == "modify-cluster-attributes":
                if cluster_id is None:
                    error_message = "cluster_id is required for modify-cluster-attributes operation"
                    return self._create_error_response(operation, error_message)

                if auto_terminate is None and termination_protected is None:
                    error_message = "At least one of auto_terminate or termination_protected must be provided for modify-cluster-attributes operation"
                    return self._create_error_response(operation, error_message)

                # Modify cluster attributes
                if auto_terminate is not None:
                    self.emr_client.set_termination_protection(
                        JobFlowIds=[cluster_id],
                        TerminationProtected=not auto_terminate,
                    )

                if termination_protected is not None:
                    self.emr_client.set_termination_protection(
                        JobFlowIds=[cluster_id],
                        TerminationProtected=termination_protected,
                    )

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully modified attributes for EMR cluster {cluster_id}",
                    )
                ]
                return ModifyClusterAttributesResponse(
                    isError=False,
                    content=content,
                    cluster_id=cluster_id,
                )

            elif operation == "terminate-clusters":
                if cluster_ids is None:
                    error_message = "cluster_ids is required for terminate-clusters operation"
                    return self._create_error_response(operation, error_message)

                # Verify that all clusters are managed by MCP before terminating
                unmanaged_clusters = []
                for cluster_id in cluster_ids:
                    try:
                        response = self.emr_client.describe_cluster(ClusterId=cluster_id)
                        tags_list = response.get('Cluster', {}).get('Tags', [])
                        cluster_tags = {tag['Key']: tag['Value'] for tag in tags_list}
                        # Check if cluster is managed by MCP
                        if cluster_tags.get(MCP_MANAGED_TAG_KEY) != MCP_MANAGED_TAG_VALUE:
                            unmanaged_clusters.append(cluster_id)
                    except Exception:
                        unmanaged_clusters.append(cluster_id)

                if unmanaged_clusters:
                    error_message = f"Cannot terminate clusters {unmanaged_clusters} - they are not managed by the MCP server (missing required tags)"
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return self._create_error_response(operation, error_message)

                # Terminate clusters
                self.emr_client.terminate_job_flows(JobFlowIds=cluster_ids)

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully initiated termination for {len(cluster_ids)} MCP-managed EMR clusters",
                    )
                ]
                return TerminateClustersResponse(
                    isError=False,
                    content=content,
                    cluster_ids=cluster_ids,
                )

            elif operation == "list-clusters":
                # Prepare parameters - only include non-None values
                params = {}
                if cluster_states is not None:
                    params["ClusterStates"] = cluster_states
                if created_after is not None:
                    params["CreatedAfter"] = created_after
                if created_before is not None:
                    params["CreatedBefore"] = created_before
                if marker is not None:
                    params["Marker"] = marker

                # List clusters
                response = self.emr_client.list_clusters(**params)

                clusters = response.get("Clusters", [])
                content: List[Content] = [
                    TextContent(
                        type="text", text="Successfully listed EMR clusters"
                    )
                ]
                return ListClustersResponse(
                    isError=False,
                    content=content,
                    clusters=clusters,
                    count=len(clusters),
                    marker=response.get("Marker"),
                    operation="list",
                )

            elif operation == "create-security-configuration":
                if (
                    security_configuration_name is None
                    or security_configuration_json is None
                ):
                    error_message = "security_configuration_name and security_configuration_json are required for create-security-configuration operation"
                    return self._create_error_response(operation, error_message)

                security_configuration_json_str = json.dumps(security_configuration_json)
                response = self.emr_client.create_security_configuration(
                    Name=security_configuration_name,
                    SecurityConfiguration=security_configuration_json_str,
                )

                creation_date_time = response.get("CreationDateTime", "")
                if hasattr(creation_date_time, "isoformat"):
                    creation_date_time = creation_date_time.isoformat()

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully created EMR security configuration {security_configuration_name}",
                    )
                ]
                return CreateSecurityConfigurationResponse(
                    isError=False,
                    content=content,
                    name=security_configuration_name,
                    creation_date_time=creation_date_time,
                )

            elif operation == "delete-security-configuration":
                if security_configuration_name is None:
                    error_message = "security_configuration_name is required for delete-security-configuration operation"
                    return self._create_error_response(operation, error_message)

                # Delete security configuration
                self.emr_client.delete_security_configuration(
                    Name=security_configuration_name
                )

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully deleted EMR security configuration {security_configuration_name}",
                    )
                ]
                return DeleteSecurityConfigurationResponse(
                    isError=False,
                    content=content,
                    name=security_configuration_name,
                )

            elif operation == "describe-security-configuration":
                if security_configuration_name is None:
                    error_message = "security_configuration_name is required for describe-security-configuration operation"
                    return self._create_error_response(operation, error_message)

                # Describe security configuration
                response = self.emr_client.describe_security_configuration(
                    Name=security_configuration_name
                )

                creation_date_time = response.get("CreationDateTime", "")
                if hasattr(creation_date_time, "isoformat"):
                    creation_date_time = creation_date_time.isoformat()

                content: List[Content] = [
                    TextContent(
                        type="text",
                        text=f"Successfully described EMR security configuration {security_configuration_name}",
                    )
                ]
                return DescribeSecurityConfigurationResponse(
                    isError=False,
                    content=content,
                    name=security_configuration_name,
                    security_configuration=response.get("SecurityConfiguration", ""),
                    creation_date_time=creation_date_time,
                )

            elif operation == "list-security-configurations":
                # Prepare parameters
                params = {}
                if marker is not None:
                    params["Marker"] = marker

                # List security configurations
                response = self.emr_client.list_security_configurations(**params)

                security_configurations = response.get("SecurityConfigurations", [])
                content: List[Content] = [
                    TextContent(
                        type="text",
                        text="Successfully listed EMR security configurations",
                    )
                ]
                return ListSecurityConfigurationsResponse(
                    isError=False,
                    content=content,
                    security_configurations=security_configurations,
                    count=len(security_configurations),
                    marker=response.get("Marker"),
                    operation="list",
                )

            else:
                error_message = f"Invalid operation: {operation}. Must be one of: create-cluster, describe-cluster, modify-cluster, modify-cluster-attributes, terminate-clusters, list-clusters, create-security-configuration, delete-security-configuration, describe-security-configuration, list-security-configurations"
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response("describe-cluster", error_message)

        except ValueError as e:
            error_message = str(e)
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
        except Exception as e:
            error_message = f"Error in manage_aws_emr_clusters: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
