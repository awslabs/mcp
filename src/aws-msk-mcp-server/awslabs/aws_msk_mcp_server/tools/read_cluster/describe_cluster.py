"""
Function to retrieve metadata about an MSK cluster.
Maps to AWS CLI command: aws kafka describe-cluster-v2
"""


def describe_cluster(cluster_arn, client):
    """
    Returns metadata about an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to describe
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Cluster metadata
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    response = client.describe_cluster_v2(ClusterArn=cluster_arn)

    return response
