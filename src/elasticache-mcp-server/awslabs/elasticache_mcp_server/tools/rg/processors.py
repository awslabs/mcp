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

"""Processor functions for ElastiCache replication group tools."""

from .parsers import (
    parse_shorthand_log_delivery,
    parse_shorthand_nodegroup,
    parse_shorthand_resharding,
)
from typing import Dict, List, Union


def process_resharding_configuration(
    resharding_configuration: Union[str, List[Dict]],
) -> List[Dict]:
    """Process resharding configuration in either shorthand or JSON format.

    Args:
        resharding_configuration: Resharding configuration in either format
            Shorthand format: "NodeGroupId=string,NewShardConfiguration={NewReplicaCount=integer,PreferredAvailabilityZones=string1,string2}"
            Multiple configurations can be separated by spaces.
            JSON format: List of dictionaries with required fields:
            - NodeGroupId: string
            - NewShardConfiguration:
                - NewReplicaCount: integer
                - PreferredAvailabilityZones: list of strings (optional)

    Returns:
        List of processed resharding configurations

    Raises:
        ValueError: If the configuration is invalid
    """
    processed_configs = []

    if isinstance(resharding_configuration, str):
        # Parse shorthand syntax
        configs = resharding_configuration.split(' ')
        for config in configs:
            if not config:
                continue
            try:
                parsed_config = parse_shorthand_resharding(config)
                processed_configs.append(parsed_config)
            except ValueError as e:
                raise ValueError(f'Invalid resharding shorthand syntax: {str(e)}')
    else:
        # Handle JSON format
        if not isinstance(resharding_configuration, list):
            raise ValueError(
                'Resharding configuration must be a list of dictionaries or a shorthand string'
            )

        for config in resharding_configuration:
            if not isinstance(config, dict):
                raise ValueError('Each resharding configuration must be a dictionary')

            # Validate required fields
            if 'NodeGroupId' not in config:
                raise ValueError('Missing required field: NodeGroupId')
            if 'NewShardConfiguration' not in config:
                raise ValueError('Missing required field: NewShardConfiguration')

            # Validate NewShardConfiguration
            new_shard = config['NewShardConfiguration']
            if not isinstance(new_shard, dict):
                raise ValueError('NewShardConfiguration must be a dictionary')
            if 'NewReplicaCount' not in new_shard:
                raise ValueError(
                    'Missing required field: NewReplicaCount in NewShardConfiguration'
                )
            if not isinstance(new_shard['NewReplicaCount'], int):
                raise ValueError('NewReplicaCount must be an integer')

            # Validate PreferredAvailabilityZones if present
            if 'PreferredAvailabilityZones' in new_shard:
                if not isinstance(new_shard['PreferredAvailabilityZones'], list):
                    raise ValueError('PreferredAvailabilityZones must be a list of strings')
                for zone in new_shard['PreferredAvailabilityZones']:
                    if not isinstance(zone, str):
                        raise ValueError('Each availability zone must be a string')

            processed_configs.append(config)

    return processed_configs


def process_log_delivery_configurations(
    log_delivery_configurations: Union[str, List[Dict]],
) -> List[Dict]:
    """Process log delivery configurations in either shorthand or JSON format.

    Args:
        log_delivery_configurations: Log delivery configurations in either format

    Returns:
        List of processed log delivery configurations

    Raises:
        ValueError: If the configuration is invalid
    """
    processed_configs = []

    if isinstance(log_delivery_configurations, str):
        # Parse shorthand syntax
        configs = log_delivery_configurations.split(' ')
        for config in configs:
            if not config:
                continue
            try:
                parsed_config = parse_shorthand_log_delivery(config)
                processed_configs.append(parsed_config)
            except ValueError as e:
                raise ValueError(f'Invalid log delivery shorthand syntax: {str(e)}')
    else:
        # Handle JSON format
        if not isinstance(log_delivery_configurations, list):
            raise ValueError(
                'Log delivery configurations must be a list of dictionaries or a shorthand string'
            )

        for config in log_delivery_configurations:
            if not isinstance(config, dict):
                raise ValueError('Each log delivery configuration must be a dictionary')

            # Validate required fields and types
            required_fields = {
                'LogType': ['slow-log', 'engine-log'],
                'DestinationType': ['cloudwatch-logs', 'kinesis-firehose'],
                'DestinationDetails': dict,
                'LogFormat': ['text', 'json'],
                'Enabled': bool,
            }

            for field, valid_values in required_fields.items():
                if field not in config:
                    raise ValueError(f'Missing required field: {field}')

                if field in ['LogType', 'DestinationType', 'LogFormat']:
                    if config[field] not in valid_values:
                        raise ValueError(f'{field} must be one of {valid_values}')
                elif field == 'DestinationDetails':
                    if not isinstance(config[field], valid_values):
                        raise ValueError(f'{field} must be a dictionary')
                elif field == 'Enabled':
                    if not isinstance(config[field], valid_values):
                        raise ValueError(f'{field} must be a boolean')

            processed_configs.append(config)

    return processed_configs


def process_nodegroup_configuration(
    node_group_configuration: Union[str, List[Dict]],
) -> List[Dict]:
    """Process nodegroup configuration in either shorthand or JSON format.

    Args:
        node_group_configuration: Nodegroup configuration in either format

    Returns:
        List of processed nodegroup configurations

    Raises:
        ValueError: If the configuration is invalid
    """
    processed_config = []

    if isinstance(node_group_configuration, str):
        # Parse shorthand syntax
        groups = node_group_configuration.split(' ')
        for group in groups:
            if not group:
                continue
            try:
                config = parse_shorthand_nodegroup(group)
                processed_config.append(config)
            except ValueError as e:
                raise ValueError(f'Invalid nodegroup shorthand syntax: {str(e)}')
    else:
        # Handle JSON format
        if not isinstance(node_group_configuration, list):
            raise ValueError(
                'Node group configuration must be a list of dictionaries or a shorthand string'
            )

        for config in node_group_configuration:
            if not isinstance(config, dict):
                raise ValueError('Each node group configuration must be a dictionary')

            # Validate required fields
            if 'NodeGroupId' not in config:
                raise ValueError('Missing required field: NodeGroupId')

            # Process the configuration
            processed_item = {}
            for k, v in config.items():
                if k == 'ReplicaCount':
                    try:
                        processed_item[k] = int(v)
                    except (ValueError, TypeError):
                        raise ValueError(f'ReplicaCount must be an integer: {v}')
                elif k in ['ReplicaAvailabilityZones', 'ReplicaOutpostArns']:
                    if isinstance(v, str):
                        processed_item[k] = v.split(',')
                    elif isinstance(v, list):
                        processed_item[k] = v
                    else:
                        raise ValueError(f'{k} must be a string or list of strings')
                else:
                    processed_item[k] = v
            processed_config.append(processed_item)

    return processed_config
