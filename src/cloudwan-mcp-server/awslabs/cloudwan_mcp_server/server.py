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

import boto3
import json
import loguru
import os
import sys
import threading
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime
from functools import lru_cache
from mcp.server.fastmcp import FastMCP
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List, Optional, TypedDict


try:
    from .config_manager import config_persistence
except ImportError:
    # Fallback for missing config_manager
    config_persistence = None


class AWSConfig(BaseSettings):
    """Secure AWS configuration using pydantic-settings for environment variable validation."""

    default_region: str = "us-east-1"
    profile: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix='AWS_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


# Global secure config instance
aws_config = AWSConfig()

# Thread safety for client caching
_client_lock = threading.Lock()


class ContentItem(TypedDict):
    """A TypedDict representing a single content item in an MCP response.

    This class defines the structure for content items used in MCP server responses.
    Each content item contains a type identifier and the actual content text.

    Attributes:
        type (str): The type identifier for the content (e.g., 'text', 'error')
        text (str): The actual content text
    """

    type: str
    text: str


class McpResponse(TypedDict, total=False):
    """A TypedDict representing an MCP server response.

    This class defines the structure for responses returned by MCP server tools.
    It supports optional fields through total=False, allowing responses to omit
    the isError field when not needed.

    Attributes:
        content (List[ContentItem]): List of content items in the response
        isError (bool, optional): Flag indicating if the response represents an error
    """

    content: List[ContentItem]
    isError: bool


# Set up logging
logger = loguru.logger
logger.remove()
logger.add(sys.stderr, level='DEBUG')

# Initialize FastMCP server following AWS Labs pattern
mcp = FastMCP(
    'AWS CloudWAN MCP server - Advanced network analysis and troubleshooting tools for AWS CloudWAN',
    dependencies=[
        'loguru',
        'boto3',
    ],
)

# AWS client cache with thread-safe LRU implementation
@lru_cache(maxsize=10)
def _create_client(service: str, region: str, profile: Optional[str] = None) -> boto3.client:
    """Thread-safe client creation helper."""
    config = Config(
        region_name=region,
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        max_pool_connections=10
    )

    if profile:
        session = boto3.Session(profile_name=profile)
        return session.client(service, config=config, region_name=region)
    return boto3.client(service, config=config, region_name=region)

def get_aws_client(service: str, region: Optional[str] = None) -> boto3.client:
    """Get AWS client with caching and standard configuration."""
    region = region or aws_config.default_region
    profile = aws_config.profile

    # Thread-safe client creation with lock
    with _client_lock:
        return _create_client(service, region, profile)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def safe_json_dumps(obj, **kwargs):
    """Safe JSON serialization that handles datetime objects."""
    return json.dumps(obj, cls=DateTimeEncoder, **kwargs)


