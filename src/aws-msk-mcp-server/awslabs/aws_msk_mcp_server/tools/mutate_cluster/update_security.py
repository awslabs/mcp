"""
Function to update the security settings for an MSK cluster.
Maps to AWS CLI command: aws kafka update-security
"""


def update_security(
    cluster_arn, current_version, client_authentication=None, encryption_info=None, client=None
):
    """
    Updates the security settings for an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        current_version (str): The version of the cluster to update from
        client_authentication (dict, optional): Includes all client authentication information
            Example: {
                "Sasl": {
                    "Scram": {
                        "Enabled": True
                    },
                    "Iam": {
                        "Enabled": True
                    }
                },
                "Tls": {
                    "CertificateAuthorityArnList": [
                        "arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abcdef12-3456-7890-abcd-ef1234567890"
                    ],
                    "Enabled": True
                },
                "Unauthenticated": {
                    "Enabled": False
                }
            }
        encryption_info (dict, optional): Includes all encryption-related information
            Example: {
                "EncryptionAtRest": {
                    "DataVolumeKMSKeyId": "arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-abcdef123456"
                },
                "EncryptionInTransit": {
                    "ClientBroker": "TLS",
                    "InCluster": True
                }
            }
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation containing ClusterArn and ClusterOperationArn
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Build the request parameters
    params = {"ClusterArn": cluster_arn, "CurrentVersion": current_version}

    # Add optional parameters if provided
    if client_authentication:
        params["ClientAuthentication"] = client_authentication

    if encryption_info:
        params["EncryptionInfo"] = encryption_info

    response = client.update_security(**params)

    return response
