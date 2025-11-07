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

"""Centralized validation utilities for AWS IoT SiteWise MCP Server.

This module provides reusable validation functions to eliminate code duplication
across validation.py, computation_data_models.py, and models.py.
"""

import re
from typing import Optional


# Common regex patterns
UUID_PATTERN = re.compile(
    r'^(?!00000000-0000-0000-0000-000000000000)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)
# AWS IoT SiteWise asset/asset model ID pattern (UUID or externalId:value)
ASSET_ID_PATTERN = re.compile(
    r'^(?!00000000-0000-0000-0000-000000000000)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$|^externalId:[a-zA-Z0-9_][a-zA-Z_\-0-9.:]*[a-zA-Z0-9_]+$'
)
CONTROL_CHAR_PATTERN = re.compile(r'^[^\u0000-\u001F\u007F]+$')
S3_BUCKET_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$')
VARIABLE_NAME_PATTERN = re.compile(r'^\$\{[a-z][a-z0-9_]*\}$')
EXPRESSION_VARIABLE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
EXTERNAL_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_][a-zA-Z_\-0-9.:]*[a-zA-Z0-9_]+$')
IANA_TIMEZONE_PATTERN = re.compile(
    r'^(UTC|GMT)([+-]\d{2}:\d{2})?$|^[A-Z][a-zA-Z_]*(/[A-Z][a-zA-Z_]*)*$'
)
TIME_RANGE_PATTERN = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$')


def validate_uuid_format(value: str, field_name: str = 'UUID') -> str:
    """Validate UUID format constraints.

    Args:
        value: The UUID string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        ValueError: If UUID format is invalid
    """
    if not value:
        raise ValueError(f'{field_name} cannot be empty')

    if len(value) != 36:
        raise ValueError(f'{field_name} must be exactly 36 characters')

    if not UUID_PATTERN.match(value):
        raise ValueError(f'Invalid {field_name} format: {value}')

    return value


def validate_asset_or_model_id(value: str, field_name: str = 'ID') -> str:
    """Validate AWS IoT SiteWise asset or asset model ID format.

    Accepts either:
    - UUID format: 12345678-1234-1234-1234-123456789012
    - External ID format: externalId:my-external-id

    Args:
        value: The ID string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated ID string

    Raises:
        ValueError: If ID format is invalid
    """
    if not value:
        raise ValueError(f'{field_name} cannot be empty')

    # Check length constraints from AWS documentation
    if not (13 <= len(value) <= 139):
        raise ValueError(f'{field_name} must be between 13 and 139 characters')

    if not ASSET_ID_PATTERN.match(value):
        raise ValueError(
            f'Invalid {field_name} format. Must be either UUID format (12345678-1234-1234-1234-123456789012) or external ID format (externalId:my-external-id)'
        )

    return value


