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

"""CloudWatch Metrics tools for MCP server."""

import boto3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    Dimension,
    MetricDataPoint,
    MetricDataResult,
    GetMetricDataResponse,
    MetricMetadata,
    MetricMetadataIndexKey,
    AlarmRecommendation,
    AlarmRecommendationThreshold,
    AlarmRecommendationDimension,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Dict, Any, Optional, List, Union, Literal


class CloudWatchMetricsTools:
    """CloudWatch Metrics tools for MCP server."""
    
    def __init__(self):
        """Initialize the CloudWatch Metrics client"""
        # Initialize client
        aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                self.cloudwatch_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
                    'cloudwatch', config=config
                )
            else:
                self.cloudwatch_client = boto3.Session(region_name=aws_region).client('cloudwatch', config=config)
        except Exception as e:
            logger.error(f'Error creating cloudwatch client: {str(e)}')
            raise

        # Load and index metric metadata
        self.metric_metadata_index: Dict[MetricMetadataIndexKey, Any] = self._load_and_index_metadata()
        logger.info(f'Loaded {len(self.metric_metadata_index)} metric metadata entries')

    def _load_and_index_metadata(self) -> Dict[MetricMetadataIndexKey, Any]:
        """Load metric metadata from JSON file and create an indexed structure.
        
        Returns:
            Dict indexed by MetricMetadataIndexKey objects.
            Structure: {MetricMetadataIndexKey: metadata_entry}
        """
        try:
            # Get the path to the metadata file
            current_dir = Path(__file__).parent
            metadata_file = current_dir / 'data' / 'metric_metadata.json'
            
            if not metadata_file.exists():
                logger.warning(f'Metric metadata file not found: {metadata_file}')
                return {}
            
            # Load the JSON data
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_list = json.load(f)
            
            logger.info(f'Loaded {len(metadata_list)} metric metadata entries')
            
            # Create the indexed structure
            index = {}
            
            for entry in metadata_list:
                try:
                    metric_id = entry.get('metricId', {})
                    namespace = metric_id.get('namespace')
                    metric_name = metric_id.get('metricName')
                    
                    if not namespace or not metric_name:
                        continue
                    
                    # Create the index key (no dimensions)
                    key = MetricMetadataIndexKey(namespace, metric_name)
                    
                    # Store the entry
                    index[key] = entry
                    
                except Exception as e:
                    logger.warning(f'Error processing metadata entry: {e}')
                    continue
            
            logger.info(f'Successfully indexed {len(index)} metric metadata entries')
            return index
            
        except Exception as e:
            logger.error(f'Error loading metric metadata: {e}')
            return {}

    def _lookup_metadata(self, namespace: str, metric_name: str) -> Dict[str, Any]:
        """Look up metadata for a specific metric.
        
        Args:
            namespace: The metric namespace
            metric_name: The metric name
            
        Returns:
            Metadata entry if found, empty dict otherwise
        """
        key = MetricMetadataIndexKey(namespace, metric_name)
        return self.metric_metadata_index.get(key, {})

    def register(self, mcp):
        """Register all CloudWatch Metrics tools with the MCP server."""
        # Register get_metric_data tool
        mcp.tool(
            name='get_metric_data'
        )(self.get_metric_data)
    
        # Register get_metric_metadata tool
        mcp.tool(
            name='get_metric_metadata'
        )(self.get_metric_metadata)

        # Register get_recommended_metric_alarms tool
        mcp.tool(
            name='get_recommended_metric_alarms'
        )(self.get_recommended_metric_alarms)
        
    async def get_metric_data(
        self,
        ctx: Context,
        namespace: str,
        metric_name: str,
        start_time: Union[str, datetime],
        dimensions: List[Dimension] = [],
        end_time: Annotated[Union[str, datetime] | None, Field(
            description="The end time for the metric data query (ISO format or datetime), defaults to current time"
        )] = None,
        statistic: Annotated[Literal["AVG", "COUNT", "MAX", "MIN", "SUM", "Average", "Sum", "Maximum", "Minimum", "SampleCount"], Field(
            description="The statistic to use for the metric"
        )] = "AVG",
        target_datapoints: Annotated[int, Field(
            description="Target number of data points to return (default: 60). Controls the granularity of the returned data."
        )] = 60,
        group_by_dimension: Annotated[str | None, Field(
            description="Dimension name to group by in Metrics Insights mode. Must be included in schema_dimension_keys."
        )] = None,
        schema_dimension_keys: Annotated[List[str], Field(
            description="List of dimension keys to include in the SCHEMA definition for Metrics Insights query."
        )] = [],
        limit: Annotated[int | None, Field(
            description="Maximum number of results to return in Metrics Insights mode (used with LIMIT clause)."
        )] = None,
        sort_order: Annotated[Literal["ASC", "DESC"] | None, Field(
            description="Sort order for results when using ORDER BY in Metrics Insights. Can be 'ASC', 'DESC', or None."
        )] = None,
        order_by_statistic: Annotated[Literal["AVG", "COUNT", "MAX", "MIN", "SUM"] | None, Field(
            description="Statistic to use in the ORDER BY clause. Required if sort_order is specified."
        )] = None,
    ) -> GetMetricDataResponse:
        """Retrieves CloudWatch metric data for a specific metric.

        This tool retrieves metric data from CloudWatch for a specific metric identified by its
        namespace, metric name, and dimensions, within a specified time range. It can use either
        standard GetMetricData API or CloudWatch Metrics Insights for more advanced querying.
        
        The function automatically determines whether to use standard GetMetricData or Metrics Insights
        based on the parameters provided. If any Metrics Insights specific parameters are provided
        (group_by_dimension, schema_dimension_keys, limit, sort_order, or order_by_statistic), it will use Metrics Insights.

        When using group_by_dimension, you must include that dimension in schema_dimension_keys.

        Usage: Use this tool to get actual metric data from CloudWatch for analysis or visualization.

        Returns:
            GetMetricDataResponse: An object containing the metric data results

        Example 1 (Standard GetMetricData):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                dimensions=[
                    Dimension(name="InstanceId", value="i-1234567890abcdef0")
                ],
                statistic="Average"
                # Period will be auto-calculated based on time window and target_datapoints
            )
            
        Example 2 (Metrics Insights with group by):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                end_time="2023-01-02T00:00:00Z",
                statistic="AVG",
                schema_dimension_keys=["InstanceType"],
                group_by_dimension="InstanceType"
                # This will generate a query like: SELECT AVG("CPUUtilization") FROM SCHEMA("AWS/EC2", "InstanceType") GROUP BY "InstanceType"
            )
            
        Example 3 (Metrics Insights with schema dimension keys):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                end_time="2023-01-02T00:00:00Z",
                statistic="AVG",
                schema_dimension_keys=["InstanceId", "InstanceType"],
                group_by_dimension="InstanceId"
                # This will generate a query like: SELECT AVG("CPUUtilization") FROM SCHEMA("AWS/EC2", "InstanceId", "InstanceType") GROUP BY "InstanceId"
            )
            
        Example 4 (Metrics Insights with ORDER BY and LIMIT to find the top 5 EC2 instances with the highest CPU utilization):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                end_time="2023-01-02T00:00:00Z",
                statistic="AVG",
                schema_dimension_keys=["InstanceId"],
                group_by_dimension="InstanceId",
                sort_order="DESC",
                limit=5,
                order_by_statistic="MAX"
                # This will generate a query like: SELECT AVG("CPUUtilization") FROM SCHEMA("AWS/EC2", "InstanceId") GROUP BY "InstanceId" ORDER BY MAX() DESC LIMIT 5
            )
            
        Example 5 (Metrics Insights with ORDER BY without sort direction to find the EC2 instances with the highest CPU utilization ordered by default ASC):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                end_time="2023-01-02T00:00:00Z",
                statistic="AVG",
                schema_dimension_keys=["InstanceId"],
                group_by_dimension="InstanceId",
                order_by_statistic="MAX"
                # This will generate a query like: SELECT AVG("CPUUtilization") FROM SCHEMA("AWS/EC2", "InstanceId") GROUP BY "InstanceId" ORDER BY MAX()
            )
            
        Example 6 (Metrics Insights without ORDER BY clause to find the EC2 instances with the highest CPU utilization in no specific order):
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                start_time="2023-01-01T00:00:00Z",
                end_time="2023-01-02T00:00:00Z",
                statistic="AVG",
                schema_dimension_keys=["InstanceId"],
                group_by_dimension="InstanceId"
                # This will generate a query like: SELECT AVG("CPUUtilization") FROM SCHEMA("AWS/EC2", "InstanceId") GROUP BY "InstanceId"
                # No ORDER BY clause is added since neither order_by_statistic nor sort_order is specified
            )
            
        For each result:
            for metric_result in result.metricDataResults:
                print(f"Metric: {metric_result.label}")
                for datapoint in metric_result.datapoints:
                    print(f"  {datapoint.timestamp}: {datapoint.value}")
        """
        try:
            # Process time parameters and calculate period
            start_time, end_time, period = self._prepare_time_parameters(start_time, end_time, target_datapoints)
            
            # Determine which query method to use and build the appropriate query
            use_metrics_insights = any([
                group_by_dimension is not None,
                schema_dimension_keys,
                limit is not None,
                sort_order is not None,
                order_by_statistic is not None
            ])
            
            if use_metrics_insights:
                metric_query = self._build_metrics_insights_query(
                    namespace, metric_name, dimensions, statistic, period,
                    group_by_dimension, schema_dimension_keys, 
                    order_by_statistic, sort_order, limit
                )
            else:
                metric_query = self._build_standard_metric_query(
                    namespace, metric_name, dimensions, statistic, period
                )
            
            # Call the GetMetricData API
            response = self.cloudwatch_client.get_metric_data(
                MetricDataQueries=[metric_query],
                StartTime=start_time,
                EndTime=end_time
            )
            
            # Process the response
            return self._process_metric_data_response(response)
            
        except Exception as e:
            logger.error(f'Error in get_metric_data: {str(e)}')
            await ctx.error(f'Error getting metric data: {str(e)}')
            raise

    def _prepare_time_parameters(self, start_time, end_time, target_datapoints):
        """Process time parameters and calculate the period."""
        # Convert string times to datetime objects
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        if end_time is None:
            end_time = datetime.utcnow()
        elif isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Calculate period based on time window and target datapoints
        time_window_seconds = int((end_time - start_time).total_seconds())
        calculated_period = max(60, int(time_window_seconds / target_datapoints))
        
        # Round up to the nearest multiple of 60
        period = calculated_period + (60 - calculated_period % 60) if calculated_period % 60 != 0 else calculated_period
        
        logger.info(f'Calculated period: {period} seconds for time window of {time_window_seconds} seconds with target of {target_datapoints} datapoints')
        
        return start_time, end_time, period

    def _build_metrics_insights_query(
        self, namespace, metric_name, dimensions, statistic, period,
        group_by_dimension, schema_dimension_keys, order_by_statistic, sort_order, limit
    ):
        """Build a Metrics Insights query."""
        logger.info(f'Building Metrics Insights query for {namespace}/{metric_name}')
        
        # Validate that group_by_dimension is included in schema_dimension_keys
        if group_by_dimension is not None and group_by_dimension not in schema_dimension_keys:
            raise ValueError(f"group_by_dimension '{group_by_dimension}' must be included in schema_dimension_keys: {schema_dimension_keys}")
        
        # Check if sort_order is specified but order_by_statistic is not
        if sort_order is not None and order_by_statistic is None:
            raise ValueError("If sort_order is specified, order_by_statistic must also be specified")
        
        # Map and validate statistics
        metrics_insights_statistic = self._map_to_metrics_insights_statistic(statistic)
        
        # Build the query components
        query_parts = []
        
        # SELECT clause
        query_parts.append(f'SELECT {metrics_insights_statistic}("{metric_name}")')
        
        # FROM clause with SCHEMA
        schema_str = self._build_schema_string(namespace, schema_dimension_keys)
        query_parts.append(f'FROM SCHEMA({schema_str})')
        
        # WHERE clause for dimensions
        if dimensions:
            where_clause = self._build_where_clause(dimensions)
            if where_clause:
                query_parts.append(where_clause)
        
        # GROUP BY clause
        if group_by_dimension:
            query_parts.append(f'GROUP BY "{group_by_dimension}"')
        
        # ORDER BY clause
        if order_by_statistic is not None:
            order_by_stat = order_by_statistic.upper()
            self._validate_metrics_insights_statistic(order_by_stat)
            
            order_clause = f'ORDER BY {order_by_stat}()'
            if sort_order is not None:
                order_clause += f' {sort_order}'
            
            query_parts.append(order_clause)
        
        # LIMIT clause
        if limit is not None and limit > 0:
            query_parts.append(f'LIMIT {limit}')
        
        # Join all parts to form the complete query
        query = ' '.join(query_parts)
        logger.info(f'Built Metrics Insights query: {query}')
        
        return {
            'Id': 'm1',
            'Expression': query,
            'Period': period,
            'ReturnData': True
        }

    def _build_standard_metric_query(self, namespace, metric_name, dimensions, statistic, period):
        """Build a standard CloudWatch metric query."""
        logger.info(f'Using standard GetMetricData for {namespace}/{metric_name}')
        logger.info(f'Dimensions: {[f"{d.name}={d.value}" for d in dimensions]}')
        
        # Map statistic to standard CloudWatch format
        cloudwatch_statistic = self._map_to_cloudwatch_statistic(statistic)
        
        # Convert dimensions to CloudWatch format
        cw_dimensions = [{'Name': d.name, 'Value': d.value} for d in dimensions]
        
        return {
            'Id': 'm1',
            'MetricStat': {
                'Metric': {
                    'Namespace': namespace,
                    'MetricName': metric_name,
                    'Dimensions': cw_dimensions
                },
                'Period': period,
                'Stat': cloudwatch_statistic
            },
            'ReturnData': True
        }

    def _process_metric_data_response(self, response):
        """Process the GetMetricData API response."""
        metric_data_results = []
        
        for result in response.get('MetricDataResults', []):
            # Process timestamps and values into data points
            datapoints = []
            timestamps = result.get('Timestamps', [])
            values = result.get('Values', [])
            
            for ts, val in zip(timestamps, values):
                datapoints.append(MetricDataPoint(
                    timestamp=ts,
                    value=val
                ))
            
            # Sort datapoints by timestamp
            datapoints.sort(key=lambda x: x.timestamp)
            
            # Create the metric data result
            metric_result = MetricDataResult(
                id=result.get('Id', ''),
                label=result.get('Label', ''),
                statusCode=result.get('StatusCode', 'Complete'),
                datapoints=datapoints,
                messages=result.get('Messages', [])
            )
            metric_data_results.append(metric_result)
        
        # Create and return the response
        return GetMetricDataResponse(
            metricDataResults=metric_data_results,
            messages=response.get('Messages', [])
        )

    def _map_to_metrics_insights_statistic(self, statistic):
        """Map and validate a statistic for Metrics Insights."""
        statistic_mapping = {
            'Average': 'AVG',
            'Sum': 'SUM',
            'Maximum': 'MAX',
            'Minimum': 'MIN',
            'SampleCount': 'COUNT'
        }
        
        metrics_insights_statistic = statistic_mapping.get(statistic, statistic.upper())
        self._validate_metrics_insights_statistic(metrics_insights_statistic)
        return metrics_insights_statistic

    def _validate_metrics_insights_statistic(self, statistic):
        """Validate that a statistic is valid for Metrics Insights."""
        valid_statistics = ['AVG', 'COUNT', 'MAX', 'MIN', 'SUM']
        if statistic not in valid_statistics:
            raise ValueError(f"Invalid statistic for Metrics Insights: {statistic}. Must be one of {', '.join(valid_statistics)}")

    def _map_to_cloudwatch_statistic(self, statistic):
        """Map a statistic to the standard CloudWatch format."""
        statistic_mapping = {
            'AVG': 'Average',
            'SUM': 'Sum',
            'MAX': 'Maximum',
            'MIN': 'Minimum',
            'COUNT': 'SampleCount'
        }
        
        return statistic_mapping.get(statistic, statistic)

    def _build_schema_string(self, namespace, schema_dimension_keys):
        """Build the SCHEMA part of a Metrics Insights query."""
        schema_parts = [f'"{namespace}"']
        
        if schema_dimension_keys:
            dimension_parts = [f'"{key}"' for key in schema_dimension_keys]
            schema_parts.extend(dimension_parts)
        
        return ', '.join(schema_parts)

    def _build_where_clause(self, dimensions):
        """Build the WHERE clause for a Metrics Insights query."""
        if not dimensions:
            return None
        
        dimension_filters = [f'"{dim.name}"=\'{dim.value}\'' for dim in dimensions]
        return f'WHERE {" AND ".join(dimension_filters)}'

    async def get_metric_metadata(
        self,
        ctx: Context,
        namespace: str = Field(
            ...,
            description="The namespace of the metric (e.g., 'AWS/EC2', 'AWS/Lambda')"
        ),
        metric_name: str = Field(
            ...,
            description="The name of the metric (e.g., 'CPUUtilization', 'Duration')"
        ),
    ) -> Optional[MetricMetadata]:
        """Gets metadata for a CloudWatch metric including description, unit and recommended
        statistics that can be used for metric data retrieval.

        This tool retrieves comprehensive metadata about a specific CloudWatch metric
        identified by its namespace and metric name.

        Usage: Use this tool to get detailed information about CloudWatch metrics,
        including their descriptions, units, and recommended statistics to use.

        Args:
            namespace: The metric namespace (e.g., "AWS/EC2", "AWS/Lambda")
            metric_name: The name of the metric (e.g., "CPUUtilization", "Duration")

        Returns:
            Optional[MetricMetadata]: An object containing the metric's description, 
                                     recommended statistics, and unit if found, 
                                     None if no metadata is available.

        Example:
            result = await get_metric_metadata(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization"
            )
            if result:
                print(f"Description: {result.description}")
                print(f"Unit: {result.unit}")
                print(f"Recommended Statistics: {result.recommendedStatistics}")
        """
        try:
            # Log the metric information for debugging
            logger.info(f'Getting metadata for metric: {namespace}/{metric_name}')
            
            # Look up metadata from the loaded index
            metadata = self._lookup_metadata(namespace, metric_name)
            
            if metadata:
                logger.info(f'Found metadata for {namespace}/{metric_name}')
                
                # Extract the required fields from metadata
                description = metadata.get('description', '')
                recommended_statistics = metadata.get('recommendedStatistics', '')
                unit = metadata.get('unitInfo', '')
                
                # Return populated MetricMetadata object
                return MetricMetadata(
                    description=description,
                    recommendedStatistics=recommended_statistics,
                    unit=unit
                )
            else:
                logger.info(f'No metadata found for {namespace}/{metric_name}')
                return None
            
        except Exception as e:
            logger.error(f'Error in get_metric_metadata: {str(e)}')
            await ctx.error(f'Error getting metric metadata: {str(e)}')
            raise

    async def get_recommended_metric_alarms(
        self,
        ctx: Context,
        namespace: str = Field(
            ...,
            description="The namespace of the metric (e.g., 'AWS/EC2', 'AWS/Lambda')"
        ),
        metric_name: str = Field(
            ...,
            description="The name of the metric (e.g., 'CPUUtilization', 'Duration')"
        ),
        dimensions: List[Dimension] = Field(
            default_factory=list,
            description="List of dimensions that identify the metric, each with name and value"
        ),
    ) -> List[AlarmRecommendation]:
        """Gets recommended alarms for a CloudWatch metric.

        This tool retrieves alarm recommendations for a specific CloudWatch metric
        identified by its namespace, metric name, and dimensions. The recommendations
        are filtered to match the provided dimensions.

        Usage: Use this tool to get recommended alarm configurations for CloudWatch metrics,
        including thresholds, evaluation periods, and other alarm settings.

        Args:
            namespace: The metric namespace (e.g., "AWS/EC2", "AWS/Lambda")
            metric_name: The name of the metric (e.g., "CPUUtilization", "Duration")
            dimensions: List of dimensions with name and value pairs

        Returns:
            List[AlarmRecommendation]: A list of alarm recommendations that match the
                                     provided dimensions. Empty list if no recommendations
                                     are found or available.

        Example:
            recommendations = await get_recommended_metric_alarms(
                ctx,
                namespace="AWS/EC2",
                metric_name="StatusCheckFailed_Instance",
                dimensions=[
                    Dimension(name="InstanceId", value="i-1234567890abcdef0")
                ]
            )
            for alarm in recommendations:
                print(f"Alarm: {alarm.alarmDescription}")
                print(f"Threshold: {alarm.threshold.staticValue}")
        """
        try:
            # Log the metric information for debugging
            logger.info(f'Getting alarm recommendations for metric: {namespace}/{metric_name}')
            logger.info(f'Dimensions: {[f"{d.name}={d.value}" for d in dimensions]}')
            
            # Look up metadata from the loaded index
            metadata = self._lookup_metadata(namespace, metric_name)
            
            if not metadata or 'alarmRecommendations' not in metadata:
                logger.info(f'No alarm recommendations found for {namespace}/{metric_name}')
                return []
            
            alarm_recommendations = metadata['alarmRecommendations']
            logger.info(f'Found {len(alarm_recommendations)} alarm recommendations for {namespace}/{metric_name}')
            
            # Filter recommendations based on provided dimensions
            matching_recommendations = []
            provided_dims = {dim.name: dim.value for dim in dimensions}
            
            for alarm_data in alarm_recommendations:
                if self._alarm_matches_dimensions(alarm_data, provided_dims):
                    try:
                        # Parse the alarm recommendation data
                        alarm_rec = self._parse_alarm_recommendation(alarm_data)
                        matching_recommendations.append(alarm_rec)
                    except Exception as e:
                        logger.warning(f'Error parsing alarm recommendation: {e}')
                        continue
            
            logger.info(f'Returning {len(matching_recommendations)} matching alarm recommendations')
            return matching_recommendations
            
        except Exception as e:
            logger.error(f'Error in get_recommended_metric_alarms: {str(e)}')
            await ctx.error(f'Error getting alarm recommendations: {str(e)}')
            raise

    def _alarm_matches_dimensions(self, alarm_data: Dict[str, Any], provided_dims: Dict[str, str]) -> bool:
        """Check if an alarm recommendation matches the provided dimensions.
        
        Args:
            alarm_data: The alarm recommendation data from metadata
            provided_dims: Dictionary of provided dimension names to values
            
        Returns:
            bool: True if the alarm matches the provided dimensions
        """
        alarm_dimensions = alarm_data.get('dimensions', [])
        
        # If alarm has no dimension requirements, it matches any dimensions
        if not alarm_dimensions:
            return True
        
        # Check if all alarm dimension requirements are satisfied
        for alarm_dim in alarm_dimensions:
            dim_name = alarm_dim.get('name')
            if not dim_name:
                continue
                
            # If alarm dimension has a specific value requirement
            if 'value' in alarm_dim:
                required_value = alarm_dim['value']
                if dim_name not in provided_dims or provided_dims[dim_name] != required_value:
                    return False
            else:
                # If alarm dimension has no specific value, just check if dimension name exists
                if dim_name not in provided_dims:
                    return False
        
        return True

    def _parse_alarm_recommendation(self, alarm_data: Dict[str, Any]) -> AlarmRecommendation:
        """Parse alarm recommendation data into AlarmRecommendation object.
        
        Args:
            alarm_data: Raw alarm recommendation data from metadata
            
        Returns:
            AlarmRecommendation: Parsed alarm recommendation object
        """
        # Parse threshold
        threshold_data = alarm_data.get('threshold', {})
        threshold = AlarmRecommendationThreshold(
            staticValue=threshold_data.get('staticValue', 0.0),
            justification=threshold_data.get('justification', '')
        )
        
        # Parse dimensions
        dimensions = []
        for dim_data in alarm_data.get('dimensions', []):
            alarm_dim = AlarmRecommendationDimension(
                name=dim_data.get('name', ''),
                value=dim_data.get('value') if 'value' in dim_data else None
            )
            dimensions.append(alarm_dim)
        
        # Create alarm recommendation
        return AlarmRecommendation(
            alarmDescription=alarm_data.get('alarmDescription', ''),
            threshold=threshold,
            period=alarm_data.get('period', 300),
            comparisonOperator=alarm_data.get('comparisonOperator', ''),
            statistic=alarm_data.get('statistic', ''),
            evaluationPeriods=alarm_data.get('evaluationPeriods', 1),
            datapointsToAlarm=alarm_data.get('datapointsToAlarm', 1),
            treatMissingData=alarm_data.get('treatMissingData', 'missing'),
            dimensions=dimensions,
            intent=alarm_data.get('intent', '')
        )
