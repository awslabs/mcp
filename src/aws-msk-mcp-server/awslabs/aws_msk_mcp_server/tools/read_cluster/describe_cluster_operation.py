"""
Function to describe a cluster operation for an MSK cluster.
Maps to AWS CLI command: aws kafka describe-cluster-operation-v2
"""


def describe_cluster_operation(cluster_operation_arn, client):
    """
    Returns information about a cluster operation.

    Args:
        cluster_operation_arn (str): The Amazon Resource Name (ARN) of the cluster operation
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Information about the cluster operation containing:
            - ClusterOperationInfo (dict): Detailed information about the operation including:
                - ClusterArn (str): The ARN of the cluster this operation is performed on
                - ClusterOperationArn (str): The ARN of the cluster operation
                - OperationType (str): The type of operation (e.g., UPDATE, CREATE, DELETE)
                - SourceClusterInfo (dict, optional): Information about the source cluster
                - TargetClusterInfo (dict, optional): Information about the target cluster configuration
                - OperationSteps (list, optional): List of steps in the operation
                - OperationState (str): The state of the operation (e.g., PENDING, IN_PROGRESS, COMPLETED)
                - ErrorInfo (dict, optional): Information about any errors that occurred
                - CreationTime (datetime): The time when the operation was created
                - EndTime (datetime, optional): The time when the operation completed
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    response = client.describe_cluster_operation_v2(ClusterOperationArn=cluster_operation_arn)

    return response
