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

"""Tests for the models module."""

import pytest
from awslabs.prometheus_mcp_server.models import MetricsList, ServerInfo


class TestModels:
    """Tests for the models defined in the models module."""

    def test_metrics_list(self):
        """Test that MetricsList model works correctly."""
        # Test with empty list
        metrics = MetricsList(metrics=[])
        assert metrics.metrics == []
        assert metrics.model_dump() == {"metrics": []}

        # Check that JSON contains expected values
        json_str = metrics.model_dump_json()
        assert "metrics" in json_str
        assert "[]" in json_str

        # Test with populated list
        metrics = MetricsList(metrics=["metric1", "metric2", "metric3"])
        assert metrics.metrics == ["metric1", "metric2", "metric3"]
        assert metrics.model_dump() == {"metrics": ["metric1", "metric2", "metric3"]}

        # Check that JSON contains expected values
        json_str = metrics.model_dump_json()
        assert "metric1" in json_str
        assert "metric2" in json_str
        assert "metric3" in json_str

    def test_server_info(self):
        """Test that ServerInfo model works correctly."""
        # Test with minimal values
        server_info = ServerInfo(
            prometheus_url="https://example.com",
            aws_region="us-east-1",
            aws_profile="default",
            service_name="aps",
        )
        assert server_info.prometheus_url == "https://example.com"
        assert server_info.aws_region == "us-east-1"
        assert server_info.aws_profile == "default"
        assert server_info.service_name == "aps"

        # Test dict representation
        info_dict = server_info.model_dump()
        assert info_dict["prometheus_url"] == "https://example.com"
        assert info_dict["aws_region"] == "us-east-1"
        assert info_dict["aws_profile"] == "default"
        assert info_dict["service_name"] == "aps"

        # Test JSON serialization
        json_str = server_info.model_dump_json()
        # Use a more robust check that handles the URL being at any position in the JSON
        import json
        json_data = json.loads(json_str)
        assert json_data["prometheus_url"] == "https://example.com"
        assert json_data["aws_region"] == "us-east-1"
        assert json_data["aws_profile"] == "default"
        assert json_data["service_name"] == "aps"