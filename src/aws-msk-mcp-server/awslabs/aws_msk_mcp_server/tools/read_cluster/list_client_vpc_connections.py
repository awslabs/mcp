"""
Function to list client VPC connections for an MSK cluster.
Maps to AWS CLI command: aws kafka list-client-vpc-connections
"""


def list_client_vpc_connections(cluster_arn, client, max_results=10, next_token=None):
    """
    Lists the client VPC connections in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list client VPC connections for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int): Maximum number of connections to return
        next_token (str): Token for pagination

    Returns:
        dict: List of client VPC connections
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    params = {"ClusterArn": cluster_arn, "MaxResults": max_results}

    if next_token:
        params["NextToken"] = next_token

    response = client.list_client_vpc_connections(**params)

    return response
