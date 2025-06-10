"""
Function to update an MSK configuration.
Maps to AWS CLI command: aws kafka update-configuration
"""


def update_configuration(arn, server_properties, client, description=""):
    """
    Updates an MSK configuration.

    Args:
        arn (str): The Amazon Resource Name (ARN) of the configuration to update
        server_properties (str): Contents of the server.properties file.
                                 Supported properties are documented in the MSK Developer Guide
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        description (str, optional): The description of the configuration revision

    Returns:
        dict: Result of the update operation containing the ARN and latest revision
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Build the request parameters
    params = {"Arn": arn, "ServerProperties": server_properties}

    # Add optional parameters if provided
    if description:
        params["Description"] = description

    response = client.update_configuration(**params)

    return response
