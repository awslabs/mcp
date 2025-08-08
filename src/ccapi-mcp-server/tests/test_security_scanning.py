# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for security scanning module."""

import pytest
from awslabs.ccapi_mcp_server.impl.tools.security_scanning import (
    run_checkov_impl,
    run_security_analysis,
)
from awslabs.ccapi_mcp_server.models.models import RunCheckovRequest
from unittest.mock import MagicMock, patch


class TestSecurityScanning:
    """Test security scanning functions."""

    # Note: _check_checkov_installed tests are in test_checkov_install.py to avoid duplication

    @pytest.mark.asyncio
    async def test_run_security_analysis_success(self):
        """Test run_security_analysis success path."""
        result = await run_security_analysis('AWS::S3::Bucket', {'BucketName': 'test'})
        assert result['passed'] is True
        assert 'message' in result

    @pytest.mark.asyncio
    async def test_run_security_analysis_with_properties(self):
        """Test run_security_analysis with various properties."""
        properties = {
            'BucketName': 'test-bucket',
            'Tags': [{'Key': 'Environment', 'Value': 'test'}],
        }
        result = await run_security_analysis('AWS::S3::Bucket', properties)
        assert result['passed'] is True

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    async def test_run_checkov_impl_not_installed(self, mock_check):
        """Test run_checkov_impl when checkov is not installed."""
        mock_check.return_value = {
            'installed': False,
            'needs_user_action': True,
            'message': 'Checkov not installed',
        }

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert result['passed'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    async def test_run_checkov_impl_success(self, mock_temp, mock_run, mock_check):
        """Test run_checkov_impl success path."""
        mock_check.return_value = {'installed': True, 'needs_user_action': False}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": {"passed_checks": [{"id": "CKV_1"}], "failed_checks": []}, "summary": {"passed": 1, "failed": 0}}',
        )

        mock_file = MagicMock()
        mock_file.name = '/tmp/test.json'
        mock_temp.return_value.__enter__.return_value = mock_file

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert 'security_scan_token' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    async def test_run_checkov_impl_failed_checks(self, mock_temp, mock_run, mock_check):
        """Test run_checkov_impl with failed checks."""
        mock_check.return_value = {'installed': True, 'needs_user_action': False}
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='{"results": {"passed_checks": [], "failed_checks": [{"id": "CKV_1"}]}, "summary": {"passed": 0, "failed": 1}}',
        )

        mock_file = MagicMock()
        mock_file.name = '/tmp/test.json'
        mock_temp.return_value.__enter__.return_value = mock_file

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert 'security_scan_token' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    async def test_run_checkov_impl_json_error(self, mock_temp, mock_run, mock_check):
        """Test run_checkov_impl with JSON decode error."""
        mock_check.return_value = {'installed': True, 'needs_user_action': False}
        mock_run.return_value = MagicMock(returncode=1, stdout='invalid json')

        mock_file = MagicMock()
        mock_file.name = '/tmp/test.json'
        mock_temp.return_value.__enter__.return_value = mock_file

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert result['passed'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    async def test_run_checkov_impl_empty_stdout(self, mock_temp, mock_run, mock_check):
        """Test run_checkov_impl with empty stdout."""
        mock_check.return_value = {'installed': True, 'needs_user_action': False}
        mock_run.return_value = MagicMock(returncode=0, stdout='')

        mock_file = MagicMock()
        mock_file.name = '/tmp/test.json'
        mock_temp.return_value.__enter__.return_value = mock_file

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert 'scan_status' in result

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.security_scanning._check_checkov_installed')
    @patch('subprocess.run')
    async def test_run_checkov_impl_subprocess_error(self, mock_run, mock_check):
        """Test run_checkov_impl with subprocess error."""
        mock_check.return_value = {'installed': True, 'needs_user_action': False}
        mock_run.side_effect = Exception('Subprocess error')

        workflow_store = {
            'test_token': {
                'type': 'explained_properties',
                'data': {
                    'cloudformation_template': '{}',
                    'properties': {'Type': 'AWS::S3::Bucket'},
                },
            }
        }

        request = RunCheckovRequest(explained_token='test_token')
        result = await run_checkov_impl(request, workflow_store)
        assert result['passed'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_checkov_impl_invalid_token(self):
        """Test run_checkov_impl with invalid token."""
        request = RunCheckovRequest(explained_token='invalid')
        with pytest.raises(Exception):
            await run_checkov_impl(request, {})
