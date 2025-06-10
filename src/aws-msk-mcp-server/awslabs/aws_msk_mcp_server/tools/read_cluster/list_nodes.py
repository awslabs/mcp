"""
Function to list nodes of an MSK cluster.
Maps to AWS CLI command: aws kafka list-nodes
"""


def list_nodes(cluster_arn, client, max_results=10, next_token=None):
    """
    Returns a list of the broker nodes in the cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list nodes for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int): Maximum number of nodes to return
        next_token (str): Token for pagination

    Returns:
        dict: List of broker nodes
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    params = {"ClusterArn": cluster_arn, "MaxResults": max_results}

    if next_token:
        params["NextToken"] = next_token

    response = client.list_nodes(**params)

    return response
