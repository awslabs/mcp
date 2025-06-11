"""
Function to retrieve bootstrap brokers for an MSK cluster.
Maps to AWS CLI command: aws kafka get-bootstrap-brokers
"""


def get_bootstrap_brokers(cluster_arn, client):
    """
    Returns connection information for the broker nodes in a cluster.

    Args:
        cluster_arn (str): The ARN of the cluster to get bootstrap brokers for
        client (boto3.client): Boto3 client for Kafka. Must be provided by get_cluster_info.

    Returns:
        dict: Connection information for the broker nodes containing:
            - BootstrapBrokerString (str, optional): A comma-separated list of broker endpoints for plaintext connections
            - BootstrapBrokerStringTls (str, optional): A comma-separated list of broker endpoints for TLS connections
            - BootstrapBrokerStringSaslScram (str, optional): A comma-separated list of broker endpoints for SASL/SCRAM connections
            - BootstrapBrokerStringSaslIam (str, optional): A comma-separated list of broker endpoints for SASL/IAM connections
            - BootstrapBrokerStringPublicTls (str, optional): A comma-separated list of broker endpoints for public TLS connections
            - BootstrapBrokerStringPublicSaslScram (str, optional): A comma-separated list of broker endpoints for public SASL/SCRAM connections
            - BootstrapBrokerStringPublicSaslIam (str, optional): A comma-separated list of broker endpoints for public SASL/IAM connections
            - BootstrapBrokerStringVpcConnectivityTls (str, optional): A comma-separated list of broker endpoints for VPC connectivity TLS connections
            - BootstrapBrokerStringVpcConnectivitySaslScram (str, optional): A comma-separated list of broker endpoints for VPC connectivity SASL/SCRAM connections
            - BootstrapBrokerStringVpcConnectivitySaslIam (str, optional): A comma-separated list of broker endpoints for VPC connectivity SASL/IAM connections
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from get_cluster_info."
        )

    # Example implementation
    response = client.get_bootstrap_brokers(ClusterArn=cluster_arn)

    return response
