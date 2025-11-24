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

"""Tests for compliance tool adapter."""

import json
import pytest
from awslabs.aws_iac_mcp_server.tools.compliance_tools import check_template_compliance


class TestComplianceTools:
    """Test compliance tool adapter."""

    def test_check_template_compliance_valid_input(self):
        """Test compliance tool with valid CloudFormation template."""
        template = """
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-test-bucket
"""
        result = check_template_compliance(template)
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should contain tool_response tags (from sanitizer)
        assert '<tool_response>' in result
        assert '</tool_response>' in result

    def test_check_template_compliance_invalid_input(self):
        """Test compliance tool with invalid input (empty template)."""
        result = check_template_compliance("")
        
        # Result should be a string
        assert isinstance(result, str)
        
        # Should contain error message
        assert 'Invalid request' in result or 'error' in result.lower()
