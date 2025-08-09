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

"""Unit tests for AWS configuration manager utilities."""

import json
import os
import pytest
from unittest.mock import patch

from awslabs.cloudwan_mcp_server.utils.aws_config_manager import (
    AWSConfigManager,
    get_aws_config,
    safe_json_dumps
)


class TestAWSConfigManager:
    """Test AWS configuration manager utilities."""

    def test_aws_config_manager_init(self):
        """Test AWSConfigManager initialization."""
        config = AWSConfigManager()
        assert config is not None

    @patch.dict(os.environ, {"AWS_PROFILE": "test-profile"})
    def test_profile_property(self):
        """Test profile property retrieves from environment."""
        config = AWSConfigManager()
        assert config.profile == "test-profile"

    @patch.dict(os.environ, {}, clear=True)
    def test_profile_property_none(self):
        """Test profile property returns None when not set."""
        config = AWSConfigManager()
        assert config.profile is None

    @patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-west-2"})
    def test_default_region_property(self):
        """Test default_region property retrieves from environment."""
        config = AWSConfigManager()
        assert config.default_region == "us-west-2"

    @patch.dict(os.environ, {}, clear=True)
    def test_default_region_property_default(self):
        """Test default_region property returns default when not set."""
        config = AWSConfigManager()
        assert config.default_region == "us-east-1"

    def test_get_aws_config_singleton(self):
        """Test get_aws_config returns singleton instance."""
        # Clear any existing instance
        import awslabs.cloudwan_mcp_server.utils.aws_config_manager as module
        if hasattr(module, '_aws_config_instance'):
            delattr(module, '_aws_config_instance')
        
        config1 = get_aws_config()
        config2 = get_aws_config()
        assert config1 is config2

    def test_get_aws_config_type(self):
        """Test get_aws_config returns correct type."""
        config = get_aws_config()
        assert isinstance(config, AWSConfigManager)

    def test_safe_json_dumps_normal(self):
        """Test safe_json_dumps with normal data."""
        data = {"key": "value", "number": 42}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_safe_json_dumps_with_datetime(self):
        """Test safe_json_dumps with datetime objects."""
        from datetime import datetime
        data = {"timestamp": datetime(2023, 1, 1, 12, 0, 0)}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert "2023-01-01" in parsed["timestamp"]

    def test_safe_json_dumps_error_handling(self):
        """Test safe_json_dumps error handling with circular references."""
        # Create circular reference
        data = {}
        data["self"] = data
        
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "JSON serialization failed" in parsed["error"]

    def test_safe_json_dumps_custom_indent(self):
        """Test safe_json_dumps with custom indent."""
        data = {"key": "value"}
        result = safe_json_dumps(data, indent=4)
        assert "    " in result  # 4-space indentation

    @patch.dict(os.environ, {"AWS_PROFILE": "prod", "AWS_DEFAULT_REGION": "eu-west-1"})
    def test_integration_full_config(self):
        """Test integration with both environment variables set."""
        config = get_aws_config()
        assert config.profile == "prod"
        assert config.default_region == "eu-west-1"

    def test_module_exports(self):
        """Test that all expected symbols are exported."""
        import awslabs.cloudwan_mcp_server.utils.aws_config_manager as module
        
        expected_exports = ['AWSConfigManager', 'get_aws_config', 'safe_json_dumps']
        for export in expected_exports:
            assert export in module.__all__
            assert hasattr(module, export)


class TestAWSConfigManagerEdgeCases:
    """Test edge cases for AWS configuration manager."""

    def test_empty_environment_variables(self):
        """Test behavior with empty (but set) environment variables."""
        with patch.dict(os.environ, {"AWS_PROFILE": "", "AWS_DEFAULT_REGION": ""}):
            config = AWSConfigManager()
            assert config.profile == ""
            assert config.default_region == ""

    def test_whitespace_environment_variables(self):
        """Test behavior with whitespace-only environment variables."""
        with patch.dict(os.environ, {"AWS_PROFILE": "  ", "AWS_DEFAULT_REGION": "  "}):
            config = AWSConfigManager()
            assert config.profile == "  "
            assert config.default_region == "  "

    def test_safe_json_dumps_large_data(self):
        """Test safe_json_dumps with large data structures."""
        data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert len(parsed["items"]) == 1000
        assert parsed["items"][999]["id"] == 999

    def test_safe_json_dumps_none_values(self):
        """Test safe_json_dumps with None values."""
        data = {"key": None, "other": "value"}
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["key"] is None
        assert parsed["other"] == "value"

    def test_multiple_config_instances_same_values(self):
        """Test multiple config instances return same environment values."""
        with patch.dict(os.environ, {"AWS_PROFILE": "test", "AWS_DEFAULT_REGION": "us-east-2"}):
            config1 = AWSConfigManager()
            config2 = AWSConfigManager()
            
            assert config1.profile == config2.profile
            assert config1.default_region == config2.default_region