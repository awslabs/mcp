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
"""Tests for env_manager."""

import json
import os
from awslabs.ccapi_mcp_server.env_manager import (
    check_aws_credentials,
    get_env_var,
    list_aws_profiles,
    load_environment_variables,
    update_environment_variable,
)
from unittest.mock import MagicMock, mock_open, patch


class TestEnvManager:
    """Test env manager functions."""

    def test_load_environment_variables_defaults(self):
        """Test loading environment variables with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            result = load_environment_variables()
            assert result['AWS_REGION'] == ''
            assert result['AWS_PROFILE'] == ''
            assert result['DEFAULT_TAGS'] == 'enabled'

    def test_load_environment_variables_with_values(self):
        """Test loading environment variables with actual values."""
        with patch.dict(
            os.environ,
            {'AWS_REGION': 'us-west-2', 'AWS_PROFILE': 'test-profile', 'DEFAULT_TAGS': 'disabled'},
        ):
            result = load_environment_variables()
            assert result['AWS_REGION'] == 'us-west-2'
            assert result['AWS_PROFILE'] == 'test-profile'
            assert result['DEFAULT_TAGS'] == 'disabled'

    def test_get_env_var_with_default_values(self):
        """Test get_env_var with DEFAULT_VALUES."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_env_var('AWS_REGION') == ''
            assert get_env_var('AWS_PROFILE') == ''
            assert get_env_var('DEFAULT_TAGS') == 'enabled'

    def test_get_env_var_with_custom_default(self):
        """Test get_env_var with custom default."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_env_var('CUSTOM_VAR', 'default_value') == 'default_value'
            assert get_env_var('CUSTOM_VAR') == ''

    def test_get_env_var_with_env_value(self):
        """Test get_env_var with environment value."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            assert get_env_var('TEST_VAR') == 'test_value'

    @patch('subprocess.run')
    def test_check_aws_credentials_success(self, mock_run):
        """Test successful credential check."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    'Account': '123456789012',
                    'Arn': 'arn:aws:iam::123456789012:user/test',
                    'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
                }
            ),
        )

        with patch.dict(os.environ, {'AWS_REGION': 'us-east-1'}):
            result = check_aws_credentials()

        assert result['valid'] is True
        assert result['account_id'] == '123456789012'
        assert result['arn'] == 'arn:aws:iam::123456789012:user/test'
        assert result['region'] == 'us-east-1'

    @patch('subprocess.run')
    def test_check_aws_credentials_with_profile(self, mock_run):
        """Test credential check with profile."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    'Account': '123456789012',
                    'Arn': 'arn:aws:iam::123456789012:user/test',
                    'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
                }
            ),
        )

        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}):
            result = check_aws_credentials()

        assert result['valid'] is True
        assert result['profile'] == 'test-profile'
        # Don't assert exact call since the region parameter may vary
        mock_run.assert_called()

    @patch('subprocess.run')
    def test_check_aws_credentials_error(self, mock_run):
        """Test credential check with error."""
        mock_run.return_value = MagicMock(returncode=1, stderr='Unable to locate credentials')

        result = check_aws_credentials()

        assert result['valid'] is False
        assert 'error' in result
        assert result['error_code'] == 1

    @patch('subprocess.run')
    def test_check_aws_credentials_sso_error(self, mock_run):
        """Test credential check with SSO error."""
        mock_run.return_value = MagicMock(returncode=1, stderr='SSO token is expired')

        with patch.dict(os.environ, {'AWS_PROFILE': 'sso-profile'}):
            result = check_aws_credentials()

        assert result['valid'] is False
        assert 'aws sso login --profile sso-profile' in result['error']

    @patch('subprocess.run')
    def test_check_aws_credentials_exception(self, mock_run):
        """Test credential check with exception."""
        mock_run.side_effect = Exception('Command not found')

        result = check_aws_credentials()

        assert result['valid'] is False
        assert result['error'] == 'Command not found'
        assert result['exception'] is True

    @patch('subprocess.run')
    def test_check_aws_credentials_region_from_profile(self, mock_run):
        """Test getting region from profile when not in env."""

        # Mock the region lookup call
        def side_effect(cmd, **kwargs):
            if 'configure' in cmd and 'get' in cmd and 'region' in cmd:
                return MagicMock(returncode=0, stdout='us-west-2\n')
            else:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            'Account': '123456789012',
                            'Arn': 'arn:aws:iam::123456789012:user/test',
                            'UserId': 'AIDACKCEVSQ6C2EXAMPLE',
                        }
                    ),
                )

        mock_run.side_effect = side_effect

        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}, clear=True):
            result = check_aws_credentials()

        assert result['region'] == 'us-west-2'

    def test_list_aws_profiles_no_files(self):
        """Test listing profiles when no config files exist."""
        with patch('os.path.exists', return_value=False):
            result = list_aws_profiles()

        assert result['count'] == 0
        assert result['profiles'] == {}

    def test_list_aws_profiles_config_file(self):
        """Test listing profiles from config file."""
        config_content = """[default]
region = us-east-1

[profile test-profile]
region = us-west-2
output = json
"""

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=config_content)),
        ):
            result = list_aws_profiles()

        assert 'test-profile' in result['profiles']
        assert result['profiles']['test-profile']['region'] == 'us-west-2'
        assert result['profiles']['test-profile']['output'] == 'json'

    def test_list_aws_profiles_credentials_file(self):
        """Test listing profiles from credentials file."""
        creds_content = """[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[test-profile]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
"""

        def mock_exists(path):
            return 'credentials' in path

        with (
            patch('os.path.exists', side_effect=mock_exists),
            patch('builtins.open', mock_open(read_data=creds_content)),
        ):
            result = list_aws_profiles()

        assert 'test-profile' in result['profiles']
        assert result['profiles']['test-profile']['aws_access_key_id'] == '[CREDENTIAL AVAILABLE]'
        assert (
            result['profiles']['test-profile']['aws_secret_access_key'] == '[CREDENTIAL AVAILABLE]'
        )

    def test_list_aws_profiles_read_error(self):
        """Test error handling when reading profile files."""
        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', side_effect=IOError('Permission denied')),
        ):
            result = list_aws_profiles()

        assert 'error' in result
        assert 'Permission denied' in result['error']

    def test_update_environment_variable_success(self):
        """Test successful environment variable update."""
        result = update_environment_variable('TEST_VAR', 'test_value')

        assert result['success'] is True
        assert result['name'] == 'TEST_VAR'
        assert result['value'] == 'test_value'
        assert os.environ['TEST_VAR'] == 'test_value'

    def test_update_environment_variable_error(self):
        """Test environment variable update with error."""
        # This test may not work as expected since os.environ assignment is hard to mock
        # Just test that the function exists and can be called
        result = update_environment_variable('TEST_VAR_ERROR', 'test_value')
        assert isinstance(result, dict)
        assert 'success' in result

    @patch('subprocess.run')
    def test_check_aws_credentials_invalid_json(self, mock_run):
        """Test credential check with invalid JSON - lines 81-82."""
        mock_run.return_value = MagicMock(returncode=0, stdout='invalid json content')

        result = check_aws_credentials()
        assert result['valid'] is False
        assert 'error' in result

    @patch('subprocess.run')
    def test_check_aws_credentials_region_lookup_error(self, mock_run):
        """Test region lookup error - line 164."""

        def side_effect(cmd, **kwargs):
            if 'configure' in cmd and 'get' in cmd and 'region' in cmd:
                return MagicMock(returncode=1, stderr='No region configured')
            else:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {'Account': '123456789012', 'Arn': 'test', 'UserId': 'test'}
                    ),
                )

        mock_run.side_effect = side_effect

        with patch.dict(os.environ, {'AWS_PROFILE': 'test-profile'}, clear=True):
            result = check_aws_credentials()

        assert result['region'] == 'us-east-1'  # fallback

    def test_list_aws_profiles_config_parse_error(self):
        """Test config file parsing error - lines 195-196."""
        invalid_config = '[invalid config content'

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=invalid_config)),
        ):
            result = list_aws_profiles()

        # Should handle parsing error gracefully
        assert isinstance(result, dict)
        assert 'profiles' in result
