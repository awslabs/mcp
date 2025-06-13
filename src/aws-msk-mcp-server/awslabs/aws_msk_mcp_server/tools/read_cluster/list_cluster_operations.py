"""
Function to list operations for an MSK cluster.
Maps to AWS CLI command: aws kafka list-cluster-operations-v2
"""


def list_cluster_operations(cluster_arn, client, max_results=10, next_token=None):
    """
    Returns a list of all operations that have been performed on a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list operations for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int): Maximum number of operations to return
        next_token (str): Token for pagination

    Returns:
        dict: List of cluster operations
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    params = {"ClusterArn": cluster_arn, "MaxResults": max_results}

    if next_token:
        params["NextToken"] = next_token

    response = client.list_cluster_operations_v2(**params)

    return response
