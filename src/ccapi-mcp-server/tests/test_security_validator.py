"""Tests for security_validator.py module."""

import datetime
import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.security_validator import validate_security_check_result


class TestSecurityValidator:
    """Test security validation functions."""

    def test_validate_security_check_result_skip(self):
        """Test validation when security check is skipped."""
        # Should not raise any exception
        validate_security_check_result(None, 'AWS::S3::Bucket', skip_security_check=True)

    def test_validate_security_check_result_invalid_input(self):
        """Test validation with invalid security check result."""
        with pytest.raises(ClientError, match='You must call run_checkov'):
            validate_security_check_result(None, 'AWS::S3::Bucket')

        with pytest.raises(ClientError, match='You must call run_checkov'):
            validate_security_check_result('invalid', 'AWS::S3::Bucket')

    def test_validate_security_check_result_old_timestamp(self):
        """Test validation with old timestamp."""
        old_time = datetime.datetime.now() - datetime.timedelta(hours=2)
        security_result = {'passed': True, 'timestamp': old_time.isoformat()}

        with pytest.raises(ClientError, match='Security check is too old'):
            validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_invalid_timestamp(self):
        """Test validation with invalid timestamp format."""
        security_result = {'passed': True, 'timestamp': 'invalid-timestamp'}

        # Should not raise exception for invalid timestamp, just continue
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_wrong_resource_type(self):
        """Test validation with wrong resource type."""
        security_result = {'passed': True, 'resource_type': 'AWS::EC2::Instance'}

        with pytest.raises(
            ClientError, match='Security check was performed for AWS::EC2::Instance'
        ):
            validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_with_high_severity(self):
        """Test validation with failed checks containing high severity issues."""
        security_result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket encryption',
                    'check_id': 'CKV_AWS_145',
                    'severity': 'HIGH',
                    'description': 'S3 bucket should be encrypted',
                    'file_path': 'template.json',
                    'resource': 'aws_s3_bucket.example',
                }
            ],
        }

        with pytest.raises(ClientError, match='Security checks failed with high severity issues'):
            validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_with_critical_severity(self):
        """Test validation with failed checks containing critical severity issues."""
        security_result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket public access',
                    'check_id': 'CKV_AWS_53',
                    'severity': 'CRITICAL',
                    'description': 'S3 bucket should not allow public access',
                    'file_path': 'template.json',
                    'resource': 'aws_s3_bucket.example',
                }
            ],
        }

        with pytest.raises(ClientError, match='Security checks failed with high severity issues'):
            validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_low_severity(self):
        """Test validation with failed checks but only low severity."""
        security_result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket versioning',
                    'check_id': 'CKV_AWS_21',
                    'severity': 'LOW',
                    'description': 'S3 bucket should have versioning enabled',
                }
            ],
        }

        # Should not raise exception for low severity issues
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_passed(self):
        """Test validation with passed security checks."""
        security_result = {'passed': True, 'failed_checks': [], 'passed_checks': ['CKV_AWS_18']}

        # Should not raise any exception
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_recent_timestamp(self):
        """Test validation with recent timestamp."""
        recent_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        security_result = {'passed': True, 'timestamp': recent_time.isoformat()}

        # Should not raise any exception
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_no_resource_type_check(self):
        """Test validation when security result has no resource_type field."""
        security_result = {'passed': True, 'failed_checks': []}

        # Should not raise exception when resource_type is not in security_result
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_failed_no_checks(self):
        """Test validation with failed result but no failed_checks list."""
        security_result = {'passed': False}

        # Should not raise exception when no failed_checks list
        validate_security_check_result(security_result, 'AWS::S3::Bucket')

    def test_validate_security_check_result_missing_severity(self):
        """Test validation with failed checks missing severity field."""
        security_result = {
            'passed': False,
            'failed_checks': [
                {
                    'check_name': 'S3 bucket encryption',
                    'check_id': 'CKV_AWS_145',
                    'description': 'S3 bucket should be encrypted',
                }
            ],
        }

        # Should not raise exception when severity is missing
        validate_security_check_result(security_result, 'AWS::S3::Bucket')