def validate_string_length(
    value: str, min_length: int, max_length: int, field_name: str = 'String'
) -> str:
    """Validate string length constraints.

    Args:
        value: The string to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        The validated string

    Raises:
        ValueError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValueError(f'{field_name} must be a string')

    if not (min_length <= len(value) <= max_length):
        raise ValueError(f'{field_name} must be between {min_length} and {max_length} characters')

    return value


def validate_control_characters(value: str, field_name: str = 'String') -> str:
    """Validate that string doesn't contain control characters.

    Args:
        value: The string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string

    Raises:
        ValueError: If string contains control characters
    """
    if not CONTROL_CHAR_PATTERN.match(value):
        raise ValueError(f'{field_name} contains invalid control characters')

    return value


def validate_regex_pattern(
    value: str,
    pattern: re.Pattern,
    field_name: str = 'String',
    pattern_description: Optional[str] = None,
) -> str:
    """Validate string against a regex pattern.

    Args:
        value: The string to validate
        pattern: Compiled regex pattern
        field_name: Name of the field for error messages
        pattern_description: Human-readable description of the pattern

    Returns:
        The validated string

    Raises:
        ValueError: If string doesn't match pattern
    """
    if not pattern.match(value):
        if pattern_description:
            raise ValueError(f'{field_name} must match pattern: {pattern_description}')
        else:
            raise ValueError(f'{field_name} format is invalid')

    return value


def validate_s3_bucket_name(bucket_name: str, field_name: str = 'bucketName') -> str:
    """Validate S3 bucket name constraints.

    Args:
        bucket_name: The bucket name to validate
        field_name: Name of the field for error messages

    Returns:
        The validated bucket name

    Raises:
        ValueError: If bucket name is invalid
    """
    validate_string_length(bucket_name, 3, 63, field_name)
    validate_regex_pattern(
        bucket_name, S3_BUCKET_NAME_PATTERN, field_name, 'S3 naming conventions'
    )
    return bucket_name


def validate_s3_prefix(prefix: str, field_name: str = 'prefix') -> str:
    """Validate S3 object prefix constraints.

    Args:
        prefix: The S3 prefix to validate
        field_name: Name of the field for error messages

    Returns:
        The validated prefix

    Raises:
        ValueError: If prefix is invalid
    """
    validate_string_length(prefix, 1, 1024, field_name)
    return prefix


def validate_external_id(external_id: str, field_name: str = 'externalId') -> str:
    """Validate external ID format constraints.

    Args:
        external_id: The external ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated external ID

    Raises:
        ValueError: If external ID is invalid
    """
    validate_string_length(external_id, 2, 128, field_name)
    validate_regex_pattern(
        external_id,
        EXTERNAL_ID_PATTERN,
        field_name,
        '^[a-zA-Z0-9_][a-zA-Z_\\-0-9.:]*[a-zA-Z0-9_]+$',
    )
    return external_id


def validate_variable_name(variable_name: str, field_name: str = 'variable') -> str:
    """Validate variable name format (${variable_name}).

    Args:
        variable_name: The variable name to validate
        field_name: Name of the field for error messages

    Returns:
        The validated variable name

    Raises:
        ValueError: If variable name is invalid
    """
    validate_string_length(variable_name, 4, 67, field_name)
    validate_regex_pattern(
        variable_name, VARIABLE_NAME_PATTERN, field_name, '^\\$\\{[a-z][a-z0-9_]*\\}$'
    )
    return variable_name


def validate_expression_variable_name(name: str, field_name: str = 'name') -> str:
    """Validate expression variable name format.

    Args:
        name: The expression variable name to validate
        field_name: Name of the field for error messages

    Returns:
        The validated name

    Raises:
        ValueError: If name is invalid
    """
    validate_string_length(name, 1, 64, field_name)
    validate_regex_pattern(name, EXPRESSION_VARIABLE_PATTERN, field_name, '^[a-z][a-z0-9_]*$')
    return name


def validate_positive_integer(value: int, field_name: str = 'value') -> int:
    """Validate positive integer constraints.

    Args:
        value: The integer to validate
        field_name: Name of the field for error messages

    Returns:
        The validated integer

    Raises:
        ValueError: If integer is not positive
    """
    if not isinstance(value, int) or value < 1:
        raise ValueError(f'{field_name} must be a positive integer (1 or greater)')

    return value


def validate_integer_range(
    value: int, min_val: int, max_val: int, field_name: str = 'value'
) -> int:
    """Validate integer within a specific range.

    Args:
        value: The integer to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        field_name: Name of the field for error messages

    Returns:
        The validated integer

    Raises:
        ValueError: If integer is outside the range
    """
    if not isinstance(value, int):
        raise ValueError(f'{field_name} must be an integer')

    if not (min_val <= value <= max_val):
        raise ValueError(f'{field_name} must be between {min_val} and {max_val}')

    return value


def validate_positive_timestamp(timestamp: int, field_name: str = 'timestamp') -> int:
    """Validate positive Unix timestamp.

    Args:
        timestamp: The timestamp to validate
        field_name: Name of the field for error messages

    Returns:
        The validated timestamp

    Raises:
        ValueError: If timestamp is not positive
    """
    if not isinstance(timestamp, int) or timestamp <= 0:
        raise ValueError(f'{field_name} must be a positive Unix epoch timestamp')

    return timestamp


def validate_iso8601_duration(duration: str, field_name: str = 'duration') -> str:
    """Validate ISO 8601 duration format.

    Args:
        duration: The duration string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated duration

    Raises:
        ValueError: If duration format is invalid
    """
    # Basic validation for ISO 8601 duration format
    if not re.match(r'^P(\d+D|(\d+Y)|(\d+M))$', duration):
        raise ValueError(f'{field_name} must be in ISO 8601 duration format (e.g., P30D, P1Y)')

    return duration


def validate_lookback_window(window: str, field_name: str = 'lookbackWindow') -> str:
    """Validate lookback window constraints.

    Args:
        window: The lookback window to validate
        field_name: Name of the field for error messages

    Returns:
        The validated window

    Raises:
        ValueError: If window is invalid
    """
    valid_windows = ['P180D', 'P360D', 'P540D', 'P720D']
    if window not in valid_windows:
        raise ValueError(f'{field_name} must be one of: {", ".join(valid_windows)}')

    return window


def validate_retraining_frequency(frequency: str, field_name: str = 'retrainingFrequency') -> str:
    """Validate retraining frequency constraints.

    Args:
        frequency: The retraining frequency to validate
        field_name: Name of the field for error messages

    Returns:
        The validated frequency

    Raises:
        ValueError: If frequency is invalid
    """
    validate_iso8601_duration(frequency, field_name)

    # Extract numeric value and unit for range validation
    if frequency.endswith('D'):
        days = int(frequency[1:-1])
        if days < 30:
            raise ValueError(f'{field_name} minimum is P30D (30 days)')
        if days > 365:
            raise ValueError(f'{field_name} maximum is P1Y (365 days)')
    elif frequency.endswith('Y'):
        years = int(frequency[1:-1])
        if years > 1:
            raise ValueError(f'{field_name} maximum is P1Y (1 year)')
    elif frequency.endswith('M'):
        months = int(frequency[1:-1])
        if months > 12:
            raise ValueError(f'{field_name} maximum is P1Y (12 months)')

    return frequency


def validate_data_upload_frequency(frequency: str, field_name: str = 'dataUploadFrequency') -> str:
    """Validate data upload frequency constraints.

    Args:
        frequency: The data upload frequency to validate
        field_name: Name of the field for error messages

    Returns:
        The validated frequency

    Raises:
        ValueError: If frequency is invalid
    """
    valid_frequencies = [
        'PT5M',
        'PT10M',
        'PT15M',
        'PT30M',
        'PT1H',
        'PT2H',
        'PT3H',
        'PT4H',
        'PT5H',
        'PT6H',
        'PT7H',
        'PT8H',
        'PT9H',
        'PT10H',
        'PT11H',
        'PT12H',
        'PT1D',
    ]
    if frequency not in valid_frequencies:
        raise ValueError(f'{field_name} must be one of: {", ".join(valid_frequencies)}')

    return frequency


def validate_target_sampling_rate(rate: str, field_name: str = 'targetSamplingRate') -> str:
    """Validate target sampling rate constraints.

    Args:
        rate: The target sampling rate to validate
        field_name: Name of the field for error messages

    Returns:
        The validated rate

    Raises:
        ValueError: If rate is invalid
    """
    valid_rates = [
        'PT1S',
        'PT5S',
        'PT10S',
        'PT15S',
        'PT30S',
        'PT1M',
        'PT5M',
        'PT10M',
        'PT15M',
        'PT30M',
        'PT1H',
    ]
    if rate not in valid_rates:
        raise ValueError(f'{field_name} must be one of: {", ".join(valid_rates)}')

    return rate


def validate_iana_timezone(timezone: str, field_name: str = 'timezone') -> str:
    """Validate IANA timezone identifier constraints.

    Args:
        timezone: The timezone identifier to validate
        field_name: Name of the field for error messages

    Returns:
        The validated timezone

    Raises:
        ValueError: If timezone is invalid
    """
    # Check for valid IANA timezone pattern
    if not IANA_TIMEZONE_PATTERN.match(timezone):
        raise ValueError(
            f'{field_name} "{timezone}" must be a valid IANA timezone identifier (e.g., "America/Chicago", "Europe/London", "UTC", "GMT+05:30")'
        )

    # Additional validation for timezone components
    if '/' in timezone:
        parts = timezone.split('/')
        # Validate that each part starts with uppercase and contains only letters/underscores
        for part in parts:
            if not re.match(r'^[A-Z][a-zA-Z_]*$', part):
                raise ValueError(
                    f'Invalid timezone component "{part}" in "{timezone}". Each component must start with uppercase letter and contain only letters/underscores'
                )

    # Validate UTC/GMT offset format if present
    if timezone.startswith(('UTC', 'GMT')) and len(timezone) > 3:
        offset_part = timezone[3:]  # Remove UTC/GMT prefix
        if not re.match(r'^[+-]\d{2}:\d{2}$', offset_part):
            raise ValueError(
                f'Invalid timezone offset format in "{timezone}". Use format like "UTC+05:30" or "GMT-08:00"'
            )

    return timezone


def validate_time_range(time_range: str, field_name: str = 'timeRange') -> str:
    """Validate time range format (HH:MM-HH:MM).

    Args:
        time_range: The time range to validate
        field_name: Name of the field for error messages

    Returns:
        The validated time range

    Raises:
        ValueError: If time range is invalid
    """
    if not TIME_RANGE_PATTERN.match(time_range):
        raise ValueError(f'{field_name} "{time_range}" must be in 24-hour format "HH:MM-HH:MM"')

    # Validate that start time is before end time
    start_time, end_time = time_range.split('-')
    start_hour, start_min = map(int, start_time.split(':'))
    end_hour, end_min = map(int, end_time.split(':'))

    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min

    if start_minutes >= end_minutes:
        raise ValueError(f'Start time must be before end time in range "{time_range}"')

    return time_range


def validate_client_token(token: str, field_name: str = 'clientToken') -> str:
    """Validate client token constraints.

    Args:
        token: The client token to validate
        field_name: Name of the field for error messages

    Returns:
        The validated token

    Raises:
        ValueError: If token is invalid
    """
    validate_string_length(token, 36, 64, field_name)
    if not re.match(r'\S{36,64}', token):
        raise ValueError(f'{field_name} format is invalid')

    return token


def validate_next_token(token: str, field_name: str = 'nextToken') -> str:
    """Validate next token constraints.

    Args:
        token: The next token to validate
        field_name: Name of the field for error messages

    Returns:
        The validated token

    Raises:
        ValueError: If token is invalid
    """
    validate_string_length(token, 1, 4096, field_name)
    if not re.match(r'^[A-Za-z0-9+/=]+$', token):
        raise ValueError(f'{field_name} must match pattern [A-Za-z0-9+/=]+')

    return token


def validate_max_results(
    max_results: int, min_val: int = 1, max_val: int = 250, field_name: str = 'maxResults'
) -> int:
    """Validate max results parameter.

    Args:
        max_results: The max results value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        field_name: Name of the field for error messages

    Returns:
        The validated max results

    Raises:
        ValueError: If max results is invalid
    """
    return validate_integer_range(max_results, min_val, max_val, field_name)


def validate_string_value(value: str, field_name: str = 'stringValue') -> str:
    """Validate string value constraints for action payloads.

    Args:
        value: The string value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string value

    Raises:
        ValueError: If string value is invalid
    """
    validate_string_length(value, 1, 1024, field_name)
    return value


def validate_action_type(action_type: str, field_name: str = 'actionType') -> str:
    """Validate action type format constraints.

    Args:
        action_type: The action type to validate
        field_name: Name of the field for error messages

    Returns:
        The validated action type

    Raises:
        ValueError: If action type is invalid
    """
    validate_string_length(action_type, 1, 256, field_name)
    if not re.match(r'^[^\u0000-\u001F\u007F]+$', action_type):
        raise ValueError(f'{field_name} contains invalid characters')

    return action_type


def validate_enum_value(value: str, valid_values: list, field_name: str = 'value') -> str:
    """Validate that a value is in a list of valid enum values.

    Args:
        value: The value to validate
        valid_values: List of valid enum values
        field_name: Name of the field for error messages

    Returns:
        The validated value

    Raises:
        ValueError: If value is not in valid_values
    """
    if value not in valid_values:
        raise ValueError(f'{field_name} must be one of: {", ".join(valid_values)}')

    return value
