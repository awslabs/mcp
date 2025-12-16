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

"""Timestamp conversion tools for AWS IoT SiteWise MCP Server."""

import datetime
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from mcp.server.fastmcp.tools import Tool
from typing import Any, Dict, Union


@tool_metadata(readonly=True)
def convert_unix_timestamp(
    timestamp: Union[int, str],
    format_string: str = '%B %d, %Y at %H:%M:%S UTC',
    timezone: str = 'UTC',
) -> Dict[str, Any]:
    """Convert Unix epoch timestamp to human-readable format.

    This tool provides accurate timestamp conversion to prevent AI agents from
    making conversion errors when interpreting Unix timestamps from API responses.

    Args:
        timestamp: Unix epoch timestamp (seconds since 1970-01-01)
        format_string: Python strftime format string for output formatting
        timezone: Timezone for conversion (currently only supports UTC)

    Returns:
        Dictionary containing conversion results and metadata

    Example:
        # Convert a single timestamp
        result = convert_unix_timestamp(1727740800)
        # Returns: {
        #   "success": True,
        #   "timestamp": 1727740800,
        #   "formatted": "October 01, 2024 at 00:00:00 UTC",
        #   "iso_format": "2024-10-01T00:00:00+00:00",
        #   "year": 2024,
        #   "month": 10,
        #   "day": 1
        # }
    """
    try:
        # Convert string to int if needed
        if isinstance(timestamp, str):
            timestamp_int = int(timestamp)
        else:
            timestamp_int = timestamp

        # Convert to datetime object in UTC
        dt = datetime.datetime.fromtimestamp(timestamp_int, tz=datetime.timezone.utc)

        # Format according to the specified format string
        formatted = dt.strftime(format_string)

        return {
            'success': True,
            'timestamp': timestamp_int,
            'formatted': formatted,
            'iso_format': dt.isoformat(),
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'second': dt.second,
            'weekday': dt.strftime('%A'),
            'timezone': 'UTC',
        }

    except (ValueError, OSError, OverflowError) as e:
        return {
            'success': False,
            'error': f'Invalid timestamp: {timestamp} ({str(e)})',
            'timestamp': timestamp,
        }


@tool_metadata(readonly=True)
def convert_multiple_timestamps(
    timestamps: Dict[str, Union[int, str]], format_string: str = '%B %d, %Y at %H:%M:%S UTC'
) -> Dict[str, Any]:
    """Convert multiple Unix epoch timestamps to human-readable format.

    This tool converts multiple timestamps at once, useful for processing
    API responses that contain several timestamp fields.

    Args:
        timestamps: Dictionary of timestamp names and values
        format_string: Python strftime format string for output formatting

    Returns:
        Dictionary containing conversion results for all timestamps

    Example:
        # Convert multiple timestamps
        result = convert_multiple_timestamps({
            "lastTrainedAt": "1761805552",
            "lastTrainedStartTime": "1759276800",
            "lastTrainedEndTime": "1760659200"
        })
    """
    try:
        results = {'success': True, 'conversions': {}, 'summary': {}}

        for name, timestamp in timestamps.items():
            conversion = convert_unix_timestamp(timestamp, format_string)
            results['conversions'][name] = conversion

            if conversion['success']:
                results['summary'][name] = {
                    'original': timestamp,
                    'formatted': conversion['formatted'],
                    'year': conversion['year'],
                }

        return results

    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing timestamps: {str(e)}',
            'timestamps': timestamps,
        }


@tool_metadata(readonly=True)
def create_timestamp_range(
    start_timestamp: Union[int, str],
    end_timestamp: Union[int, str],
    format_string: str = '%B %d, %Y',
) -> Dict[str, Any]:
    """Create a formatted timestamp range from start and end timestamps.

    This tool formats a range of timestamps for display, useful for showing
    training periods, evaluation periods, or other time ranges.

    Args:
        start_timestamp: Start Unix epoch timestamp
        end_timestamp: End Unix epoch timestamp
        format_string: Python strftime format string for output formatting

    Returns:
        Dictionary containing formatted range and individual conversions

    Example:
        # Create a training period range
        result = create_timestamp_range(1727740800, 1729123200)
        # Returns formatted range like "October 01, 2024 - October 17, 2024"
    """
    try:
        start_conversion = convert_unix_timestamp(start_timestamp, format_string)
        end_conversion = convert_unix_timestamp(end_timestamp, format_string)

        if not start_conversion['success'] or not end_conversion['success']:
            return {
                'success': False,
                'error': 'Failed to convert one or both timestamps',
                'start_conversion': start_conversion,
                'end_conversion': end_conversion,
            }

        # Calculate duration
        start_dt = datetime.datetime.fromtimestamp(
            int(start_timestamp) if isinstance(start_timestamp, str) else start_timestamp,
            tz=datetime.timezone.utc,
        )
        end_dt = datetime.datetime.fromtimestamp(
            int(end_timestamp) if isinstance(end_timestamp, str) else end_timestamp,
            tz=datetime.timezone.utc,
        )

        duration = end_dt - start_dt
        duration_days = duration.days

        return {
            'success': True,
            'range': f'{start_conversion["formatted"]} - {end_conversion["formatted"]}',
            'start': start_conversion,
            'end': end_conversion,
            'duration_days': duration_days,
            'duration_hours': duration.total_seconds() / 3600,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error creating timestamp range: {str(e)}',
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
        }


@tool_metadata(readonly=True)
def get_current_timestamp() -> Dict[str, Any]:
    """Get the current Unix timestamp and formatted time.

    This tool provides the current timestamp in both Unix epoch format
    and human-readable format, useful for reference when working with timestamps.

    Returns:
        Dictionary containing current timestamp information
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp = int(now.timestamp())

        return {
            'success': True,
            'current_timestamp': timestamp,
            'formatted': now.strftime('%B %d, %Y at %H:%M:%S UTC'),
            'iso_format': now.isoformat(),
            'year': now.year,
            'month': now.month,
            'day': now.day,
            'hour': now.hour,
            'minute': now.minute,
            'second': now.second,
            'timezone': 'UTC',
        }

    except Exception as e:
        return {'success': False, 'error': f'Error getting current timestamp: {str(e)}'}


# Create MCP tools
convert_unix_timestamp_tool = Tool.from_function(
    fn=convert_unix_timestamp,
    name='convert_unix_timestamp',
    description=(
        'Convert Unix epoch timestamp to human-readable format. '
        'Provides accurate timestamp conversion to prevent AI agents from '
        'making conversion errors when interpreting Unix timestamps.'
    ),
)

convert_multiple_timestamps_tool = Tool.from_function(
    fn=convert_multiple_timestamps,
    name='convert_multiple_timestamps',
    description=(
        'Convert multiple Unix epoch timestamps to human-readable format. '
        'Useful for processing API responses that contain several timestamp fields.'
    ),
)

create_timestamp_range_tool = Tool.from_function(
    fn=create_timestamp_range,
    name='create_timestamp_range',
    description=(
        'Create a formatted timestamp range from start and end timestamps. '
        'Useful for showing training periods, evaluation periods, or other time ranges.'
    ),
)

get_current_timestamp_tool = Tool.from_function(
    fn=get_current_timestamp,
    name='get_current_timestamp',
    description=(
        'Get the current Unix timestamp and formatted time. '
        'Useful for reference when working with timestamps.'
    ),
)
