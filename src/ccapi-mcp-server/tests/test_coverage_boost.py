"""Simple tests to boost coverage to 88%+."""

import json
import pytest
from awslabs.ccapi_mcp_server.errors import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


class TestCoverageBoost:
    """Simple tests to boost coverage."""

    def setup_method(self):
        """Initialize context for each test."""
        from awslabs.ccapi_mcp_server.context import Context

        Context.initialize(False)

    # Simple tests that hit missing lines without complex logic
    def test_cloud_control_utils_line_63(self):
        """Test line 63 in cloud_control_utils.py."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import add_default_tags

        # Test with no existing Tags property
        schema = {'properties': {'BucketName': {'type': 'string'}}}
        properties = {'BucketName': 'test'}

        result = add_default_tags(properties, schema)
        assert 'Tags' in result

    def test_cloud_control_utils_line_97(self):
        """Test line 97 in cloud_control_utils.py."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import validate_patch

        # Test invalid operation
        with pytest.raises(ClientError):
            validate_patch([{'op': 'invalid', 'path': '/test'}])

    def test_explanation_generator_line_133(self):
        """Test line 133 in explanation_generator.py."""
        from awslabs.ccapi_mcp_server.explanation_generator import _explain_dict

        # Test with nested data in summary format
        data = {'nested': {'key': 'value'}, 'list': [1, 2, 3, 4, 5]}
        result = _explain_dict(data, 'summary')
        assert 'nested' in result

    @pytest.mark.asyncio
    async def test_server_readonly_checks(self):
        """Test readonly mode checks in server functions."""
        from awslabs.ccapi_mcp_server.server import _properties_store, create_resource

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True}}

        # Test readonly mode
        with pytest.raises(ClientError, match='read-only'):
            await create_resource(
                resource_type='AWS::S3::Bucket',
                aws_session_info={'credentials_valid': True, 'readonly_mode': True},
                execution_token=token,
            )

    def test_env_manager_simple_cases(self):
        """Test simple cases in env_manager."""
        from awslabs.ccapi_mcp_server.env_manager import check_aws_credentials

        with patch('os.environ.get') as mock_env:
            mock_env.return_value = None

            with patch('boto3.Session') as mock_session:
                mock_session.side_effect = Exception('No credentials')

                result = check_aws_credentials()
                assert not result.get('valid', True)

    @pytest.mark.asyncio
    async def test_infrastructure_generator_simple(self):
        """Test simple infrastructure generator cases."""
        from awslabs.ccapi_mcp_server.infrastructure_generator import generate_infrastructure_code

        # Test with empty properties for create operation
        with patch('awslabs.ccapi_mcp_server.infrastructure_generator.schema_manager') as mock_sm:
            mock_schema_manager = MagicMock()
            mock_schema_manager.get_schema = AsyncMock(
                return_value={'properties': {'BucketName': {'type': 'string'}}}
            )
            mock_sm.return_value = mock_schema_manager

            result = await generate_infrastructure_code(
                resource_type='AWS::S3::Bucket',
                properties={'BucketName': 'test-bucket'},
                region='us-east-1',
            )

            assert result['operation'] == 'create'

    def test_schema_manager_simple(self):
        """Test simple schema manager cases."""
        from awslabs.ccapi_mcp_server.schema_manager import schema_manager

        sm = schema_manager()

        # Test loading metadata with corrupted file
        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_file.read.side_effect = json.JSONDecodeError('Invalid', '', 0)
            mock_open.return_value.__enter__.return_value = mock_file

            with patch('pathlib.Path.exists', return_value=True):
                metadata = sm._load_metadata()
                assert 'version' in metadata

    @pytest.mark.asyncio
    async def test_server_security_warnings(self):
        """Test security warning paths in server."""
        from awslabs.ccapi_mcp_server.server import _properties_store, create_resource

        token = 'test-token'
        _properties_store[token] = {'BucketName': 'test'}
        _properties_store['_metadata'] = {token: {'explained': True}}

        with patch('awslabs.ccapi_mcp_server.server.environ.get') as mock_env:
            mock_env.side_effect = (
                lambda key, default='enabled': 'disabled'
                if key == 'SECURITY_SCANNING'
                else default
            )

            with patch('awslabs.ccapi_mcp_server.server.get_aws_client') as mock_client:
                mock_client.return_value.create_resource.return_value = {
                    'ProgressEvent': {
                        'OperationStatus': 'SUCCESS',
                        'Identifier': 'test-bucket',
                        'TypeName': 'AWS::S3::Bucket',
                        'RequestToken': 'test-request-token',
                    }
                }

                with patch('awslabs.ccapi_mcp_server.server.progress_event') as mock_progress:
                    mock_progress.return_value = {'status': 'SUCCESS'}

                    result = await create_resource(
                        resource_type='AWS::S3::Bucket',
                        aws_session_info={'credentials_valid': True, 'readonly_mode': False},
                        execution_token=token,
                    )

                    # Should include security warning when scanning is disabled
                    assert 'security_warning' in result

    def test_simple_error_cases(self):
        """Test simple error handling cases."""
        from awslabs.ccapi_mcp_server.cloud_control_utils import validate_patch

        # Test missing path field
        with pytest.raises(ClientError, match="'path'"):
            validate_patch([{'op': 'add', 'value': 'test'}])

        # Test missing op field
        with pytest.raises(ClientError, match="'op'"):
            validate_patch([{'path': '/test', 'value': 'test'}])
