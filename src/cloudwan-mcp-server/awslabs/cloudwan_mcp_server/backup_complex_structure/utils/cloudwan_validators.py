"""
CloudWAN-specific validation utilities.

This module provides validation functions specifically for CloudWAN resources
and configuration parameters.
"""

import logging
import re
from typing import Any, List, Optional, Dict

logger = logging.getLogger(__name__)


class CloudWANValidator:
    """Validator class for CloudWAN-specific resources."""

    @staticmethod
    def validate_core_network_id(core_network_id: str) -> str:
        """
        Validate core network ID format.

        Args:
            core_network_id: The core network ID to validate

        Returns:
            The validated core network ID

        Raises:
            ValueError: If the core network ID format is invalid
        """
        # Core network ID pattern: core-network-<hex/digits>
        pattern = r"^core-network-[0-9a-f]{17}$"

        if not re.match(pattern, core_network_id):
            # Try alternative format (which might be used in some environments)
            alt_pattern = r"^core-network-\d+$"
            if not re.match(alt_pattern, core_network_id):
                raise ValueError(
                    f"Invalid core network ID format: '{core_network_id}'. "
                    f"Expected format: 'core-network-<17 char id>'"
                )
            else:
                # Log warning but accept the alternative format
                logger.warning(
                    f"Core network ID '{core_network_id}' uses non-standard format. "
                    f"Standard format is 'core-network-<17 hex characters>'."
                )

        return core_network_id

    @staticmethod
    def validate_policy_version_id(policy_version: Optional[str]) -> Optional[str]:
        """
        Validate policy version ID format.

        Args:
            policy_version: Policy version ID to validate or None for default (LIVE)

        Returns:
            Validated policy version ID or None

        Raises:
            ValueError: If the policy version ID format is invalid
        """
        if policy_version is None:
            return None

        # Policy versions are typically numeric but can have special values like "LATEST"
        if policy_version.upper() in ["LIVE", "LATEST"]:
            return policy_version.upper()

        # Check if it's a numeric version
        if not policy_version.isdigit():
            raise ValueError(
                f"Invalid policy version ID: '{policy_version}'. "
                f"Expected numeric ID or 'LIVE'/'LATEST'."
            )

        return policy_version

    @staticmethod
    def validate_attachment_requirements(
        requires_acceptance: bool, isolate_attachments: bool
    ) -> None:
        """
        Validate attachment requirements for compatibility.

        Args:
            requires_acceptance: Whether attachment requires acceptance
            isolate_attachments: Whether attachments should be isolated

        Raises:
            ValueError: If there's a conflict in attachment requirements
        """
        # Currently, AWS CloudWAN doesn't have conflicts between these settings,
        # but this function provides a hook for any future validation rules
        pass

    @staticmethod
    def validate_segment_name(name: str) -> str:
        """
        Validate CloudWAN segment name.

        Args:
            name: The segment name to validate

        Returns:
            The validated segment name

        Raises:
            ValueError: If the segment name format is invalid
        """
        # CloudWAN segment name rules:
        # 1. 1-256 characters
        # 2. Alphanumeric, hyphens, underscores allowed
        # 3. Cannot start/end with hyphen

        if not name:
            raise ValueError("Segment name cannot be empty")

        if len(name) > 256:
            raise ValueError(f"Segment name '{name}' exceeds 256 character limit")

        # Check for valid characters and pattern
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$"
        if not re.match(pattern, name):
            raise ValueError(
                f"Invalid segment name: '{name}'. "
                f"Segment names must contain only alphanumeric characters, "
                f"hyphens, and underscores, and cannot start or end with hyphens."
            )

        return name

    @staticmethod
    def validate_edge_locations(edge_locations: List[str]) -> List[str]:
        """
        Validate edge location names.

        Args:
            edge_locations: List of edge location names to validate

        Returns:
            The validated list of edge locations

        Raises:
            ValueError: If any edge location format is invalid
        """
        # Import only when needed to avoid circular imports
        from ...utils.validators import validate_aws_region

        validated_locations = []

        for location in edge_locations:
            try:
                # Edge locations are typically AWS regions
                validated_region = validate_aws_region(location)
                validated_locations.append(validated_region)
            except ValueError as e:
                raise ValueError(f"Invalid edge location: {location} - {str(e)}")

        return validated_locations

    @staticmethod
    def validate_attachment_type(attachment_type: str) -> str:
        """
        Validate CloudWAN attachment type.

        Args:
            attachment_type: The attachment type to validate

        Returns:
            The validated attachment type

        Raises:
            ValueError: If the attachment type is invalid
        """
        # List of valid CloudWAN attachment types
        valid_types = [
            "vpc",
            "tgw",
            "tgw-connect",
            "site-to-site-vpn",
            "connect",
            "direct-connect",
            "transit-gateway-attachment",
            "connect-peer",
        ]

        attachment_type = attachment_type.lower()

        # Check for common aliases and normalize
        type_aliases = {
            "vpc-attachment": "vpc",
            "transitgateway": "tgw",
            "transit-gateway": "tgw",
            "vpn": "site-to-site-vpn",
            "dx": "direct-connect",
            "directconnect": "direct-connect",
        }

        normalized_type = type_aliases.get(attachment_type, attachment_type)

        if normalized_type not in valid_types:
            raise ValueError(
                f"Invalid attachment type: '{attachment_type}'. "
                f"Valid types are: {', '.join(valid_types)}"
            )

        return normalized_type

    @staticmethod
    def validate_allow_filter(allow_filter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate segment allow filter configuration.

        Args:
            allow_filter: Allow filter configuration to validate

        Returns:
            The validated allow filter configuration

        Raises:
            ValueError: If the allow filter configuration is invalid
        """
        if not allow_filter:
            return {}

        if "types" not in allow_filter:
            return allow_filter

        # Validate each attachment type in the filter
        validated_types = []
        for attachment_type in allow_filter["types"]:
            try:
                validated_type = CloudWANValidator.validate_attachment_type(attachment_type)
                validated_types.append(validated_type)
            except ValueError as e:
                raise ValueError(f"Invalid allow filter type: {str(e)}")

        # Replace with validated types
        validated_filter = allow_filter.copy()
        validated_filter["types"] = validated_types

        return validated_filter
