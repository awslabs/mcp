"""
Function to retrieve the cluster policy for an MSK cluster.
Maps to AWS CLI command: aws kafka get-cluster-policy
"""

import json


def get_cluster_policy(cluster_arn, client):
    """
    Returns the JSON string representation of the cluster's policy.

    Args:
        cluster_arn (str): The ARN of the cluster to get the policy for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Cluster policy information containing:
            - Policy (str): The JSON string representation of the cluster's policy
            - PolicyDict (dict): The parsed policy as a Python dictionary (added by this function)
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    response = client.get_cluster_policy(ClusterArn=cluster_arn)

    # The policy is returned as a JSON string, so we parse it for easier use
    if "Policy" in response and response["Policy"]:
        try:
            # Parse the JSON string into a Python dictionary
            policy_dict = json.loads(response["Policy"])
            response["PolicyDict"] = policy_dict
        except json.JSONDecodeError:
            # If parsing fails, keep the original string
            pass

    return response
