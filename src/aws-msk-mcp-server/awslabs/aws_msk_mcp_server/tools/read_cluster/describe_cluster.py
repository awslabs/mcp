"""
Function to retrieve metadata about an MSK cluster.
Maps to AWS CLI command: aws kafka describe-cluster-v2
"""


def describe_cluster(cluster_arn, client):
    """
    Returns metadata about an MSK cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to describe
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Cluster metadata containing:
            - ClusterInfo (dict): Detailed information about the cluster including:
                - ClusterArn (str): The Amazon Resource Name (ARN) of the cluster
                - ClusterName (str): The name of the cluster
                - CreationTime (datetime): The time when the cluster was created
                - CurrentVersion (str): The current version of the cluster
                - State (str): The state of the cluster (e.g., ACTIVE, CREATING, UPDATING)
                - StateInfo (dict, optional): Additional information about the cluster state
                - Tags (dict, optional): Tags attached to the cluster
                - ClientAuthentication (dict, optional): Authentication settings for the cluster
                - EncryptionInfo (dict, optional): Encryption settings for the cluster
                - EnhancedMonitoring (str, optional): The enhanced monitoring level
                - OpenMonitoring (dict, optional): Open monitoring settings
                - LoggingInfo (dict, optional): Logging configuration
                - StorageMode (str, optional): Storage mode for the cluster
                - Provisioned (dict, optional): Information about provisioned clusters
                - Serverless (dict, optional): Information about serverless clusters
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    response = client.describe_cluster_v2(ClusterArn=cluster_arn)

    return response
