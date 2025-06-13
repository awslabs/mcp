"""
Function to describe a cluster operation for an MSK cluster.
Maps to AWS CLI command: aws kafka describe-cluster-operation-v2
"""


def describe_cluster_operation(cluster_operation_arn, client):
    """
    Returns information about a cluster operation.

    Args:
        cluster_operation_arn (str): The Amazon Resource Name (ARN) of the cluster operation
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Information about the cluster operation
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    response = client.describe_cluster_operation_v2(ClusterOperationArn=cluster_operation_arn)

    return response
