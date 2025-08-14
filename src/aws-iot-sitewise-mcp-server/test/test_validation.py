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

"""Tests for AWS IoT SiteWise Validation Functions."""

import os
import sys
from datetime import datetime
from unittest.mock import Mock

import pytest

# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))

from awslabs.aws_iot_sitewise_mcp_server.validation import (
    ValidationError,
    validate_access_policy_permission,
    validate_aggregate_types,
    validate_asset_id,
    validate_asset_model_id,
    validate_asset_model_properties,
    validate_asset_name,
    validate_batch_entries,
    validate_data_type,
    validate_encryption_type,
    validate_gateway_platform,
    validate_max_results,
    validate_property_alias,
    validate_quality,
    validate_region,
    validate_service_quotas,
    validate_storage_type,
    validate_time_ordering,
    validate_timestamp,
)


class TestValidation:
    """Test cases for validation functions."""

    def test_validate_asset_id_valid(self):
        """Test valid asset ID validation."""
        # Should not raise any exception
        validate_asset_id("test-asset-123")
        validate_asset_id("asset_456")

    def test_validate_asset_id_invalid(self):
        """Test invalid asset ID validation."""
        with pytest.raises(ValidationError, match="Asset ID cannot be empty"):
            validate_asset_id("")

        with pytest.raises(ValidationError, match="Asset ID cannot exceed 36 characters"):
            validate_asset_id("a" * 37)

        with pytest.raises(ValidationError, match="Asset ID contains invalid characters"):
            validate_asset_id("invalid@asset!")

    def test_validate_asset_model_id_valid(self):
        """Test valid asset model ID validation."""
        validate_asset_model_id("test-model-123")
        validate_asset_model_id("model_456")

    def test_validate_asset_model_id_invalid(self):
        """Test invalid asset model ID validation."""
        with pytest.raises(ValidationError, match="Asset model ID cannot be empty"):
            validate_asset_model_id("")

        with pytest.raises(ValidationError, match="Asset model ID cannot exceed 36 characters"):
            validate_asset_model_id("a" * 37)

    def test_validate_asset_name_valid(self):
        """Test valid asset name validation."""
        validate_asset_name("Test Asset 123")
        validate_asset_name("Asset-Name_123.test")

    def test_validate_asset_name_invalid(self):
        """Test invalid asset name validation."""
        with pytest.raises(ValidationError, match="Asset name cannot be empty"):
            validate_asset_name("")

        with pytest.raises(ValidationError, match="Asset name cannot exceed 256 characters"):
            validate_asset_name("a" * 257)

        with pytest.raises(ValidationError, match="Asset name contains invalid characters"):
            validate_asset_name("invalid@asset!")

    def test_validate_property_alias_valid(self):
        """Test valid property alias validation."""
        validate_property_alias("/test/alias")
        validate_property_alias("/complex/path/to/property")

    def test_validate_property_alias_invalid(self):
        """Test invalid property alias validation."""
        with pytest.raises(ValidationError, match="Property alias cannot be empty"):
            validate_property_alias("")

        with pytest.raises(ValidationError, match="Property alias must start with '/'"):
            validate_property_alias("invalid-alias")

        with pytest.raises(ValidationError, match="Property alias cannot exceed 2048 characters"):
            validate_property_alias("/" + "a" * 2048)

    def test_validate_region_valid(self):
        """Test valid region validation."""
        validate_region("us-east-1")
        validate_region("eu-west-1")

    def test_validate_region_invalid(self):
        """Test invalid region validation."""
        with pytest.raises(ValidationError, match="Region cannot be empty"):
            validate_region("")

        with pytest.raises(ValidationError, match="Invalid AWS region format"):
            validate_region("INVALID_REGION!")

    def test_validate_max_results_valid(self):
        """Test valid max results validation."""
        validate_max_results(50)
        validate_max_results(1, min_val=1, max_val=250)

    def test_validate_max_results_invalid(self):
        """Test invalid max results validation."""
        with pytest.raises(ValidationError, match="Max results must be at least"):
            validate_max_results(0, min_val=1)

        with pytest.raises(ValidationError, match="Max results cannot exceed"):
            validate_max_results(300, max_val=250)

    def test_validate_timestamp_valid(self):
        """Test valid timestamp validation."""
        # Valid timestamps
        validate_timestamp("2023-01-01T00:00:00Z")
        validate_timestamp("2023-01-01T00:00:00+00:00")
        validate_timestamp(1640995200)  # Unix timestamp
        validate_timestamp(datetime.now())

    def test_validate_timestamp_invalid(self):
        """Test invalid timestamp validation."""
        with pytest.raises(ValidationError, match="Invalid timestamp format"):
            validate_timestamp("invalid-timestamp")

        with pytest.raises(ValidationError, match="Timestamp cannot be negative"):
            validate_timestamp(-1)

        with pytest.raises(ValidationError, match="Timestamp too large"):
            validate_timestamp(2147483648)  # Beyond 2038

    def test_validate_data_type_valid(self):
        """Test valid data type validation."""
        for data_type in ["STRING", "INTEGER", "DOUBLE", "BOOLEAN", "STRUCT"]:
            validate_data_type(data_type)

    def test_validate_data_type_invalid(self):
        """Test invalid data type validation."""
        with pytest.raises(ValidationError, match="Invalid data type"):
            validate_data_type("INVALID_TYPE")

    def test_validate_quality_valid(self):
        """Test valid quality validation."""
        for quality in ["GOOD", "BAD", "UNCERTAIN"]:
            validate_quality(quality)

    def test_validate_quality_invalid(self):
        """Test invalid quality validation."""
        with pytest.raises(ValidationError, match="Invalid quality"):
            validate_quality("INVALID_QUALITY")

    def test_validate_aggregate_types_valid(self):
        """Test valid aggregate types validation."""
        validate_aggregate_types(["AVERAGE", "COUNT"])
        validate_aggregate_types(["MAXIMUM", "MINIMUM", "SUM", "STANDARD_DEVIATION"])

    def test_validate_aggregate_types_invalid(self):
        """Test invalid aggregate types validation."""
        with pytest.raises(ValidationError, match="Invalid aggregate type"):
            validate_aggregate_types(["INVALID_TYPE"])

    def test_validate_time_ordering_valid(self):
        """Test valid time ordering validation."""
        validate_time_ordering("ASCENDING")
        validate_time_ordering("DESCENDING")

    def test_validate_time_ordering_invalid(self):
        """Test invalid time ordering validation."""
        with pytest.raises(ValidationError, match="Invalid time ordering"):
            validate_time_ordering("INVALID_ORDER")

    def test_validate_asset_model_properties_valid(self):
        """Test valid asset model properties validation."""
        valid_properties = [
            {
                "name": "Temperature",
                "dataType": "DOUBLE",
                "type": {"measurement": {}},
            }
        ]
        validate_asset_model_properties(valid_properties)

    def test_validate_asset_model_properties_invalid(self):
        """Test invalid asset model properties validation."""
        # Too many properties
        with pytest.raises(ValidationError, match="Cannot have more than 200 properties"):
            validate_asset_model_properties(
                [
                    {"name": f"prop{i}", "dataType": "DOUBLE", "type": {"measurement": {}}}
                    for i in range(201)
                ]
            )

        # Missing required fields
        with pytest.raises(ValidationError, match="Property must have a name"):
            validate_asset_model_properties([{"dataType": "DOUBLE", "type": {"measurement": {}}}])

        with pytest.raises(ValidationError, match="Property must have a dataType"):
            validate_asset_model_properties([{"name": "Temperature", "type": {"measurement": {}}}])

        with pytest.raises(ValidationError, match="Property must have a type"):
            validate_asset_model_properties([{"name": "Temperature", "dataType": "DOUBLE"}])

    def test_validate_batch_entries_valid(self):
        """Test valid batch entries validation."""
        entries = [{"entryId": "entry1"}, {"entryId": "entry2"}]
        validate_batch_entries(entries)

    def test_validate_batch_entries_invalid(self):
        """Test invalid batch entries validation."""
        with pytest.raises(ValidationError, match="Batch entries cannot be empty"):
            validate_batch_entries([])

        with pytest.raises(ValidationError, match="Cannot process more than"):
            validate_batch_entries([{"entryId": f"entry{i}"} for i in range(15)])

        with pytest.raises(ValidationError, match="Entry .* missing required 'entryId'"):
            validate_batch_entries([{"invalid": "entry"}])

    def test_validate_access_policy_permission_valid(self):
        """Test valid access policy permission validation."""
        for permission in ["ADMINISTRATOR", "VIEWER"]:
            validate_access_policy_permission(permission)

    def test_validate_access_policy_permission_invalid(self):
        """Test invalid access policy permission validation."""
        with pytest.raises(ValidationError, match="Invalid permission level"):
            validate_access_policy_permission("INVALID_PERMISSION")

    def test_validate_encryption_type_valid(self):
        """Test valid encryption type validation."""
        for enc_type in ["SITEWISE_DEFAULT_ENCRYPTION", "KMS_BASED_ENCRYPTION"]:
            validate_encryption_type(enc_type)

    def test_validate_encryption_type_invalid(self):
        """Test invalid encryption type validation."""
        with pytest.raises(ValidationError, match="Invalid encryption type"):
            validate_encryption_type("INVALID_TYPE")

    def test_validate_storage_type_valid(self):
        """Test valid storage type validation."""
        for storage_type in ["SITEWISE_DEFAULT_STORAGE", "MULTI_LAYER_STORAGE"]:
            validate_storage_type(storage_type)

    def test_validate_storage_type_invalid(self):
        """Test invalid storage type validation."""
        with pytest.raises(ValidationError, match="Invalid storage type"):
            validate_storage_type("INVALID_TYPE")

    def test_validate_gateway_platform_valid(self):
        """Test valid gateway platform validation."""
        validate_gateway_platform(
            {"greengrass": {"groupArn": "arn:aws:greengrass:us-east-1:<account-id>:group/test"}}
        )
        validate_gateway_platform({"greengrassV2": {"coreDeviceThingName": "test-device"}})

    def test_validate_gateway_platform_invalid(self):
        """Test invalid gateway platform validation."""
        with pytest.raises(ValidationError, match="Gateway platform configuration cannot be empty"):
            validate_gateway_platform({})

        with pytest.raises(ValidationError, match="Gateway platform must specify either"):
            validate_gateway_platform({"invalid": "config"})

        with pytest.raises(ValidationError, match="Greengrass configuration must include"):
            validate_gateway_platform({"greengrass": {}})

        with pytest.raises(ValidationError, match="Greengrass V2 configuration must include"):
            validate_gateway_platform({"greengrassV2": {}})

    def test_validate_service_quotas_valid(self):
        """Test valid service quotas validation."""
        # This would typically be tested with actual counts, but we can test the structure
        validate_service_quotas("create_asset", 0)  # Should not raise

        # In a real scenario, this would fail if the current count exceeds quota
        # validate_service_quotas("create_asset", 100001)  # Would raise ValidationError


if __name__ == "__main__":
    pytest.main([__file__])
