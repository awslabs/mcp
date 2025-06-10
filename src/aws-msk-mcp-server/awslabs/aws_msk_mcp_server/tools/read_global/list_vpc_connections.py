"""
Function to list VPC connections.
Maps to AWS CLI command: aws kafka list-vpc-connections
"""


def list_vpc_connections(client, max_results=10, next_token=None):
    """
    Returns a list of VPC connections for this account.

    Args:
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_global_info.
        max_results (int): Maximum number of connections to return
        next_token (str): Token for pagination

    Returns:
        dict: List of VPC connections
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_global_info."
        )

    # Example implementation
    params = {"MaxResults": max_results}

    if next_token:
        params["NextToken"] = next_token

    response = client.list_vpc_connections(**params)

    return response
