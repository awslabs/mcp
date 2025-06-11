"""
Function to list nodes of an MSK cluster.
Maps to AWS CLI command: aws kafka list-nodes
"""


def list_nodes(cluster_arn, client, max_results=10, next_token=None):
    """
    Returns a list of the broker nodes in the cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to list nodes for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.
        max_results (int): Maximum number of nodes to return
        next_token (str): Token for pagination

    Returns:
        dict: List of broker nodes containing:
            - NodeInfoList (list): List of broker nodes, each containing:
                - BrokerNodeInfo (dict): Information about the broker node including:
                    - AttachedENIId (str): The attached Elastic Network Interface ID
                    - BrokerId (float): The ID of the broker
                    - ClientSubnet (str): The client subnet
                    - ClientVpcIpAddress (str): The client VPC IP address
                    - CurrentBrokerSoftwareInfo (dict): Information about the broker software
                    - Endpoints (list): List of broker endpoints
                    - InstanceType (str): The instance type of the broker
                    - NodeARN (str): The ARN of the node
                    - NodeType (str): The type of node (BROKER)
                    - ZookeeperNodeInfo (dict, optional): Information about the ZooKeeper node
                - InstanceType (str, optional): The instance type of the node
                - NodeARN (str): The ARN of the node
                - NodeType (str): The type of node (BROKER or ZOOKEEPER)
                - ZookeeperNodeInfo (dict, optional): Information about the ZooKeeper node
            - NextToken (str, optional): Token for pagination if there are more results
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    params = {"ClusterArn": cluster_arn, "MaxResults": max_results}

    if next_token:
        params["NextToken"] = next_token

    response = client.list_nodes(**params)

    return response
