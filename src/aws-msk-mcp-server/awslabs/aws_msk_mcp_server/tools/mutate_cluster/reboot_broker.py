"""
Function to reboot a broker in an MSK cluster.
Maps to AWS CLI command: aws kafka reboot-broker
"""


def reboot_broker(cluster_arn, broker_ids, client):
    """
    Reboots brokers in an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        broker_ids (list): A list of broker IDs to reboot
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the reboot operation
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.reboot_broker(ClusterArn=cluster_arn, BrokerIds=broker_ids)

    return response
