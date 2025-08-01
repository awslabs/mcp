# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for infrastructure generation module."""

import pytest
from awslabs.ccapi_mcp_server.impl.tools.infrastructure_generation import (
    generate_infrastructure_code_impl_wrapper,
)
from awslabs.ccapi_mcp_server.models.models import GenerateInfrastructureCodeRequest
from unittest.mock import patch


class TestInfrastructureGeneration:
    """Test infrastructure generation functions."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.ccapi_mcp_server.impl.tools.infrastructure_generation.generate_infrastructure_code_impl'
    )
    async def test_generate_infrastructure_code_impl_wrapper_success(self, mock_impl):
        """Test generate_infrastructure_code_impl_wrapper success path."""
        mock_impl.return_value = {
            'properties': {'BucketName': 'test-bucket'},
            'cloudformation_template': '{"Resources": {}}',
        }

        workflow_store = {
            'creds_token': {'type': 'credentials', 'data': {'credentials_valid': True}}
        }

        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket',
            properties={'BucketName': 'test-bucket'},
            credentials_token='creds_token',
            region='us-east-1',
        )

        result = await generate_infrastructure_code_impl_wrapper(request, workflow_store)

        assert 'generated_code_token' in result
        assert 'properties' in result
        assert result['properties']['BucketName'] == 'test-bucket'

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_impl_wrapper_invalid_credentials(self):
        """Test generate_infrastructure_code_impl_wrapper with invalid credentials."""
        workflow_store = {}

        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket', credentials_token='invalid_token', region='us-east-1'
        )

        with pytest.raises(Exception):
            await generate_infrastructure_code_impl_wrapper(request, workflow_store)

    @pytest.mark.asyncio
    @patch(
        'awslabs.ccapi_mcp_server.impl.tools.infrastructure_generation.generate_infrastructure_code_impl'
    )
    async def test_generate_infrastructure_code_impl_wrapper_with_identifier(self, mock_impl):
        """Test generate_infrastructure_code_impl_wrapper with identifier."""
        mock_impl.return_value = {
            'properties': {'BucketName': 'test-bucket'},
            'cloudformation_template': '{"Resources": {}}',
        }

        workflow_store = {
            'creds_token': {'type': 'credentials', 'data': {'credentials_valid': True}}
        }

        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds_token',
            region='us-east-1',
        )

        result = await generate_infrastructure_code_impl_wrapper(request, workflow_store)

        assert 'generated_code_token' in result
        assert 'properties' in result

    @pytest.mark.asyncio
    @patch(
        'awslabs.ccapi_mcp_server.impl.tools.infrastructure_generation.generate_infrastructure_code_impl'
    )
    async def test_generate_infrastructure_code_impl_wrapper_with_patch_document(self, mock_impl):
        """Test generate_infrastructure_code_impl_wrapper with patch document."""
        mock_impl.return_value = {
            'properties': {'BucketName': 'new-bucket'},
            'cloudformation_template': '{"Resources": {}}',
        }

        workflow_store = {
            'creds_token': {'type': 'credentials', 'data': {'credentials_valid': True}}
        }

        request = GenerateInfrastructureCodeRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/BucketName', 'value': 'new-bucket'}],
            credentials_token='creds_token',
            region='us-east-1',
        )

        result = await generate_infrastructure_code_impl_wrapper(request, workflow_store)

        assert 'generated_code_token' in result
        assert 'properties' in result
