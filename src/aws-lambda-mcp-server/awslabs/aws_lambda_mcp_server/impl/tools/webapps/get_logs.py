"""Get logs tool for AWS Lambda MCP Server."""

import os
import boto3
import json
import datetime
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import GetLogsRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger
import tempfile

# Define the directory where deployment status files will be stored
DEPLOYMENT_STATUS_DIR = os.path.join(tempfile.gettempdir(), 'serverless-web-mcp-deployments')

async def get_logs(request: GetLogsRequest) -> Dict[str, Any]:
    """
    Get logs from a deployed web application.
    
    Args:
        request: GetLogsRequest object containing log retrieval parameters
    
    Returns:
        Dict: Log retrieval result
    """
    try:
        project_name = request.project_name
        start_time = request.start_time
        end_time = request.end_time
        limit = request.limit
        filter_pattern = request.filter_pattern
        
        logger.info(f"Getting logs for project {project_name}")
        
        # Get deployment status to find the CloudWatch log group
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
        logs_client = session.client('logs')
        
        # Use the provided log group name or determine it based on the deployment type
        log_group_name = request.log_group_name
        
        if not log_group_name:
            deployment_type = status_data.get('deploymentType')
            
            if deployment_type in ['backend', 'fullstack']:
                # For backend deployments, the log group is for the Lambda function
                log_group_name = f"/aws/lambda/{project_name}"
            else:
                # For frontend-only deployments, there are no Lambda logs
                return {
                    'success': False,
                    'message': f"Frontend-only deployments do not have Lambda logs",
                    'deploymentType': deployment_type
                }
        
        # Convert ISO format timestamps to milliseconds since epoch if provided
        query_params = {
            'logGroupName': log_group_name,
            'limit': limit
        }
        
        if start_time:
            try:
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query_params['startTime'] = int(start_dt.timestamp() * 1000)
            except ValueError:
                logger.warning(f"Invalid start_time format: {start_time}")
        
        if end_time:
            try:
                end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query_params['endTime'] = int(end_dt.timestamp() * 1000)
            except ValueError:
                logger.warning(f"Invalid end_time format: {end_time}")
        
        if filter_pattern:
            query_params['filterPattern'] = filter_pattern
        
        # Get log streams
        try:
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5  # Get the 5 most recent log streams
            )
            
            log_streams = streams_response.get('logStreams', [])
            
            if not log_streams:
                return {
                    'success': True,
                    'message': f"No log streams found for project '{project_name}'",
                    'logGroupName': log_group_name,
                    'events': []
                }
            
            # Get logs from each stream
            all_events = []
            
            for stream in log_streams:
                stream_name = stream.get('logStreamName')
                
                try:
                    events_response = logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=stream_name,
                        startFromHead=False,
                        limit=limit // len(log_streams)  # Distribute the limit across streams
                    )
                    
                    events = events_response.get('events', [])
                    
                    # Format the events
                    for event in events:
                        timestamp = event.get('timestamp')
                        if timestamp:
                            event['timestampIso'] = datetime.datetime.fromtimestamp(
                                timestamp / 1000, datetime.timezone.utc
                            ).isoformat()
                        
                        event['logStreamName'] = stream_name
                    
                    all_events.extend(events)
                except Exception as e:
                    logger.error(f"Error getting logs from stream {stream_name}: {str(e)}")
            
            # Sort events by timestamp
            all_events.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Limit the total number of events
            all_events = all_events[:limit]
            
            return {
                'success': True,
                'message': f"Retrieved {len(all_events)} log events for project '{project_name}'",
                'logGroupName': log_group_name,
                'events': all_events
            }
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to get logs for project '{project_name}'",
                'error': str(e)
            }
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to get logs for project '{project_name}'",
            'error': str(e)
        }
