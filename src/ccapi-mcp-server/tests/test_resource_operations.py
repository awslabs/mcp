# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for resource operations module."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.impl.tools.resource_operations import (
    _validate_token_chain,
    check_readonly_mode,
    check_security_scanning,
    create_resource_impl,
    delete_resource_impl,
    get_resource_impl,
    get_resource_request_status_impl,
    update_resource_impl,
)
from awslabs.ccapi_mcp_server.models.models import (
    CreateResourceRequest,
    DeleteResourceRequest,
    GetResourceRequest,
    UpdateResourceRequest,
)
from unittest.mock import patch


class TestResourceOperations:
    """Test resource operations functions."""

    def setup_method(self):
        """Set up test context."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)

    def test_check_readonly_mode_normal(self):
        """Test check_readonly_mode with normal mode."""
        aws_session_data = {'readonly_mode': False}
        # Should not raise exception
        check_readonly_mode(aws_session_data)

    def test_check_readonly_mode_readonly(self):
        """Test check_readonly_mode with readonly mode."""
        aws_session_data = {'readonly_mode': True}
        with pytest.raises(ClientError):
            check_readonly_mode(aws_session_data)

    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    def test_check_security_scanning_enabled(self, mock_environ):
        """Test check_security_scanning when enabled."""
        mock_environ.get.return_value = 'enabled'
        enabled, warning = check_security_scanning()
        assert enabled is True
        assert warning is None

    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    def test_check_security_scanning_disabled(self, mock_environ):
        """Test check_security_scanning when disabled."""
        mock_environ.get.return_value = 'disabled'
        enabled, warning = check_security_scanning()
        assert enabled is False
        assert warning is not None

    def test_validate_token_chain_valid(self):
        """Test _validate_token_chain with valid tokens."""
        workflow_store = {
            'explained': {'type': 'explained_properties', 'data': {}},
            'security': {'type': 'security_scan', 'data': {}},
        }
        _validate_token_chain('explained', 'security', workflow_store)
        assert workflow_store['security']['parent_token'] == 'explained'

    def test_validate_token_chain_invalid_explained(self):
        """Test _validate_token_chain with invalid explained token."""
        workflow_store = {
            'explained': {'type': 'wrong_type', 'data': {}},
            'security': {'type': 'security_scan', 'data': {}},
        }
        with pytest.raises(ClientError):
            _validate_token_chain('explained', 'security', workflow_store)

    def test_validate_token_chain_invalid_security(self):
        """Test _validate_token_chain with invalid security token."""
        workflow_store = {
            'explained': {'type': 'explained_properties', 'data': {}},
            'security': {'type': 'wrong_type', 'data': {}},
        }
        with pytest.raises(ClientError):
            _validate_token_chain('explained', 'security', workflow_store)

    def test_validate_token_chain_missing_tokens(self):
        """Test _validate_token_chain with missing tokens."""
        workflow_store = {}
        with pytest.raises(ClientError):
            _validate_token_chain('missing', 'missing', workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    async def test_create_resource_impl_success(self, mock_environ, mock_client):
        """Test create_resource_impl success path."""
        mock_environ.get.return_value = 'disabled'
        mock_client.return_value.create_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
        ) as mock_progress:
            mock_progress.return_value = {'status': 'SUCCESS'}
            result = await create_resource_impl(request, workflow_store)
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_create_resource_impl_invalid_credentials(self):
        """Test create_resource_impl with invalid credentials."""
        workflow_store = {'creds': {'type': 'credentials', 'data': {'credentials_valid': False}}}

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError):
            await create_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_impl_success(self, mock_client):
        """Test get_resource_impl success path."""
        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {
                'Identifier': 'test-bucket',
                'Properties': '{"BucketName": "test-bucket"}',
            }
        }

        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            region='us-east-1',
            analyze_security=False,
        )

        result = await get_resource_impl(request)
        assert result['identifier'] == 'test-bucket'
        assert result['properties']['BucketName'] == 'test-bucket'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_request_status_impl_success(self, mock_client):
        """Test get_resource_request_status_impl success path."""
        mock_client.return_value.get_resource_request_status.return_value = {
            'ProgressEvent': {'Status': 'SUCCESS'}
        }

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
        ) as mock_progress:
            mock_progress.return_value = {'status': 'SUCCESS'}
            result = await get_resource_request_status_impl('test-token', 'us-east-1')
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_get_resource_request_status_impl_empty_token(self):
        """Test get_resource_request_status_impl with empty token."""
        with pytest.raises(ClientError):
            await get_resource_request_status_impl('', 'us-east-1')

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    async def test_update_resource_impl_success(self, mock_environ, mock_client):
        """Test update_resource_impl success path."""
        mock_environ.get.return_value = 'disabled'
        mock_client.return_value.update_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/BucketName', 'value': 'new-name'}],
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
        ) as mock_progress:
            with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.validate_patch'):
                mock_progress.return_value = {'status': 'SUCCESS'}
                result = await update_resource_impl(request, workflow_store)
                assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_update_resource_impl_empty_patch(self):
        """Test update_resource_impl with empty patch document."""
        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[],
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError):
            await update_resource_impl(request, {})

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_delete_resource_impl_success(self, mock_client):
        """Test delete_resource_impl success path."""
        mock_client.return_value.delete_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_delete',
                'data': {'test': 'value'},
                'operation': 'delete',
            },
        }

        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=True,
            region='us-east-1',
        )

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
        ) as mock_progress:
            mock_progress.return_value = {'status': 'SUCCESS'}
            result = await delete_resource_impl(request, workflow_store)
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_delete_resource_impl_not_confirmed(self):
        """Test delete_resource_impl without confirmation."""
        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=False,
            region='us-east-1',
        )

        with pytest.raises(ClientError):
            await delete_resource_impl(request, {})

    @pytest.mark.asyncio
    async def test_delete_resource_impl_wrong_operation(self):
        """Test delete_resource_impl with wrong operation token."""
        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_delete',
                'data': {'test': 'value'},
                'operation': 'create',
            },
        }

        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=True,
            region='us-east-1',
        )

        with pytest.raises(ClientError):
            await delete_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_impl_without_workflow_store(self, mock_client):
        """Test get_resource_impl without workflow store (no security analysis)."""
        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {
                'Identifier': 'test-bucket',
                'Properties': '{"BucketName": "test-bucket"}',
            }
        }

        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            analyze_security=True,
            region='us-east-1',
        )

        result = await get_resource_impl(request, {})
        # When workflow_store is empty dict, security analysis should fail and be included in result
        assert 'security_analysis' in result
        assert 'error' in result['security_analysis']
        assert result['identifier'] == 'test-bucket'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_impl_api_error(self, mock_client):
        """Test get_resource_impl with API error."""
        mock_client.return_value.get_resource.side_effect = Exception('API Error')

        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            region='us-east-1',
            analyze_security=False,
        )

        with pytest.raises(Exception):
            await get_resource_impl(request)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_impl_json_properties(self, mock_client):
        """Test get_resource_impl with JSON string properties."""
        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {
                'Identifier': 'test-bucket',
                'Properties': '{"BucketName": "test-bucket"}',
            }
        }

        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            region='us-east-1',
            analyze_security=False,
        )

        result = await get_resource_impl(request)
        assert result['properties']['BucketName'] == 'test-bucket'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_impl_dict_properties(self, mock_client):
        """Test get_resource_impl with dict properties."""
        mock_client.return_value.get_resource.return_value = {
            'ResourceDescription': {
                'Identifier': 'test-bucket',
                'Properties': {'BucketName': 'test-bucket'},
            }
        }

        request = GetResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            region='us-east-1',
            analyze_security=False,
        )

        result = await get_resource_impl(request)
        assert result['properties']['BucketName'] == 'test-bucket'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    async def test_create_resource_impl_security_disabled_no_skip(self, mock_environ):
        """Test create_resource_impl with security disabled but no skip flag."""
        mock_environ.get.return_value = 'disabled'

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError):
            await create_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    async def test_create_resource_impl_security_enabled_no_token(self, mock_environ):
        """Test create_resource_impl with security enabled but no token."""
        mock_environ.get.return_value = 'enabled'

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError):
            await create_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    async def test_update_resource_impl_security_enabled_no_token(self, mock_environ):
        """Test update_resource_impl with security enabled but no token."""
        mock_environ.get.return_value = 'enabled'

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError):
            await update_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ')
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_update_resource_impl_skip_security(self, mock_client, mock_environ):
        """Test update_resource_impl with skip security."""
        mock_environ.get.return_value = 'disabled'
        mock_client.return_value.update_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
        ) as mock_progress:
            with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.validate_patch'):
                mock_progress.return_value = {'status': 'SUCCESS'}
                result = await update_resource_impl(request, workflow_store)
                assert 'security_warning' in result

    @pytest.mark.asyncio
    async def test_update_resource_impl_readonly_mode_error(self):
        """Test update_resource_impl with readonly mode error message."""
        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': True},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError) as exc_info:
            await update_resource_impl(request, workflow_store)
        assert 'readonly mode' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_resource_impl_readonly_mode_error(self):
        """Test delete_resource_impl with readonly mode error message."""
        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': True},
            },
            'explained': {
                'type': 'explained_delete',
                'data': {'test': 'value'},
                'operation': 'delete',
            },
        }

        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=True,
            region='us-east-1',
        )

        with pytest.raises(ClientError) as exc_info:
            await delete_resource_impl(request, workflow_store)
        assert 'readonly mode' in str(exc_info.value)

    def test_validate_token_chain_missing_explained(self):
        """Test _validate_token_chain with missing explained token."""
        workflow_store = {'security': {'type': 'security_scan', 'data': {}}}

        with pytest.raises(ClientError):
            _validate_token_chain('missing', 'security', workflow_store)

    def test_validate_token_chain_missing_security(self):
        """Test _validate_token_chain with missing security token."""
        workflow_store = {'explained': {'type': 'explained_properties', 'data': {}}}

        with pytest.raises(ClientError):
            _validate_token_chain('explained', 'missing', workflow_store)

    def test_validate_token_chain_empty_tokens(self):
        """Test _validate_token_chain with empty tokens."""
        workflow_store = {}

        with pytest.raises(ClientError):
            _validate_token_chain('', 'security', workflow_store)

        with pytest.raises(ClientError):
            _validate_token_chain('explained', '', workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_create_resource_impl_with_security_token(self, mock_client):
        """Test create_resource_impl with security token validation."""
        mock_client.return_value.create_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
            'security': {'type': 'security_scan', 'data': {'passed': True}},
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            security_scan_token='security',
            region='us-east-1',
            skip_security_check=False,
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            with patch(
                'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
            ) as mock_progress:
                mock_env.get.return_value = 'enabled'
                mock_progress.return_value = {'status': 'SUCCESS'}
                result = await create_resource_impl(request, workflow_store)
                assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_update_resource_impl_with_security_enabled(self, mock_client):
        """Test update_resource_impl with security enabled and valid token."""
        mock_client.return_value.update_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
            'security': {'type': 'security_scan', 'data': {'passed': True}},
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            security_scan_token='security',
            region='us-east-1',
            skip_security_check=False,
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            with patch(
                'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
            ) as mock_progress:
                with patch(
                    'awslabs.ccapi_mcp_server.impl.tools.resource_operations.validate_patch'
                ):
                    mock_env.get.return_value = 'enabled'
                    mock_progress.return_value = {'status': 'SUCCESS'}
                    result = await update_resource_impl(request, workflow_store)
                    assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_create_resource_impl_api_error(self, mock_client):
        """Test create_resource_impl with API error."""
        mock_client.return_value.create_resource.side_effect = Exception('API Error')

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            mock_env.get.return_value = 'disabled'
            with pytest.raises(Exception):
                await create_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_update_resource_impl_api_error(self, mock_client):
        """Test update_resource_impl with API error."""
        mock_client.return_value.update_resource.side_effect = Exception('API Error')

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.validate_patch'):
                mock_env.get.return_value = 'disabled'
                with pytest.raises(Exception):
                    await update_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_delete_resource_impl_api_error(self, mock_client):
        """Test delete_resource_impl with API error."""
        mock_client.return_value.delete_resource.side_effect = Exception('API Error')

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_delete',
                'data': {'test': 'value'},
                'operation': 'delete',
            },
        }

        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=True,
            region='us-east-1',
        )

        with pytest.raises(Exception):
            await delete_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_get_resource_request_status_impl_api_error(self, mock_client):
        """Test get_resource_request_status_impl with API error."""
        mock_client.return_value.get_resource_request_status.side_effect = Exception('API Error')

        with pytest.raises(Exception):
            await get_resource_request_status_impl('test-token', 'us-east-1')

    def test_check_security_scanning_edge_cases(self):
        """Test check_security_scanning function."""
        enabled, warning = check_security_scanning()
        assert isinstance(enabled, bool)
        assert warning is None or isinstance(warning, str)

    def test_check_readonly_mode_context(self):
        """Test check_readonly_mode with Context.readonly_mode()."""
        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.Context'
        ) as mock_context:
            mock_context.readonly_mode.return_value = True

            with pytest.raises(ClientError):
                check_readonly_mode({'readonly_mode': False})

    @pytest.mark.asyncio
    @patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.get_aws_client')
    async def test_update_resource_impl_security_disabled_workflow(self, mock_client):
        """Test update_resource_impl with security disabled workflow path."""
        mock_client.return_value.update_resource.return_value = {
            'ProgressEvent': {'OperationStatus': 'SUCCESS'}
        }

        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            with patch(
                'awslabs.ccapi_mcp_server.impl.tools.resource_operations.progress_event'
            ) as mock_progress:
                with patch(
                    'awslabs.ccapi_mcp_server.impl.tools.resource_operations.validate_patch'
                ):
                    mock_env.get.return_value = 'disabled'
                    mock_progress.return_value = {'status': 'SUCCESS'}
                    result = await update_resource_impl(request, workflow_store)
                    assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_update_resource_impl_security_enabled_workflow(self):
        """Test update_resource_impl with security enabled workflow path."""
        workflow_store = {
            'creds': {
                'type': 'credentials',
                'data': {'credentials_valid': True, 'readonly_mode': False},
            },
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            mock_env.get.return_value = 'enabled'
            with pytest.raises(ClientError) as exc_info:
                await update_resource_impl(request, workflow_store)
            assert 'Security scan token required' in str(exc_info.value)

    def test_check_readonly_mode_with_context(self):
        """Test check_readonly_mode when Context.readonly_mode() returns True."""
        with patch(
            'awslabs.ccapi_mcp_server.impl.tools.resource_operations.Context.readonly_mode',
            return_value=True,
        ):
            with pytest.raises(ClientError):
                check_readonly_mode({'readonly_mode': False})

    @pytest.mark.asyncio
    async def test_create_resource_impl_invalid_credentials_line_87(self):
        """Test create_resource_impl with invalid credentials (line 87)."""
        workflow_store = {
            'creds': {'type': 'credentials', 'data': {'credentials_valid': False}},
            'explained': {
                'type': 'explained_properties',
                'data': {'properties': {'test': 'value'}},
            },
        }

        request = CreateResourceRequest(
            resource_type='AWS::S3::Bucket',
            credentials_token='creds',
            explained_token='explained',
            skip_security_check=True,
            region='us-east-1',
        )

        with patch('awslabs.ccapi_mcp_server.impl.tools.resource_operations.environ') as mock_env:
            mock_env.get.return_value = 'disabled'
            with pytest.raises(ClientError, match='Invalid AWS credentials'):
                await create_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    async def test_update_resource_impl_invalid_credentials_line_129(self):
        """Test update_resource_impl with invalid credentials (line 129)."""
        workflow_store = {'creds': {'type': 'credentials', 'data': {'credentials_valid': False}}}

        request = UpdateResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            patch_document=[{'op': 'replace', 'path': '/test', 'value': 'new'}],
            credentials_token='creds',
            explained_token='explained',
            region='us-east-1',
            skip_security_check=False,
        )

        with pytest.raises(ClientError, match='Invalid AWS credentials'):
            await update_resource_impl(request, workflow_store)

    @pytest.mark.asyncio
    async def test_delete_resource_impl_invalid_credentials_line_198(self):
        """Test delete_resource_impl with invalid credentials (line 198)."""
        workflow_store = {
            'creds': {'type': 'credentials', 'data': {'credentials_valid': False}},
            'explained': {
                'type': 'explained_delete',
                'data': {'test': 'value'},
                'operation': 'delete',
            },
        }

        request = DeleteResourceRequest(
            resource_type='AWS::S3::Bucket',
            identifier='test-bucket',
            credentials_token='creds',
            explained_token='explained',
            confirmed=True,
            region='us-east-1',
        )

        with pytest.raises(ClientError, match='Invalid AWS credentials'):
            await delete_resource_impl(request, workflow_store)
