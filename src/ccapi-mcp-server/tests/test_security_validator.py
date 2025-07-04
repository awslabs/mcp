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
"""Tests for security_validator."""

import datetime
import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.security_validator import validate_security_check_result


class TestSecurityValidator:
    """Test security validator functions."""

    def test_validate_security_check_result_valid(self):
        """Test valid security check result."""
        result = {'passed': True, 'checkov_validation_token': 'test-token'}
        # Should not raise exception
        validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_invalid(self):
        """Test invalid security check result."""
        with pytest.raises(ClientError):
            validate_security_check_result({}, 'AWS::S3::Bucket')

    def test_validate_security_check_result_none(self):
        """Test None security check result."""
        with pytest.raises(ClientError):
            validate_security_check_result(None, 'AWS::S3::Bucket')

    def test_validate_security_check_result_skip_security_check(self):
        """Test skipping security check."""
        # Should not raise exception when skipping
        validate_security_check_result(None, 'AWS::S3::Bucket', skip_security_check=True)
        validate_security_check_result({}, 'AWS::S3::Bucket', skip_security_check=True)

    def test_validate_security_check_result_wrong_resource_type(self):
        """Test security check with wrong resource type."""
        result = {
            'passed': True,
            'resource_type': 'AWS::EC2::Instance',
            'checkov_validation_token': 'test-token',
        }
        with pytest.raises(
            ClientError, match='Security check was performed for AWS::EC2::Instance'
        ):
            validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_old_timestamp(self):
        """Test security check with old timestamp - lines 52-53."""
        old_time = datetime.datetime.now() - datetime.timedelta(hours=2)
        result = {
            'passed': True,
            'timestamp': old_time.isoformat(),
            'checkov_validation_token': 'test-token',
        }
        with pytest.raises(ClientError, match='Security check is too old'):
            validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_recent_timestamp(self):
        """Test security check with recent timestamp."""
        recent_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        result = {
            'passed': True,
            'timestamp': recent_time.isoformat() + 'Z',
            'checkov_validation_token': 'test-token',
        }
        # Should not raise exception
        validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_invalid_timestamp(self):
        """Test security check with invalid timestamp format."""
        result = {
            'passed': True,
            'timestamp': 'invalid-timestamp',
            'checkov_validation_token': 'test-token',
        }
        # Should not raise exception for invalid timestamp format
        validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_with_high_severity(self):
        """Test failed security check with high severity issues."""
        result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket should have encryption',
                    'check_id': 'CKV_AWS_145',
                    'severity': 'HIGH',
                    'description': 'S3 bucket should be encrypted',
                    'file_path': 'template.yaml',
                    'resource': 'MyBucket',
                }
            ],
            'checkov_validation_token': 'test-token',
        }
        with pytest.raises(ClientError, match='Security checks failed with high severity issues'):
            validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_with_critical_severity(self):
        """Test failed security check with critical severity issues."""
        result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket public access',
                    'check_id': 'CKV_AWS_53',
                    'severity': 'CRITICAL',
                    'description': 'S3 bucket should not allow public access',
                    'file_path': 'template.yaml',
                    'resource': 'MyBucket',
                }
            ],
            'checkov_validation_token': 'test-token',
        }
        with pytest.raises(ClientError, match='Security checks failed with high severity issues'):
            validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_with_low_severity(self):
        """Test failed security check with only low severity issues."""
        result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket versioning',
                    'check_id': 'CKV_AWS_21',
                    'severity': 'LOW',
                    'description': 'S3 bucket should have versioning enabled',
                    'file_path': 'template.yaml',
                    'resource': 'MyBucket',
                }
            ],
            'checkov_validation_token': 'test-token',
        }
        # Should not raise exception for low severity issues
        validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_no_checks(self):
        """Test failed security check with no failed_checks array."""
        result = {'passed': False, 'checkov_validation_token': 'test-token'}
        # Should not raise exception when no failed_checks
        validate_security_check_result(result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_empty_checks(self):
        """Test failed security check with empty failed_checks array."""
        result = {'passed': False, 'failed_checks': [], 'checkov_validation_token': 'test-token'}
        # Should not raise exception when failed_checks is empty
        validate_security_check_result(result, 'AWS::S3::Bucket')
