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

"""Change tracking tools for AWS Application Signals MCP Server."""

import json
from .aws_clients import applicationsignals_client
from .utils import parse_timestamp
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone
from typing import Dict, Optional


async def list_change_events(
    start_time: str,
    end_time: str,
    service_key_attributes: Optional[Dict[str, str]] = None,
    max_results: int = 100,
    region: Optional[str] = None,
    comprehensive_history: bool = True,
) -> str:
    """Retrieve change events for AWS resources within specified time range.

    Args:
        start_time: Start time for change event query (ISO 8601 or Unix timestamp)
        end_time: End time for change event query (ISO 8601 or Unix timestamp)
        service_key_attributes: Service attributes to filter events. REQUIRED for comprehensive_history=True (ListEntityEvents). Optional for comprehensive_history=False (ListServiceStates). Use get_service_detail() to retrieve these attributes.
        max_results: Maximum number of events to return (1-250, default: 100)
        region: AWS region (optional, defaults to configured region)
        comprehensive_history: If True, retrieves complete change history using ListEntityEvents (requires service_key_attributes).
                             If False, retrieves only latest service states using ListServiceStates (service_key_attributes optional).

    Returns:
        JSON string containing change events with timeline analysis
    """
    try:
        # Validate time parameters
        start_dt = parse_timestamp(start_time)
        end_dt = parse_timestamp(end_time)

        if start_dt >= end_dt:
            return json.dumps(
                {
                    'error': 'start_time must be before end_time',
                    'start_time': start_dt.isoformat(),
                    'end_time': end_dt.isoformat(),
                }
            )

        # Validate service_key_attributes requirement for ListEntityEvents
        if comprehensive_history and not service_key_attributes:
            return json.dumps(
                {
                    'error': 'service_key_attributes is required when comprehensive_history=True (ListEntityEvents API). Use get_service_detail() to retrieve service key attributes first.',
                    'suggestion': 'Either provide service_key_attributes or set comprehensive_history=False to use ListServiceStates API',
                    'start_time': start_time,
                    'end_time': end_time,
                }
            )

        # Validate max_results (AWS API limit is 250)
        if not (1 <= max_results <= 250):
            max_results = min(max(max_results, 1), 250)

        # Convert to Unix timestamps for AWS API
        start_timestamp = float(start_dt.timestamp())
        end_timestamp = float(end_dt.timestamp())

        # Use appropriate API based on comprehensive_history flag
        if comprehensive_history:
            return await _list_entity_events(
                applicationsignals_client,
                start_timestamp,
                end_timestamp,
                service_key_attributes,
                max_results,
            )
        else:
            return await _list_service_states(
                applicationsignals_client,
                start_timestamp,
                end_timestamp,
                service_key_attributes,
                max_results,
            )

    except NoCredentialsError:
        return json.dumps(
            {
                'error': 'AWS credentials not found. Please configure your AWS credentials.',
                'start_time': start_time,
                'end_time': end_time,
                'service_key_attributes': service_key_attributes,
            }
        )

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'ValidationException':
            return json.dumps(
                {
                    'error': f'Invalid request parameters: {error_message}',
                    'error_code': error_code,
                    'start_time': start_time,
                    'end_time': end_time,
                    'service_key_attributes': service_key_attributes,
                }
            )
        elif error_code == 'ThrottlingException':
            return json.dumps(
                {
                    'error': 'Request was throttled. Please try again later.',
                    'error_code': error_code,
                    'start_time': start_time,
                    'end_time': end_time,
                    'service_key_attributes': service_key_attributes,
                }
            )
        else:
            return json.dumps(
                {
                    'error': f'AWS API error: {error_message}',
                    'error_code': error_code,
                    'start_time': start_time,
                    'end_time': end_time,
                    'service_key_attributes': service_key_attributes,
                }
            )

    except Exception as e:
        return json.dumps(
            {
                'error': f'Failed to retrieve change events: {str(e)}',
                'start_time': start_time,
                'end_time': end_time,
                'service_key_attributes': service_key_attributes,
            }
        )


