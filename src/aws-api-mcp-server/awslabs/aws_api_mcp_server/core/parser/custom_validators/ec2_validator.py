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

import re
from ...common.errors import (
    ParameterSchemaValidationError,
    ParameterValidationErrorRecord,
)
from typing import Any


"""
EC2 does server side validation on some of the parameter values
(for example: instance id is "i-[alphanumeric]").
Adding this to client side validation to avoid unecessary 4XX errors during Execute.
"""

MALFORMED_PARAMETER_VALUE_MESSAGE: str = (
    'Invalid parameter value: The parameter {parameter} does not match the {pattern} pattern'
)

PARAMETER_VALUE_REGEX = {
    # Instance id
    'InstanceId': r'^i-[a-f0-9]{8,17}$',
    'InstanceIds': r'^i-[a-f0-9]{8,17}$',
    # Group id
    'GroupId': r'^sg-[a-f0-9]{8,17}$',
    'GroupIds': r'^sg-[a-f0-9]{8,17}$',
    'Groups': r'^sg-[a-f0-9]{8,17}$',
    'SecurityGroups': r'^sg-[a-f0-9]{8,17}$',
    'SecurityGroupIds': r'^sg-[a-f0-9]{8,17}$',
    # Network interface id
    'NetworkInterfaceId': r'^eni-[a-f0-9]{8,17}$',
    'NetworkInterfaceIds': r'^eni-[a-f0-9]{8,17}$',
    # Volume id
    'VolumeId': r'^vol-[a-f0-9]{8,17}$',
    'VolumeIds': r'^vol-[a-f0-9]{8,17}$',
    # Snapshot id
    'SnapshotId': r'^snap-[a-f0-9]{8,17}$',
    'SnapshotIds': r'^snap-[a-f0-9]{8,17}$',
    # Image id
    'ImageId': r'^ami-[a-f0-9]{8,17}$',
    'ImageIds': r'^ami-[a-f0-9]{8,17}$',
    # Launch template id
    'LaunchTemplateId': r'^lt-[a-f0-9]{8,17}$',
    'LaunchTemplateIds': r'^lt-[a-f0-9]{8,17}$',
    # Nat gateway id
    'NatGatewayId': r'^nat-[a-f0-9]{8,17}$',
    'NatGatewayIds': r'^nat-[a-f0-9]{8,17}$',
}


def validate_ec2_parameter_values(parameters: dict[str, Any]):
    """Validate EC2 parameter values for custom rules."""
    errors = []
    for parameter, value in parameters.items():
        parameter_value_regex = PARAMETER_VALUE_REGEX.get(parameter, '')
        if parameter_value_regex:
            values = value if isinstance(value, list) else [value]
            invalid_values = [
                val for val in values if not re.match(parameter_value_regex, str(val))
            ]
            if invalid_values:
                errors.append(
                    ParameterValidationErrorRecord(
                        parameter,
                        MALFORMED_PARAMETER_VALUE_MESSAGE.format(
                            parameter=parameter, pattern=parameter_value_regex
                        ),
                    )
                )
    if errors:
        raise ParameterSchemaValidationError(errors)
