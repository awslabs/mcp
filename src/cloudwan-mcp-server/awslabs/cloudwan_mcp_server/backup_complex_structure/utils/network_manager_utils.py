"""
Utility functions for Network Manager operations.

This module provides utility functions for working with AWS Network Manager,
including endpoint management and client creation.
"""

import os
import logging
from typing import Optional, Tuple
import boto3

# Import NetworkManagerConfig if available
try:
    from ..config import NetworkManagerConfig

    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

logger = logging.getLogger(__name__)


def get_network_manager_endpoint(
    custom_endpoint: Optional[str] = None,
    region: Optional[str] = None,
    use_omega_endpoint: bool = True,
) -> Tuple[str, str]:
    """
    Get the appropriate Network Manager endpoint URL and region.

    This function determines the appropriate endpoint URL for Network Manager
    based on the provided parameters and environment variables, following this
    priority order:
    1. Custom endpoint provided as parameter
    2. Custom endpoint from environment variable
    3. Omega endpoint (if enabled) or standard endpoint with the provided region

    Args:
        custom_endpoint: Optional custom endpoint URL
        region: AWS region to use (defaults to us-west-2)
        use_omega_endpoint: Whether to use the omega endpoint format

    Returns:
        Tuple[str, str]: A tuple containing (endpoint_url, region)
    """
    effective_region = (
        region or os.environ.get("CLOUDWAN_AWS_NETWORK_MANAGER_REGION") or "us-west-2"
    )
    endpoint_url = None

    # Try using NetworkManagerConfig if available
    if HAS_CONFIG:
        try:
            # Initialize config with parameters and environment variables
            nm_config = NetworkManagerConfig(
                custom_endpoint=custom_endpoint,
                region=effective_region,
                use_omega_endpoint=use_omega_endpoint,
            )

            # Get endpoint URL and region from config
            endpoint_url = nm_config.get_endpoint_url()
            effective_region = nm_config.region

            logger.debug(f"Using endpoint from NetworkManagerConfig: {endpoint_url}")
            return endpoint_url, effective_region
        except Exception as e:
            logger.warning(f"Error using NetworkManagerConfig: {e}")

    # Fallback to direct endpoint construction
    # Check for custom endpoint parameter or environment variable
    if custom_endpoint:
        endpoint_url = custom_endpoint
    elif os.environ.get("CLOUDWAN_AWS_NETWORK_MANAGER_CUSTOM_ENDPOINT"):
        endpoint_url = os.environ.get("CLOUDWAN_AWS_NETWORK_MANAGER_CUSTOM_ENDPOINT")
    else:
        # Construct endpoint based on format and region
        if use_omega_endpoint:
            endpoint_url = f"https://networkmanageromega.{effective_region}.amazonaws.com"
        else:
            endpoint_url = f"https://networkmanager.{effective_region}.amazonaws.com"

    logger.debug(f"Using Network Manager endpoint: {endpoint_url} with region {effective_region}")
    return endpoint_url, effective_region


def create_network_manager_client(
    profile_name: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    use_omega_endpoint: bool = True,
    set_env_vars: bool = True,
) -> boto3.client:
    """
    Create a boto3 client for Network Manager with the appropriate endpoint.

    This function creates a boto3 client for Network Manager with the appropriate
    endpoint URL and region, and optionally sets the environment variables for
    future boto3 clients.

    Args:
        profile_name: AWS profile to use for authentication
        region: AWS region to use (defaults to us-west-2)
        endpoint_url: Optional custom endpoint URL
        use_omega_endpoint: Whether to use the omega endpoint format
        set_env_vars: Whether to set environment variables for AWS_ENDPOINT_URL_NETWORKMANAGER
                      and AWS_DEFAULT_REGION

    Returns:
        boto3.client: Network Manager client
    """
    # Get endpoint URL and region
    endpoint_url, effective_region = get_network_manager_endpoint(
        custom_endpoint=endpoint_url,
        region=region,
        use_omega_endpoint=use_omega_endpoint,
    )

    # Set environment variables if requested
    if set_env_vars:
        os.environ["AWS_ENDPOINT_URL_NETWORKMANAGER"] = endpoint_url
        os.environ["AWS_DEFAULT_REGION"] = effective_region
        logger.debug(f"Set AWS_ENDPOINT_URL_NETWORKMANAGER={endpoint_url}")
        logger.debug(f"Set AWS_DEFAULT_REGION={effective_region}")

    # Create session with profile
    session = boto3.Session(profile_name=profile_name)

    # Create client with endpoint URL and region
    client = session.client(
        "networkmanager", region_name=effective_region, endpoint_url=endpoint_url
    )

    logger.info(
        f"Created Network Manager client in {effective_region} with endpoint {endpoint_url}"
    )
    return client
