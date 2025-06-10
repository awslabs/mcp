"""
Function to create a new MSK configuration.
Maps to AWS CLI command: aws kafka create-configuration
"""


def create_configuration(name, server_properties, client, description="", kafka_versions=None):
    """
    Creates a new MSK configuration.

    Args:
        name (str): The name of the configuration
        server_properties (str): Contents of the server.properties file.
                                Supported properties are documented in the MSK Developer Guide
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        description (str, optional): The description of the configuration
        kafka_versions (list, optional): The versions of Apache Kafka with which you can use this MSK configuration

    Returns:
        dict: Result of the create operation containing the ARN, creation time, latest revision, and name
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Build the request parameters
    params = {"Name": name, "ServerProperties": server_properties}

    # Add optional parameters if provided
    if description:
        params["Description"] = description

    if kafka_versions:
        params["KafkaVersions"] = kafka_versions

    response = client.create_configuration(**params)

    return response
