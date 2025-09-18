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

"""AWS IoT SiteWise Data Ingestion and Retrieval Tools."""

from ..validation import (
    ValidationError,
    validate_asset_id,
    validate_max_results,
    validate_property_alias,
    validate_region,
)
from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client
from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.server.fastmcp.tools import Tool
from pydantic import Field
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional


@tool_metadata(readonly=False)
def batch_put_asset_property_value(
    entries: List[Dict[str, Any]] = Field(
        ..., description='List of asset property value entries to send to AWS IoT SiteWise'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Send a list of asset property values to AWS IoT SiteWise.

    Args:
            entries: The list of asset property value entries to send to AWS IoT SiteWise
            region: AWS region (default: us-east-1)

    Returns:
            Dictionary containing batch put response
    """
    try:
        client = create_sitewise_client(region)

        response = client.batch_put_asset_property_value(entries=entries)

        return {'success': True, 'error_entries': response.get('errorEntries', [])}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_value(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the current value for the given asset property.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing current property value
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {}
        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias

        response = client.get_asset_property_value(**params)

        property_value = response['propertyValue']
        return {
            'success': True,
            'value': property_value['value'],
            'timestamp': property_value['timestamp'],
            'quality': property_value.get('quality', 'GOOD'),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_value_history(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    start_date: Optional[str] = Field(
        None, description='The exclusive start of the range (ISO 8601 format)'
    ),
    end_date: Optional[str] = Field(
        None, description='The inclusive end of the range (ISO 8601 format)'
    ),
    qualities: Optional[List[str]] = Field(
        None, description='The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)'
    ),
    time_ordering: str = Field(
        'ASCENDING', description='The chronological sorting order (ASCENDING, DESCENDING)'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the history of an asset property's values.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        start_date: The exclusive start of the range (ISO 8601 format)
        end_date: The inclusive end of the range (ISO 8601 format)
        qualities: The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)
        time_ordering: The chronological sorting order of the requested information \
            (ASCENDING, DESCENDING)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing property value history
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=4000)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'timeOrdering': time_ordering,
            'maxResults': max_results,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if start_date:
            params['startDate'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            params['endDate'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if qualities:
            params['qualities'] = qualities
        if next_token:
            params['nextToken'] = next_token

        response = client.get_asset_property_value_history(**params)

        return {
            'success': True,
            'asset_property_value_history': response['assetPropertyValueHistory'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_asset_property_aggregates(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    aggregate_types: Optional[List[str]] = Field(
        None,
        description='The data aggregating function (AVERAGE, COUNT, MAXIMUM, MINIMUM, SUM, STANDARD_DEVIATION)',
    ),
    resolution: str = Field('1h', description='The time interval over which to aggregate data'),
    start_date: Optional[str] = Field(
        None, description='The exclusive start of the range (ISO 8601 format)'
    ),
    end_date: Optional[str] = Field(
        None, description='The inclusive end of the range (ISO 8601 format)'
    ),
    qualities: Optional[List[str]] = Field(
        None, description='The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)'
    ),
    time_ordering: str = Field(
        'ASCENDING', description='The chronological sorting order (ASCENDING, DESCENDING)'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get aggregated values for an asset property.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        aggregate_types: The data aggregating function (AVERAGE, COUNT, MAXIMUM, \
            MINIMUM, SUM, STANDARD_DEVIATION)
        resolution: The time interval over which to aggregate data
        start_date: The exclusive start of the range (ISO 8601 format)
        end_date: The inclusive end of the range (ISO 8601 format)
        qualities: The quality by which to filter asset data (GOOD, BAD, UNCERTAIN)
        time_ordering: The chronological sorting order of the requested information \
            (ASCENDING, DESCENDING)
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing property aggregates
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=4000)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        if not aggregate_types:
            aggregate_types = ['AVERAGE']

        params: Dict[str, Any] = {
            'aggregateTypes': aggregate_types,
            'resolution': resolution,
            'timeOrdering': time_ordering,
            'maxResults': max_results,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if start_date:
            params['startDate'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            params['endDate'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if qualities:
            params['qualities'] = qualities
        if next_token:
            params['nextToken'] = next_token

        response = client.get_asset_property_aggregates(**params)

        return {
            'success': True,
            'aggregated_values': response['aggregatedValues'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def get_interpolated_asset_property_values(
    asset_id: Optional[str] = Field(None, description='The ID of the asset'),
    property_id: Optional[str] = Field(None, description='The ID of the asset property'),
    property_alias: Optional[str] = Field(
        None, description='The alias that identifies the property'
    ),
    start_time_in_seconds: Optional[int] = Field(
        None, description='The exclusive start of the range (Unix epoch time in seconds)'
    ),
    end_time_in_seconds: Optional[int] = Field(
        None, description='The inclusive end of the range (Unix epoch time in seconds)'
    ),
    quality: str = Field(
        'GOOD', description='The quality of the asset property value (GOOD, BAD, UNCERTAIN)'
    ),
    interval_in_seconds: int = Field(
        3600, description='The time interval in seconds over which to interpolate data'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-250)'),
    interpolation_type: str = Field(
        'LINEAR_INTERPOLATION',
        description='The interpolation type (LINEAR_INTERPOLATION, LOCF_INTERPOLATION)',
    ),
    interval_window_in_seconds: Optional[int] = Field(
        None, description='The query interval for interpolated values'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get interpolated values for an asset property for a specified time interval.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the asset property
        property_alias: The alias that identifies the property
        start_time_in_seconds: The exclusive start of the range (Unix epoch \
            time in seconds)
        end_time_in_seconds: The inclusive end of the range (Unix epoch time \
            in seconds)
        quality: The quality of the asset property value (GOOD, BAD, UNCERTAIN)
        interval_in_seconds: The time interval in seconds over which to \
            interpolate data
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        interpolation_type: The interpolation type (LINEAR_INTERPOLATION, \
            LOCF_INTERPOLATION)
        interval_window_in_seconds: The query interval for the window
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing interpolated property values
    """
    try:
        # Validate parameters
        if not isinstance(region, FieldInfo):
            validate_region(region)
        if not isinstance(max_results, FieldInfo):
            validate_max_results(max_results, min_val=1, max_val=250)
        if asset_id and not isinstance(asset_id, FieldInfo):
            validate_asset_id(asset_id)
        if property_alias and not isinstance(property_alias, FieldInfo):
            validate_property_alias(property_alias)

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'startTimeInSeconds': start_time_in_seconds,
            'endTimeInSeconds': end_time_in_seconds,
            'quality': quality,
            'intervalInSeconds': interval_in_seconds,
            'maxResults': max_results,
            'type': interpolation_type,
        }

        if asset_id:
            params['assetId'] = asset_id
        if property_id:
            params['propertyId'] = property_id
        if property_alias:
            params['propertyAlias'] = property_alias
        if next_token:
            params['nextToken'] = next_token
        if interval_window_in_seconds:
            params['intervalWindowInSeconds'] = interval_window_in_seconds

        response = client.get_interpolated_asset_property_values(**params)

        return {
            'success': True,
            'interpolated_asset_property_values': response['interpolatedAssetPropertyValues'],
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_value(
    entries: List[Dict[str, Any]] = Field(
        ..., description='The list of asset property identifiers for the batch get request'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the current values for multiple asset properties.

    Args:
        entries: The list of asset property identifiers for the batch get request
        next_token: The token to be used for the next set of paginated results
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_value(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_value_history(
    entries: List[Dict[str, Any]] = Field(
        ...,
        description='The list of asset property historical value entries for the batch get request',
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get the historical values for multiple asset properties.

    Args:
        entries: The list of asset property historical value entries for the \
            batch get request
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get history response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries, 'maxResults': max_results}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_value_history(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def batch_get_asset_property_aggregates(
    entries: List[Dict[str, Any]] = Field(
        ..., description='The list of asset property aggregate entries for the batch get request'
    ),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-4000)'),
    region: str = Field('us-east-1', description='AWS region'),
) -> Dict[str, Any]:
    """Get aggregated values for multiple asset properties.

    Args:
        entries: The list of asset property aggregate entries for the batch get request
        next_token: The token to be used for the next set of paginated results
        max_results: The maximum number of results to return (1-4000, default: 100)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing batch get aggregates response
    """
    try:
        client = create_sitewise_client(region)

        params: Dict[str, Any] = {'entries': entries, 'maxResults': max_results}
        if next_token:
            params['nextToken'] = next_token

        response = client.batch_get_asset_property_aggregates(**params)

        return {
            'success': True,
            'success_entries': response.get('successEntries', []),
            'skipped_entries': response.get('skippedEntries', []),
            'error_entries': response.get('errorEntries', []),
            'next_token': response.get('nextToken', ''),
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


@tool_metadata(readonly=True)
def execute_query(
    query_statement: str = Field(
        ..., description='SQL query statement to execute against AWS IoT SiteWise data'
    ),
    region: str = Field('us-east-1', description='AWS region'),
    next_token: Optional[str] = Field(
        None, description='The token to be used for the next set of paginated results'
    ),
    max_results: int = Field(100, description='The maximum number of results to return (1-10000)'),
) -> Dict[str, Any]:
    """Execute comprehensive SQL queries against AWS IoT SiteWise data using the executeQuery API.

    The AWS IoT SiteWise query language supports SQL capabilities including:
    - Views: asset, asset_property, raw_time_series, \
        latest_value_time_series, precomputed_aggregates
    - SQL clauses: SELECT, FROM, WHERE, GROUP BY, ORDER BY, HAVING, LIMIT
    - Functions: Aggregation, date/time, string, mathematical, conditional
    - Operators: Comparison, logical, arithmetic, pattern matching (LIKE)
    - JOIN operations: JOIN, LEFT JOIN,
        UNION (prefer implicit joins for performance)

    Available Views and Schema (From Official AWS Documentation):

    ASSET VIEW: Contains information about the asset and model derivation
    - asset_id (string), asset_name (string), asset_description (string)
    - asset_model_id (string), parent_asset_id (string),
        asset_external_id (string)
    - asset_external_model_id (string), hierarchy_id (string)

    ASSET_PROPERTY VIEW: Contains information about the asset property's structure
    - asset_id (string), property_id (string), property_name (string),
        property_alias (string)
    - property_external_id (string), asset_composite_model_id (string),
        property_type (string)
    - property_data_type (string), int_attribute_value (integer),
        double_attribute_value (double)
    - boolean_attribute_value (boolean), string_attribute_value (string)

    RAW_TIME_SERIES VIEW: Contains the historical data of the time series
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), boolean_value (boolean), int_value (integer),
        double_value (double), string_value (string)

    LATEST_VALUE_TIME_SERIES VIEW: Contains the latest value of the time series
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), boolean_value (boolean), int_value (integer),
        double_value (double), string_value (string)

    PRECOMPUTED_AGGREGATES VIEW: Contains automatically computed \
        aggregated asset property values
    - asset_id (string), property_id (string), property_alias (string),
        event_timestamp (timestamp)
    - quality (string), resolution (string), sum_value (double),
        count_value (integer)
    - average_value (double), maximum_value (double),
        minimum_value (double), stdev_value (double)

    Complete SQL Function Reference (From AWS IoT SiteWise User Guide):

    DATE/TIME FUNCTIONS:
    - DATE_ADD(
        unit,
        value,
        date): Add time to date (e.g.,
        DATE_ADD(DAY, 7, event_timestamp))    - DATE_SUB(
        unit,
        value,
        date): Subtract time from date (e.g.,
        DATE_SUB(
            YEAR,
            2,
            event_timestamp))    - TIMESTAMP_ADD(
                unit,
                value,
                timestamp): Add time to timestamp
    - TIMESTAMP_SUB(unit, value, timestamp): Subtract time from timestamp
    - NOW(
        ): Current timestamp (supported,
        but use TIMESTAMP_ADD/SUB for math operations)    - \
            TIMESTAMP literals: Use TIMESTAMP '2023-01-01 00:00:00' for specific dates
    - CAST(expression AS TIMESTAMP): Convert string to timestamp

    Note: NOW() IS supported. When doing math on NOW() or \
        any timestamp, use TIMESTAMP_ADD/TIMESTAMP_SUB functions rather than \
            +/- operators.

    TYPE CONVERSION FUNCTIONS:
    - TO_DATE(integer): Convert epoch milliseconds to date
    - TO_DATE(expression, format): Convert string to date with format
    - TO_TIMESTAMP(double): Convert epoch seconds to timestamp
    - TO_TIMESTAMP(string, format): Convert string to timestamp with format
    - TO_TIME(int): Convert epoch milliseconds to time
    - TO_TIME(string, format): Convert string to time with format
    - CAST(expression AS data_type): Convert between BOOLEAN, INTEGER,
        TIMESTAMP, DATE, STRING, etc.

    AGGREGATE FUNCTIONS:
    - AVG(expression): Average value
    - COUNT(expression): Count rows (COUNT(*) is supported)
    - MAX(expression): Maximum value
    - MIN(expression): Minimum value
    - SUM(expression): Sum values
    - STDDEV(expression): Standard deviation
    - GROUP BY expression: Group results
    - HAVING boolean-expression: Filter grouped results

    IMPORTANT LIMITATIONS:
    - Window functions, CTEs (WITH clauses), DISTINCT, SELECT *, and \
        ILIKE are NOT supported

    SUPPORTED FEATURES:
    - CASE statements (CASE WHEN...THEN...ELSE...END pattern) ARE supported
    - COUNT(*) IS supported (only SELECT * is blocked)
    - Use implicit JOINs for better performance when possible

    Args:
        query_statement: The SQL query statement to execute (max 64KB)
        region: AWS region (default: us-east-1)
        next_token: Token for paginated results
        max_results: Maximum results to return (1-4000, default: 100)

    Returns:
        Dictionary containing:
        - success: Boolean indicating query success
        - columns: List of column definitions
        - rows: List of result rows
        - next_token: Token for next page (if applicable)
        - query_statistics: Execution statistics
        - query_status: Query execution status

    Example Queries (Using Correct View and Column Names):

    Basic Asset Discovery:
        "SELECT asset_id, asset_name, asset_model_id FROM asset"

    Metadata Filtering:
        "SELECT a.asset_name, p.property_name FROM asset a, asset_property p \
            WHERE a.asset_id = p.asset_id AND a.asset_name LIKE 'Windmill%'"

    Value Filtering with Time Range:
        "SELECT a.asset_name, r.int_value FROM asset a, raw_time_series r
         WHERE a.asset_id = r.asset_id
         AND r.int_value > 30
         AND r.event_timestamp > TIMESTAMP '2022-01-05 12:15:00'
         AND r.event_timestamp < TIMESTAMP '2022-01-05 12:20:00'"

    Aggregation with Grouping:
        "SELECT MAX(d.int_value) AS max_int_value, d.asset_id
         FROM raw_time_series AS d
         GROUP BY d.asset_id
         HAVING MAX(d.int_value) > 5"

    Date/Time Manipulation:
        "SELECT r.asset_id, r.int_value,
         DATE_ADD(DAY, 7, r.event_timestamp) AS date_in_future,
         DATE_SUB(YEAR, 2, r.event_timestamp) AS date_in_past,
         TIMESTAMP_ADD(DAY, 2, r.event_timestamp) AS timestamp_in_future,
         TIMESTAMP_SUB(DAY, 2, r.event_timestamp) AS timestamp_in_past
         FROM raw_time_series AS r"

    Type Conversion Examples:
        "SELECT r.asset_id, TO_DATE(r.event_timestamp) AS date_value,
         TO_TIME(r.event_timestamp) AS time_value
         FROM raw_time_series AS r"

    Attribute Property Filtering (For Attribute Properties Only - \
        Note: Only one attribute value type can be non-null per property):
        "SELECT p.property_name,
         CASE
             WHEN p.string_attribute_value IS NOT NULL THEN p.string_attribute_value
             WHEN p.double_attribute_value IS NOT NULL THEN \
                 CAST(p.double_attribute_value AS STRING)
             ELSE 'NULL'
         END as attribute_value
         FROM asset_property p
         WHERE p.property_type = 'attribute'
         AND (p.string_attribute_value LIKE 'my-property-%' OR \
             p.double_attribute_value > 100.0)"

    Precomputed Aggregates (Include quality and resolution filters):
        "SELECT asset_id, property_id, average_value, event_timestamp
         FROM precomputed_aggregates
         WHERE quality = 'GOOD'
         AND resolution = '1h'
         AND event_timestamp BETWEEN TIMESTAMP '2023-01-01 00:00:00' AND \
             TIMESTAMP '2023-01-02 00:00:00'"

    Implicit JOIN for Better Performance:
        "SELECT a.asset_name, p.property_name, r.double_value
         FROM asset a, asset_property p, raw_time_series r
         WHERE a.asset_id = p.asset_id
         AND p.property_id = r.property_id
         AND r.quality = 'GOOD'"

    Data Quality Analysis:
        "SELECT asset_id, property_alias,
         SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) as good_readings,
         SUM(CASE WHEN quality = 'BAD' THEN 1 ELSE 0 END) as bad_readings,
         ROUND(
             SUM(CASE WHEN quality = 'GOOD' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),

             2) as quality_percent         FROM raw_time_series WHERE \
                 event_timestamp >= TIMESTAMP '2023-01-01 00:00:00'
         GROUP BY asset_id, property_alias HAVING COUNT(*) > 10"

    CASE Statement and COUNT(*) Examples:
        "SELECT asset_id, COUNT(*) as total_records,
         CASE WHEN COUNT(*) = 0 THEN 'No Data' ELSE 'Has Data' END as data_status
         FROM raw_time_series GROUP BY asset_id"

    Query Optimization Guidelines (From AWS Documentation):

    1. METADATA FILTERS - \
        Use WHERE clause with these operators for metadata fields:
       - Equals (=), Not equals (!=), LIKE, IN, AND, OR
       - Use literals on right side of operators for better performance

    2. RAW DATA FILTERS - Always filter on event_timestamp using:
       - Equals (
           =), Greater than (>), Less than (<), Greater/Less than or \
               equals (>=,
           <=)       - BETWEEN, AND operators
       - Avoid != and OR operators as they don't limit data scan effectively

    3. PRECOMPUTED AGGREGATES - Always specify:
       - Quality filter (quality = 'GOOD') to reduce data scanned
       - Resolution filter (1m, 15m, 1h, 1d) to avoid full table scan

    4. JOIN OPTIMIZATION:
       - Use implicit JOINs instead of explicit JOIN keyword when possible
       - Push metadata filters into subqueries for better performance
       - Apply filters on individual JOINed tables to minimize data scanned

    5. PERFORMANCE TIPS:
       - Use LIMIT clause to reduce data scanned for some queries
       - Set page size to maximum 20000 for large queries
       - Use attribute value columns (
           double_attribute_value,
           etc.) for better performance than latest_value_time_series       - \
               Filter on asset_id, property_id for indexed access
       - Always include quality = 'GOOD' filters for reliable data

    """
    try:
        # Validate parameters
        if not query_statement or not query_statement.strip():
            raise ValidationError('Query statement cannot be empty')

        if len(query_statement) > 65536:  # 64KB limit
            raise ValidationError('Query statement cannot exceed 64KB')

        validate_region(region)
        validate_max_results(max_results, min_val=1, max_val=4000)

        if next_token and len(next_token) > 4096:
            raise ValidationError('Next token too long')

        client = create_sitewise_client(region)

        params: Dict[str, Any] = {
            'queryStatement': query_statement.strip(),
            'maxResults': max_results,
        }

        if next_token:
            params['nextToken'] = next_token

        response = client.execute_query(**params)

        return {
            'success': True,
            'columns': response.get('columns', []),
            'rows': response.get('rows', []),
            'next_token': response.get('nextToken', ''),
            'query_statistics': response.get('queryStatistics', {}),
            'query_status': response.get('queryStatus', 'COMPLETED'),
        }

    except ValidationError as e:
        return {
            'success': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'ValidationException',
        }
    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code'],
        }


batch_put_asset_property_value_tool = Tool.from_function(
    fn=batch_put_asset_property_value,
    name='batch_put_asset_property_value',
    description=('Send a list of asset property values to AWS IoT SiteWise for data ingestion.'),
)


get_asset_property_value_tool = Tool.from_function(
    fn=get_asset_property_value,
    name='get_asset_property_value',
    description=('Get the current value for a given asset property in AWS IoT SiteWise.'),
)

get_asset_property_value_history_tool = Tool.from_function(
    fn=get_asset_property_value_history,
    name='get_asset_property_value_history',
    description=('Get the historical values for an asset property in AWS IoT SiteWise.'),
)

get_asset_property_aggregates_tool = Tool.from_function(
    fn=get_asset_property_aggregates,
    name='get_asset_property_aggregates',
    description='Get aggregated values (average, count, maximum, minimum, '
    'sum, standard deviation) for an asset property in AWS IoT SiteWise.',
)

get_interpolated_asset_property_values_tool = Tool.from_function(
    fn=get_interpolated_asset_property_values,
    name='get_interpl_asset_property_values',
    description=(
        'Get interpolated values for an asset property for a '
        'specified time interval in AWS IoT SiteWise.'
    ),
)

batch_get_asset_property_value_tool = Tool.from_function(
    fn=batch_get_asset_property_value,
    name='batch_get_asset_property_value',
    description=('Get the current values for multiple asset properties in AWS IoT SiteWise.'),
)

batch_get_asset_property_value_history_tool = Tool.from_function(
    fn=batch_get_asset_property_value_history,
    name='batch_get_asset_property_value_hist',
    description=('Get the historical values for multiple asset properties in AWS IoT SiteWise.'),
)

batch_get_asset_property_aggregates_tool = Tool.from_function(
    fn=batch_get_asset_property_aggregates,
    name='batch_get_asset_property_aggregates',
    description=('Get aggregated values for multiple asset properties in AWS IoT SiteWise.'),
)

execute_query_tool = Tool.from_function(
    fn=execute_query,
    name='execute_query',
    description=(
        'Execute comprehensive SQL queries against AWS IoT SiteWise data '
        'with SQL capabilities including views (asset, asset_property, '
        'raw_time_series, latest_value_time_series, precomputed_aggregates), '
        'functions (aggregation, date/time, string, mathematical), '
        'operators, joins, and analytics for industrial IoT data exploration.'
    ),
)
