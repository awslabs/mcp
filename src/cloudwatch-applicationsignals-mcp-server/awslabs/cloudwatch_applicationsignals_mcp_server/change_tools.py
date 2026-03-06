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
from .aws_clients import AWS_REGION, applicationsignals_client
from .utils import parse_timestamp
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone
from pydantic import Field
from typing import Dict, List, Optional


def _filter_service_states_by_attributes(
    service_states: List[Dict], service_key_attributes: Dict[str, str]
) -> List[Dict]:
    """Filter service states based on service key attributes.

    Args:
        service_states: List of service state dictionaries from AWS API
        service_key_attributes: Dictionary of service attributes to match against

    Returns:
        List of filtered service states that match the provided attributes
    """
    filtered_states = []

    for state in service_states:
        service = state.get('Service', {})

        # Check if all provided service_key_attributes match the service attributes
        if all(
            service.get(key) == expected_value
            for key, expected_value in service_key_attributes.items()
        ):
            filtered_states.append(state)

    return filtered_states


def _process_change_events(events: List[Dict]) -> tuple[List[Dict], Dict[str, int]]:
    """Process change events into a standardized format.

    Args:
        events: List of change event dictionaries from AWS API

    Returns:
        Tuple of (processed_events, events_by_type_count)
    """
    processed_events = []
    events_by_type = {}
    current_time = datetime.now(timezone.utc)

    for event in events:
        # AWS API returns datetime objects via boto3, but handle numeric timestamps too
        timestamp_value = event.get('Timestamp')
        if isinstance(timestamp_value, (int, float)):
            # Convert numeric timestamp to datetime
            event_dt = datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
        elif timestamp_value is not None:
            # Assume it's already a datetime object
            event_dt = timestamp_value.astimezone(timezone.utc)
        else:
            # Skip events without timestamps
            continue
        timestamp = event_dt.isoformat()

        # Calculate seconds since event occurred
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

    # Sort events by timestamp
    processed_events.sort(key=lambda x: x['timestamp'])

    return processed_events, events_by_type


