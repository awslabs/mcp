"""Tools for managing IAM access to MSK clusters."""

import re
from typing import Any, Dict

from botocore.exceptions import ClientError
from loguru import logger

from .. import common_functions


def list_customer_iam_access(cluster_arn: str, client_manager=None) -> Dict[str, Any]:
    """
    List IAM access information for an MSK cluster.

    Args:
        cluster_arn: The ARN of the MSK cluster
        client_manager: AWSClientManager instance. Must be provided by the tool function.

    Returns:
        Dictionary containing:
        - cluster_info: Basic cluster information including IAM auth status
        - resource_policies: Resource-based policies attached to the cluster
        - matching_policies: IAM policies that grant access to this cluster
    """
    try:
        # Validate client manager
        if client_manager is None:
            raise ValueError(
                "Client manager must be provided. This function should only be called from a tool function."
            )

        # Get clients from the client manager
        kafka = client_manager.get_client("kafka")
        iam = client_manager.get_client("iam")

        if not cluster_arn.startswith("arn:aws:kafka:"):
            raise ValueError("cluster_arn must be a valid MSK cluster ARN")

        # Get cluster details
        cluster_info = kafka.describe_cluster(ClusterArn=cluster_arn)["ClusterInfo"]

        # Extract cluster name from ARN
        cluster_name = common_functions.get_cluster_name(cluster_arn)

        # Check IAM authentication status
        iam_auth_enabled = (
            cluster_info.get("BrokerNodeGroupInfo", {})
            .get("ConnectivityInfo", {})
            .get("VpcConnectivity", {})
            .get("ClientAuthentication", {})
            .get("Sasl", {})
            .get("Iam", {})
            .get("Enabled", False)
        )

        # Get resource-based policies
        try:
            resource_policies = kafka.get_cluster_policy(ClusterArn=cluster_arn).get("Policy", [])
        except ClientError as e:
            if e.response["Error"]["Code"] == "NotFoundException":
                resource_policies = []
            else:
                raise

        # First find policies that explicitly reference this cluster
        matching_policies = {}
        paginator = iam.get_paginator("list_policies")
        for page in paginator.paginate(Scope="Local"):  # Only look at customer-managed policies
            for policy in page["Policies"]:
                try:
                    version = iam.get_policy_version(
                        PolicyArn=policy["Arn"], VersionId=policy["DefaultVersionId"]
                    )

                    for statement in version["PolicyVersion"]["Document"]["Statement"]:
                        resources = statement.get("Resource", [])
                        if isinstance(resources, str):
                            resources = [resources]

                        # Check if any kafka-related actions are allowed
                        actions = statement.get("Action", [])
                        if isinstance(actions, str):
                            actions = [actions]

                        logger.info(
                            f"Checking policy {policy['PolicyName']} with actions: {actions}"
                        )
                        if any(
                            action.startswith(("kafka:", "kafka-cluster:")) for action in actions
                        ):
                            logger.info(f"Found kafka actions in policy {policy['PolicyName']}")
                            # Check various resource patterns that could match this cluster
                            matches = False
                            match_type = None

                            for resource in resources:
                                if resource == cluster_arn:
                                    matches = True
                                    match_type = "exact"
                                    break
                                elif resource == "*":
                                    matches = True
                                    match_type = "global_wildcard"
                                    break
                                # Extract region from cluster ARN
                                cluster_region = cluster_arn.split(":")[3]

                                if (
                                    resource
                                    == f"arn:aws:kafka:{cluster_region}:*:cluster/{cluster_name}/*"
                                ):
                                    matches = True
                                    match_type = "cluster_wildcard"
                                    break
                                elif resource.startswith("arn:aws:kafka:") and "*" in resource:
                                    # Check if wildcard pattern could match this cluster
                                    pattern = resource.replace("*", ".*").replace("?", ".")
                                    if re.match(pattern, cluster_arn):
                                        matches = True
                                        match_type = "pattern_match"
                                        break
                            if matches:
                                matching_policies[policy["Arn"]] = {
                                    "PolicyName": policy["PolicyName"],
                                    "Statement": statement,
                                    "ResourceType": match_type,
                                    "AttachedRoles": [],
                                }
                                break
                except Exception as e:
                    logger.error(f"Error processing policy {policy['PolicyName']}: {str(e)}")
                    continue
        # For each matching policy, find attached roles
        for policy_arn in matching_policies:
            try:
                attached_entities = iam.list_entities_for_policy(PolicyArn=policy_arn)
                matching_policies[policy_arn].update(attached_entities)
            except Exception as e:
                logger.error(f"Error getting roles for policy {policy_arn}: {str(e)}")
                continue
        return {
            "cluster_info": {
                "cluster_arn": cluster_arn,
                "cluster_name": cluster_name,
                "iam_auth_enabled": iam_auth_enabled,
            },
            "resource_policies": resource_policies,
            "matching_policies": matching_policies,
        }
    except ClientError as e:
        logger.error(
            f"AWS API error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
