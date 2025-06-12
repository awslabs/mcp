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

"""Parser functions for ElastiCache replication group tools."""

import json
from typing import Any, Dict


def parse_shorthand_resharding(config: str) -> Dict[str, Any]:
    """Parse a single resharding configuration from shorthand syntax.

    Args:
        config: Shorthand syntax string for resharding configuration
               Format: NodeGroupId=string,NewShardConfiguration={NewReplicaCount=integer,PreferredAvailabilityZones=string1,string2}

    Returns:
        Dictionary containing the parsed resharding configuration

    Raises:
        ValueError: If the syntax is invalid
    """
    if not config:
        raise ValueError('Empty resharding configuration')

    result = {}
    pairs = config.split(',')

    # Define valid keys and their processors
    key_processors = {
        'NodeGroupId': str,
        'NewShardConfiguration': lambda x: parse_new_shard_config(x),
    }

    for pair in pairs:
        if '=' not in pair:
            raise ValueError(f'Invalid format. Each parameter must be in key=value format: {pair}')

        key, value = pair.split('=', 1)
        if not key or not value:
            raise ValueError(f'Empty key or value: {pair}')

        if key not in key_processors:
            raise ValueError(f'Invalid parameter: {key}')

        try:
            result[key] = key_processors[key](value)
        except ValueError as e:
            raise ValueError(f'Invalid value for {key}: {value}') from e

    # Validate required fields
    if 'NodeGroupId' not in result:
        raise ValueError('Missing required field: NodeGroupId')
    if 'NewShardConfiguration' not in result:
        raise ValueError('Missing required field: NewShardConfiguration')

    return result


def parse_new_shard_config(config: str) -> Dict[str, Any]:
    """Parse the NewShardConfiguration portion of resharding configuration.

    Args:
        config: String containing new shard configuration
               Format: {NewReplicaCount=integer,PreferredAvailabilityZones=string1,string2}

    Returns:
        Dictionary containing the parsed new shard configuration

    Raises:
        ValueError: If the syntax is invalid
    """
    if not config.startswith('{') or not config.endswith('}'):
        raise ValueError('NewShardConfiguration must be enclosed in curly braces')

    # Remove curly braces
    config = config[1:-1]

    result = {}
    pairs = config.split(',')

    # Define valid keys and their processors
    key_processors = {
        'NewReplicaCount': int,
        'PreferredAvailabilityZones': lambda x: x.split(','),
    }

    for pair in pairs:
        if '=' not in pair:
            raise ValueError(f'Invalid format. Each parameter must be in key=value format: {pair}')

        key, value = pair.split('=', 1)
        if not key or not value:
            raise ValueError(f'Empty key or value: {pair}')

        if key not in key_processors:
            raise ValueError(f'Invalid parameter: {key}')

        try:
            result[key] = key_processors[key](value)
        except ValueError as e:
            raise ValueError(f'Invalid value for {key}: {value}') from e

    # Validate required fields
    if 'NewReplicaCount' not in result:
        raise ValueError('Missing required field: NewReplicaCount')

    return result


def parse_shorthand_nodegroup(group: str) -> Dict[str, Any]:
    """Parse a single nodegroup from shorthand syntax.

    Args:
        group: Shorthand syntax string for a nodegroup

    Returns:
        Dictionary containing the parsed nodegroup configuration

    Raises:
        ValueError: If the syntax is invalid
    """
    if not group:
        raise ValueError('Empty nodegroup configuration')

    config = {}

    # Define valid keys
    valid_keys = {
        'NodeGroupId',
        'Slots',
        'ReplicaCount',
        'PrimaryAvailabilityZone',
        'ReplicaAvailabilityZones',
        'PrimaryOutpostArn',
        'ReplicaOutpostArns',
    }

    # Define keys that should be treated as arrays
    array_keys = {'ReplicaAvailabilityZones', 'ReplicaOutpostArns'}

    # Split into key-value pairs
    pairs = group.split(',')
    current_key = None
    current_values = []

    for pair in pairs:
        pair = pair.strip()

        # If this part contains an equals sign, it's a new key-value pair
        if '=' in pair:
            # Save any previous array values
            if current_key in array_keys and current_values:
                config[current_key] = current_values
                current_values = []

            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()

            if not key or not value:
                raise ValueError(f'Empty key or value: {pair}')

            if key not in valid_keys:
                raise ValueError(f'Invalid parameter: {key}')

            current_key = key

            try:
                if key == 'ReplicaCount':
                    config[key] = int(value)
                elif key in array_keys:
                    current_values = [value]
                else:
                    config[key] = value
            except ValueError as e:
                raise ValueError(f'Invalid value for {key}: {value}') from e

        # If no equals sign and we're in an array key context, treat as array value
        elif current_key in array_keys:
            current_values.append(pair)
        else:
            raise ValueError(f'Invalid format. Each parameter must be in key=value format: {pair}')

    # Handle any remaining array values
    if current_key in array_keys and current_values:
        config[current_key] = current_values

    # Validate required fields
    if 'NodeGroupId' not in config:
        raise ValueError('Missing required field: NodeGroupId')

    return config


def parse_shorthand_log_delivery(config: str) -> Dict[str, Any]:
    """Parse a single log delivery configuration from shorthand syntax.

    Args:
        config: Shorthand syntax string for log delivery configuration

    Returns:
        Dictionary containing the parsed log delivery configuration

    Raises:
        ValueError: If the syntax is invalid
    """
    if not config:
        raise ValueError('Empty log delivery configuration')

    result = {}
    pairs = config.split(',')

    # Define valid keys and their processors
    key_processors = {
        'LogType': str,
        'DestinationType': str,
        'DestinationDetails': lambda x: json.loads(x.replace("'", '"')),
        'LogFormat': str,
        'Enabled': lambda x: x.lower() == 'true',
    }

    for pair in pairs:
        if '=' not in pair:
            raise ValueError(f'Invalid format. Each parameter must be in key=value format: {pair}')

        key, value = pair.split('=', 1)
        if not key or not value:
            raise ValueError(f'Empty key or value: {pair}')

        if key not in key_processors:
            raise ValueError(f'Invalid parameter: {key}')

        try:
            result[key] = key_processors[key](value)
        except ValueError as e:
            raise ValueError(f'Invalid value for {key}: {value}') from e

    # Validate required fields
    required_fields = ['LogType', 'DestinationType', 'DestinationDetails', 'LogFormat', 'Enabled']
    missing_fields = [field for field in required_fields if field not in result]
    if missing_fields:
        raise ValueError(f'Missing required fields: {", ".join(missing_fields)}')

    # Validate LogType
    if result['LogType'] not in ['slow-log', 'engine-log']:
        raise ValueError("LogType must be either 'slow-log' or 'engine-log'")

    # Validate DestinationType
    if result['DestinationType'] not in ['cloudwatch-logs', 'kinesis-firehose']:
        raise ValueError("DestinationType must be either 'cloudwatch-logs' or 'kinesis-firehose'")

    # Validate LogFormat
    if result['LogFormat'] not in ['text', 'json']:
        raise ValueError("LogFormat must be either 'text' or 'json'")

    return result
