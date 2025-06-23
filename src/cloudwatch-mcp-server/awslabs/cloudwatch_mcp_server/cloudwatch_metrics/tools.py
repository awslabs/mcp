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
from typing import Dict, Any, Optional, List, Union


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
        start_time: Union[str, datetime] = Field(
            ...,
            description="The start time for the metric data query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object"
        ),
        end_time: Optional[Union[str, datetime]] = Field(
            None,
            description="The end time for the metric data query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object. Defaults to current time if not provided."
        ),
        statistic: str = Field(
            "Average",
            description="The statistic to use for the metric (e.g., 'Average', 'Sum', 'Maximum', 'Minimum', 'SampleCount', 'p99')"
        ),
        target_datapoints: int = Field(
            60,
            description="Target number of data points to return (default: 60). Controls the granularity of the returned data."
        ),
    ) -> GetMetricDataResponse:
        """Retrieves CloudWatch metric data for a specific metric.

        This tool retrieves metric data from CloudWatch for a specific metric identified by its
        namespace, metric name, and dimensions, within a specified time range.

        Usage: Use this tool to get actual metric data from CloudWatch for analysis or visualization.

        Args:
            namespace: The metric namespace (e.g., "AWS/EC2", "AWS/Lambda")
            metric_name: The name of the metric (e.g., "CPUUtilization", "Duration")
            dimensions: List of dimensions with name and value pairs
            start_time: The start time for the metric data query (ISO format or datetime)
            end_time: The end time for the metric data query (ISO format or datetime), defaults to current time
            statistic: The statistic to use for the metric (e.g., 'Average', 'Sum')
            target_datapoints: Target number of data points to return (default: 60). Controls the granularity of the returned data.

        Returns:
            GetMetricDataResponse: An object containing the metric data results

        Example:
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions=[
                    Dimension(name="InstanceId", value="i-1234567890abcdef0")
                ],
                start_time="2023-01-01T00:00:00Z",
                # period will be auto-calculated based on time window
                statistic="Average"
            )
            for metric_result in result.metricDataResults:
                print(f"Metric: {metric_result.label}")
                for datapoint in metric_result.datapoints:
                    print(f"  {datapoint.timestamp}: {datapoint.value}")
        """
        try:
            # Process start_time and end_time
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            if end_time is None:
                end_time = datetime.utcnow()
            elif isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Calculate period based on time window and target datapoints
            time_window_seconds = int((end_time - start_time).total_seconds())
            
            # Calculate period based on time window and target datapoints
            # Ensure period is at least 60 seconds and a multiple of 60
            calculated_period = max(60, int(time_window_seconds / target_datapoints))
            # Round up to the nearest multiple of 60
            period = calculated_period + (60 - calculated_period % 60) if calculated_period % 60 != 0 else calculated_period
            
            logger.info(f'Calculated period: {period} seconds for time window of {time_window_seconds} seconds with target of {target_datapoints} datapoints')
            
            logger.info(f'Getting metric data for {namespace}/{metric_name} from {start_time} to {end_time} with period {period}s (target: {target_datapoints} datapoints)')
            logger.info(f'Dimensions: {[f"{d.name}={d.value}" for d in dimensions]}')
            
            # Convert dimensions to CloudWatch format
            cw_dimensions = [{'Name': d.name, 'Value': d.value} for d in dimensions]
            
            # Create the metric data query
            metric_query = {
                'Id': 'm1',  # Using a simple ID for the single metric query
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name,
                        'Dimensions': cw_dimensions
                    },
                    'Period': period,
                    'Stat': statistic
                },
                'ReturnData': True
            }
            
            # Call the GetMetricData API
            response = self.cloudwatch_client.get_metric_data(
                MetricDataQueries=[metric_query],
                StartTime=start_time,
                EndTime=end_time
            )
            
            # Process the response
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
            
        except Exception as e:
            logger.error(f'Error in get_metric_data: {str(e)}')
            await ctx.error(f'Error getting metric data: {str(e)}')
            raise

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