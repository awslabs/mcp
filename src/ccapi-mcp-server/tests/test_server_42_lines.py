"""Tests to cover the 42 missing lines in server.py."""

import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from unittest.mock import MagicMock, patch


class TestServer42Lines:
    """Tests to cover the 42 missing lines in server.py."""

    def setup_method(self):
        """Initialize context for each test."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)

    @pytest.mark.asyncio
    async def test_explain_with_content_and_delete_operation(self):
        """Test explain with content and delete operation - creates execution token."""
        from awslabs.ccapi_mcp_server.server import _properties_store, explain

        content = {'BucketName': 'test-bucket'}

        result = await explain(content=content, operation='delete', context='S3 Bucket Deletion')

        assert 'execution_token' in result
        assert result['operation_type'] == 'delete'

        # Check that execution token was stored with delete operation
        token = result['execution_token']
        assert token in _properties_store
        assert _properties_store['_metadata'][token]['operation'] == 'delete'

    @pytest.mark.asyncio
    async def test_explain_with_content_and_destroy_operation(self):
        """Test explain with content and destroy operation - creates execution token."""
        from awslabs.ccapi_mcp_server.server import _properties_store, explain

        content = {'InstanceId': 'i-1234567890abcdef0'}

        result = await explain(
            content=content, operation='destroy', context='EC2 Instance Destruction'
        )

        assert 'execution_token' in result
        assert result['operation_type'] == 'destroy'

        # Check that execution token was stored with destroy operation
        token = result['execution_token']
        assert token in _properties_store
        assert _properties_store['_metadata'][token]['operation'] == 'destroy'

    @pytest.mark.asyncio
    async def test_explain_with_content_non_delete_operation(self):
        """Test explain with content but non-delete operation - no execution token."""
        from awslabs.ccapi_mcp_server.server import explain

        content = {'BucketName': 'test-bucket'}

        result = await explain(content=content, operation='analyze', context='S3 Bucket Analysis')

        assert 'execution_token' not in result
        assert result['operation_type'] == 'analyze'

    @pytest.mark.asyncio
    async def test_run_checkov_with_temp_file_cleanup(self):
        """Test run_checkov with temporary file cleanup on exception."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': True,
                'message': 'OK',
                'needs_user_action': False,
            }

            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = MagicMock()
                mock_file.name = '/tmp/test_file.json'
                mock_temp.return_value.__enter__.return_value = mock_file

                with patch('subprocess.run') as mock_run:
                    mock_run.side_effect = Exception('Subprocess error')

                    with patch('os.path.exists') as mock_exists:
                        mock_exists.return_value = True

                        with patch('os.unlink') as mock_unlink:
                            result = await run_checkov(content='{}', file_type='json')

                            # Should handle exception and clean up file
                            assert not result['passed']
                            assert 'error' in result
                            mock_unlink.assert_called_once_with('/tmp/test_file.json')

    @pytest.mark.asyncio
    async def test_run_checkov_file_cleanup_no_exists(self):
        """Test run_checkov file cleanup when file doesn't exist."""
        from awslabs.ccapi_mcp_server.server import run_checkov

        with patch('awslabs.ccapi_mcp_server.server._check_checkov_installed') as mock_check:
            mock_check.return_value = {
                'installed': True,
                'message': 'OK',
                'needs_user_action': False,
            }

            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = MagicMock()
                mock_file.name = '/tmp/nonexistent_file.json'
                mock_temp.return_value.__enter__.return_value = mock_file

                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = '{"results": {"passed_checks": []}}'

                    with patch('os.path.exists') as mock_exists:
                        mock_exists.return_value = False  # File doesn't exist

                        with patch('os.unlink') as mock_unlink:
                            result = await run_checkov(content='{}', file_type='json')

                            # Should not try to unlink non-existent file
                            assert result['passed']
                            mock_unlink.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_aws_session_info_short_arn(self):
        """Test get_aws_session_info with short ARN (no masking)."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        env_check = {'properly_configured': True}

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            mock_check.return_value = {
                'valid': True,
                'arn': 'short',  # Less than 8 characters
                'user_id': 'abc',  # Less than 4 characters
                'account_id': '123456789012',
                'region': 'us-east-1',
                'credential_source': 'profile',
            }

            result = await get_aws_session_info(env_check)

            # Short ARN and user_id should not be masked
            assert result['arn'] == 'short'
            assert result['user_id'] == 'abc'

    @pytest.mark.asyncio
    async def test_get_aws_session_info_unknown_values(self):
        """Test get_aws_session_info with Unknown ARN and user_id."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        env_check = {'properly_configured': True}

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            mock_check.return_value = {
                'valid': True,
                'arn': 'Unknown',
                'user_id': 'Unknown',
                'account_id': '123456789012',
                'region': 'us-east-1',
                'credential_source': 'profile',
            }

            result = await get_aws_session_info(env_check)

            # Unknown values should not be masked
            assert result['arn'] == 'Unknown'
            assert result['user_id'] == 'Unknown'

    @pytest.mark.asyncio
    async def test_get_aws_session_info_env_credentials_short(self):
        """Test get_aws_session_info with short environment credentials."""
        from awslabs.ccapi_mcp_server.server import get_aws_session_info

        env_check = {'properly_configured': True}

        with patch('awslabs.ccapi_mcp_server.server.check_aws_credentials') as mock_check:
            mock_check.return_value = {
                'valid': True,
                'aws_auth_type': 'env',
                'credential_source': 'env',
                'account_id': '123456789012',
                'region': 'us-east-1',
                'arn': 'arn:aws:iam::123456789012:user/test',
                'user_id': 'AIDACKCEVSQ6C2EXAMPLE',
            }

            with patch('awslabs.ccapi_mcp_server.server.environ.get') as mock_env:
                mock_env.side_effect = lambda key, default='': {
                    'AWS_ACCESS_KEY_ID': 'ABC',  # Less than 4 characters
                    'AWS_SECRET_ACCESS_KEY': 'XYZ',  # Less than 4 characters
                }.get(key, default)

                result = await get_aws_session_info(env_check)

                # Short credentials should show as ****
                assert result['masked_credentials']['AWS_ACCESS_KEY_ID'] == '****'
                assert result['masked_credentials']['AWS_SECRET_ACCESS_KEY'] == '****'

    def test_get_aws_profile_info_with_env_vars(self):
        """Test get_aws_profile_info with environment variables set."""
        from awslabs.ccapi_mcp_server.server import get_aws_profile_info

        with patch('awslabs.ccapi_mcp_server.server.environ.get') as mock_env:
            mock_env.side_effect = (
                lambda key, default='': {
                    'AWS_PROFILE': 'test-profile',
                    'AWS_REGION': 'eu-west-1',
                    'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                    'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                }.get(key, default)
            )

            with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
                mock_sts = MagicMock()
                mock_sts.get_caller_identity.return_value = {
                    'Account': '123456789012',
                    'Arn': 'arn:aws:iam::123456789012:user/test',
                }
                mock_client.return_value = mock_sts

                result = get_aws_profile_info()

                assert result['profile'] == 'test-profile'
                assert result['region'] == 'eu-west-1'
                assert result['using_env_vars'] is True

    def test_get_aws_profile_info_no_env_vars(self):
        """Test get_aws_profile_info with no environment variables."""
        from awslabs.ccapi_mcp_server.server import get_aws_profile_info

        with patch('awslabs.ccapi_mcp_server.server.environ.get') as mock_env:
            mock_env.return_value = ''  # No env vars set

            with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
                mock_sts = MagicMock()
                mock_sts.get_caller_identity.return_value = {
                    'Account': '123456789012',
                    'Arn': 'arn:aws:iam::123456789012:user/test',
                }
                mock_client.return_value = mock_sts

                result = get_aws_profile_info()

                assert result['profile'] == ''
                assert result['region'] == 'us-east-1'  # Default region
                assert result['using_env_vars'] is False

    @pytest.mark.asyncio
    async def test_create_template_with_save_file_error(self):
        """Test create_template with file save error."""
        from awslabs.ccapi_mcp_server.server import create_template

        with patch('awslabs.ccapi_mcp_server.server.create_template_impl') as mock_impl:
            mock_impl.side_effect = Exception('File save error')

            with pytest.raises(Exception, match='File save error'):
                await create_template(
                    template_id='test-id', save_to_file='/invalid/path/template.yaml'
                )

    def test_checkov_install_print_statements(self):
        """Test _check_checkov_installed print statements."""
        from awslabs.ccapi_mcp_server.server import _check_checkov_installed

        with patch('awslabs.ccapi_mcp_server.server.subprocess.run') as mock_run:
            # First call raises FileNotFoundError, second call succeeds
            mock_run.side_effect = [FileNotFoundError(), MagicMock(returncode=0)]

            with patch('builtins.print') as mock_print:
                result = _check_checkov_installed()

                # Should print installation messages
                assert mock_print.call_count >= 2
                mock_print.assert_any_call('Checkov not found, attempting to install...')
                mock_print.assert_any_call('Successfully installed Checkov')

                assert result['installed']

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_invalid_session_none(self):
        """Test generate_infrastructure_code with None aws_session_info."""
        from awslabs.ccapi_mcp_server.server import generate_infrastructure_code

        with pytest.raises(ClientError, match='Valid AWS credentials are required'):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket', aws_session_info=None
            )

    @pytest.mark.asyncio
    async def test_generate_infrastructure_code_invalid_session_no_valid_key(self):
        """Test generate_infrastructure_code with aws_session_info missing credentials_valid key."""
        from awslabs.ccapi_mcp_server.server import generate_infrastructure_code

        with pytest.raises(ClientError, match='Valid AWS credentials are required'):
            await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket', aws_session_info={'some_other_key': 'value'}
            )
