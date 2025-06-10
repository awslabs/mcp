"""
Function to update the EC2 instance type for an MSK cluster.
Maps to AWS CLI command: aws kafka update-broker-type
"""


def update_broker_type(cluster_arn, current_version, target_instance_type, client):
    """
    Updates EC2 instance type for all brokers in an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        current_version (str): The cluster version that you want to change
        target_instance_type (str): The Amazon MSK broker type that you want all brokers to be
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation containing ClusterArn and ClusterOperationArn
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.update_broker_type(
        ClusterArn=cluster_arn,
        CurrentVersion=current_version,
        TargetInstanceType=target_instance_type,
    )

    return response
