# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for MSK cluster metrics operations."""

import json
from ..common_functions import get_cluster_name
from .metric_config import METRICS, SERVERLESS_METRICS, get_metric_config
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from typing import Any, Dict, List, Mapping, Optional, Union


def get_monitoring_level_rank(level: str) -> int:
    """Get the numeric rank of a monitoring level for comparison.

    Args:
        level: The monitoring level string

    Returns:
        Numeric rank where higher number means more detailed monitoring
    """
    ranks = {
        'DEFAULT': 0,
        'PER_BROKER': 1,
        'PER_TOPIC_PER_BROKER': 2,
        'PER_TOPIC_PER_PARTITION': 3,
    }
    return ranks.get(level, -1)


def list_available_metrics(monitoring_level: str, serverless: bool = False) -> Dict[str, Any]:
    """List available metrics and their configurations.

    Args:
        monitoring_level: Monitoring level to filter by ('DEFAULT', 'PER_BROKER', etc.)
        serverless: Whether to return metrics for serverless clusters (default: False)

    Returns:
        Dictionary containing available metrics and their configurations

    Raises:
        ValueError: If no monitoring level is provided
    """
    if serverless:
        if monitoring_level is None:
            raise ValueError('Monitoring level must be provided')

        return {
            name: config
            for name, config in SERVERLESS_METRICS.items()
            if config['monitoring_level'] == monitoring_level
        }
    else:
        if monitoring_level is None:
            raise ValueError('Monitoring level must be provided')

        return {
            name: config
            for name, config in METRICS.items()
            if config['monitoring_level'] == monitoring_level
        }


