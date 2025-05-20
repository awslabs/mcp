"""Get metrics tool for AWS Lambda MCP Server."""

import os
import boto3
import json
import datetime
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import GetMetricsRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger
import tempfile

# Define the directory where deployment status files will be stored
DEPLOYMENT_STATUS_DIR = os.path.join(tempfile.gettempdir(), 'serverless-web-mcp-deployments')

async def get_metrics(request: GetMetricsRequest) -> Dict[str, Any]:
    """
    Get metrics from a deployed web application.
    
    Args:
        request: GetMetricsRequest object containing metrics retrieval parameters
    
    Returns:
        Dict: Metrics retrieval result
    """
    try:
        project_name = request.project_name
        metric_names = request.metric_names
        start_time = request.start_time
        end_time = request.end_time
        period = request.period
        statistics = request.statistics
        
        logger.info(f"Getting metrics for project {project_name}")
        
        # Get deployment status to find the CloudWatch metrics
        status_file_path = os.path.join(DEPLOYMENT_STATUS_DIR, f'{project_name}.json')
        
        if not os.path.exists(status_file_path):
            return {
                'success': False,
                'message': f"No deployment found for project '{project_name}'",
                'status': 'NOT_FOUND'
            }
        
        with open(status_file_path, 'r') as f:
            status_data = json.load(f)
        
        # Check if the deployment was successful
        if status_data.get('status') != 'DEPLOYED':
            return {
                'success': False,
                'message': f"Deployment for project '{project_name}' is not in DEPLOYED state",
                'status': status_data.get('status')
            }
        
        # Initialize AWS clients
        session = boto3.Session(
            region_name=request.region or os.environ.get('AWS_REGION', 'us-east-1'),
            profile_name=os.environ.get('AWS_PROFILE', 'default')
        )
        cloudwatch_client = session.client('cloudwatch')
        
        # Determine the namespace and dimensions based on the deployment type
        deployment_type = status_data.get('deploymentType')
        
        if deployment_type in ['backend', 'fullstack']:
            # For backend deployments, use Lambda metrics
            namespace = 'AWS/Lambda'
            dimensions = [{'Name': 'FunctionName', 'Value': project_name}]
            
            # Map common metric names to AWS metric names
            metric_name_map = {
                'invocations': 'Invocations',
                'errors': 'Errors',
                'duration': 'Duration',
                'throttles': 'Throttles',
                'concurrentExecutions': 'ConcurrentExecutions',
                'memory': 'MemoryUtilization'
            }
            
            # Map user-friendly metric names to AWS metric names
            aws_metric_names = []
            for metric_name in metric_names:
                aws_name = metric_name_map.get(metric_name.lower())
                if aws_name:
                    aws_metric_names.append(aws_name)
                else:
                    aws_metric_names.append(metric_name)  # Use as-is if not in the map
        elif deployment_type == 'frontend':
            # For frontend deployments, use CloudFront metrics
            namespace = 'AWS/CloudFront'
            
            # Get the CloudFront distribution ID from the deployment status
            distribution_id = status_data.get('outputs', {}).get('CloudFrontDistributionId')
            
            if not distribution_id:
                return {
                    'success': False,
                    'message': f"CloudFront distribution ID not found for project '{project_name}'",
                    'deploymentType': deployment_type
                }
            
            dimensions = [{'Name': 'DistributionId', 'Value': distribution_id}]
            
            # Map common metric names to AWS metric names
            metric_name_map = {
                'requests': 'Requests',
                'bytesDownloaded': 'BytesDownloaded',
                'bytesUploaded': 'BytesUploaded',
                'totalErrorRate': 'TotalErrorRate',
                '4xxErrorRate': '4xxErrorRate',
                '5xxErrorRate': '5xxErrorRate'
            }
            
            # Map user-friendly metric names to AWS metric names
            aws_metric_names = []
            for metric_name in metric_names:
                aws_name = metric_name_map.get(metric_name.lower())
                if aws_name:
                    aws_metric_names.append(aws_name)
                else:
                    aws_metric_names.append(metric_name)  # Use as-is if not in the map
        else:
            return {
                'success': False,
                'message': f"Unknown deployment type: {deployment_type}",
                'deploymentType': deployment_type
            }
        
        # Convert ISO format timestamps to datetime objects if provided
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid start_time format: {start_time}")
                start_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)
        else:
            # Default to 3 hours ago
            start_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)
        
        if end_time:
            try:
                end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid end_time format: {end_time}")
                end_dt = datetime.datetime.now(datetime.timezone.utc)
        else:
            # Default to now
            end_dt = datetime.datetime.now(datetime.timezone.utc)
        
        # Get metrics
        try:
            metrics_data = {}
            
            for metric_name in aws_metric_names:
                try:
                    response = cloudwatch_client.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric_name,
                        Dimensions=dimensions,
                        StartTime=start_dt,
                        EndTime=end_dt,
                        Period=period,
                        Statistics=statistics
                    )
                    
                    datapoints = response.get('Datapoints', [])
                    
                    # Format the datapoints
                    formatted_datapoints = []
                    for datapoint in datapoints:
                        formatted_datapoint = {}
                        
                        # Convert timestamp to ISO format
                        if 'Timestamp' in datapoint:
                            formatted_datapoint['timestamp'] = datapoint['Timestamp'].isoformat()
                        
                        # Include statistics
                        for stat in statistics:
                            if stat in datapoint:
                                formatted_datapoint[stat.lower()] = datapoint[stat]
                        
                        formatted_datapoints.append(formatted_datapoint)
                    
                    # Sort datapoints by timestamp
                    formatted_datapoints.sort(key=lambda x: x.get('timestamp', ''))
                    
                    metrics_data[metric_name] = {
                        'datapoints': formatted_datapoints,
                        'label': metric_name
                    }
                except Exception as e:
                    logger.error(f"Error getting metric {metric_name}: {str(e)}")
                    metrics_data[metric_name] = {
                        'error': str(e),
                        'label': metric_name
                    }
            
            return {
                'success': True,
                'message': f"Retrieved metrics for project '{project_name}'",
                'namespace': namespace,
                'dimensions': dimensions,
                'startTime': start_dt.isoformat(),
                'endTime': end_dt.isoformat(),
                'period': period,
                'statistics': statistics,
                'metrics': metrics_data
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to get metrics for project '{project_name}'",
                'error': str(e)
            }
    except Exception as e:
        logger.error(f"Error in get_metrics: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to get metrics for project '{project_name}'",
            'error': str(e)
        }