async def _list_entity_events(
    client,
    start_timestamp: float,
    end_timestamp: float,
    service_key_attributes: Optional[Dict[str, str]],
    max_results: int,
) -> str:
    """Use ListEntityEvents API for comprehensive change history."""
    # Build entity filter
    entity = {}
    if service_key_attributes:
        for key in ['Type', 'Name', 'Environment', 'ResourceType', 'Identifier', 'AwsAccountId']:
            if key in service_key_attributes:
                entity[key] = service_key_attributes[key]

    if not entity:
        entity = {'Type': 'Service'}

    # Call API with pagination
    all_events = []
    next_token = None

    while True:
        params = {
            'StartTime': start_timestamp,
            'EndTime': end_timestamp,
            'Entity': entity,
            'MaxResults': max_results,
        }
        if next_token:
            params['NextToken'] = next_token

        response = client.list_entity_events(**params)
        events = response.get('ChangeEvents', [])
        all_events.extend(events)

        next_token = response.get('NextToken')
        if not next_token or len(all_events) >= max_results:
            break

    # Process events
    processed_events = []
    events_by_type = {}

    for event in all_events[:max_results]:
        # Handle both datetime objects and numeric timestamps from AWS API
        timestamp_value = event.get('Timestamp', 0)
        if hasattr(timestamp_value, 'timestamp'):
            # It's a datetime object, convert to UTC string
            event_dt = timestamp_value.astimezone(timezone.utc)
            timestamp = event_dt.isoformat()
        else:
            # It's a numeric value, convert to datetime then UTC string
            event_dt = datetime.fromtimestamp(float(timestamp_value), tz=timezone.utc)
            timestamp = event_dt.isoformat()

        # Calculate seconds since event occurred
        current_time = datetime.now(timezone.utc)
        seconds_since_event = int((current_time - event_dt).total_seconds())

        processed_event = {
            'event_id': event.get('EventId', ''),
            'event_name': event.get('EventName', ''),
            'change_event_type': event.get('ChangeEventType', ''),
            'timestamp': timestamp,
            'seconds_since_event': seconds_since_event,
            'account_id': event.get('AccountId', ''),
            'region': event.get('Region', ''),
            'user_name': event.get('UserName', ''),
        }
        processed_events.append(processed_event)

        event_type = processed_event['change_event_type']
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

    processed_events.sort(key=lambda x: x['timestamp'])

    return json.dumps(
        {
            'change_events': processed_events,
            'next_token': response.get('NextToken'),
            'total_events': len(processed_events),
            'events_by_type': events_by_type,
        },
        indent=2,
    )


async def _list_service_states(
    client,
    start_timestamp: float,
    end_timestamp: float,
    service_key_attributes: Optional[Dict[str, str]],
    max_results: int,
) -> str:
    """Use ListServiceStates API for latest service states."""
    # Build attribute filters
    attribute_filters = []
    if service_key_attributes:
        for key, value in service_key_attributes.items():
            if key in ['Name', 'Environment', 'Type']:
                attribute_filters.append(
                    {'AttributeFilterName': key, 'AttributeFilterValues': [value]}
                )

    # Call API with pagination
    all_states = []
    next_token = None

    while True:
        params = {
            'StartTime': start_timestamp,
            'EndTime': end_timestamp,
            'MaxResults': min(max_results, 250),
        }
        if attribute_filters:
            params['AttributeFilters'] = attribute_filters
        if next_token:
            params['NextToken'] = next_token

        response = client.list_service_states(**params)
        states = response.get('ServiceStates', [])
        all_states.extend(states)

        next_token = response.get('NextToken')
        if not next_token or len(all_states) >= max_results:
            break

    # Extract change events from service states
    processed_events = []
    events_by_type = {}

    for state in all_states[:max_results]:
        # Process LatestChangeEvents from each service state
        latest_change_events = state.get('LatestChangeEvents', [])

        for event in latest_change_events:
            # Handle both datetime objects and numeric timestamps from AWS API
            timestamp_value = event.get('Timestamp', start_timestamp)
            if hasattr(timestamp_value, 'timestamp'):
                # It's a datetime object, convert to UTC string
                event_dt = timestamp_value.astimezone(timezone.utc)
                timestamp = event_dt.isoformat()
            else:
                # It's a numeric value, convert to datetime then UTC string
                event_dt = datetime.fromtimestamp(float(timestamp_value), tz=timezone.utc)
                timestamp = event_dt.isoformat()

            # Calculate seconds since event occurred
            current_time = datetime.now(timezone.utc)
            seconds_since_event = int((current_time - event_dt).total_seconds())

            processed_event = {
                'event_id': event.get('EventId'),
                'event_name': event.get('EventName'),
                'change_event_type': event.get('ChangeEventType'),
                'timestamp': timestamp,
                'seconds_since_event': seconds_since_event,
                'account_id': event.get('AccountId', ''),
                'region': event.get('Region', ''),
                'user_name': event.get('UserName'),
                'entity': event.get('Entity'),
            }
            processed_events.append(processed_event)

            event_type = processed_event['change_event_type']
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

    processed_events.sort(key=lambda x: x['timestamp'])

    return json.dumps(
        {
            'change_events': processed_events,
            'next_token': response.get('NextToken'),
            'total_events': len(processed_events),
            'events_by_type': events_by_type,
        },
        indent=2,
    )
