"""
Function to list Apache Kafka versions supported by Amazon MSK.
Maps to AWS CLI command: aws kafka list-kafka-versions
"""


def list_kafka_versions(client):
    """
    Returns a list of Apache Kafka versions supported by Amazon MSK.

    Args:
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_global_info.

    Returns:
        dict: List of supported Kafka versions
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_global_info."
        )

    # Example implementation
    response = client.list_kafka_versions()

    return response
