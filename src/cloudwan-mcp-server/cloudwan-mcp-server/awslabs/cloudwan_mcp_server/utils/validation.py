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

"""Input validation utilities following AWS Labs patterns."""

import ipaddress
import re


def validate_core_network_id(network_id: str | None) -> bool:
    """Validate AWS CloudWAN Core Network ID format.

    Args:
        network_id: Core network ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not network_id:
        return False

    # AWS Core Network ID pattern: core-network-[17 char hex]
    pattern = r"^core-network-[0-9a-f]{17}$"
    return bool(re.match(pattern, network_id))


def validate_global_network_id(network_id: str | None) -> bool:
    """Validate AWS CloudWAN Global Network ID format.

    Args:
        network_id: Global network ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not network_id:
        return False

    # AWS Global Network ID pattern: global-network-[17 char hex]
    pattern = r"^global-network-[0-9a-f]{17}$"
    return bool(re.match(pattern, network_id))


def validate_ip_address(ip: str | None) -> bool:
    """Validate IP address format (IPv4 or IPv6).

    Args:
        ip: IP address to validate

    Returns:
        True if valid, False otherwise
    """
    if not ip:
        return False

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_cidr_block(cidr: str | None) -> bool:
    """Validate CIDR block format.

    Args:
        cidr: CIDR block to validate

    Returns:
        True if valid, False otherwise
    """
    if not cidr:
        return False

    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except ValueError:
        return False


def validate_aws_region(region: str | None) -> bool:
    """Validate AWS region format.

    Args:
        region: AWS region to validate

    Returns:
        True if valid, False otherwise
    """
    if not region:
        return False

    # AWS region pattern: 2-3 letter prefix, dash, direction, dash, number
    pattern = r"^[a-z]{2,3}-[a-z]+-\d+$"
    return bool(re.match(pattern, region))


def validate_required_fields(data: dict, required_fields: list, field_name: str = "input") -> bool:
    """Validate that required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        field_name: Name of the field being validated (for error messages)

    Returns:
        True if all required fields are present, False otherwise

    Raises:
        ValueError: If required fields are missing
    """
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a dictionary")

    missing_fields = [field for field in required_fields if field not in data or data[field] is None]

    if missing_fields:
        raise ValueError(f"Missing required fields in {field_name}: {', '.join(missing_fields)}")

    return True
