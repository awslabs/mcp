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

"""Tests for failure_cases module."""

from awslabs.aws_iac_mcp_server.failure_cases import match_failure_case


class TestMatchFailureCase:
    """Test failure case matching logic."""

    def test_match_with_correct_resource_type(self):
        """Test matching with correct resource type."""
        result = match_failure_case(
            'The bucket you tried to delete is not empty', 'AWS::S3::Bucket', 'DELETE'
        )
        assert result is not None
        assert result['case_id'] == 'S3_BUCKET_NOT_EMPTY'

    def test_no_match_with_wrong_resource_type(self):
        """Test no match when resource type doesn't match."""
        result = match_failure_case(
            'The bucket you tried to delete is not empty',
            'AWS::EC2::Instance',  # Wrong resource type
            'DELETE',
        )
        assert result is None

    def test_no_match_with_wrong_operation(self):
        """Test no match when operation doesn't match."""
        result = match_failure_case(
            'The bucket you tried to delete is not empty',
            'AWS::S3::Bucket',
            'CREATE',  # Wrong operation
        )
        assert result is None

    def test_match_without_resource_type_filter(self):
        """Test matching without resource type filter."""
        result = match_failure_case(
            'The bucket you tried to delete is not empty',
            None,  # No resource type filter
            'DELETE',
        )
        assert result is not None
        assert result['case_id'] == 'S3_BUCKET_NOT_EMPTY'

    def test_match_without_operation_filter(self):
        """Test matching without operation filter."""
        result = match_failure_case(
            'The bucket you tried to delete is not empty',
            'AWS::S3::Bucket',
            None,  # No operation filter
        )
        assert result is not None
        assert result['case_id'] == 'S3_BUCKET_NOT_EMPTY'

    def test_no_match_for_unknown_error(self):
        """Test no match for unknown error pattern."""
        result = match_failure_case(
            'Some completely unknown error message', 'AWS::S3::Bucket', 'DELETE'
        )
        assert result is None