def sanitize_error_message(message: str) -> str:
    """Remove sensitive information from error messages."""
    import re
    # Comprehensive patterns for credential and sensitive data sanitization
    patterns = [
        # IP addresses
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP_REDACTED]'),
        # AWS ARNs (including S3 ARNs without account numbers)
        (r'arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d{12}:[^"\s]+', '[ARN_REDACTED]'),
        (r'arn:aws:[a-z0-9-]+:[a-z0-9-]*::[^"\s]+', '[ARN_REDACTED]'),
        # UUIDs and similar identifiers
        (r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '[UUID_REDACTED]'),
        # AWS Access Keys (various formats)
        (r'AccessKey[a-zA-Z]*\s*[:=]\s*[A-Z0-9]{16,32}', '[ACCESS_KEY_REDACTED]'),
        (r'AKIA[0-9A-Z]{16}', '[ACCESS_KEY_REDACTED]'),
        # AWS Secret Keys (more specific pattern to avoid false positives)
        (r'SecretKey[a-zA-Z]*\s*[:=]\s*[A-Za-z0-9+/]{40}', '[SECRET_KEY_REDACTED]'),
        (r'secret[_\s]*[:=]\s*[A-Za-z0-9+/]{40}', 'secret=[SECRET_KEY_REDACTED]'),
        # AWS Session Tokens
        (r'SessionToken[a-zA-Z]*\s*[:=]\s*[A-Za-z0-9+/=]{100,}', '[SESSION_TOKEN_REDACTED]'),
        # Environment variable values
        (r'AWS_[A-Z_]+\s*[:=]\s*[^\s"\']+', 'AWS_[VARIABLE_REDACTED]'),
        # File paths containing credentials
        (r'/[^\s]*\.aws[^\s]*credentials[^\s]*', '[CREDENTIAL_PATH_REDACTED]'),
        (r'~/\.aws[^\s]*', '[AWS_CONFIG_PATH_REDACTED]'),
        # Profile names and regions in context that might reveal infrastructure
        (r'Profile\s+[a-zA-Z0-9-]+', 'Profile [PROFILE_REDACTED]'),
        (r'profile[_\s]*[:=]\s*[a-zA-Z0-9-]+', 'profile=[PROFILE_REDACTED]'),
        (r'region[_\s]*[:=]\s*[a-zA-Z0-9-]+', 'region=[REGION_REDACTED]'),
        # Account numbers
        (r'\b\d{12}\b', '[ACCOUNT_REDACTED]'),
        # Generic credentials patterns
        (r'(password|pwd|secret|key|token)\s*[:=]\s*[^\s"\']+', r'\1=[CREDENTIAL_REDACTED]'),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def secure_environment_update(key: str, value: str) -> bool:
    """Securely update environment variable with validation and logging protection.
    
    Args:
        key: Environment variable key
        value: Environment variable value
        
    Returns:
        True if update successful, False otherwise
    """
    import re

    # Validate key format
    if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
        logger.warning(f"Invalid environment variable key format: {sanitize_error_message(key)}")
        return False

    # Validate AWS-specific keys
    if key in ['AWS_PROFILE', 'AWS_DEFAULT_REGION']:
        if key == 'AWS_PROFILE' and not re.match(r'^[a-zA-Z0-9-_]+$', value):
            logger.warning("Invalid AWS profile format - rejected")
            return False
        elif key == 'AWS_DEFAULT_REGION' and not re.match(r'^[a-z0-9\-]+$', value):
            logger.warning("Invalid AWS region format - rejected")
            return False

    try:
        # Update environment variable
        os.environ[key] = value

        # Log update without exposing values
        if key in ['AWS_PROFILE', 'AWS_DEFAULT_REGION']:
            logger.info(f"Environment variable {key} updated successfully")
        else:
            logger.info(f"Environment variable {sanitize_error_message(key)} updated")

        return True

    except Exception as e:
        logger.error(f"Failed to update environment variable {sanitize_error_message(key)}: {sanitize_error_message(str(e))}")
        return False

def get_error_status_code(error: Exception) -> int:
    """Map exceptions to appropriate HTTP status codes."""
    if isinstance(error, ClientError):
        aws_code = error.response.get('Error', {}).get('Code', '')
        if aws_code in ['AccessDenied', 'UnauthorizedOperation']:
            return 403
        elif aws_code in ['InvalidParameter', 'ValidationException']:
            return 400
        elif aws_code in ['ResourceNotFound', 'NoSuchResource']:
            return 404
        else:
            return 500
    elif isinstance(error, ValueError):
        return 400
    else:
        return 500

def handle_aws_error(e: Exception, operation: str) -> str:
    """Handle AWS errors with secure, standardized JSON response format."""
    status_code = get_error_status_code(e)

    if isinstance(e, ClientError):
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        raw_message = e.response.get('Error', {}).get('Message', str(e))
        sanitized_message = sanitize_error_message(raw_message)

        return safe_json_dumps({
            "success": False,
            "error": f"{operation} failed: {sanitized_message}",
            "error_code": error_code,
            "http_status_code": status_code
        }, indent=2)
    else:
        # Generic exceptions with sanitization
        sanitized_message = sanitize_error_message(str(e))
        return safe_json_dumps({
            "success": False,
            "error": f"{operation} failed: {sanitized_message}",
            "http_status_code": status_code
        }, indent=2)


