"""
Function to disassociate SCRAM secrets from an MSK cluster.
Maps to AWS CLI command: aws kafka batch-disassociate-scram-secret
"""


def batch_disassociate_scram_secret(cluster_arn, secret_arns, client):
    """
    Disassociates SCRAM secrets from an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) of the cluster
        secret_arns (list): A list of secret ARNs to disassociate from the cluster
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Information about the disassociated secrets
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.batch_disassociate_scram_secret(
        ClusterArn=cluster_arn, SecretArnList=secret_arns
    )

    return response
