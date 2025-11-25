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

"""Tests for cloudformation_pre_deploy_validation module."""

import json
from awslabs.aws_iac_mcp_server.tools.cloudformation_pre_deploy_validation import (
    cloudformation_pre_deploy_validation,
)


def test_cloudformation_pre_deploy_validation_returns_valid_json():
    """Test that cloudformation_pre_deploy_validation returns valid JSON."""
    result = cloudformation_pre_deploy_validation()
    parsed = json.loads(result)

    assert 'overview' in parsed
    assert 'validation_types' in parsed
    assert 'workflow' in parsed


def test_cloudformation_pre_deploy_validation_includes_required_fields():
    """Test that result includes all required instruction fields."""
    result = cloudformation_pre_deploy_validation()
    parsed = json.loads(result)

    assert 'validation_types' in parsed
    assert 'property_syntax' in parsed['validation_types']
    assert 'resource_name_conflict' in parsed['validation_types']
    assert 's3_bucket_emptiness' in parsed['validation_types']
    assert 'workflow' in parsed
    assert 'key_considerations' in parsed
