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

"""Parser functions for ElastiCache cache cluster tools."""

from typing import Any, Dict


def parse_shorthand_scale_config(config: str) -> Dict[str, Any]:
    """Parse a scale configuration from shorthand syntax.

    Args:
        config: Shorthand syntax string for scale configuration
            Format: ReplicasPerNodeGroup=int,AutomaticFailoverEnabled=bool,ScaleOutEnabled=bool,
                   ScaleInEnabled=bool,TargetCapacity=int,MinCapacity=int,MaxCapacity=int

    Returns:
        Dictionary containing the parsed scale configuration

    Raises:
        ValueError: If the syntax is invalid
    """
    if not config:
        raise ValueError('Empty scale configuration')

    result = {}
    pairs = config.split(',')

    # Define valid keys and their processors
    key_processors = {
        'ReplicasPerNodeGroup': int,
        'AutomaticFailoverEnabled': lambda x: x.lower() == 'true',
        'ScaleOutEnabled': lambda x: x.lower() == 'true',
        'ScaleInEnabled': lambda x: x.lower() == 'true',
        'TargetCapacity': int,
        'MinCapacity': int,
        'MaxCapacity': int,
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

    # Validate capacity values if present
    if 'MinCapacity' in result and 'MaxCapacity' in result:
        if result['MinCapacity'] > result['MaxCapacity']:
            raise ValueError('MinCapacity cannot be greater than MaxCapacity')
        if 'TargetCapacity' in result:
            if (
                result['TargetCapacity'] < result['MinCapacity']
                or result['TargetCapacity'] > result['MaxCapacity']
            ):
                raise ValueError('TargetCapacity must be between MinCapacity and MaxCapacity')

    return result
