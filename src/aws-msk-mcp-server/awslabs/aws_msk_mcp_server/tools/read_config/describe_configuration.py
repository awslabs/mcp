"""
Function to describe an MSK configuration.
Maps to AWS CLI command: aws kafka describe-configuration
"""


def describe_configuration(arn, client):
    """
    Returns information about an MSK configuration.

    Args:
        arn (str): The Amazon Resource Name (ARN) of the configuration
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_configuration_info.

    Returns:
        dict: Information about the configuration
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_configuration_info."
        )

    response = client.describe_configuration(Arn=arn)

    return response
