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
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Get metrics tool for AWS Serverless MCP Server."""

import datetime
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


class GetMetricsTool:
    """GetMetricsTool for retrieving metrics from a deployed web application."""

    def __init__(self, mcp: FastMCP):
        """Initialize the GetMetricsTool with a FastMCP instance."""
        mcp.tool(name='get_metrics')(self.get_metrics)

    async def get_metrics(
        self,
        ctx: Context,
        project_name: str = Field(description='Project name'),
        start_time: Optional[str] = Field(
            default=None, description='Start time for metrics (ISO format)'
        ),
        end_time: Optional[str] = Field(
            default=None, description='End time for metrics (ISO format)'
        ),
        period: Optional[int] = Field(default=60, description='Period for metrics in seconds'),
        resources: Optional[List[Literal['lambda', 'apiGateway', 'cloudfront']]] = Field(
            default=['lambda', 'apiGateway'], description='Resources to get metrics for'
        ),
        distribution_id: Optional[str] = Field(
            default=None,
            description='CloudFront distribution ID to get metrics for. You can find the id from the CFN stack output',
        ),
        region: Optional[str] = Field(
            default=None, description='AWS region to use (e.g., us-east-1)'
        ),
        stage: Optional[str] = Field(default='prod', description='API Gateway stage'),
    ) -> Dict[str, Any]:
        """Retrieves CloudWatch metrics from a deployed web application.

        Use this tool get metrics on error rates, latency, throttles, etc. of Lambda functions, API Gateways, or CloudFront disributions.
        This tool can help provide insights into anomolies and monitor operations, which can help with troubleshooting.

        Returns:
            Dict: Metrics retrieval result
        """
        try:
            project_name = project_name
            resources = resources
            start_time = start_time
            end_time = end_time
            period = period
            region = region
            stage = stage

            logger.info(f'Getting metrics for project {project_name} in region {region}')

            # Initialize AWS clients
            cloudwatch_client = get_aws_client('cloudwatch', region)

            # Calculate time range for metrics
            end_dt = None
            start_dt = None

            if end_time:
                try:
                    end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f'Invalid end_time format: {end_time}')
                    end_dt = datetime.datetime.now(datetime.timezone.utc)
            else:
                end_dt = datetime.datetime.now(datetime.timezone.utc)

            if start_time:
                try:
                    start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f'Invalid start_time format: {start_time}')
                    start_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                        hours=24
                    )
            else:
                # Default to 24 hours ago
                start_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                    hours=24
                )

            # Prepare metric queries based on requested resources
            metric_queries = []

            # Initialize query_id before any conditional blocks
            query_id = 0

            # Build metric data queries for each resource type
            if resources is not None and 'lambda' in resources:
                # Lambda metrics
                lambda_function_name = project_name

                # Assign unique incremental IDs for each metric query
                query_id = 0
                metric_queries.extend(
                    [
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Invocations',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': lambda_function_name}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'Lambda Invocations',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Duration',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': lambda_function_name}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Average',
                            },
                            'Label': 'Lambda Duration (Average)',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Duration',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': lambda_function_name}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'p99',
                            },
                            'Label': 'Lambda Duration (p99)',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Errors',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': lambda_function_name}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'Lambda Errors',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/Lambda',
                                    'MetricName': 'Throttles',
                                    'Dimensions': [
                                        {'Name': 'FunctionName', 'Value': lambda_function_name}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'Lambda Throttles',
                        },
                    ]
                )

            if resources is not None and 'apiGateway' in resources:
                # API Gateway metrics
                api_name = project_name

                metric_queries.extend(
                    [
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApiGateway',
                                    'MetricName': 'Count',
                                    'Dimensions': [
                                        {'Name': 'ApiName', 'Value': api_name},
                                        {'Name': 'Stage', 'Value': stage},
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'API Gateway Requests',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApiGateway',
                                    'MetricName': 'Latency',
                                    'Dimensions': [
                                        {'Name': 'ApiName', 'Value': api_name},
                                        {'Name': 'Stage', 'Value': stage},
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Average',
                            },
                            'Label': 'API Gateway Latency (Average)',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApiGateway',
                                    'MetricName': 'Latency',
                                    'Dimensions': [
                                        {'Name': 'ApiName', 'Value': api_name},
                                        {'Name': 'Stage', 'Value': stage},
                                    ],
                                },
                                'Period': period,
                                'Stat': 'p95',
                            },
                            'Label': 'API Gateway Latency (p95)',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApiGateway',
                                    'MetricName': '4XXError',
                                    'Dimensions': [
                                        {'Name': 'ApiName', 'Value': api_name},
                                        {'Name': 'Stage', 'Value': stage},
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'API Gateway 4XX Errors',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/ApiGateway',
                                    'MetricName': '5XXError',
                                    'Dimensions': [
                                        {'Name': 'ApiName', 'Value': api_name},
                                        {'Name': 'Stage', 'Value': stage},
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'API Gateway 5XX Errors',
                        },
                    ]
                )

            if resources is not None and 'cloudfront' in resources:
                # CloudFront metrics
                # Note: CloudFront metrics are global, so we use the distribution ID
                distribution_id = (
                    distribution_id if distribution_id else f'{project_name}-distribution'
                )

                metric_queries.extend(
                    [
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/CloudFront',
                                    'MetricName': 'Requests',
                                    'Dimensions': [
                                        {'Name': 'DistributionId', 'Value': distribution_id}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'CloudFront Requests',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/CloudFront',
                                    'MetricName': 'BytesDownloaded',
                                    'Dimensions': [
                                        {'Name': 'DistributionId', 'Value': distribution_id}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Sum',
                            },
                            'Label': 'CloudFront Bytes Downloaded',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/CloudFront',
                                    'MetricName': 'TotalErrorRate',
                                    'Dimensions': [
                                        {'Name': 'DistributionId', 'Value': distribution_id}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Average',
                            },
                            'Label': 'CloudFront Error Rate',
                        },
                        {
                            'Id': f'q{(query_id := query_id + 1)}',
                            'MetricStat': {
                                'Metric': {
                                    'Namespace': 'AWS/CloudFront',
                                    'MetricName': 'OriginLatency',
                                    'Dimensions': [
                                        {'Name': 'DistributionId', 'Value': distribution_id}
                                    ],
                                },
                                'Period': period,
                                'Stat': 'Average',
                            },
                            'Label': 'CloudFront Origin Latency',
                        },
                    ]
                )

            # If no valid metrics were found, return an error
            if not metric_queries:
                return {
                    'success': False,
                    'message': 'No valid metrics found for the specified resources',
                }

            # Execute the GetMetricData command
            response = cloudwatch_client.get_metric_data(
                StartTime=start_dt,
                EndTime=end_dt,
                MetricDataQueries=metric_queries,
                ScanBy='TimestampAscending',
            )

            # Process and organize the results
            metrics = {'lambda': {}, 'apiGateway': {}, 'cloudfront': {}}

            # Process metric results
            for result in response.get('MetricDataResults', []):
                label = result.get('Label', '')
                timestamps = result.get('Timestamps', [])
                values = result.get('Values', [])

                # Format the data points
                data_points = []
                for i, timestamp in enumerate(timestamps):
                    if i < len(values):
                        data_points.append(
                            {
                                'timestamp': timestamp.isoformat(),
                                'value': values[i],
                                'unit': self.get_unit_for_metric(label),
                            }
                        )

                # Categorize by service
                if 'Lambda' in label:
                    metric_name = label.replace('Lambda ', '').lower()
                    metrics['lambda'][metric_name] = data_points
                elif 'API Gateway' in label:
                    metric_name = label.replace('API Gateway ', '').lower()
                    metrics['apiGateway'][metric_name] = data_points
                elif 'CloudFront' in label:
                    metric_name = label.replace('CloudFront ', '').lower()
                    metrics['cloudfront'][metric_name] = data_points

            return {'success': True, 'metrics': metrics}
        except Exception as e:
            logger.error(f'Error in get_metrics: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to retrieve metrics: {str(e)}',
                'error': str(e),
            }

    @staticmethod
    def get_unit_for_metric(label: str) -> str:
        """Helper function to determine the appropriate unit for a metric based on its label.

        Args:
            label: The metric label

        Returns:
            str: The appropriate unit for the metric
        """
        if 'Duration' in label or 'Latency' in label:
            return 'Milliseconds'
        elif 'Bytes' in label:
            return 'Bytes'
        elif 'Rate' in label or 'Percentage' in label:
            return 'Percent'
        else:
            return 'Count'
