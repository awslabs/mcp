"""
Function to add tags to an MSK resource.
Maps to AWS CLI command: aws kafka tag-resource
"""


def tag_resource(resource_arn, tags, client):
    """
    Adds tags to an MSK resource.

    Args:
        resource_arn (str): The Amazon Resource Name (ARN) of the resource
        tags (dict): A map of tags to add to the resource
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Empty response if successful
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    response = client.tag_resource(ResourceArn=resource_arn, Tags=tags)

    return response
