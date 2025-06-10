"""
Function to reject a client VPC connection for an MSK cluster.
Maps to AWS CLI command: aws kafka reject-client-vpc-connection
"""


def reject_client_vpc_connection(cluster_arn, vpc_connection_arn, client):
    """
    Rejects a client VPC connection for an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the rejected VPC connection
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.reject_client_vpc_connection(
        ClusterArn=cluster_arn, VpcConnectionArn=vpc_connection_arn
    )

    return response
