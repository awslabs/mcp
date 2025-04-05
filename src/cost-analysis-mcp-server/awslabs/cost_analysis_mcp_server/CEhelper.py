import boto3
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Optional


class DaysParam(BaseModel):
    """Parameters for specifying the number of days to look back."""

    days: int = Field(default=7, description='Number of days to look back for cost data')


class BedrockLogsParams(BaseModel):
    """Parameters for retrieving Bedrock invocation logs."""

    days: int = Field(
        default=7, description='Number of days to look back for Bedrock logs', ge=1, le=90
    )
    region: str = Field(default='us-east-1', description='AWS region to retrieve logs from')
    log_group_name: str = Field(
        description='Bedrock Log Group Name',
        default=os.environ.get('BEDROCK_LOG_GROUP_NAME', 'BedrockModelInvocationLogGroup'),
    )


def get_instance_type_breakdown(ce_client, date, region, service, dimension_key):
    """Helper function to get instance type or usage type breakdown for a specific service.

    Args:
        ce_client: The Cost Explorer client
        date: The date to query
        region: The AWS region
        service: The AWS service name
        dimension_key: The dimension to group by (e.g., 'INSTANCE_TYPE' or 'USAGE_TYPE')

    Returns:
        DataFrame containing the breakdown or None if no data
    """
    tomorrow = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    instance_response = ce_client.get_cost_and_usage(
        TimePeriod={'Start': date, 'End': tomorrow},
        Granularity='DAILY',
        Filter={
            'And': [
                {'Dimensions': {'Key': 'REGION', 'Values': [region]}},
                {'Dimensions': {'Key': 'SERVICE', 'Values': [service]}},
            ]
        },
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': dimension_key}],
    )

    if (
        'ResultsByTime' in instance_response
        and instance_response['ResultsByTime']
        and 'Groups' in instance_response['ResultsByTime'][0]
        and instance_response['ResultsByTime'][0]['Groups']
    ):
        instance_data = instance_response['ResultsByTime'][0]
        instance_costs = []

        for instance_group in instance_data['Groups']:
            type_value = instance_group['Keys'][0]
            cost_value = float(instance_group['Metrics']['UnblendedCost']['Amount'])

            # Add a better label for the dimension used
            column_name = 'Instance Type' if dimension_key == 'INSTANCE_TYPE' else 'Usage Type'

            instance_costs.append({column_name: type_value, 'Cost': cost_value})

        # Create DataFrame and sort by cost
        result_df = pd.DataFrame(instance_costs)
        if not result_df.empty:
            result_df = result_df.sort_values('Cost', ascending=False)
            return result_df

    return None


def get_bedrock_logs(params: BedrockLogsParams) -> Optional[pd.DataFrame]:
    """Retrieve Bedrock invocation logs for the last n days in a given region as a dataframe.

    Args:
        params: Pydantic model containing parameters:
            - days: Number of days to look back (default: 7)
            - region: AWS region to query (default: us-east-1)

    Returns:
        pd.DataFrame: DataFrame containing the log data with columns:
            - timestamp: Timestamp of the invocation
            - region: AWS region
            - modelId: Bedrock model ID
            - userId: User ARN
            - inputTokens: Number of input tokens
            - completionTokens: Number of completion tokens
            - totalTokens: Total tokens used
    """
    # Initialize CloudWatch Logs client
    client = boto3.client('logs', region_name=params.region)

    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=params.days)

    # Convert to milliseconds since epoch
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)

    filtered_logs = []

    try:
        paginator = client.get_paginator('filter_log_events')

        # Parameters for the log query
        query_params = {
            'logGroupName': params.log_group_name,  # Use the provided log group name
            'logStreamNames': ['aws/bedrock/modelinvocations'],  # The specific log stream
            'startTime': start_time_ms,
            'endTime': end_time_ms,
        }

        # Paginate through results
        for page in paginator.paginate(**query_params):
            for event in page.get('events', []):
                try:
                    # Parse the message as JSON
                    message = json.loads(event['message'])

                    # Get user prompt from the input messages
                    prompt = ''
                    if message.get('input', {}).get('inputBodyJson', {}).get('messages'):
                        for msg in message['input']['inputBodyJson']['messages']:
                            if msg.get('role') == 'user' and msg.get('content'):
                                for content in msg['content']:
                                    if content.get('text'):
                                        prompt += content['text'] + ' '
                        prompt = prompt.strip()

                    # Extract only the required fields
                    filtered_event = {
                        'timestamp': message.get('timestamp'),
                        'region': message.get('region'),
                        'modelId': message.get('modelId'),
                        'userId': message.get('identity', {}).get('arn'),
                        'inputTokens': message.get('input', {}).get('inputTokenCount'),
                        'completionTokens': message.get('output', {}).get('outputTokenCount'),
                        'totalTokens': (
                            message.get('input', {}).get('inputTokenCount', 0)
                            + message.get('output', {}).get('outputTokenCount', 0)
                        ),
                    }

                    filtered_logs.append(filtered_event)
                except json.JSONDecodeError:
                    continue  # Skip non-JSON messages
                except KeyError:
                    continue  # Skip messages missing required fields

        # Create DataFrame if we have logs
        if filtered_logs:
            df = pd.DataFrame(filtered_logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        else:
            print('No logs found for the specified time period.')
            return None

    except client.exceptions.ResourceNotFoundException:
        print(
            f"Log group '{params.log_group_name}' or stream 'aws/bedrock/modelinvocations' not found"
        )
        return None
    except Exception as e:
        print(f'Error retrieving logs: {str(e)}')
        return None
