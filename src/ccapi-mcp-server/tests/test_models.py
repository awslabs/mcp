# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for models module."""

import pytest
from awslabs.ccapi_mcp_server.models.models import (
    CreateResourceRequest,
    DeleteResourceRequest,
    ExplainRequest,
    GenerateInfrastructureCodeRequest,
    GetResourceRequest,
    ResourceOperationResult,
    RunCheckovRequest,
    SecurityScanResult,
    UpdateResourceRequest,
)
from pydantic import ValidationError


class TestModels:
    """Test pydantic models."""

    def test_create_resource_request_valid(self):
        """Test CreateResourceRequest with valid data."""
        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds_token',
            explained_token='explained_token',
            region='us-east-1',
            skip_security_check=False,
        )
        assert request.resource_type == 'AWS::S3::Bucket'
        assert request.credentials_token == 'creds_token'
        assert request.explained_token == 'explained_token'

    def test_create_resource_request_missing_required(self):
        """Test CreateResourceRequest with missing required fields."""
        with pytest.raises(ValidationError):
            # Create with missing required field to trigger validation error
            data = {
                'region': 'us-east-1',
                'credentials_token': 'test_token',
                'explained_token': 'test_token',
                'skip_security_check': False,
                # Missing required 'resource_type' field
            }
            CreateResourceRequest(**data)

    def test_update_resource_request_valid(self):
        """Test UpdateResourceRequest with valid data."""
        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds_token',
            explained_token='explained_token',
            region='us-east-1',
            skip_security_check=False,
        )
        assert request.resource_type == 'AWS::S3::Bucket'
        assert request.identifier == 'test-bucket'

    def test_update_resource_request_with_patch_document(self):
        """Test UpdateResourceRequest with patch document."""
        patch_doc = [{'op': 'replace', 'path': '/BucketName', 'value': 'new-name'}]
        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=patch_doc,
            credentials_token='creds_token',
            explained_token='explained_token',
            region='us-east-1',
            skip_security_check=False,
        )
        assert request.patch_document == patch_doc

    def test_delete_resource_request_valid(self):
        """Test DeleteResourceRequest with valid data."""
        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds_token',
            explained_token='explained_token',
            confirmed=True,
            region='us-east-1',
        )
        assert request.confirmed is True

    def test_delete_resource_request_not_confirmed(self):
        """Test DeleteResourceRequest with confirmed=False."""
        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds_token',
            explained_token='explained_token',
            confirmed=False,
            region='us-east-1',
        )
        assert request.confirmed is False

    def test_get_resource_request_valid(self):
        """Test GetResourceRequest with valid data."""
        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            region='us-east-1',
            analyze_security=False,
        )
        assert request.resource_type == 'AWS::S3::Bucket'
        assert request.identifier == 'test-bucket'
        assert request.analyze_security is False

    def test_get_resource_request_with_security_analysis(self):
        """Test GetResourceRequest with security analysis enabled."""
        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            analyze_security=True,
            region='us-east-1',
        )
        assert request.analyze_security is True

    def test_generate_infrastructure_code_request_valid(self):
        """Test GenerateInfrastructureCodeRequest with valid data."""
        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket', credentials_token='creds_token', region='us-east-1'
        )
        assert request.resource_type == 'AWS::S3::Bucket'
        assert request.properties == {}

    def test_generate_infrastructure_code_request_with_properties(self):
        """Test GenerateInfrastructureCodeRequest with properties."""
        properties = {'BucketName': 'test-bucket'}
        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket',
            properties=properties,
            credentials_token='creds_token',
            region='us-east-1',
        )
        assert request.properties == properties

    def test_explain_request_with_content(self):
        """Test ExplainRequest with content."""
        content = {'test': 'data'}
        request = ExplainRequest(content=content)
        assert request.content == content
        assert request.generated_code_token == ''

    def test_explain_request_with_generated_code_token(self):
        """Test ExplainRequest with generated code token."""
        request = ExplainRequest(generated_code_token='test_token', content=None)
        assert request.generated_code_token == 'test_token'
        assert request.content is None

    def test_explain_request_with_operation(self):
        """Test ExplainRequest with operation."""
        request = ExplainRequest(content={'test': 'data'}, operation='create', format='detailed')
        assert request.operation == 'create'
        assert request.format == 'detailed'

    def test_run_checkov_request_valid(self):
        """Test RunCheckovRequest with valid data."""
        request = RunCheckovRequest(explained_token='test_token')
        assert request.explained_token == 'test_token'
        assert request.framework == 'cloudformation'

    def test_run_checkov_request_with_framework(self):
        """Test RunCheckovRequest with custom framework."""
        request = RunCheckovRequest(explained_token='test_token', framework='terraform')
        assert request.framework == 'terraform'

    def test_resource_operation_result_valid(self):
        """Test ResourceOperationResult with valid data."""
        result = ResourceOperationResult(
            status='SUCCESS',
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            is_complete=True,
            status_message='Operation completed successfully',
        )
        assert result.status == 'SUCCESS'
        assert result.status_message == 'Operation completed successfully'
        assert result.is_complete is True

    def test_resource_operation_result_with_error(self):
        """Test ResourceOperationResult with error."""
        result = ResourceOperationResult(
            status='FAILED',
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            is_complete=True,
            status_message='Operation failed',
        )
        assert result.status == 'FAILED'
        assert result.status_message == 'Operation failed'

    def test_security_scan_result_valid(self):
        """Test SecurityScanResult with valid data."""
        result = SecurityScanResult(
            scan_status='PASSED',
            resource_type='AWS::S3::Bucket',
            timestamp='2023-01-01T00:00:00Z',
            message='Security scan completed',
        )
        assert result.scan_status == 'PASSED'
        assert result.resource_type == 'AWS::S3::Bucket'
        assert result.message == 'Security scan completed'

    def test_security_scan_result_with_failed_checks(self):
        """Test SecurityScanResult with failed checks."""
        failed_checks = [{'check_id': 'CKV_1', 'check_name': 'Test check'}]
        result = SecurityScanResult(
            scan_status='FAILED',
            raw_failed_checks=failed_checks,
            resource_type='AWS::S3::Bucket',
            timestamp='2023-01-01T00:00:00Z',
            message='Security scan found issues',
        )
        assert result.scan_status == 'FAILED'
        assert len(result.raw_failed_checks) == 1
        assert result.raw_failed_checks[0]['check_id'] == 'CKV_1'