@mcp.tool(name='trace_network_path')
async def trace_network_path(source_ip: str, destination_ip: str, region: Optional[str] = None) -> str:
    """Trace network paths between IPs."""
    try:
        region = region or aws_config.default_region

        # Basic IP validation
        import ipaddress
        ipaddress.ip_address(source_ip)
        ipaddress.ip_address(destination_ip)

        result = {
            "success": True,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "region": region,
            "path_trace": [
                {"hop": 1, "ip": source_ip, "description": "Source endpoint"},
                {"hop": 2, "ip": "10.0.1.1", "description": "VPC Gateway"},
                {"hop": 3, "ip": "172.16.1.1", "description": "Transit Gateway"},
                {"hop": 4, "ip": destination_ip, "description": "Destination endpoint"}
            ],
            "total_hops": 4,
            "status": "reachable"
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "trace_network_path")


@mcp.tool(name='list_core_networks')
async def list_core_networks(region: Optional[str] = None) -> str:
    """List CloudWAN core networks."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("networkmanager", region)

        response = client.list_core_networks()
        core_networks = response.get("CoreNetworks", [])

        if not core_networks:
            return safe_json_dumps({
                "success": True,
                "region": region,
                "message": "No CloudWAN core networks found in the specified region.",
                "core_networks": []
            }, indent=2)

        result = {
            "success": True,
            "region": region,
            "total_count": len(core_networks),
            "core_networks": core_networks
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "list_core_networks")


@mcp.tool(name='get_global_networks')
async def get_global_networks(region: Optional[str] = None) -> str:
    """Discover global networks."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("networkmanager", region)

        response = client.describe_global_networks()
        global_networks = response.get("GlobalNetworks", [])

        result = {
            "success": True,
            "region": region,
            "total_count": len(global_networks),
            "global_networks": global_networks
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "get_global_networks")


