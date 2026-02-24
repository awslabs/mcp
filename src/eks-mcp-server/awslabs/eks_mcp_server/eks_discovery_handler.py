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

"""EKS cluster discovery handler for the EKS MCP Server.

This module provides tools for discovering and listing configured EKS clusters
across multiple AWS regions and accounts.
"""

import json
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.config import ClusterConfig, ConfigManager
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from typing import List, Optional


class ClusterInfo(BaseModel):
    """Information about a configured EKS cluster.

    Attributes:
        name: EKS cluster name
        region: AWS region where the cluster is located
        account_id: AWS account ID (if provided in config)
        description: Human-readable description (if provided in config)
        access_method: How credentials are obtained (role_assumption, profile, or default)
        status: Cluster status (ACTIVE, CREATING, etc.) - only populated when validate=True
        version: Kubernetes version - only populated when validate=True
    """

    name: str = Field(..., description="EKS cluster name")
    region: str = Field(..., description="AWS region")
    account_id: Optional[str] = Field(None, description="AWS account ID")
    description: Optional[str] = Field(None, description="Cluster description")
    access_method: str = Field(
        ...,
        description="Credential access method: role_assumption, profile, or default",
    )
    status: Optional[str] = Field(
        None, description="Cluster status (only when validated)"
    )
    version: Optional[str] = Field(
        None, description="Kubernetes version (only when validated)"
    )


class DiscoveryError(BaseModel):
    """Information about an error that occurred during discovery.

    Attributes:
        account_id: AWS account ID where the error occurred
        region: AWS region where the error occurred
        error_type: Type of error (e.g., AccessDeniedException, ServiceException)
        error_message: Detailed error message
        actionable_guidance: Guidance on how to fix the error
    """

    account_id: str = Field(..., description="AWS account ID")
    region: str = Field(..., description="AWS region")
    error_type: str = Field(..., description="Error type")
    error_message: str = Field(..., description="Error message")
    actionable_guidance: str = Field(..., description="How to fix this error")


class ListClustersData(BaseModel):
    """Response data for list_eks_clusters tool.

    Attributes:
        count: Number of configured clusters
        clusters: List of cluster information
        errors: List of errors encountered during discovery (if any)
    """

    count: int = Field(..., description="Number of configured clusters")
    clusters: List[ClusterInfo] = Field(..., description="List of cluster information")
    errors: List[DiscoveryError] = Field(
        default_factory=list, description="Errors encountered during discovery"
    )


