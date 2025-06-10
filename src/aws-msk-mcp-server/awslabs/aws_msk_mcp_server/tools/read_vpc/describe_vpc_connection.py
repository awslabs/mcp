"""
Function to describe a VPC connection for an MSK cluster.
Maps to AWS CLI command: aws kafka describe-vpc-connection
"""


def describe_vpc_connection(vpc_connection_arn, client):
    """
    Returns information about a VPC connection.

    Args:
        vpc_connection_arn (str): The Amazon Resource Name (ARN) of the VPC connection
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the VPC connection
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.describe_vpc_connection(VpcConnectionArn=vpc_connection_arn)

    return response
