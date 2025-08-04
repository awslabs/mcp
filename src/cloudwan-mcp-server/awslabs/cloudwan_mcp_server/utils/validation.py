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

import re
import ipaddress
from typing import Optional


def validate_core_network_id(network_id: Optional[str]) -> bool:
    """Validate AWS CloudWAN Core Network ID format.
    
    Args:
        network_id: Core network ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not network_id:
        return False
    
    # AWS Core Network ID pattern: core-network-[17 char hex]
    pattern = r'^core-network-[0-9a-f]{17}$'
    return bool(re.match(pattern, network_id))


def validate_global_network_id(network_id: Optional[str]) -> bool:
    """Validate AWS CloudWAN Global Network ID format.
    
    Args:
        network_id: Global network ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not network_id:
        return False
    
    # AWS Global Network ID pattern: global-network-[17 char hex]
    pattern = r'^global-network-[0-9a-f]{17}$'
    return bool(re.match(pattern, network_id))


def validate_ip_address(ip: Optional[str]) -> bool:
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


def validate_cidr_block(cidr: Optional[str]) -> bool:
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


def validate_aws_region(region: Optional[str]) -> bool:
    """Validate AWS region format.
    
    Args:
        region: AWS region to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not region:
        return False
    
    # AWS region pattern: 2-3 letter prefix, dash, direction, dash, number
    pattern = r'^[a-z]{2,3}-[a-z]+-\d+$'
    return bool(re.match(pattern, region))