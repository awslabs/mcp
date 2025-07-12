"""Tests to boost server.py coverage."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from unittest.mock import patch


class TestServerCoverage:
    """Tests to cover missing lines in server.py."""

    def setup_method(self):
        """Initialize context for each test."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)

    @pytest.mark.asyncio
    async def test_explain_no_content_or_token(self):
        """Test explain with neither content nor properties_token."""
        from awslabs.ccapi_mcp_server.server import explain

        with pytest.raises(
            ClientError, match="Either 'content' or 'properties_token' must be provided"
        ):
            await explain()

    @pytest.mark.asyncio
    async def test_explain_invalid_properties_token(self):
        """Test explain with invalid properties_token."""
        from awslabs.ccapi_mcp_server.server import explain

        with pytest.raises(ClientError, match='Invalid properties token'):
            await explain(properties_token='invalid-token')

    @pytest.mark.asyncio
    async def test_create_resource_invalid_execution_token(self):
        """Test create_resource with invalid execution_token."""
        from awslabs.ccapi_mcp_server.server import create_resource

        with pytest.raises(ClientError, match='Invalid execution token'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'region': 'us-east-1'},
                execution_token='invalid-token',
            )

    @pytest.mark.asyncio
    async def test_create_resource_not_explained(self):
        """Test create_resource with token not properly explained."""
        from awslabs.ccapi_mcp_server.server import _properties_store, create_resource

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': False}}

        with pytest.raises(ClientError, match='infrastructure was not properly explained'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'region': 'us-east-1'},
                execution_token=token,
            )

    @pytest.mark.asyncio
    async def test_update_resource_invalid_execution_token(self):
        """Test update_resource with invalid execution_token."""
        from awslabs.ccapi_mcp_server.server import update_resource

        with pytest.raises(ClientError, match='Invalid execution token'):
            await update_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                patch_document=[{'op': 'replace', 'path': '/Tags', 'value': []}],
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                execution_token='invalid-token',
            )

    @pytest.mark.asyncio
    async def test_delete_resource_invalid_execution_token(self):
        """Test delete_resource with invalid execution_token."""
        from awslabs.ccapi_mcp_server.server import delete_resource

        with pytest.raises(ClientError, match='Invalid execution token'):
            await delete_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                confirmed=True,
                execution_token='invalid-token',
            )

    @pytest.mark.asyncio
    async def test_delete_resource_wrong_operation(self):
        """Test delete_resource with token for wrong operation."""
        from awslabs.ccapi_mcp_server.server import _properties_store, delete_resource

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True, 'operation': 'create'}}

        with pytest.raises(ClientError, match='token was not generated for delete operation'):
            await delete_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                aws_session_info={'account_id': 'test', 'region': 'us-east-1'},
                confirmed=True,
                execution_token=token,
            )

    def test_checkov_not_installed(self):
        """Test _check_checkov_installed when checkov is not found."""
        import subprocess
        from awslabs.ccapi_mcp_server.server import _check_checkov_installed

        with patch('awslabs.ccapi_mcp_server.server.subprocess.run') as mock_run:
            # First call (checking if checkov exists) raises FileNotFoundError
            # Second call (trying to install) raises CalledProcessError
            mock_run.side_effect = [FileNotFoundError(), subprocess.CalledProcessError(1, 'pip')]

            result = _check_checkov_installed()
            assert not result['installed']
            assert result['needs_user_action']

    @pytest.mark.asyncio
    async def test_run_checkov_not_installed(self):
        """Test run_checkov when checkov is not installed."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': False,
                'message': 'Checkov not found',
                'needs_user_action': True,
            }

            result = await run_checkov(content='{}', file_type='json')
            assert not result['passed']
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_checkov_invalid_content(self):
        """Test run_checkov with invalid content."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': True,
                'message': 'OK',
                'needs_user_action': False,
            }

            # Test with object that can't be JSON serialized
            class BadObject:
                pass

            result = await run_checkov(content=BadObject(), file_type='json')
            assert not result['passed']
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_run_checkov_failed_checks(self):
        """Test run_checkov with failed security checks."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': True,
                'message': 'OK',
                'needs_user_action': False,
            }

            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 1
                mock_run.return_value.stdout = (
                    '{"results": {"failed_checks": [{"id": "CKV_1"}], "passed_checks": []}}'
                )

                result = await run_checkov(content='{}', file_type='json')
                assert not result['passed']
                assert 'failed_checks' in result

    @pytest.mark.asyncio
    async def test_run_checkov_error_exit_code(self):
        """Test run_checkov with error exit code."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': True,
                'message': 'OK',
                'needs_user_action': False,
            }

            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 2
                mock_run.return_value.stderr = 'Checkov error'

                result = await run_checkov(content='{}', file_type='json')
                assert not result['passed']
                assert 'error' in result

    def test_get_aws_profile_info_exception(self):
        """Test get_aws_profile_info with exception."""
        from awslabs.ccapi_mcp_server.server import get_aws_profile_info

        with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
            mock_client.side_effect = Exception('AWS error')

            result = get_aws_profile_info()
            assert 'error' in result
            assert 'AWS error' in result['error']

    @pytest.mark.asyncio
    async def test_get_aws_session_info_invalid_env_check(self):
        """Test get_aws_session_info with invalid env_check_result."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        with pytest.raises(ClientError, match='You must call check_environment_variables'):
            await get_aws_session_info(None)

    @pytest.mark.asyncio
    async def test_get_aws_session_info_not_configured(self):
        """Test get_aws_session_info with improperly configured environment."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        env_check = {'properly_configured': False, 'error': 'No credentials'}

        with pytest.raises(ClientError, match='No credentials'):
            await get_aws_session_info(env_check)

    @pytest.mark.asyncio
    async def test_get_aws_session_info_invalid_credentials(self):
        """Test get_aws_session_info with invalid credentials."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        env_check = {'properly_configured': True}

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            mock_check.return_value = {'valid': False, 'error': 'Invalid creds'}

            with pytest.raises(ClientError, match='Invalid creds'):
                await get_aws_session_info(env_check)

    def test_main_function(self):
        """Test main function with arguments."""
        from awslabs.ccapi_mcp_server.server import main

        with patch('sys.argv', ['server.py', '--readonly']):
            with patch('awslabs.ccapi_mcp_server.server.mcp.run') as mock_run:
                with patch('awslabs.ccapi_mcp_server.server.get_aws_profile_info') as mock_info:
                    mock_info.return_value = {
                        'profile': 'test-profile',
                        'account_id': '123456789012',
                        'region': 'us-east-1',
                    }

                    main()
                    mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_invalid_session(self):
        """Test generate_infrastructure_code with invalid AWS session."""
        from awslabs.ccapi_mcp_server.server import generate_infrastructure_code

        with pytest.raises(ClientError, match='Valid AWS credentials are required'):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket', aws_session_info={'credentials_valid': False}
            )

    @pytest.mark.asyncio
    async def test_create_resource_readonly_mode(self):
        """Test create_resource in readonly mode."""
        from awslabs.ccapi_mcp_server.context import Context
        from awslabs.ccapi_mcp_server.server import _properties_store, create_resource

        Context.initialize(True)

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True}}

        with pytest.raises(ClientError, match='read-only mode'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'readonly_mode': True},
                execution_token=token,
            )

    @pytest.mark.asyncio
    async def test_update_resource_readonly_mode(self):
        """Test update_resource in readonly mode."""
        from awslabs.ccapi_mcp_server.context import Context
        from awslabs.ccapi_mcp_server.server import _properties_store, update_resource

        Context.initialize(True)

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True}}

        with pytest.raises(ClientError, match='readonly mode'):
            await update_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                patch_document=[{'op': 'replace', 'path': '/Tags', 'value': []}],
                aws_session_info={
                    'account_id': 'test',
                    'region': 'us-east-1',
                    'readonly_mode': True,
                },
                execution_token=token,
            )

    @pytest.mark.asyncio
    async def test_delete_resource_readonly_mode(self):
        """Test delete_resource in readonly mode."""
        from awslabs.ccapi_mcp_server.context import Context
        from awslabs.ccapi_mcp_server.server import _properties_store, delete_resource

        Context.initialize(True)

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True, 'operation': 'delete'}}

        with pytest.raises(ClientError, match='readonly mode'):
            await delete_resource(
                resource_type='AWS::S3::Bucket',
                identifier='test-bucket',
                aws_session_info={
                    'account_id': 'test',
                    'region': 'us-east-1',
                    'readonly_mode': True,
                },
                confirmed=True,
                execution_token=token,
            )
