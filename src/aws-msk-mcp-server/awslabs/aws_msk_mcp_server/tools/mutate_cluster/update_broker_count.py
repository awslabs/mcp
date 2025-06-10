"""
Function to update the broker count for an MSK cluster.
Maps to AWS CLI command: aws kafka update-broker-count
"""


def update_broker_count(cluster_arn, current_version, target_number_of_broker_nodes, client):
    """
    Updates the number of broker nodes in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to update
        current_version (str): The current version of the cluster
        target_number_of_broker_nodes (int): The target number of broker nodes
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Example implementation
    response = client.update_broker_count(
        ClusterArn=cluster_arn,
        CurrentVersion=current_version,
        TargetNumberOfBrokerNodes=target_number_of_broker_nodes,
    )

    return response