class EKSDiscoveryHandler:
    """Handler for EKS cluster discovery operations.

    This class provides tools for discovering and listing EKS clusters
    that are configured in the cluster configuration file.
    """

    def __init__(self, mcp):
        """Initialize the EKS discovery handler.

        Args:
            mcp: The MCP server instance
        """
        self.mcp = mcp

        # Register tools
        self.mcp.tool(name="list_eks_clusters")(self.list_eks_clusters)

    @staticmethod
    def discover_clusters_with_default_credentials() -> List[ClusterConfig]:
        """Discover EKS clusters using default AWS credentials.

        This method is called when no config file is provided. It uses the default
        AWS credentials from the environment (AWS_PROFILE, AWS_ACCESS_KEY_ID, etc.)
        and discovers clusters in the default region (AWS_REGION or us-east-1).

        This method also creates a minimal config in ConfigManager to ensure the
        system functions properly even without a config file.

        Returns:
            List of discovered ClusterConfig objects

        Raises:
            Exception: If discovery fails critically (authentication, permissions, etc.)
        """
        from awslabs.eks_mcp_server.config import AccountConfig, ClustersConfig
        from loguru import logger

        discovered_clusters: List[ClusterConfig] = []

        try:
            # Get default credentials and account info using STS
            sts_client = AwsHelper.create_boto3_client("sts")
            caller_identity = sts_client.get_caller_identity()
            account_id = caller_identity["Account"]

            logger.info(f"Using default credentials for account {account_id}")

            # Get default region from environment or use us-east-1
            region_name = AwsHelper.get_aws_region() or "us-east-1"
            logger.info(f"Discovering clusters in region {region_name}")

            # Create a minimal config with this account/region
            account_config = AccountConfig(
                account_id=account_id,
                regions=[region_name],
            )
            minimal_config = ClustersConfig(
                accounts=[account_config],
                clusters=None,  # No explicit clusters, will use discovery
            )
            # Set the minimal config in ConfigManager
            ConfigManager._config = minimal_config
            logger.debug(
                f"Created minimal config for account {account_id}, region {region_name}"
            )

            # Create EKS client with default credentials
            eks_client = AwsHelper.create_boto3_client("eks", region_name=region_name)

            # List clusters in the region
            response = eks_client.list_clusters()
            cluster_names = response.get("clusters", [])

            logger.info(
                f"Found {len(cluster_names)} clusters in {region_name}: {cluster_names}"
            )

            # Create ClusterConfig for each discovered cluster
            for cluster_name in cluster_names:
                cluster_config = ClusterConfig(
                    name=cluster_name,
                    region=region_name,
                    account_id=account_id,
                    description=f"Auto-discovered cluster using default credentials in {region_name}",
                    validated=True,  # Discovery process confirms cluster exists
                )
                discovered_clusters.append(cluster_config)
                logger.debug(f"Discovered cluster: {cluster_name} in {region_name}")

            if discovered_clusters:
                logger.info(
                    f"Successfully discovered {len(discovered_clusters)} clusters "
                    f"in account {account_id}, region {region_name}"
                )
            else:
                logger.info(
                    f"No clusters found in account {account_id}, region {region_name}"
                )

        except Exception as e:
            error_msg = (
                f"Failed to discover clusters using default credentials: {str(e)}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        return discovered_clusters

    @staticmethod
    def discover_clusters_at_startup() -> List[ClusterConfig]:
        """Discover all EKS clusters in configured accounts and regions at startup.

        This method is called during server initialization when no explicit clusters
        are configured. It discovers all clusters across configured account/region
        combinations and stores them for later use.

        Returns:
            List of discovered ClusterConfig objects

        Raises:
            Exception: If discovery fails critically (account/region config issues)
        """
        from loguru import logger

        discovered_clusters: List[ClusterConfig] = []

        # Check if configuration is loaded
        if not ConfigManager.is_configured():
            logger.warning("No cluster configuration loaded - skipping discovery")
            return discovered_clusters

        # Only discover if no explicit clusters are configured
        if ConfigManager.has_explicit_clusters():
            logger.info("Explicit clusters configured - skipping automatic discovery")
            return discovered_clusters

        logger.info(
            "No explicit clusters configured - starting automatic cluster discovery"
        )

        account_region_combos = ConfigManager.list_account_region_combinations()
        logger.info(
            f"Discovering clusters in {len(account_region_combos)} account/region combinations"
        )

        errors_encountered = []

        for account_id, region_name in account_region_combos:
            account = ConfigManager.get_account(account_id)
            if not account:
                logger.warning(f"Account {account_id} not found in configuration")
                continue

            try:
                logger.debug(
                    f"Discovering clusters in account {account_id}, region {region_name}"
                )
                eks_client = AwsHelper.create_boto3_client_for_account_region(
                    account_id, region_name, "eks"
                )
                response = eks_client.list_clusters()
                cluster_names = response.get("clusters", [])

                logger.debug(
                    f"Found {len(cluster_names)} clusters in {account_id}/{region_name}: {cluster_names}"
                )

                for cluster_name in cluster_names:
                    cluster_config = ClusterConfig(
                        name=cluster_name,
                        region=region_name,
                        account_id=account_id,
                        description=f"Auto-discovered cluster in {region_name}",
                        validated=True,  # Discovery process confirms cluster exists
                    )
                    discovered_clusters.append(cluster_config)
                    logger.debug(f"Discovered cluster: {cluster_name} in {region_name}")

            except Exception as e:
                error_msg = f"Failed to discover clusters in {account_id}/{region_name}: {str(e)}"
                logger.warning(error_msg)
                errors_encountered.append(error_msg)

        if discovered_clusters:
            logger.info(
                f"Successfully discovered {len(discovered_clusters)} clusters "
                f"across {len(account_region_combos)} account/region combinations"
            )
            if errors_encountered:
                logger.warning(
                    f"{len(errors_encountered)} errors occurred during discovery"
                )
        else:
            logger.info("No clusters discovered in configured accounts/regions")
            if errors_encountered:
                logger.warning(
                    f"{len(errors_encountered)} errors occurred during discovery"
                )

        return discovered_clusters

    @staticmethod
    def _parse_error_for_guidance(
        error: Exception, account_id: str, region: str
    ) -> tuple[str, str]:
        """Parse an error and provide actionable guidance.

        Args:
            error: The exception that occurred
            account_id: AWS account ID where error occurred
            region: AWS region where error occurred

        Returns:
            Tuple of (error_type, actionable_guidance)
        """
        error_str = str(error)
        error_type = type(error).__name__

        # Check for AccessDeniedException
        if (
            "AccessDeniedException" in error_str
            or "not authorized" in error_str.lower()
        ):
            error_type = "AccessDeniedException"

            # Extract the specific permission that's missing
            if "eks:ListClusters" in error_str:
                return (
                    error_type,
                    f"Missing IAM permission: eks:ListClusters. "
                    f"Update the IAM role/user for account {account_id} to include "
                    f"eks:ListClusters permission. "
                    f'Example policy: {{"Effect": "Allow", "Action": "eks:ListClusters", '
                    f'"Resource": "arn:aws:eks:{region}:{account_id}:cluster/*"}}',
                )
            elif "eks:DescribeCluster" in error_str:
                return (
                    error_type,
                    f"Missing IAM permission: eks:DescribeCluster. "
                    f"Update the IAM role/user for account {account_id} to include "
                    f"eks:DescribeCluster permission.",
                )
            elif "sts:AssumeRole" in error_str:
                return (
                    error_type,
                    "Missing IAM permission: sts:AssumeRole or trust relationship not configured. "
                    "Ensure the role has a trust relationship allowing the current principal to assume it.",
                )
            else:
                return (
                    error_type,
                    f"Access denied in account {account_id}, region {region}. "
                    f"Verify IAM permissions for EKS operations. Full error: {error_str}",
                )

        # Check for credential errors
        elif "credential" in error_str.lower() or "InvalidClientTokenId" in error_str:
            return (
                "CredentialError",
                f"Invalid or missing AWS credentials for account {account_id}. "
                f"Verify AWS credentials configuration (AWS_PROFILE, role_arn, etc.).",
            )

        # Check for service errors
        elif "ServiceException" in error_str or "InternalFailure" in error_str:
            return (
                "ServiceException",
                f"AWS service error in {region}. This is typically temporary. "
                f"Retry the operation or check AWS service health.",
            )

        # Check for region errors
        elif "InvalidRegion" in error_str or "region" in error_str.lower():
            return (
                "RegionError",
                f"Invalid or unsupported region: {region}. "
                f"Verify the region name is correct and EKS is available in this region.",
            )

        # Generic error
        return (
            error_type,
            f"Error in account {account_id}, region {region}: {error_str}. "
            f"Check AWS service status and verify configuration.",
        )

    async def list_eks_clusters(
        self,
        ctx: Context,
        validate: bool = Field(
            False,
            description="""Whether to validate each cluster is accessible by calling describe_cluster.
            When true, includes cluster status and Kubernetes version in the response.
            When false, returns only the cached configuration data without making API calls.""",
        ),
    ) -> CallToolResult:
        """List all EKS clusters cached at server startup.

        This tool returns the list of EKS clusters that were loaded or discovered when
        the server started. If clusters were explicitly configured, it returns those.
        If no clusters were configured, it returns clusters that were auto-discovered
        at startup from the configured accounts/regions.

        It can optionally validate each cluster is accessible by querying the AWS API.

        ## Requirements
        - A cluster configuration file must be provided via --cluster-config flag
          or EKS_CLUSTER_CONFIG environment variable
        - Clusters must have been loaded or discovered at server startup

        ## Response Information
        The response includes for each cluster:
        - name: Cluster name
        - region: AWS region
        - account_id: AWS account ID
        - description: Description (if configured or auto-generated)
        - access_method: How credentials are obtained (role_assumption, profile, or default)
        - status: Cluster status (only when validate=True)
        - version: Kubernetes version (only when validate=True)

        ## Usage Tips
        - Use without validation for quick listing of cached clusters
        - Use with validation to verify cluster accessibility and get current status
        - Validation makes API calls and may take longer for many clusters
        - This tool only returns clusters cached at startup, it does not perform discovery

        Args:
            ctx: MCP context
            validate: Whether to validate cluster accessibility (default: False)

        Returns:
            ListClustersResponse with list of cached clusters (explicit or discovered)
        """
        try:
            # Check if configuration is loaded
            if not ConfigManager.is_configured():
                error_msg = (
                    "No cluster configuration loaded. "
                    "Please provide a cluster configuration file via --cluster-config flag "
                    "or EKS_CLUSTER_CONFIG environment variable."
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=error_msg)],
                )

            results: List[ClusterInfo] = []
            errors: List[DiscoveryError] = []

            # Check if we have clusters to process (explicit or pre-discovered)
            if (
                ConfigManager.has_explicit_clusters()
                or ConfigManager.has_discovered_clusters()
            ):
                # Use clusters from ConfigManager (which returns explicit or discovered clusters)
                clusters = ConfigManager.list_clusters()
                cluster_source = (
                    "explicitly configured"
                    if ConfigManager.has_explicit_clusters()
                    else "pre-discovered"
                )
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f"Found {len(clusters)} {cluster_source} clusters",
                )

                # Process clusters
                for cluster in clusters:
                    account = ConfigManager.get_account(cluster.account_id)
                    if not account:
                        log_with_request_id(
                            ctx,
                            LogLevel.WARNING,
                            f"Account {cluster.account_id} not found for cluster {cluster.name}",
                        )
                        continue

                    info = ClusterInfo(
                        name=cluster.name,
                        region=cluster.region,
                        account_id=cluster.account_id,
                        description=cluster.description,
                        access_method=account.get_access_method(),
                        status=None,
                        version=None,
                    )

                    # Validate cluster if requested and not already validated
                    if validate:
                        if cluster.validated:
                            # Cluster already validated (e.g., during discovery), skip API call
                            log_with_request_id(
                                ctx,
                                LogLevel.DEBUG,
                                f"Cluster {cluster.name} already validated, skipping API call",
                            )
                        else:
                            # Cluster not validated yet, call API to validate
                            try:
                                log_with_request_id(
                                    ctx,
                                    LogLevel.DEBUG,
                                    f"Validating cluster {cluster.name} in {cluster.region}",
                                )
                                eks_client = AwsHelper.create_boto3_client_for_cluster(
                                    cluster, "eks"
                                )
                                response = eks_client.describe_cluster(
                                    name=cluster.name
                                )
                                info.status = response["cluster"]["status"]
                                info.version = response["cluster"]["version"]
                                # Update validated flag
                                cluster.validated = True
                                log_with_request_id(
                                    ctx,
                                    LogLevel.DEBUG,
                                    f"Cluster {cluster.name}: status={info.status}, version={info.version}",
                                )
                            except Exception as e:
                                error_type, guidance = self._parse_error_for_guidance(
                                    e, cluster.account_id, cluster.region
                                )
                                info.status = f"{error_type}: {guidance}"
                                log_with_request_id(
                                    ctx,
                                    LogLevel.WARNING,
                                    f"Failed to validate cluster {cluster.name}: {e}",
                                )

                    results.append(info)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f"Successfully listed {len(results)} clusters"
                + (" with validation" if validate else "")
                + (f" ({len(errors)} errors)" if errors else ""),
            )

            data = ListClustersData(
                count=len(results),
                clusters=results,
                errors=errors,
            )

            discovery_mode = not ConfigManager.has_explicit_clusters()

            # Build response message
            response_parts = []
            response_parts.append(
                f"Found {len(results)} EKS clusters"
                + (" (discovered)" if discovery_mode else " (configured)")
                + (" (validated)" if validate else "")
            )

            # Add error summary if there are errors
            if errors:
                response_parts.append(
                    f"\n\n⚠️  {len(errors)} error(s) occurred during discovery:"
                )
                for err in errors:
                    response_parts.append(
                        f"\n• Account {err.account_id}, Region {err.region}: {err.error_type}"
                    )
                    response_parts.append(f"  → {err.actionable_guidance}")

            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type="text",
                        text="".join(response_parts),
                    ),
                    TextContent(
                        type="text",
                        text=json.dumps(data.model_dump()),
                    ),
                ],
            )

        except Exception as e:
            error_msg = f"Failed to list EKS clusters: {str(e)}"
            log_with_request_id(ctx, LogLevel.ERROR, error_msg)

            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=error_msg)],
            )
