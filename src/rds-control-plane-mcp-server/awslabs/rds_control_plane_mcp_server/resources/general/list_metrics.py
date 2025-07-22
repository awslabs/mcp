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

"""Resource for listing available CloudWatch metrics for RDS resources (instances and clusters)."""

from ...common.connection import CloudwatchConnectionManager
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from ...common.utils import handle_paginated_aws_api_call
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class MetricList(BaseModel):
    """A model for a list of metrics included in the response of the available metrics resources."""

    metrics: List[str] = Field(..., description='List of metrics')
    count: int = Field(..., description='Number of metrics in the list')
    namespace: str = 'AWS/RDS'
    resource_uri: Optional[str] = Field(
        None, description='URI of the resource for which metrics are listed'
    )


def list_metrics(dimension_name: str, dimension_value: str) -> MetricList:
    """List available CloudWatch metrics for a given RDS resource.

    Args:
        dimension_name: The name of the dimension to filter metrics by (e.g., 'DBInstanceIdentifier')
        dimension_value: The value of the dimension to filter metrics by (e.g., instance ID)

    Returns:
        MetricList: List of metrics with information about availability
        and recent activity
    """
    cloudwatch_client = CloudwatchConnectionManager.get_connection()

    operation_parameters = {
        'Namespace': 'AWS/RDS',
        'Dimensions': [
            {'Name': dimension_name, 'Value': dimension_value},
        ],
    }

    metrics = handle_paginated_aws_api_call(
        client=cloudwatch_client,
        paginator_name='list_metrics',
        operation_parameters=operation_parameters,
        format_function=lambda metric_dict: metric_dict['MetricName'],
        result_key='Metrics',
    )

    return MetricList(
        metrics=metrics,
        count=len(metrics),
        namespace='AWS/RDS',
        resource_uri=None,
    )


@mcp.resource(
    uri='aws-rds://{resource_type}/{resource_identifier}/cloudwatch_metrics',
    name='ListRDSMetrics',
    description='List available metrics for a RDS resource (db-instance or db-cluster).',
    mime_type='text/plain',
)
@handle_exceptions
def list_rds_metrics(
    resource_type: Literal['db-instance', 'db-cluster'], resource_identifier: str
) -> MetricList:
    """List available metrics for an Amazon RDS resource.

    This function retrieves a list of all available CloudWatch metrics for a specified
    RDS resource (instance or cluster). It determines the appropriate dimension name based on
    the resource type and uses the resource identifier to filter metrics.

    Args:
        resource_type (str): The type of RDS resource ('db-instance' or 'db-cluster').
        resource_identifier (str): The identifier of the RDS resource to retrieve metrics for.

    Returns:
        MetricList: A list of available metrics for the specified RDS resource.
    """
    dimension_mapping = {
        'db-instance': 'DBInstanceIdentifier',
        'db-cluster': 'DBClusterIdentifier',
    }

    dimension_name = dimension_mapping.get(resource_type)
    if not dimension_name:
        raise ValueError(
            f"Unsupported resource type: {resource_type}. Must be 'db-instance' or 'db-cluster'."
        )

    result = list_metrics(
        dimension_name=dimension_name,
        dimension_value=resource_identifier,
    )
    result.resource_uri = f'aws-rds://{resource_type}/{resource_identifier}/cloudwatch_metrics'
    return result
