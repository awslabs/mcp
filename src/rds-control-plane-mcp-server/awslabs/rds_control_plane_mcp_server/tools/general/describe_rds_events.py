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

"""describe_rds_events helpers, data models and tool implementation."""

from ...common.connection import RDSConnectionManager
from ...common.context import RDSContext
from ...common.decorators.handle_exceptions import handle_exceptions
from ...common.server import mcp
from datetime import datetime
from mcp.types import ToolAnnotations
from mypy_boto3_rds.type_defs import EventTypeDef
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


SOURCE_TYPE_TO_EVENT_CATEGORIES = {
    'db-instance': [
        'availability',
        'backup',
        'configuration change',
        'creation',
        'deletion',
        'failover',
        'failure',
        'low storage',
        'maintenance',
        'notification',
        'read replica',
        'recovery',
        'restoration',
        'security',
        'security patching',
    ],
    'db-cluster': [
        'configuration change',
        'creation',
        'failover',
        'failure',
        'maintenance',
        'notification',
        'read replica',
    ],
    'db-cluster-snapshot': ['backup', 'notification'],
    'db-parameter-group': ['configuration change'],
    'db-security-group': ['configuration change', 'failure'],
    'db-snapshot': ['creation', 'deletion', 'notification', 'restoration'],
    'db-proxy': ['configuration change', 'creation', 'deletion', 'failure'],
    'blue-green-deployment': ['creation', 'failure', 'deletion', 'notification'],
    'custom-engine-version': ['creation', 'failure', 'restoring'],
}


class Event(BaseModel):
    """A model representing a database event."""

    message: str = Field(..., description='Text of this event')
    event_categories: List[str] = Field(..., description='Categories for the event')
    date: str = Field(..., description='Date and time of the event')
    source_arn: Optional[str] = Field(
        None, description='The Amazon Resource Name (ARN) for the event'
    )

    @classmethod
    def from_event_data(cls, event: EventTypeDef) -> 'Event':
        """Create Event from AWS API event data.

        Args:
            event (EventTypeDef): The AWS RDS event data dictionary containing event details

        Returns:
            Event: A new Event instance populated with the AWS event data
        """
        date_value = event.get('Date')
        if date_value is None:
            formatted_date = ''
        elif isinstance(date_value, datetime):
            formatted_date = date_value.isoformat()
        else:
            formatted_date = str(date_value)

        return cls(
            message=event.get('Message', ''),
            event_categories=event.get('EventCategories', []),
            date=formatted_date,
            source_arn=event.get('SourceArn'),
        )


class EventList(BaseModel):
    """A model representing the response of the describe_rds_events function."""

    source_identifier: str = Field(..., description='Identifier for the source of the event')
    source_type: str = Field(..., description='The type of source')
    events: List[Event] = Field(..., description='List of RDS events')
    count: int = Field(..., description='Total number of events')


DESCRIBE_EVENTS_TOOL_DESCRIPTION = """List events for an RDS resource.

This tool retrieves events for RDS resources such as DB instances, clusters, security groups, etc. Events include operational activities, status changes, and notifications that can be filtered by source identifier, category, time period, and source type.
"""


@mcp.tool(
    name='DescribeRDSEvents',
    description=DESCRIBE_EVENTS_TOOL_DESCRIPTION,
    annotations=ToolAnnotations(
        title='DescribeRDSEvents',
        readOnlyHint=True,
    ),
)
@handle_exceptions
def describe_rds_events(
    source_identifier: str = Field(
        ...,
        description='The identifier of the event source (e.g., DBInstanceIdentifier or DBClusterIdentifier). A valid identifier must be provided.',
    ),
    source_type: Literal[
        'db-instance',
        'db-parameter-group',
        'db-security-group',
        'db-snapshot',
        'db-cluster',
        'db-cluster-snapshot',
        'custom-engine-version',
        'db-proxy',
        'blue-green-deployment',
    ] = Field(..., description='The type of source'),
    event_categories: Optional[List[str]] = Field(
        None,
        description='The categories of events (e.g., backup, configuration change, low storage, etc.)',
    ),
    duration: Optional[int] = Field(
        None,
        description='The number of minutes in the past to retrieve events (up to 14 days/20160 minutes)',
    ),
    start_time: Optional[str] = Field(
        None, description='The beginning of the time interval to retrieve events (ISO8601 format)'
    ),
    end_time: Optional[str] = Field(
        None, description='The end of the time interval to retrieve events (ISO8601 format)'
    ),
) -> EventList:
    """List events for an RDS resource.

    Args:
        source_identifier: The identifier of the event source (e.g., DB instance or DB cluster)
        source_type: The type of source (db-instance, db-cluster, etc.)
        event_categories: List of categories of events (e.g., backup, configuration change, etc.)
        duration: The number of minutes in the past to retrieve events (up to 14 days/20160 minutes)
        start_time: The beginning of the time interval to retrieve events
        end_time: The end of the time interval to retrieve events

    Returns:
        EventList: List of events for the specified resource
    """
    params = {
        'SourceIdentifier': source_identifier,
        'SourceType': source_type,
        'MaxRecords': RDSContext.max_items(),
    }

    if event_categories:
        valid_categories = SOURCE_TYPE_TO_EVENT_CATEGORIES.get(source_type, [])
        invalid_categories = [cat for cat in event_categories if cat not in valid_categories]
        if invalid_categories:
            raise ValueError(
                f'Invalid event categories for {source_type}: {invalid_categories}. Valid categories: {valid_categories}'
            )
        params['EventCategories'] = event_categories
    if duration:
        params['Duration'] = duration
    if start_time:
        params['StartTime'] = start_time
    if end_time:
        params['EndTime'] = end_time

    rds_client = RDSConnectionManager.get_connection()
    response = rds_client.describe_events(**params)
    raw_events = response.get('Events', [])
    processed_events = [Event.from_event_data(event) for event in raw_events]

    return EventList(
        events=processed_events,
        count=len(processed_events),
        source_identifier=source_identifier,
        source_type=source_type,
    )
