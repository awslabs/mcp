"""
Function to retrieve bootstrap brokers for an MSK cluster.
Maps to AWS CLI command: aws kafka get-bootstrap-brokers
"""


def get_bootstrap_brokers(cluster_arn, client):
    """
    Returns connection information for the broker nodes in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to get bootstrap brokers for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Connection information for the broker nodes
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    response = client.get_bootstrap_brokers(ClusterArn=cluster_arn)

    return response
