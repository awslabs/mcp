"""
Function to list all MSK clusters.
Maps to AWS CLI command: aws kafka list-clusters-v2
"""


def list_clusters(
    client, cluster_name_filter=None, cluster_type_filter=None, max_results=10, next_token=None
):
    """
    Returns a list of all the MSK clusters in this account.

    Args:
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_global_info.
        cluster_name_filter (str): Filter clusters by name prefix
        cluster_type_filter (str): Filter clusters by type (PROVISIONED or SERVERLESS)
        max_results (int): Maximum number of clusters to return
        next_token (str): Token for pagination

    Returns:
        dict: List of MSK clusters containing:
            - ClusterInfoList (list): List of cluster information objects, each containing:
                - ClusterArn (str): The Amazon Resource Name (ARN) of the cluster
                - ClusterName (str): The name of the cluster
                - CreationTime (datetime): The time when the cluster was created
                - CurrentVersion (str): The current version of the cluster
                - State (str): The state of the cluster (e.g., ACTIVE, CREATING, UPDATING)
                - StateInfo (dict, optional): Additional information about the cluster state
                - Tags (dict, optional): Tags attached to the cluster
                - ClusterType (str): The type of the cluster (PROVISIONED or SERVERLESS)
            - NextToken (str, optional): Token for pagination if there are more results
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_global_info."
        )

    # Example implementation
    params = {"MaxResults": max_results}

    if cluster_name_filter:
        params["ClusterNameFilter"] = cluster_name_filter

    if cluster_type_filter:
        params["ClusterTypeFilter"] = cluster_type_filter

    if next_token:
        params["NextToken"] = next_token

    response = client.list_clusters_v2(**params)

    return response
