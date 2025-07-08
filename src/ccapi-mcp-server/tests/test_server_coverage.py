"""Additional tests to increase server.py coverage."""

import pytest
from unittest.mock import MagicMock, patch
from awslabs.ccapi_mcp_server.errors import ClientError


class TestServerCoverage:
    """Tests to increase server.py coverage."""

    def setup_method(self):
        """Initialize context for each test."""
        from awslabs.ccapi_mcp_server.context import Context
        Context.initialize(False)

    @pytest.mark.asyncio

    @pytest.mark.asyncio
    async def test_explain_tool_errors(self):
        """Test explain tool error conditions."""
        from awslabs.ccapi_mcp_server.server import explain

        # Test with invalid properties_token
        with pytest.raises(ClientError):
            await explain(properties_token='invalid_token')

        # Test with neither content nor properties_token
        with pytest.raises(ClientError):
            await explain()

    @pytest.mark.asyncio
    async def test_create_resource_comprehensive_paths(self):
        """Test create_resource with various execution paths."""
        from awslabs.ccapi_mcp_server.server import create_resource, _properties_store

        # Test with valid execution token and metadata
        _properties_store['valid_token'] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {'valid_token': {'explained': True, 'operation': 'create'}}

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.return_value.create_resource.return_value = {
                'ProgressEvent': {'OperationStatus': 'SUCCESS', 'TypeName': 'AWS::S3::Bucket', 'RequestToken': 'token'}
            }
            
            result = await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'account_id': 'test', 'readonly_mode': False},
                execution_token='valid_token'
            )
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_create_resource_metadata_validation(self):
        """Test create_resource metadata validation paths."""
        from awslabs.ccapi_mcp_server.server import create_resource, _properties_store

        # Test with execution token but no metadata
        _properties_store['no_metadata_token'] = {'BucketName': 'test'}
        
        with pytest.raises(ClientError, match='Invalid execution token'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'account_id': 'test'},
                execution_token='no_metadata_token'
            )

        # Test with metadata but not explained
        _properties_store['not_explained_token'] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {'not_explained_token': {'explained': False}}
        
        with pytest.raises(ClientError, match='not properly explained'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'account_id': 'test'},
                execution_token='not_explained_token'
            )

    @pytest.mark.asyncio
    async def test_update_resource_comprehensive_paths(self):
        """Test update_resource with various execution paths."""
        from awslabs.ccapi_mcp_server.server import update_resource, _properties_store

        # Test with valid execution token and metadata
        _properties_store['update_token'] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {'update_token': {'explained': True, 'operation': 'update'}}

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.return_value.update_resource.return_value = {
                'ProgressEvent': {'OperationStatus': 'SUCCESS', 'TypeName': 'AWS::S3::Bucket', 'RequestToken': 'token'}
            }
            
            result = await update_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                patch_document=[{'op': 'replace', 'path': '/Tags', 'value': []}],
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                execution_token='update_token'
            )
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_delete_resource_comprehensive_paths(self):
        """Test delete_resource with various execution paths."""
        from awslabs.ccapi_mcp_server.server import delete_resource, _properties_store

        # Test with valid execution token for delete operation
        _properties_store['delete_token'] = {'resource': 'data'}
        _properties_store['_metadata'] = {'delete_token': {'explained': True, 'operation': 'delete'}}

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.return_value.delete_resource.return_value = {
                'ProgressEvent': {'OperationStatus': 'SUCCESS', 'TypeName': 'AWS::S3::Bucket', 'RequestToken': 'token'}
            }
            
            result = await delete_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                confirmed=True,
                execution_token='delete_token'
            )
            assert result['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_delete_resource_wrong_operation_token(self):
        """Test delete_resource with token for wrong operation."""
        from awslabs.ccapi_mcp_server.server import delete_resource, _properties_store

        # Test with execution token for create operation (should fail for delete)
        _properties_store['create_token'] = {'resource': 'data'}
        _properties_store['_metadata'] = {'create_token': {'explained': True, 'operation': 'create'}}

        with pytest.raises(ClientError, match='token was not generated for delete operation'):
            await delete_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                confirmed=True,
                execution_token='create_token'
            )

    @pytest.mark.asyncio
    async def test_list_resources_pagination_error(self):
        """Test list_resources with pagination error."""
        from awslabs.ccapi_mcp_server.server import list_resources

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_paginator = MagicMock()
            # Make the iterator raise an exception
            mock_paginator.paginate.return_value = iter([Exception('Pagination error')])
            mock_client.return_value.get_paginator.return_value = mock_paginator

            with patch('awslabs.ccapi_mcp_server.server.handle_aws_api_error') as mock_handle:
                mock_handle.side_effect = ClientError('Handled pagination error')
                
                with pytest.raises(ClientError):
                    await list_resources(resource_type='AWS::S3::Bucket')

    @pytest.mark.asyncio
    async def test_get_resource_json_parsing(self):
        """Test get_resource with JSON parsing."""
        from awslabs.ccapi_mcp_server.server import get_resource

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.return_value.get_resource.return_value = {
                'ResourceDescription': {
                    'Identifier': 'test-bucket',
                    'Properties': '{"BucketName": "test-bucket", "Tags": []}'
                }
            }
            
            result = await get_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket'
            )
            assert result['identifier'] == 'test-bucket'
            assert 'properties' in result

    def test_main_function_paths(self):
        """Test main function execution paths."""
        import sys
        from awslabs.ccapi_mcp_server.server import main

        original_argv = sys.argv

        try:
            # Test with no arguments
            sys.argv = ['server.py']
            
            with patch('awslabs.ccapi_mcp_server.server.get_aws_profile_info') as mock_profile:
                with patch('awslabs.ccapi_mcp_server.server.mcp.run') as mock_run:
                    # Test path with profile
                    mock_profile.return_value = {
                        'profile': 'test-profile',
                        'account_id': '123456789012',
                        'region': 'us-east-1',
                        'using_env_vars': False
                    }
                    main()
                    mock_run.assert_called_once()

            # Test with --readonly flag
            sys.argv = ['server.py', '--readonly']
            
            with patch('awslabs.ccapi_mcp_server.server.get_aws_profile_info') as mock_profile:
                with patch('awslabs.ccapi_mcp_server.server.mcp.run') as mock_run:
                    mock_profile.return_value = {
                        'profile': '',
                        'account_id': 'Unknown',
                        'region': 'us-east-1',
                        'using_env_vars': True
                    }
                    main()
                    mock_run.assert_called_once()

        finally:
            sys.argv = original_argv

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_region_fallback(self):
        """Test generate_infrastructure_code region fallback logic."""
        from awslabs.ccapi_mcp_server.server import generate_infrastructure_code

        with patch('awslabs.ccapi_mcp_server.server.generate_infrastructure_code_impl') as mock_impl:
            mock_impl.return_value = {
                'properties': {'BucketName': 'test'},
                'cloudformation_template': {}
            }

            # Test region fallback: None -> session region -> default
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'region': 'us-west-2'},
                region=None
            )
            
            # Should use session region
            call_args = mock_impl.call_args[1]
            assert call_args['region'] == 'us-west-2'

            # Test fallback to default when both are None
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'region': None},
                region=None
            )
            
            # Should use default
            call_args = mock_impl.call_args[1]
            assert call_args['region'] == 'us-east-1'

    @pytest.mark.asyncio
    async def test_create_template_error_handling(self):
        """Test create_template error handling."""
        from awslabs.ccapi_mcp_server.server import create_template

        with patch('awslabs.ccapi_mcp_server.server.create_template_impl') as mock_impl:
            mock_impl.side_effect = Exception('Template creation failed')
            
            with pytest.raises(Exception):
                await create_template(template_name='test-template')

    def test_get_aws_profile_info_exception_path(self):
        """Test get_aws_profile_info exception handling."""
        from awslabs.ccapi_mcp_server.server import get_aws_profile_info

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.side_effect = Exception('AWS client error')
            
            result = get_aws_profile_info()
            assert 'error' in result
            assert 'AWS client error' in result['error']

    @pytest.mark.asyncio
    async def test_get_aws_session_info_arn_user_id_masking(self):
        """Test ARN and user ID masking in get_aws_session_info."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            # Test with long ARN and user ID
            mock_check.return_value = {
                'valid': True,
                'account_id': '123456789012',
                'region': 'us-east-1',
                'arn': 'arn:aws:iam::123456789012:user/very-long-user-name',
                'user_id': 'AIDACKCEVSQ6C2EXAMPLELONG',
                'credential_source': 'profile'
            }

            result = await get_aws_session_info({'properly_configured': True})
            
            # ARN should be masked (all but last 8 chars)
            assert result['arn'].endswith('ser-name')
            assert result['arn'].startswith('*')
            
            # User ID should be masked (all but last 4 chars)
            assert result['user_id'].endswith('LONG')
            assert result['user_id'].startswith('*')

            # Test with short ARN and user ID (no masking)
            mock_check.return_value.update({
                'arn': 'short',
                'user_id': 'abc'
            })

            result = await get_aws_session_info({'properly_configured': True})
            assert result['arn'] == 'short'
            assert result['user_id'] == 'abc'

    @pytest.mark.asyncio
    async def test_get_aws_session_info_env_vars_masking(self):
        """Test environment variable masking in get_aws_session_info."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            with patch('awslabs.ccapi_mcp_server.server.environ') as mock_environ:
                mock_check.return_value = {
                    'valid': True,
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'arn': 'arn:aws:iam::123456789012:user/test',
                    'user_id': 'AIDACKCEVSQ6C2EXAMPLE',
                    'credential_source': 'env'
                }

                # Test with long credentials
                mock_environ.get.side_effect = lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',
                    'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
                }.get(key, default)

                result = await get_aws_session_info({'properly_configured': True})
                
                assert result['using_env_vars'] is True
                assert 'masked_credentials' in result
                assert result['masked_credentials']['AWS_ACCESS_KEY_ID'].endswith('MPLE')
                assert result['masked_credentials']['AWS_SECRET_ACCESS_KEY'].endswith('EKEY')

                # Test with short credentials
                mock_environ.get.side_effect = lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'ABC',
                    'AWS_SECRET_ACCESS_KEY': 'XYZ'
                }.get(key, default)

                result = await get_aws_session_info({'properly_configured': True})
                assert result['masked_credentials']['AWS_ACCESS_KEY_ID'] == '****'
                assert result['masked_credentials']['AWS_SECRET_ACCESS_KEY'] == '****'