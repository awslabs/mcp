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
# ruff: noqa: D101, D102, D103
"""Tests for the data models."""

from awslabs.eks_mcp_server.models import (
    ApplyYamlData,
)


class TestApplyYamlData:
    """Tests for the ApplyYamlData model."""

    def test_apply_yaml_data_success(self):
        """Test creating a successful ApplyYamlData."""
        data = ApplyYamlData(
            force_applied=False,
            resources_created=1,
            resources_updated=0,
        )

        assert data.force_applied is False
        assert data.resources_created == 1
        assert data.resources_updated == 0

    def test_apply_yaml_data_with_updates(self):
        """Test creating ApplyYamlData with updates."""
        data = ApplyYamlData(
            force_applied=True,
            resources_created=0,
            resources_updated=2,
        )

        assert data.force_applied is True
        assert data.resources_created == 0
        assert data.resources_updated == 2

    def test_apply_yaml_data_with_defaults(self):
        """Test that ApplyYamlData can be created with default values."""
        data = ApplyYamlData(force_applied=False, resources_created=0, resources_updated=0)
        assert data.force_applied is False
        assert data.resources_created == 0
        assert data.resources_updated == 0


# FailedResource tests removed as the class is no longer used
# ResourceConditionResponse tests removed as the class is no longer used
