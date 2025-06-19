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

"""Tool for getting CloudWatch metric statistics."""

from ...common.connection import CloudWatchConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from typing import Any, Dict, List, Optional


@mcp.tool(name='get-metric-statistics')
@handle_exceptions
async def get_metric_statistics(
    metric_name: str,
    start_time: str,
    end_time: str,
    period: int,
    dimensions: Optional[List[Dict[str, str]]] = None,
    statistics: Optional[List[str]] = None,
    extended_statistics: Optional[List[str]] = None,
    unit: Optional[str] = None,
) -> Dict[str, Any]:
    """Get CloudWatch metric statistics.

    Args:
        metric_name: The name of the metric
        start_time: The start time in ISO 8601 format
        end_time: The end time in ISO 8601 format
        period: The granularity, in seconds, of the returned data points
        dimensions: The dimensions to filter by
        statistics: The metric statistics to return
        extended_statistics: The percentile statistics to return
        unit: The unit for the metric

    Returns:
        Dict containing metric statistics
    """
    client = CloudWatchConnectionManager.get_connection()

    # Convert ISO 8601 strings to datetime objects
    start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

    # Build request parameters
    params: Dict[str, Any] = {
        'Namespace': 'AWS/ElastiCache',
        'MetricName': metric_name,
        'StartTime': start,
        'EndTime': end,
        'Period': period,
    }

    # Add optional parameters
    if dimensions:
        # Ensure dimensions are properly formatted as [{'Name': name, 'Value': value}, ...]
        formatted_dimensions = []
        for d in dimensions:
            # Check if the dimension is already in the correct format
            if 'Name' in d and 'Value' in d:
                formatted_dimensions.append(d)
            else:
                # Convert from {key: value} format to {'Name': key, 'Value': value}
                for k, v in d.items():
                    formatted_dimensions.append({'Name': k, 'Value': v})
        params['Dimensions'] = formatted_dimensions
    if statistics:
        params['Statistics'] = statistics
    if extended_statistics:
        params['ExtendedStatistics'] = extended_statistics
    if unit:
        params['Unit'] = unit

    # Make API call
    response = client.get_metric_statistics(**params)

    # Extract relevant information
    datapoints = response.get('Datapoints', [])
    label = response.get('Label')

    result = {'Label': label, 'Datapoints': datapoints}

    return result
