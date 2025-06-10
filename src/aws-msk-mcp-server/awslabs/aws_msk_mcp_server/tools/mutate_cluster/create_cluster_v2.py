"""
Function to create a new MSK cluster.
Maps to AWS CLI command: aws kafka create-cluster-v2
"""


def create_cluster_v2(cluster_name, cluster_type="PROVISIONED", client=None, **kwargs):
    """
    Creates a new MSK cluster.

    Args:
        cluster_name (str): The name of the cluster
        cluster_type (str): Type of cluster to create (PROVISIONED or SERVERLESS)
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.
        **kwargs: Additional arguments based on cluster type:
            For PROVISIONED:
                broker_node_group_info (dict): Information about the broker nodes
                kafka_version (str): Apache Kafka version
                number_of_broker_nodes (int): Number of broker nodes
                client_authentication (dict): Authentication settings
                encryption_info (dict): Encryption settings
                enhanced_monitoring (str): Monitoring level
                open_monitoring (dict): Prometheus monitoring settings
                logging_info (dict): Log delivery settings
                configuration_info (dict): Cluster configuration
                storage_mode (str): Storage tier mode
                tags (dict): Resource tags
            For SERVERLESS:
                vpc_configs (list): VPC configuration
                client_authentication (dict): Authentication settings
                tags (dict): Resource tags

    Returns:
        dict: Result of the create operation
    """
    if client is None:
        raise ValueError(
            "Client must be provided. This function should only be called from a tool function."
        )

    # Base parameters
    params = {"ClusterName": cluster_name}

    # Add cluster type specific parameters
    if cluster_type == "PROVISIONED":
        provisioned_params = {}

        # Add required parameters for provisioned clusters
        if "broker_node_group_info" in kwargs:
            provisioned_params["BrokerNodeGroupInfo"] = kwargs.get("broker_node_group_info")

        if "kafka_version" in kwargs:
            provisioned_params["KafkaVersion"] = kwargs.get("kafka_version")

        if "number_of_broker_nodes" in kwargs:
            provisioned_params["NumberOfBrokerNodes"] = kwargs.get("number_of_broker_nodes")

        # Add optional parameters if provided
        for param, key in [
            ("client_authentication", "ClientAuthentication"),
            ("encryption_info", "EncryptionInfo"),
            ("enhanced_monitoring", "EnhancedMonitoring"),
            ("open_monitoring", "OpenMonitoring"),
            ("logging_info", "LoggingInfo"),
            ("configuration_info", "ConfigurationInfo"),
            ("storage_mode", "StorageMode"),
        ]:
            if param in kwargs:
                provisioned_params[key] = kwargs.get(param)

        params["Provisioned"] = provisioned_params

    elif cluster_type == "SERVERLESS":
        serverless_params = {}

        # Add required parameters for serverless clusters
        if "vpc_configs" in kwargs:
            serverless_params["VpcConfigs"] = kwargs.get("vpc_configs")

        # Add optional parameters if provided
        if "client_authentication" in kwargs:
            serverless_params["ClientAuthentication"] = kwargs.get("client_authentication")

        params["Serverless"] = serverless_params

    # Add tags if provided
    if "tags" in kwargs:
        params["Tags"] = kwargs.get("tags")

    # Example implementation
    response = client.create_cluster_v2(**params)

    return response
