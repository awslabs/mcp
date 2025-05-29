# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# ruff: noqa: D101, D102, D103
"""Tests for the data models."""

import pytest
from awslabs.eks_mcp_server.models import (
    ApplyYamlResponse,
)
from mcp.types import TextContent
from pydantic import ValidationError
from typing import Any, cast


class TestApplyYamlResponse:
    """Tests for the ApplyYamlResponse model."""

    def test_apply_yaml_response_success(self):
        """Test creating a successful ApplyYamlResponse."""
        response = ApplyYamlResponse(
            isError=False,
            content=[TextContent(type='text', text='Successfully applied all resources')],
            force_applied=False,
            resources_created=1,
            resources_updated=0,
        )

        assert response.isError is False
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Successfully applied all resources'

    def test_apply_yaml_response_error(self):
        """Test creating an error ApplyYamlResponse."""
        response = ApplyYamlResponse(
            isError=True,
            content=[TextContent(type='text', text='Failed to apply YAML')],
            force_applied=False,
            resources_created=0,
            resources_updated=0,
        )

        assert response.isError is True
        assert len(response.content) == 1
        assert response.content[0].type == 'text'
        assert response.content[0].text == 'Failed to apply YAML'

    def test_apply_yaml_response_missing_required_fields(self):
        """Test that ValidationError is raised when required fields are missing."""
        # Using cast to bypass type checking for the test
        # We're intentionally passing an invalid value to test validation
        with pytest.raises(ValidationError):
            ApplyYamlResponse(
                isError=False,
                content=cast(Any, None),  # Using cast to bypass type checking
                force_applied=False,
                resources_created=0,
                resources_updated=0,
            )


# FailedResource tests removed as the class is no longer used
# ResourceConditionResponse tests removed as the class is no longer used
