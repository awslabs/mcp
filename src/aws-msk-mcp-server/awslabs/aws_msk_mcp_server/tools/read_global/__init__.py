"""
Global Information API Module

This module provides functions to retrieve global information about MSK resources.
"""

import boto3
from mcp.server.fastmcp import FastMCP

from .list_clusters import list_clusters
from .list_configurations import list_configurations
from .list_kafka_versions import list_kafka_versions
from .list_vpc_connections import list_vpc_connections


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name="get_global_info")
    def get_global_info(region, info_type="all", kwargs={}):
        """
        Unified API to retrieve various types of global information about MSK resources.

        Prompt the user for the region if it is not already specified.

        Args:
            info_type (str): Type of information to retrieve (clusters, configurations, vpc_connections, kafka_versions, all)
            region (str): AWS region.
            kwargs (dict, optional): Additional arguments specific to each info type
                - For "clusters": cluster_name_filter, cluster_type_filter, max_results, next_token
                - For "configurations": max_results, next_token
                - For "vpc_connections": max_results, next_token

        Returns:
            dict: Global information of the requested type, or a dictionary containing all types if info_type is "all"
        """
        # Create a single boto3 client to be shared across all function calls
        client = boto3.client("kafka", region_name=region)

        if info_type == "all":
            # Retrieve all types of information
            result = {
                "clusters": list_clusters(
                    client,
                    cluster_name_filter=kwargs.get("cluster_name_filter"),
                    cluster_type_filter=kwargs.get("cluster_type_filter"),
                    max_results=kwargs.get("max_results", 10),
                    next_token=kwargs.get("next_token"),
                ),
                "configurations": list_configurations(
                    client,
                    max_results=kwargs.get("max_results", 10),
                    next_token=kwargs.get("next_token"),
                ),
                "vpc_connections": list_vpc_connections(
                    client,
                    max_results=kwargs.get("max_results", 10),
                    next_token=kwargs.get("next_token"),
                ),
                "kafka_versions": list_kafka_versions(client),
            }
            return result
        elif info_type == "clusters":
            cluster_name_filter = kwargs.get("cluster_name_filter")
            cluster_type_filter = kwargs.get("cluster_type_filter")
            max_results = kwargs.get("max_results", 10)
            next_token = kwargs.get("next_token")

            return list_clusters(
                client,
                cluster_name_filter=cluster_name_filter,
                cluster_type_filter=cluster_type_filter,
                max_results=max_results,
                next_token=next_token,
            )
        elif info_type == "configurations":
            max_results = kwargs.get("max_results", 10)
            next_token = kwargs.get("next_token")

            return list_configurations(client, max_results=max_results, next_token=next_token)
        elif info_type == "vpc_connections":
            max_results = kwargs.get("max_results", 10)
            next_token = kwargs.get("next_token")

            return list_vpc_connections(client, max_results=max_results, next_token=next_token)
        elif info_type == "kafka_versions":
            return list_kafka_versions(client)
        else:
            raise ValueError(f"Unsupported info_type: {info_type}")
