"""
Function to create a VPC connection for an MSK cluster.
Maps to AWS CLI command: aws kafka create-vpc-connection
"""


def create_vpc_connection(
    cluster_arn,
    vpc_id,
    subnet_ids,
    security_groups,
    client,
    authentication_type=None,
    client_subnets=None,
    tags=None,
):
    """
    Creates a VPC connection for an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        vpc_id (str): The ID of the VPC to connect to
        subnet_ids (list): A list of subnet IDs for the client VPC connection
        security_groups (list): A list of security group IDs for the client VPC connection
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        authentication_type (str, optional): The authentication type for the VPC connection (e.g., 'IAM')
        client_subnets (list, optional): A list of client subnet IDs for the VPC connection
        tags (dict, optional): A map of tags to attach to the VPC connection

    Returns:
        dict: Information about the created VPC connection
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    params = {
        "ClusterArn": cluster_arn,
        "VpcId": vpc_id,
        "SubnetIds": subnet_ids,
        "SecurityGroups": security_groups,
    }

    if authentication_type:
        params["Authentication"] = {"Type": authentication_type}

    if client_subnets:
        params["ClientSubnets"] = client_subnets

    if tags:
        params["Tags"] = tags

    response = client.create_vpc_connection(**params)

    return response