def get_cluster_metrics(
    region: str,
    cluster_arn: str,
    start_time: datetime,
    end_time: datetime,
    period: int,
    metrics: Union[List[str], Mapping[str, Optional[str]]],
    client_manager=None,
    scan_by: Optional[str] = None,
    label_options: Optional[Dict[str, str]] = None,
    pagination_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Get metrics for an MSK cluster.

    Args:
        region: AWS region where the cluster is located
        cluster_arn: The ARN of the MSK cluster
        start_time: Start time for metric data retrieval
        end_time: End time for metric data retrieval
        period: The granularity, in seconds, of the returned data points
        metrics: Either:
            - List of metric names from metric_config.py (e.g., ['BytesInPerSec', 'BytesOutPerSec'])
            - Dictionary mapping metric names from metric_config.py to optional statistics
              (e.g., {'BytesInPerSec': 'Sum', 'BytesOutPerSec': 'Average'})
            If statistic is None, the default statistic from metric_config will be used.
        client_manager: AWSClientManager instance. Must be provided by get_cluster_telemetry.
        scan_by: Optional scan order for data points ('TimestampDescending' or 'TimestampAscending')
        label_options: Optional dictionary containing label options:
            - timezone: Timezone for labels (e.g., 'UTC', 'US/Pacific')
        pagination_config: Optional dictionary containing pagination settings:
            - MaxItems: Maximum number of items to return
            - PageSize: Number of items per page
            - StartingToken: Token for starting position

    Note:
        See metric_config.py for the complete list
        of supported metrics.

    Returns:
        Dictionary containing metric data results
    """
    try:
        # Validate client manager
        if client_manager is None:
            raise ValueError(
                'Client manager must be provided. This function should only be called from get_cluster_telemetry.'
            )

        # Get clients from the client manager
        kafka_client = client_manager.get_client(region, 'kafka')
        cloudwatch_client = client_manager.get_client(region, 'cloudwatch')

        # Get cluster's monitoring level
        cluster_info = kafka_client.describe_cluster_v2(ClusterArn=cluster_arn)['ClusterInfo']
        cluster_monitoring = cluster_info.get('EnhancedMonitoring', 'DEFAULT')
        cluster_type = cluster_info.get('ClusterType')
        cluster_monitoring_rank = get_monitoring_level_rank(cluster_monitoring)
        metric_queries = []

        # Convert list of metrics to dict with None statistics to use defaults
        if isinstance(metrics, list):
            metrics = dict.fromkeys(metrics)
        # Process each metric
        for i, (metric_name, statistic) in enumerate(metrics.items()):
            logger.info(f'Processing metric {metric_name} with statistic {statistic}')
            try:
                # Get metric configuration
                metric_config = get_metric_config(metric_name, cluster_type == 'SERVERLESS')

                if cluster_type == 'SERVERLESS' and (metric_name not in SERVERLESS_METRICS.keys()):
                    logger.warning(
                        f'Metric {metric_name} requires {metric_config["monitoring_level"]} monitoring '
                        f'but cluster is configured for {cluster_monitoring}. Skipping metric.'
                    )
                    continue

                elif cluster_type == 'PROVISIONED':
                    # Check if metric's monitoring level is supported
                    metric_level_rank = get_monitoring_level_rank(
                        metric_config['monitoring_level']
                    )
                    if metric_level_rank > cluster_monitoring_rank:
                        logger.warning(
                            f'Metric {metric_name} requires {metric_config["monitoring_level"]} monitoring '
                            f'but cluster is configured for {cluster_monitoring}. Skipping metric.'
                        )
                        continue

                # Get default statistic if none provided
                if not statistic:
                    statistic = metric_config['default_statistic']

                # Check if metric needs broker-specific data
                if 'Broker ID' in metric_config['dimensions']:
                    # Get broker IDs from the cluster
                    nodes = kafka_client.list_nodes(ClusterArn=cluster_arn)
                    logger.info(f'Got nodes response: {nodes}')
                    broker_ids = [
                        str(int(node['BrokerNodeInfo']['BrokerId']))
                        for node in nodes['NodeInfoList']
                    ]
                    logger.info(f'Extracted broker IDs: {broker_ids}')

                    # Create a query for each broker
                    for broker_id in broker_ids:
                        dimensions = []
                        for dim_name in metric_config['dimensions']:
                            if dim_name == 'Cluster Name':
                                dimensions.append(
                                    {'Name': dim_name, 'Value': get_cluster_name(cluster_arn)}
                                )
                            elif dim_name == 'Broker ID':
                                dimensions.append({'Name': dim_name, 'Value': broker_id})
                            elif dim_name == 'ClientAuthentication':
                                # Skip client auth dimensions for now
                                logger.warning(
                                    f'ClientAuthentication dimension not yet supported for metric {metric_name}'
                                )
                            else:
                                logger.warning(
                                    f'Unsupported dimension {dim_name} for metric {metric_name}'
                                )
                        query = {
                            'Id': f'm{i}_{broker_id}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Kafka',
                                    'MetricName': metric_name,
                                    'Dimensions': dimensions,
                                },
                                'Period': period,
                                'Stat': statistic,
                            },
                        }
                        metric_queries.append(query)
                else:
                    # Non-broker-specific metric
                    dimensions = []
                    for dim_name in metric_config['dimensions']:
                        if dim_name == 'Cluster Name':
                            dimensions.append(
                                {'Name': dim_name, 'Value': get_cluster_name(cluster_arn)}
                            )
                        else:
                            logger.warning(
                                f'Unsupported dimension {dim_name} for metric {metric_name}'
                            )
                    # If no dimensions were added, use cluster name as fallback
                    if not dimensions:
                        dimensions.append(
                            {'Name': 'Cluster Name', 'Value': get_cluster_name(cluster_arn)}
                        )

                    query = {
                        'Id': f'm{i}',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/Kafka',
                                'MetricName': metric_name,
                                'Dimensions': dimensions,
                            },
                            'Period': period,
                            'Stat': statistic,
                        },
                    }
                    metric_queries.append(query)
            except KeyError:
                # Fallback to basic configuration if metric not found
                logger.warning(
                    f'No configuration found for metric {metric_name}, using default configuration'
                )
                statistic = statistic or 'Average'
                dimensions = [{'Name': 'Cluster Name', 'Value': get_cluster_name(cluster_arn)}]

                query = {
                    'Id': f'm{i}',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Kafka',
                            'MetricName': metric_name,
                            'Dimensions': dimensions,
                        },
                        'Period': period,
                        'Stat': statistic,
                    },
                }
                metric_queries.append(query)
        # Prepare GetMetricData parameters
        params = {
            'MetricDataQueries': metric_queries,
            'StartTime': start_time,
            'EndTime': end_time,
        }
        logger.info(f'Final metric queries: {json.dumps(metric_queries, indent=2)}')

        # Add optional parameters if provided
        if scan_by:
            params['ScanBy'] = scan_by
        if label_options:
            params['LabelOptions'] = label_options

        # Handle pagination if config is provided
        if pagination_config:
            paginator = cloudwatch_client.get_paginator('get_metric_data')
            response = paginator.paginate(
                **params, PaginationConfig=pagination_config
            ).build_full_result()
        else:
            response = cloudwatch_client.get_metric_data(**params)

        return response
    except ClientError as e:
        logger.error(
            f'AWS API error: {e.response["Error"]["Code"]} - {e.response["Error"]["Message"]}'
        )
        raise
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        raise
