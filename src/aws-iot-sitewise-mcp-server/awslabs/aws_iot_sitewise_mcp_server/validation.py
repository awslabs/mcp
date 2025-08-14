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

"""AWS IoT SiteWise parameter validation utilities."""

import re
from datetime import datetime
from typing import Any, Dict, List, Union


class ValidationError(Exception):
    """Custom exception for parameter validation errors."""

    pass


def validate_asset_id(asset_id: str) -> None:
    """Validate asset ID format."""
    if not asset_id:
        raise ValidationError("Asset ID cannot be empty")
    if len(asset_id) > 36:
        raise ValidationError("Asset ID cannot exceed 36 characters")
    # Asset IDs are typically UUIDs or custom identifiers
    if not re.match(r"^[a-zA-Z0-9_-]+$", asset_id):
        raise ValidationError("Asset ID contains invalid characters")


def validate_asset_model_id(asset_model_id: str) -> None:
    """Validate asset model ID format."""
    if not asset_model_id:
        raise ValidationError("Asset model ID cannot be empty")
    if len(asset_model_id) > 36:
        raise ValidationError("Asset model ID cannot exceed 36 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", asset_model_id):
        raise ValidationError("Asset model ID contains invalid characters")


def validate_asset_name(asset_name: str) -> None:
    """Validate asset name format."""
    if not asset_name:
        raise ValidationError("Asset name cannot be empty")
    if len(asset_name) > 256:
        raise ValidationError("Asset name cannot exceed 256 characters")
    # Asset names have specific character restrictions
    if not re.match(r"^[a-zA-Z0-9_\-\s\.]+$", asset_name):
        raise ValidationError("Asset name contains invalid characters")


def validate_property_alias(property_alias: str) -> None:
    """Validate property alias format."""
    if not property_alias:
        raise ValidationError("Property alias cannot be empty")
    if len(property_alias) > 2048:
        raise ValidationError("Property alias cannot exceed 2048 characters")
    # Property aliases must start with '/'
    if not property_alias.startswith("/"):
        raise ValidationError("Property alias must start with '/'")
    # Validate alias path format
    if not re.match(r"^/[a-zA-Z0-9_\-/]+$", property_alias):
        raise ValidationError("Property alias contains invalid characters")


def validate_region(region: str) -> None:
    """Validate AWS region format."""
    if not region:
        raise ValidationError("Region cannot be empty")
    # AWS region format validation
    if not re.match(r"^[a-z0-9-]+$", region):
        raise ValidationError("Invalid AWS region format")
    # Common AWS regions (not exhaustive, but covers most cases)
    valid_regions = [
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-central-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-south-1",
        "ca-central-1",
        "sa-east-1",
    ]
    if region not in valid_regions:
        # Don't fail for unknown regions, just warn
        pass


def validate_max_results(max_results: int, min_val: int = 1, max_val: int = 250) -> None:
    """Validate max results parameter."""
    if max_results < min_val:
        raise ValidationError(f"Max results must be at least {min_val}")
    if max_results > max_val:
        raise ValidationError(f"Max results cannot exceed {max_val}")


def validate_timestamp(timestamp: Union[int, str, datetime]) -> None:
    """Validate timestamp format."""
    if isinstance(timestamp, str):
        try:
            # Try to parse ISO format
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("Invalid timestamp format. Use ISO 8601 format.")
    elif isinstance(timestamp, int):
        # Unix timestamp validation
        if timestamp < 0:
            raise ValidationError("Timestamp cannot be negative")
        if timestamp > 2147483647:  # Year 2038 problem
            raise ValidationError("Timestamp too large")


def validate_data_type(data_type: str) -> None:
    """Validate IoT SiteWise data type."""
    valid_types = ["STRING", "INTEGER", "DOUBLE", "BOOLEAN", "STRUCT"]
    if data_type not in valid_types:
        raise ValidationError(f"Invalid data type. Must be one of: {', '.join(valid_types)}")


def validate_quality(quality: str) -> None:
    """Validate data quality indicator."""
    valid_qualities = ["GOOD", "BAD", "UNCERTAIN"]
    if quality not in valid_qualities:
        raise ValidationError(f"Invalid quality. Must be one of: {', '.join(valid_qualities)}")


def validate_aggregate_types(aggregate_types: List[str]) -> None:
    """Validate aggregate types."""
    valid_types = ["AVERAGE", "COUNT", "MAXIMUM", "MINIMUM", "SUM", "STANDARD_DEVIATION"]
    for agg_type in aggregate_types:
        if agg_type not in valid_types:
            raise ValidationError(
                f"Invalid aggregate type: {agg_type}. Must be one of: {', '.join(valid_types)}"
            )


def validate_time_ordering(time_ordering: str) -> None:
    """Validate time ordering parameter."""
    valid_orderings = ["ASCENDING", "DESCENDING"]
    if time_ordering not in valid_orderings:
        raise ValidationError(
            f"Invalid time ordering. Must be one of: {', '.join(valid_orderings)}"
        )