async def _list_change_events(
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
    # Define valid and required attributes
    valid_attrs = ['Type', 'Name', 'Environment', 'AwsAccountId']
    required_attrs = ['Type', 'Name', 'Environment']

    entity = {}
    if service_key_attributes:
        for key in valid_attrs:
            if key in service_key_attributes:
                entity[key] = service_key_attributes[key]

    # Validate that we have the minimum required attributes
    missing_attrs = [attr for attr in required_attrs if attr not in entity]

    if missing_attrs:
        raise ValueError(
            f'Missing required service_key_attributes: {", ".join(missing_attrs)}. '
            f'Use get_service_detail() to retrieve the correct service key attributes.'
        )

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

    # Process events using shared function
    processed_events, events_by_type = _process_change_events(all_events[:max_results])

    return json.dumps(
        {
            'change_events': processed_events,
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
    # Call API with pagination
    all_states = []
    next_token = None

    while True:
        params = {
            'StartTime': start_timestamp,
            'EndTime': end_timestamp,
            'MaxResults': min(max_results, 250),
        }
        if next_token:
            params['NextToken'] = next_token

        response = client.list_service_states(**params)
        states = response.get('ServiceStates', [])

        # Filter states as we fetch them if service_key_attributes provided
        if service_key_attributes:
            filtered_batch = _filter_service_states_by_attributes(states, service_key_attributes)
            all_states.extend(filtered_batch)
        else:
            all_states.extend(states)

        next_token = response.get('NextToken')
        if not next_token or len(all_states) >= max_results:
            break

    # Extract change events from filtered service states
    all_change_events = []
    for state in all_states:
        # Process LatestChangeEvents from each service state
        latest_change_events = state.get('LatestChangeEvents', [])
        all_change_events.extend(latest_change_events)

    # Process events using shared function
    processed_events, events_by_type = _process_change_events(all_change_events)

    return json.dumps(
        {
            'change_events': processed_events,
            'total_events': len(processed_events),
            'events_by_type': events_by_type,
        },
        indent=2,
    )


async def list_change_events(
    start_time: str = Field(
        description='Start time for change event query (ISO 8601 datetime string or Unix timestamp)'
    ),
    end_time: str = Field(
        description='End time for change event query (ISO 8601 datetime string or Unix timestamp)'
    ),
    service_key_attributes: Optional[Dict[str, str]] = Field(
        default=None,
        description='Service key attributes to filter events. REQUIRED when comprehensive_history=True (ListEntityEvents API). Optional when comprehensive_history=False (ListServiceStates API). Use get_service_detail() to retrieve these attributes first. Dictionary with supported keys: "Type", "Name", "Environment", "AwsAccountId". Example: {"Environment": "ecs:ecs-pet-clinic-demo", "Name": "pet-clinic-vets-service", "Type": "Service"}',
    ),
    max_results: int = Field(
        default=100, description='Maximum number of events to return (1-250, default: 100)'
    ),
    region: str = Field(
        default=AWS_REGION, description='AWS region to query (defaults to configured region)'
    ),
    comprehensive_history: bool = Field(
        default=True,
        description='If True, uses ListEntityEvents API for complete change history (REQUIRES service_key_attributes). If False, uses ListServiceStates API for current service state information (service_key_attributes optional).',
    ),
) -> str:
    """Query AWS Application Signals change events to correlate infrastructure and application changes with service performance issues.

    This tool provides access to AWS Application Signals' change detection capabilities through two complementary APIs:
    - **ListEntityEvents**: Comprehensive change history for incident investigation and root cause analysis
    - **ListServiceStates**: Current service state information for status monitoring

    **Key Capabilities:**
    - **Change Correlation**: Link deployments, configuration changes, and infrastructure modifications to performance issues
    - **Timeline Analysis**: Build accurate timelines of events leading to incidents, alarms, or SLO breaches
    - **Service-Specific Filtering**: Focus on changes to specific services using Application Signals service attributes
    - **Multi-Change Type Tracking**: Monitor deployment events, configuration updates, infrastructure scaling, and other modifications
    - **Incident Investigation**: Essential for root cause analysis when services experience performance degradation

    **API Selection Guide:**
    - **comprehensive_history=True (default)**: Uses ListEntityEvents API
      - **Question it answers**: "What are the changes in my service?" - Comprehensive change history
      - **Best for**: Incident investigation, change correlation, root cause analysis, timeline reconstruction
      - **Returns**: Complete chronological list of all change events (deployments, configurations, scaling) within time range
      - **Use when**: You need to see all changes that happened and correlate them with performance issues

    - **comprehensive_history=False**: Uses ListServiceStates API
      - **Question it answers**: "Has anything changed in my service?" - Current change status
      - **Best for**: Service status monitoring, checking if recent changes occurred, troubleshooting current state
      - **Returns**: Information about the last deployment and other change states of services, providing visibility into recent changes that may have affected service performance
      - **Use when**: You want to quickly check if there were recent changes without needing the full history

    **Common Use Cases:**
    1. **Alarm-Triggered Investigation**: "My checkout-service alarm is firing. What changed recently?"
    2. **Canary Failure Analysis**: "My checkout-canary is failing. Show me recent changes that might be related."
    3. **Log-Based Error Investigation**: "I'm seeing errors in payment-service logs. What deployments happened before these errors?"
    4. **Service Change History**: "Show me all changes to user-authentication-service in the last 24 hours."
    5. **SLO Breach Timeline**: "I had an SLO breach at 3 PM. What changes led up to it?"
    6. **Deployment Impact Analysis**: "Did the 2 PM deployment cause the performance degradation?"

    **Service Key Attributes (Required for ListEntityEvents):**
    When using comprehensive_history=True (ListEntityEvents API), service_key_attributes is REQUIRED. Get these attributes from get_service_detail() first:
    - **Type**: Usually "Service" for Application Signals monitored services
    - **Name**: Service name (e.g., "checkout-service", "payment-api", "hello-world-python")
    - **Environment**: Service environment (e.g., "ecs:production-cluster", "lambda:default", "eks:my-cluster")
    - **AwsAccountId**: AWS account ID for cross-account filtering (optional)

    Example service key attributes:
    ```json
    {
        "Type": "Service",
        "Name": "hello-world-python",
        "Environment": "lambda:default"
    }
    ```

    When using comprehensive_history=False (ListServiceStates API), service_key_attributes is optional.

    **Integration with Other Tools:**
    - **Enhances audit_services()**: Provides change context for service health issues
    - **Correlates with audit_slos()**: Links changes to SLO breach analysis
    - **Supports audit_service_operations()**: Adds timeline context for operation performance investigations
    - **Complements analyze_canary_failures()**: Provides deployment correlation for canary issues

    **Response Format:**
    Returns JSON with comprehensive change event data including:
    - **change_events**: Array of change events with timestamps, event types, and entity information
    - **events_by_type**: Summary of change types (DEPLOYMENT, CONFIGURATION, etc.)
    - **affected_services**: List of services with change counts and latest change timestamps
    - **api_used**: Which AWS API was used (ListEntityEvents or ListServiceStates)

    Args:
        start_time: Start time for change event query (ISO 8601 datetime string or Unix timestamp)
        end_time: End time for change event query (ISO 8601 datetime string or Unix timestamp)
        service_key_attributes: Service attributes dictionary to filter events to specific services. REQUIRED when comprehensive_history=True (ListEntityEvents). Optional when comprehensive_history=False (ListServiceStates). Use get_service_detail() to retrieve these attributes.
        max_results: Maximum number of events to return (1-250, default: 100)
        region: AWS region to query (defaults to configured region)
        comprehensive_history: If True, uses ListEntityEvents for complete change history. If False, uses ListServiceStates for current service states.

    Returns:
        JSON string containing change events with timeline analysis and correlation insights for incident investigation
    """
    return await _list_change_events(
        start_time=start_time,
        end_time=end_time,
        service_key_attributes=service_key_attributes,
        max_results=max_results,
        region=region,
        comprehensive_history=comprehensive_history,
    )
