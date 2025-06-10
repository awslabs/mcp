"""
Function to list tags for an MSK resource.
Maps to AWS CLI command: aws kafka list-tags-for-resource
"""


def list_tags_for_resource(resource_arn, client):
    """
    Lists tags for an MSK resource.

    Args:
        resource_arn (str): The Amazon Resource Name (ARN) of the resource
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Tags for the resource
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.list_tags_for_resource(ResourceArn=resource_arn)

    return response
