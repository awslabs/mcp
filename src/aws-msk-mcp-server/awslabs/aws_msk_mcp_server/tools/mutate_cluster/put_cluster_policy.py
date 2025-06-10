"""
Function to create or update an MSK cluster policy.
Maps to AWS CLI command: aws kafka put-cluster-policy
"""


def put_cluster_policy(cluster_arn, policy, client, current_version=None):
    """
    Creates or updates the MSK cluster policy specified by the cluster ARN.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        policy (str): The JSON string representation of the cluster's policy
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        current_version (str, optional): The policy version

    Returns:
        dict: Result containing the current version of the policy
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Build the request parameters
    params = {"ClusterArn": cluster_arn, "Policy": policy}

    # Add optional parameters if provided
    if current_version:
        params["CurrentVersion"] = current_version

    response = client.put_cluster_policy(**params)

    return response