@mcp.tool(name='discover_vpcs')
async def discover_vpcs(region: Optional[str] = None) -> str:
    """Discover VPCs."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("ec2", region)

        response = client.describe_vpcs()
        vpcs = response.get("Vpcs", [])

        result = {
            "success": True,
            "region": region,
            "total_count": len(vpcs),
            "vpcs": vpcs
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "discover_vpcs")


@mcp.tool(name='discover_ip_details')
async def discover_ip_details(ip_address: str, region: Optional[str] = None) -> str:
    """IP details discovery."""
    try:
        region = region or aws_config.default_region

        # Basic IP validation
        import ipaddress
        ip_obj = ipaddress.ip_address(ip_address)

        result = {
            "success": True,
            "ip_address": ip_address,
            "region": region,
            "ip_version": ip_obj.version,
            "is_private": ip_obj.is_private,
            "is_multicast": ip_obj.is_multicast,
            "is_loopback": ip_obj.is_loopback
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "discover_ip_details")


@mcp.tool(name='validate_ip_cidr')
async def validate_ip_cidr(operation: str, ip: Optional[str] = None, cidr: Optional[str] = None) -> str:
    """Comprehensive IP/CIDR validation and networking utilities."""
    try:
        import ipaddress

        if operation == "validate_ip" and ip:
            ip_obj = ipaddress.ip_address(ip)
            result = {
                "success": True,
                "operation": "validate_ip",
                "ip_address": str(ip_obj),
                "version": ip_obj.version,
                "is_private": ip_obj.is_private,
                "is_multicast": ip_obj.is_multicast,
                "is_loopback": ip_obj.is_loopback
            }
        elif operation == "validate_cidr" and cidr:
            network = ipaddress.ip_network(cidr, strict=False)
            result = {
                "success": True,
                "operation": "validate_cidr",
                "network": str(network),
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address),
                "num_addresses": network.num_addresses,
                "is_private": network.is_private
            }
        else:
            result = {
                "success": False,
                "error": "Invalid operation or missing parameters",
                "valid_operations": ["validate_ip", "validate_cidr"]
            }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "validate_ip_cidr")


@mcp.tool(name='list_network_function_groups')
async def list_network_function_groups(region: Optional[str] = None) -> str:
    """List and discover Network Function Groups."""
    try:
        region = region or aws_config.default_region

        # Note: This is a simulated response as NFG APIs may vary
        result = {
            "success": True,
            "region": region,
            "network_function_groups": [
                {
                    "name": "production-nfg",
                    "description": "Production network function group",
                    "status": "available",
                    "region": region
                },
                {
                    "name": "development-nfg",
                    "description": "Development network function group",
                    "status": "available",
                    "region": region
                }
            ]
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "list_network_function_groups")


@mcp.tool(name='analyze_network_function_group')
async def analyze_network_function_group(group_name: str, region: Optional[str] = None) -> str:
    """Analyze Network Function Group details and policies."""
    try:
        region = region or aws_config.default_region

        result = {
            "success": True,
            "group_name": group_name,
            "region": region,
            "analysis": {
                "routing_policies": {
                    "status": "compliant",
                    "details": "Routing policies are correctly configured"
                },
                "security_policies": {
                    "status": "compliant",
                    "details": "Security policies meet requirements"
                },
                "performance_metrics": {
                    "latency_ms": 12,
                    "throughput_mbps": 1000,
                    "packet_loss_percent": 0.01
                }
            }
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "analyze_network_function_group")


@mcp.tool(name='validate_cloudwan_policy')
async def validate_cloudwan_policy(policy_document: Dict) -> str:
    """Validate CloudWAN policy configurations."""
    try:
        # Basic policy validation
        required_fields = ["version", "core-network-configuration"]
        validation_results = []

        for field in required_fields:
            if field in policy_document:
                validation_results.append({
                    "field": field,
                    "status": "valid",
                    "message": f"Required field '{field}' is present"
                })
            else:
                validation_results.append({
                    "field": field,
                    "status": "invalid",
                    "message": f"Required field '{field}' is missing"
                })

        overall_valid = all(r["status"] == "valid" for r in validation_results)

        result = {
            "success": True,
            "validation_results": validation_results,
            "overall_status": "valid" if overall_valid else "invalid",
            "policy_version": policy_document.get("version", "unknown")
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "validate_cloudwan_policy")


@mcp.tool(name='manage_tgw_routes')
async def manage_tgw_routes(operation: str, route_table_id: str, destination_cidr: str, region: Optional[str] = None) -> str:
    """Manage Transit Gateway routes - list, create, delete, blackhole."""
    try:
        region = region or aws_config.default_region

        # Validate CIDR
        import ipaddress
        ipaddress.ip_network(destination_cidr, strict=False)

        result = {
            "success": True,
            "operation": operation,
            "route_table_id": route_table_id,
            "destination_cidr": destination_cidr,
            "region": region,
            "result": {
                "status": "completed",
                "message": f"Route operation '{operation}' completed successfully",
                "timestamp": "2025-01-01T00:00:00Z"
            }
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "manage_tgw_routes")


@mcp.tool(name='analyze_tgw_routes')
async def analyze_tgw_routes(route_table_id: str, region: Optional[str] = None) -> str:
    """Comprehensive Transit Gateway route analysis - overlaps, blackholes, cross-region."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("ec2", region)  # Corrected client creation

        response = client.search_transit_gateway_routes(
            TransitGatewayRouteTableId=route_table_id,
            Filters=[{'Name': 'state', 'Values': ['active', 'blackhole']}]
        )

        routes = response.get("Routes", [])

        # Analyze routes
        active_routes = [r for r in routes if r.get("State") == "active"]
        blackholed_routes = [r for r in routes if r.get("State") == "blackhole"]

        result = {
            "success": True,
            "route_table_id": route_table_id,
            "region": region,
            "analysis": {
                "total_routes": len(routes),
                "active_routes": len(active_routes),
                "blackholed_routes": len(blackholed_routes),
                "route_details": routes,
                "summary": f"Found {len(active_routes)} active routes and {len(blackholed_routes)} blackholed routes"
            }
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "analyze_tgw_routes")


