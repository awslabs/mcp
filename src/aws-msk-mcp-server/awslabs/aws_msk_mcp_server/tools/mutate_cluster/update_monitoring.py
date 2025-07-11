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
"""Function to update the monitoring settings for an MSK cluster.

Maps to AWS CLI command: aws kafka update-monitoring.
"""


def update_monitoring(
    cluster_arn,
    current_version,
    enhanced_monitoring,
    open_monitoring=None,
    logging_info=None,
    client=None,
):
    """Updates the monitoring settings for an MSK cluster.

    Args:
        cluster_arn (str): The Amazon Resource Name (ARN) that uniquely identifies the cluster
        current_version (str): The version of the cluster to update from
        enhanced_monitoring (str): Specifies the level of monitoring for the MSK cluster.
                                  Options: DEFAULT, PER_BROKER, PER_TOPIC_PER_BROKER
        open_monitoring (dict, optional): The settings for open monitoring
            Example: {
                "Prometheus": {
                    "JmxExporter": {
                        "EnabledInBroker": True
                    },
                    "NodeExporter": {
                        "EnabledInBroker": True
                    }
                }
            }
        logging_info (dict, optional): The settings for broker logs
            Example: {
                "BrokerLogs": {
                    "CloudWatchLogs": {
                        "Enabled": True,
                        "LogGroup": "my-log-group"
                    },
                    "Firehose": {
                        "Enabled": True,
                        "DeliveryStream": "my-delivery-stream"
                    },
                    "S3": {
                        "Enabled": True,
                        "Bucket": "my-bucket",
                        "Prefix": "logs/"
                    }
                }
            }
        client (boto3.client): Boto3 client for Kafka. Must be provided by the tool function.

    Returns:
        dict: Result of the update operation containing ClusterArn and ClusterOperationArn
    """
    if client is None:
        raise ValueError(
            'Client must be provided. This function should only be called from a tool function.'
        )

    # Build the request parameters
    params = {'ClusterArn': cluster_arn, 'CurrentVersion': current_version}

    # Add optional parameters if provided
    if enhanced_monitoring:
        params['EnhancedMonitoring'] = enhanced_monitoring

    if open_monitoring:
        params['OpenMonitoring'] = open_monitoring

    if logging_info:
        params['LoggingInfo'] = logging_info

    response = client.update_monitoring(**params)

    return response
