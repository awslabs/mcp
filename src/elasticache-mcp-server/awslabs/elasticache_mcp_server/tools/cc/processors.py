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

"""Processor functions for ElastiCache cache cluster tools."""

from .parsers import parse_shorthand_scale_config
from typing import Dict, Union


def process_scale_config(scale_config: Union[str, Dict]) -> Dict:
    """Process scale configuration in either shorthand or JSON format.

    Args:
        scale_config: Scale configuration in either format
            Shorthand format: "ReplicasPerNodeGroup=int,AutomaticFailoverEnabled=bool,..."
            JSON format: Dictionary with scale configuration parameters

    Returns:
        Dictionary containing the processed scale configuration

    Raises:
        ValueError: If the configuration is invalid
    """
    if isinstance(scale_config, str):
        # Parse shorthand syntax
        try:
            return parse_shorthand_scale_config(scale_config)
        except ValueError as e:
            raise ValueError(f'Invalid scale config shorthand syntax: {str(e)}')
    else:
        # Handle JSON format
        if not isinstance(scale_config, dict):
            raise ValueError('Scale configuration must be a dictionary or a shorthand string')

        # Validate required fields and types
        field_types = {
            'ReplicasPerNodeGroup': int,
            'AutomaticFailoverEnabled': bool,
            'ScaleOutEnabled': bool,
            'ScaleInEnabled': bool,
            'TargetCapacity': int,
            'MinCapacity': int,
            'MaxCapacity': int,
        }

        processed_config = {}
        for field, field_type in field_types.items():
            if field in scale_config:
                if not isinstance(scale_config[field], field_type):
                    raise ValueError(f'{field} must be of type {field_type.__name__}')
                processed_config[field] = scale_config[field]

        # Validate capacity values if present
        if 'MinCapacity' in processed_config and 'MaxCapacity' in processed_config:
            if processed_config['MinCapacity'] > processed_config['MaxCapacity']:
                raise ValueError('MinCapacity cannot be greater than MaxCapacity')
            if 'TargetCapacity' in processed_config and (
                processed_config['TargetCapacity'] < processed_config['MinCapacity']
                or processed_config['TargetCapacity'] > processed_config['MaxCapacity']
            ):
                raise ValueError('TargetCapacity must be between MinCapacity and MaxCapacity')

        return processed_config