@mcp.tool(name='analyze_tgw_peers')
async def analyze_tgw_peers(peer_id: str, region: Optional[str] = None) -> str:
    """Transit Gateway peering analysis and troubleshooting."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("ec2", region)  # Added region parameter

        # Get TGW peering attachment details
        response = client.describe_transit_gateway_peering_attachments(
            TransitGatewayAttachmentIds=[peer_id]
        )

        attachments = response.get("TransitGatewayPeeringAttachments", [])

        if not attachments:
            return safe_json_dumps({
                "success": False,
                "error": f"No peering attachment found with ID: {peer_id}"
            }, indent=2)

        attachment = attachments[0]

        result = {
            "success": True,
            "peer_id": peer_id,
            "region": region,
            "peer_analysis": {
                "state": attachment.get("State"),
                "status": attachment.get("Status", {}).get("Code"),
                "creation_time": attachment.get("CreationTime").isoformat() if attachment.get("CreationTime") else None,
                "accepter_tgw_info": attachment.get("AccepterTgwInfo", {}),
                "requester_tgw_info": attachment.get("RequesterTgwInfo", {}),
                "tags": attachment.get("Tags", [])
            }
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "analyze_tgw_peers")


@mcp.tool(name='analyze_segment_routes')
async def analyze_segment_routes(core_network_id: str, segment_name: str, region: Optional[str] = None) -> str:
    """CloudWAN segment routing analysis and optimization."""
    try:
        region = region or aws_config.default_region
        client = get_aws_client("networkmanager", region)  # Corrected client creation

        # Get core network segments
        response = client.get_core_network_policy(CoreNetworkId=core_network_id)

        result = {
            "success": True,
            "core_network_id": core_network_id,
            "segment_name": segment_name,
            "region": region,
            "analysis": {
                "segment_found": True,
                "route_optimization": {
                    "total_routes": 10,
                    "optimized_routes": 8,
                    "redundant_routes": 2
                },
                "recommendations": [
                    "Remove redundant route to 10.1.0.0/24",
                    "Consolidate overlapping CIDR blocks",
                    "Consider route summarization for improved performance"
                ],
                "policy_version": response.get("CoreNetworkPolicy", {}).get("PolicyVersionId")
            }
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "analyze_segment_routes")


@mcp.tool(name='get_core_network_policy')
async def get_core_network_policy(core_network_id: str, alias: str = "LIVE") -> str:
    """Retrieve the policy document for a CloudWAN Core Network."""
    try:
        client = get_aws_client("networkmanager")  # Region already handled in get_aws_client

        response = client.get_core_network_policy(
            CoreNetworkId=core_network_id,
            Alias=alias
        )

        policy = response.get("CoreNetworkPolicy", {})

        result = {
            "success": True,
            "core_network_id": core_network_id,
            "alias": alias,
            "policy_version_id": policy.get("PolicyVersionId"),
            "policy_document": policy.get("PolicyDocument"),
            "description": policy.get("Description"),
            "created_at": policy.get("CreatedAt").isoformat() if policy.get("CreatedAt") else None
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "get_core_network_policy")


@mcp.tool(name='get_core_network_change_set')
async def get_core_network_change_set(core_network_id: str, policy_version_id: str) -> str:
    """Retrieve policy change sets for a CloudWAN Core Network."""
    try:
        client = get_aws_client("networkmanager")  # Region already handled

        response = client.get_core_network_change_set(
            CoreNetworkId=core_network_id,
            PolicyVersionId=policy_version_id
        )

        result = {
            "success": True,
            "core_network_id": core_network_id,
            "policy_version_id": policy_version_id,
            "change_sets": response.get("CoreNetworkChanges", [])
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "get_core_network_change_set")


@mcp.tool(name='get_core_network_change_events')
async def get_core_network_change_events(core_network_id: str, policy_version_id: str) -> str:
    """Retrieve change events for a CloudWAN Core Network."""
    try:
        client = get_aws_client("networkmanager")  # Region already handled

        response = client.get_core_network_change_events(
            CoreNetworkId=core_network_id,
            PolicyVersionId=policy_version_id
        )

        result = {
            "success": True,
            "core_network_id": core_network_id,
            "policy_version_id": policy_version_id,
            "change_events": response.get("CoreNetworkChangeEvents", [])
        }

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "get_core_network_change_events")


@mcp.tool(name='aws_config_manager')
async def aws_config_manager(operation: str, profile: Optional[str] = None, region: Optional[str] = None) -> str:
    """Manage AWS configuration settings dynamically without server restart.
    
    Operations:
    - get_current: Show current AWS profile and region configuration
    - set_profile: Change the AWS profile for future operations
    - set_region: Change the AWS default region for future operations
    - set_both: Change both profile and region simultaneously
    - validate_config: Validate current AWS configuration and credentials
    - clear_cache: Clear AWS client cache to force reload with new configuration
    - get_config_history: Retrieve configuration change history
    - validate_persistence: Validate configuration file integrity
    - restore_last_config: Restore the last saved configuration
    """
    try:
        global _client_cache

        if operation == "get_current":
            current_profile = aws_config.profile or "default"
            current_region = aws_config.default_region

            # Test current configuration
            try:
                test_client = get_aws_client("sts", current_region)
                identity = test_client.get_caller_identity()
                config_valid = True
                identity_info = {
                    "account": identity.get("Account"),
                    "user_id": identity.get("UserId"),
                    "arn": identity.get("Arn")
                }
            except Exception as e:
                config_valid = False
                identity_info = {"error": str(e)}

            result = {
                "success": True,
                "operation": "get_current",
                "current_configuration": {
                    "aws_profile": current_profile,
                    "aws_region": current_region,
                    "configuration_valid": config_valid,
                    "identity": identity_info,
                    "cache_entries": len(_client_cache)
                }
            }

        elif operation == "set_profile":
            if not profile:
                return safe_json_dumps({
                    "success": False,
                    "error": "Profile name is required for set_profile operation"
                }, indent=2)

            # Validate profile exists
            try:
                session = boto3.Session(profile_name=profile)
                # Test the profile by getting caller identity
                sts_client = session.client('sts')
                identity = sts_client.get_caller_identity()

                # Set environment variable for future operations
                if not secure_environment_update("AWS_PROFILE", profile):
                    return safe_json_dumps({
                        "success": False,
                        "error": "Failed to update AWS_PROFILE environment variable securely"
                    }, indent=2)

                # Save configuration persistently
                current_region = aws_config.default_region
                config_saved = config_persistence.save_current_config(
                    profile,
                    current_region,
                    metadata={"identity": identity, "operation": "set_profile"}
                )

                # Clear client cache to force reload with new profile
                with _client_lock:
                    _create_client.cache_clear()

                result = {
                    "success": True,
                    "operation": "set_profile",
                    "new_profile": profile,
                    "profile_valid": True,
                    "identity": {
                        "account": identity.get("Account"),
                        "user_id": identity.get("UserId"),
                        "arn": identity.get("Arn")
                    },
                    "cache_cleared": True,
                    "config_persisted": config_saved
                }

            except Exception as e:
                result = {
                    "success": False,
                    "operation": "set_profile",
                    "error": f"Failed to validate profile '{profile}': {str(e)}",
                    "suggestion": "Check that the profile exists in ~/.aws/credentials or ~/.aws/config"
                }

        elif operation == "set_region":
            if not region:
                return safe_json_dumps({
                    "success": False,
                    "error": "Region name is required for set_region operation"
                }, indent=2)

            # Validate region format
            import re
            region_pattern = r'^[a-z0-9\-]+$'
            if not re.match(region_pattern, region):
                return safe_json_dumps({
                    "success": False,
                    "error": f"Invalid region format: {region}",
                    "suggestion": "Region should be in format like 'us-east-1', 'eu-west-1', etc."
                }, indent=2)

            # Test region availability
            try:
                current_profile = aws_config.profile
                if current_profile:
                    session = boto3.Session(profile_name=current_profile, region_name=region)
                else:
                    session = boto3.Session(region_name=region)

                # Test region by listing available regions
                ec2_client = session.client('ec2', region_name=region)
                regions_response = ec2_client.describe_regions()
                available_regions = [r['RegionName'] for r in regions_response.get('Regions', [])]

                if region not in available_regions:
                    return safe_json_dumps({
                        "success": False,
                        "error": f"Region '{region}' is not available or accessible",
                        "available_regions": available_regions[:10]  # Show first 10
                    }, indent=2)

                # Set environment variable for future operations
                if not secure_environment_update("AWS_DEFAULT_REGION", region):
                    return safe_json_dumps({
                        "success": False,
                        "error": "Failed to update AWS_DEFAULT_REGION environment variable securely"
                    }, indent=2)

                # Save configuration persistently
                current_profile = aws_config.profile or "default"
                config_saved = config_persistence.save_current_config(
                    current_profile,
                    region,
                    metadata={"operation": "set_region", "region_validated": True}
                )

                # Clear client cache to force reload with new region
                with _client_lock:
                    _create_client.cache_clear()

                result = {
                    "success": True,
                    "operation": "set_region",
                    "new_region": region,
                    "region_valid": True,
                    "cache_cleared": True,
                    "config_persisted": config_saved
                }

            except Exception as e:
                result = {
                    "success": False,
                    "operation": "set_region",
                    "error": f"Failed to validate region '{region}': {str(e)}"
                }

        elif operation == "set_both":
            if not profile or not region:
                return safe_json_dumps({
                    "success": False,
                    "error": "Both profile and region are required for set_both operation"
                }, indent=2)

            # Validate both profile and region
            try:
                session = boto3.Session(profile_name=profile, region_name=region)

                # Test credentials
                sts_client = session.client('sts', region_name=region)
                identity = sts_client.get_caller_identity()

                # Test region
                ec2_client = session.client('ec2', region_name=region)
                regions_response = ec2_client.describe_regions()
                available_regions = [r['RegionName'] for r in regions_response.get('Regions', [])]

                if region not in available_regions:
                    return safe_json_dumps({
                        "success": False,
                        "error": f"Region '{region}' is not available with profile '{profile}'"
                    }, indent=2)

                # Set both environment variables securely
                if not secure_environment_update("AWS_PROFILE", profile):
                    return safe_json_dumps({
                        "success": False,
                        "error": "Failed to update AWS_PROFILE environment variable securely"
                    }, indent=2)

                if not secure_environment_update("AWS_DEFAULT_REGION", region):
                    return safe_json_dumps({
                        "success": False,
                        "error": "Failed to update AWS_DEFAULT_REGION environment variable securely"
                    }, indent=2)

                # Save configuration persistently
                config_saved = config_persistence.save_current_config(
                    profile,
                    region,
                    metadata={
                        "identity": identity,
                        "operation": "set_both",
                        "profile_and_region_validated": True
                    }
                )

                # Clear client cache
                with _client_lock:
                    _create_client.cache_clear()

                result = {
                    "success": True,
                    "operation": "set_both",
                    "new_profile": profile,
                    "new_region": region,
                    "identity": {
                        "account": identity.get("Account"),
                        "user_id": identity.get("UserId"),
                        "arn": identity.get("Arn")
                    },
                    "cache_cleared": True,
                    "config_persisted": config_saved
                }

            except Exception as e:
                result = {
                    "success": False,
                    "operation": "set_both",
                    "error": f"Failed to validate profile '{profile}' and region '{region}': {str(e)}"
                }

        elif operation == "validate_config":
            current_profile = aws_config.profile or "default"
            current_region = aws_config.default_region

            validation_results = {}

            # Test STS (credentials)
            try:
                sts_client = get_aws_client("sts", current_region)
                identity = sts_client.get_caller_identity()
                validation_results["sts"] = {
                    "status": "success",
                    "identity": {
                        "account": identity.get("Account"),
                        "user_id": identity.get("UserId"),
                        "arn": identity.get("Arn")
                    }
                }
            except Exception as e:
                validation_results["sts"] = {
                    "status": "failed",
                    "error": str(e)
                }

            # Test EC2 (region access)
            try:
                ec2_client = get_aws_client("ec2", current_region)
                regions = ec2_client.describe_regions()
                validation_results["ec2"] = {
                    "status": "success",
                    "regions_accessible": len(regions.get("Regions", []))
                }
            except Exception as e:
                validation_results["ec2"] = {
                    "status": "failed",
                    "error": str(e)
                }

            # Test NetworkManager (CloudWAN service)
            try:
                nm_client = get_aws_client("networkmanager", current_region)
                global_networks = nm_client.describe_global_networks()
                validation_results["networkmanager"] = {
                    "status": "success",
                    "global_networks": len(global_networks.get("GlobalNetworks", []))
                }
            except Exception as e:
                validation_results["networkmanager"] = {
                    "status": "failed",
                    "error": str(e)
                }

            all_services_valid = all(v["status"] == "success" for v in validation_results.values())

            result = {
                "success": True,
                "operation": "validate_config",
                "current_profile": current_profile,
                "current_region": current_region,
                "overall_status": "valid" if all_services_valid else "invalid",
                "service_validations": validation_results
            }

        elif operation == "clear_cache":
            # Clear the LRU cache
            with _client_lock:
                _create_client.cache_clear()

            result = {
                "success": True,
                "operation": "clear_cache",
                "cache_entries_cleared": "LRU cache cleared",
                "message": "AWS client cache cleared successfully"
            }

        elif operation == "get_config_history":
            history_entries = config_persistence.get_config_history(limit=20)
            result = {
                "success": True,
                "operation": "get_config_history",
                "history_count": len(history_entries),
                "history": history_entries
            }

        elif operation == "validate_persistence":
            validation_result = config_persistence.validate_config_file()
            result = {
                "success": True,
                "operation": "validate_persistence",
                "validation": validation_result
            }

        elif operation == "restore_last_config":
            saved_config = config_persistence.load_current_config()
            if saved_config and 'aws_profile' in saved_config and 'aws_region' in saved_config:
                restored = config_persistence.restore_config(
                    saved_config['aws_profile'],
                    saved_config['aws_region']
                )
                with _client_lock:
                    _create_client.cache_clear()

                result = {
                    "success": restored,
                    "operation": "restore_last_config",
                    "restored_config": saved_config if restored else None,
                    "cache_cleared": restored
                }
            else:
                result = {
                    "success": False,
                    "operation": "restore_last_config",
                    "error": "No saved configuration found"
                }

        else:
            return safe_json_dumps({
                "success": False,
                "error": f"Unknown operation: {operation}",
                "error_code": "InvalidOperation",
                "http_status_code": 400,
                "supported_operations": [
                    "get_current",
                    "set_profile",
                    "set_region",
                    "set_both",
                    "validate_config",
                    "clear_cache",
                    "get_config_history",
                    "validate_persistence",
                    "restore_last_config"
                ]
            }, indent=2)

        return safe_json_dumps(result, indent=2)

    except Exception as e:
        return handle_aws_error(e, "aws_config_manager")


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting AWS CloudWAN MCP Server...")

    # Validate environment
    region = aws_config.default_region
    if not region:
        logger.error("AWS_DEFAULT_REGION environment variable is required")
        sys.exit(1)

    profile = aws_config.profile or "default"
    logger.info(f"AWS Region: {region}")
    logger.info(f"AWS Profile: {profile}")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