def validate_asset_model_properties(properties: List[Dict[str, Any]]) -> None:
    """Validate asset model properties structure."""
    if len(properties) > 200:
        raise ValidationError("Cannot have more than 200 properties per asset model")

    for prop in properties:
        if "name" not in prop:
            raise ValidationError("Property must have a name")
        if "dataType" not in prop:
            raise ValidationError("Property must have a dataType")
        if "type" not in prop:
            raise ValidationError("Property must have a type")

        # Validate property name
        prop_name = prop["name"]
        if not prop_name or len(prop_name) > 256:
            raise ValidationError("Property name must be 1-256 characters")

        # Validate data type
        validate_data_type(prop["dataType"])

        # Validate property type structure
        prop_type = prop["type"]
        valid_prop_types = ["measurement", "attribute", "transform", "metric"]
        if not any(pt in prop_type for pt in valid_prop_types):
            raise ValidationError(
                f"Property type must contain one of: {', '.join(valid_prop_types)}"
            )


def validate_batch_entries(entries: List[Dict[str, Any]], max_entries: int = 10) -> None:
    """Validate batch operation entries."""
    if not entries:
        raise ValidationError("Batch entries cannot be empty")
    if len(entries) > max_entries:
        raise ValidationError(f"Cannot process more than {max_entries} entries in a single batch")

    for i, entry in enumerate(entries):
        if "entryId" not in entry:
            raise ValidationError(f"Entry {i} missing required 'entryId'")

        entry_id = entry["entryId"]
        if not entry_id or len(entry_id) > 64:
            raise ValidationError(f"Entry ID must be 1-64 characters: {entry_id}")


def validate_access_policy_permission(permission: str) -> None:
    """Validate access policy permission level."""
    valid_permissions = ["ADMINISTRATOR", "VIEWER"]
    if permission not in valid_permissions:
        raise ValidationError(
            f"Invalid permission level. Must be one of: {', '.join(valid_permissions)}"
        )


def validate_encryption_type(encryption_type: str) -> None:
    """Validate encryption type."""
    valid_types = ["SITEWISE_DEFAULT_ENCRYPTION", "KMS_BASED_ENCRYPTION"]
    if encryption_type not in valid_types:
        raise ValidationError(f"Invalid encryption type. Must be one of: {', '.join(valid_types)}")


def validate_storage_type(storage_type: str) -> None:
    """Validate storage type."""
    valid_types = ["SITEWISE_DEFAULT_STORAGE", "MULTI_LAYER_STORAGE"]
    if storage_type not in valid_types:
        raise ValidationError(f"Invalid storage type. Must be one of: {', '.join(valid_types)}")


def validate_gateway_platform(platform: Dict[str, Any]) -> None:
    """Validate gateway platform configuration."""
    if not platform:
        raise ValidationError("Gateway platform configuration cannot be empty")

    # Must have either greengrass or greengrassV2
    if "greengrass" not in platform and "greengrassV2" not in platform:
        raise ValidationError("Gateway platform must specify either 'greengrass' or 'greengrassV2'")

    # Validate Greengrass configuration
    if "greengrass" in platform:
        gg_config = platform["greengrass"]
        if "groupArn" not in gg_config:
            raise ValidationError("Greengrass configuration must include 'groupArn'")

    if "greengrassV2" in platform:
        gg2_config = platform["greengrassV2"]
        if "coreDeviceThingName" not in gg2_config:
            raise ValidationError("Greengrass V2 configuration must include 'coreDeviceThingName'")


# Service quota constants (as of 2024)
class SiteWiseQuotas:
    """AWS IoT SiteWise service quotas and limits."""

    MAX_ASSETS_PER_ACCOUNT = 100000
    MAX_ASSET_MODELS_PER_ACCOUNT = 10000
    MAX_PROPERTIES_PER_ASSET_MODEL = 200
    MAX_HIERARCHIES_PER_ASSET_MODEL = 10
    MAX_COMPOSITE_MODELS_PER_ASSET_MODEL = 10

    MAX_BATCH_PUT_ENTRIES = 10
    MAX_BATCH_GET_ENTRIES = 16
    MAX_PROPERTY_VALUES_PER_ENTRY = 10

    MAX_GATEWAYS_PER_ACCOUNT = 1000
    MAX_TIME_SERIES_PER_ACCOUNT = 1000000

    # API rate limits (requests per second)
    CONTROL_PLANE_RPS = 10
    DATA_PLANE_RPS = 1000
    QUERY_RPS = 10


def validate_service_quotas(operation: str, current_count: int = 0) -> None:
    """Validate against service quotas where applicable."""
    quotas = {
        "create_asset": SiteWiseQuotas.MAX_ASSETS_PER_ACCOUNT,
        "create_asset_model": SiteWiseQuotas.MAX_ASSET_MODELS_PER_ACCOUNT,
        "create_gateway": SiteWiseQuotas.MAX_GATEWAYS_PER_ACCOUNT,
    }

    if operation in quotas and current_count >= quotas[operation]:
        raise ValidationError(f"Service quota exceeded for {operation}: {quotas[operation]}")
