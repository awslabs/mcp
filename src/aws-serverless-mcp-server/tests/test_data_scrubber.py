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

"""Tests for data scrubbing utilities."""

from awslabs.aws_serverless_mcp_server.utils.data_scrubber import DataScrubber


class TestDataScrubber:
    """Test cases for DataScrubber class."""

    def test_scrub_text_with_account_id(self):
        """Test scrubbing AWS account IDs from text."""
        text = 'Account ID: 123456789012 is being used'
        result = DataScrubber.scrub_text(text)
        assert '123456789012' not in result
        assert '************' in result

    def test_scrub_text_with_access_key(self):
        """Test scrubbing AWS access keys from text."""
        text = 'Access key: AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        result = DataScrubber.scrub_text(text)
        assert 'AKIAIOSFODNN7EXAMPLE' not in result  # pragma: allowlist secret
        assert 'AKIA****************' in result

    def test_scrub_text_with_secret_key(self):
        """Test scrubbing AWS secret keys from text."""
        text = 'Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # pragma: allowlist secret
        result = DataScrubber.scrub_text(text)
        assert 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' not in result  # pragma: allowlist secret
        assert '****************************************' in result

    def test_scrub_text_with_session_token(self):
        """Test scrubbing AWS session tokens from text."""
        long_token = 'A' * 150  # Long base64-like string
        text = f'Session token: {long_token}'
        result = DataScrubber.scrub_text(text)
        assert long_token not in result
        assert '[REDACTED_SESSION_TOKEN]' in result

    def test_scrub_text_with_ip_address(self):
        """Test scrubbing IP addresses from text."""
        text = 'Server IP: 192.168.1.100'
        result = DataScrubber.scrub_text(text)
        assert '192.168.1.100' not in result
        assert 'XXX.XXX.XXX.XXX' in result

    def test_scrub_text_with_email(self):
        """Test scrubbing email addresses from text."""
        text = 'Contact: user@example.com'
        result = DataScrubber.scrub_text(text)
        assert 'user@example.com' not in result
        assert '[REDACTED_EMAIL]' in result

    def test_scrub_text_with_phone(self):
        """Test scrubbing phone numbers from text."""
        text = 'Phone: +1-555-123-4567'
        result = DataScrubber.scrub_text(text)
        assert '+1-555-123-4567' not in result
        assert '[REDACTED_PHONE]' in result

    def test_scrub_text_with_url_credentials(self):
        """Test scrubbing URLs with credentials from text."""
        text = 'URL: https://user:pass@example.com/path'  # pragma: allowlist secret
        result = DataScrubber.scrub_text(text)
        assert 'user:pass' not in result  # pragma: allowlist secret
        # The email pattern might match first, so just check credentials are removed
        assert 'pass@example.com' not in result

    def test_scrub_text_with_db_connection(self):
        """Test scrubbing database connection strings from text."""
        text = 'DB: mysql://user:password@localhost:3306/db'  # pragma: allowlist secret
        result = DataScrubber.scrub_text(text)
        assert 'user:password' not in result  # pragma: allowlist secret
        assert '[REDACTED_DB_CONNECTION]' in result

    def test_scrub_text_with_jwt_token(self):
        """Test scrubbing JWT tokens from text."""
        jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'  # pragma: allowlist secret
        text = f'Token: {jwt}'
        result = DataScrubber.scrub_text(text)
        assert jwt not in result
        assert '[REDACTED_JWT_TOKEN]' in result

    def test_scrub_text_non_string_input(self):
        """Test scrubbing non-string input returns unchanged."""
        assert DataScrubber.scrub_text(123) == 123
        assert DataScrubber.scrub_text(None) is None
        assert DataScrubber.scrub_text([]) == []

    def test_scrub_dict_basic(self):
        """Test basic dictionary scrubbing."""
        data = {
            'username': 'john',
            'password': 'secret123',  # pragma: allowlist secret
            'account_id': '123456789012',
        }  # pragma: allowlist secret
        result = DataScrubber.scrub_dict(data)
        assert result['username'] == 'john'
        assert result['password'] == '[REDACTED]'
        assert '123456789012' not in str(result)

    def test_scrub_dict_deep_copy_default(self):
        """Test that scrub_dict creates deep copy by default."""
        data = {'password': 'secret'}  # pragma: allowlist secret
        result = DataScrubber.scrub_dict(data)
        assert result is not data
        assert data['password'] == 'secret'  # Original unchanged  # pragma: allowlist secret
        assert result['password'] == '[REDACTED]'  # pragma: allowlist secret

    def test_scrub_dict_no_deep_copy(self):
        """Test scrub_dict without deep copy."""
        data = {'password': 'secret', 'normal': 'value'}  # pragma: allowlist secret
        result = DataScrubber.scrub_dict(data, deep_copy=False)
        assert result is not data  # Still creates a copy
        assert data['password'] == 'secret'  # Original unchanged  # pragma: allowlist secret

    def test_scrub_dict_non_dict_input(self):
        """Test scrubbing non-dict input returns unchanged."""
        assert DataScrubber.scrub_dict('string') == 'string'
        assert DataScrubber.scrub_dict(123) == 123
        assert DataScrubber.scrub_dict(None) is None

    def test_scrub_dict_recursive_nested_dict(self):
        """Test recursive scrubbing of nested dictionaries."""
        data = {
            'level1': {
                'level2': {'password': 'secret', 'normal': 'value'}  # pragma: allowlist secret
            }  # pragma: allowlist secret
        }  # pragma: allowlist secret
        result = DataScrubber._scrub_dict_recursive(data)
        assert result['level1']['level2']['password'] == '[REDACTED]'
        assert result['level1']['level2']['normal'] == 'value'

    def test_scrub_dict_recursive_list(self):
        """Test recursive scrubbing of lists."""
        data = [
            {'password': 'secret1'},  # pragma: allowlist secret
            {'password': 'secret2', 'normal': 'value'},  # pragma: allowlist secret
        ]
        result = DataScrubber._scrub_dict_recursive(data)
        assert result[0]['password'] == '[REDACTED]'
        assert result[1]['password'] == '[REDACTED]'
        assert result[1]['normal'] == 'value'

    def test_scrub_dict_recursive_string(self):
        """Test recursive scrubbing of strings."""
        text = 'Account: 123456789012'
        result = DataScrubber._scrub_dict_recursive(text)
        assert '123456789012' not in result
        assert '************' in result

    def test_scrub_dict_recursive_other_types(self):
        """Test recursive scrubbing of other data types."""
        assert DataScrubber._scrub_dict_recursive(123) == 123
        assert DataScrubber._scrub_dict_recursive(None) is None
        assert DataScrubber._scrub_dict_recursive(True) is True

    def test_is_sensitive_field_name_exact_matches(self):
        """Test exact matches for sensitive field names."""
        assert DataScrubber._is_sensitive_field_name('password')
        assert DataScrubber._is_sensitive_field_name('SECRET')
        assert DataScrubber._is_sensitive_field_name('AccessKeyId')
        assert DataScrubber._is_sensitive_field_name('SessionToken')

    def test_is_sensitive_field_name_partial_matches(self):
        """Test partial matches for sensitive field names."""
        assert DataScrubber._is_sensitive_field_name('user_password')
        assert DataScrubber._is_sensitive_field_name('api_key_value')
        assert DataScrubber._is_sensitive_field_name('auth_token')
        assert DataScrubber._is_sensitive_field_name('db_credential')

    def test_is_sensitive_field_name_non_sensitive(self):
        """Test non-sensitive field names."""
        assert not DataScrubber._is_sensitive_field_name('username')
        assert not DataScrubber._is_sensitive_field_name('email')
        assert not DataScrubber._is_sensitive_field_name('normal_field')

    def test_scrub_lambda_config_basic(self):
        """Test scrubbing Lambda configuration."""
        config = {
            'FunctionName': 'my-function',
            'Environment': {
                'Variables': {
                    'API_KEY': 'secret123',  # pragma: allowlist secret
                    'DEBUG': 'true',
                    'PASSWORD': 'mysecret',  # pragma: allowlist secret
                }  # pragma: allowlist secret
            },
        }
        result = DataScrubber.scrub_lambda_config(config)
        assert result['FunctionName'] == 'my-function'
        assert result['Environment']['Variables']['API_KEY'] == '[REDACTED]'
        assert result['Environment']['Variables']['DEBUG'] == 'true'
        assert (
            result['Environment']['Variables']['PASSWORD'] == '[REDACTED]'
        )  # pragma: allowlist secret

    def test_scrub_lambda_config_sensitive_values(self):
        """Test scrubbing Lambda config with sensitive-looking values."""
        config = {
            'Environment': {
                'Variables': {
                    'NORMAL_VAR': 'AKIAIOSFODNN7EXAMPLE',  # Looks like access key  # pragma: allowlist secret
                    'ANOTHER_VAR': 'short',  # Short value, not sensitive
                }
            }
        }
        result = DataScrubber.scrub_lambda_config(config)
        # Access key pattern is detected and replaced with specific pattern
        assert result['Environment']['Variables']['NORMAL_VAR'] == 'AKIA****************'
        assert result['Environment']['Variables']['ANOTHER_VAR'] == 'short'

    def test_scrub_esm_config_basic(self):
        """Test scrubbing ESM configuration."""
        config = {
            'EventSourceArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test',
            'SourceAccessConfigurations': [{'Type': 'SASL_SCRAM_512_AUTH', 'URI': 'secret-arn'}],
        }
        result = DataScrubber.scrub_esm_config(config)
        assert '123456789012' not in str(result)
        assert result['SourceAccessConfigurations'][0]['Type'] == 'SASL_SCRAM_512_AUTH'

    def test_scrub_esm_config_non_dict_input(self):
        """Test scrubbing ESM config with non-dict input."""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo()
        result = DataScrubber.scrub_esm_config(field_info)
        assert result == {}

    def test_scrub_esm_config_sensitive_fields(self):
        """Test scrubbing ESM config with sensitive fields."""
        config = {
            'SelfManagedEventSource': {
                'Endpoints': {'KAFKA_BOOTSTRAP_SERVERS': ['broker1:9092']},
                'ConsumerGroupId': 'my-group',
            },
            'AmazonManagedKafkaEventSourceConfig': {'ConsumerGroupId': 'managed-group'},
        }
        result = DataScrubber.scrub_esm_config(config)
        assert 'SelfManagedEventSource' in result
        assert 'AmazonManagedKafkaEventSourceConfig' in result

    def test_looks_like_sensitive_value_short_values(self):
        """Test that short values are not considered sensitive."""
        assert not DataScrubber._looks_like_sensitive_value('short')
        assert not DataScrubber._looks_like_sensitive_value('1234567')  # 7 chars

    def test_scrub_text_all_patterns(self):
        """Test scrubbing text with all sensitive patterns."""
        # Test data with sensitive patterns - pragma: allowlist secret
        text_with_secrets = (
            'Account: 123456789012\n'
            'Access Key: AKIAIOSFODNN7EXAMPLE\n'  # pragma: allowlist secret
            'Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n'  # pragma: allowlist secret
            'Session Token: ' + 'A' * 100 + '\n'  # pragma: allowlist secret
            'IP: 192.168.1.1\n'
            'Email: user@example.com\n'
            'Phone: +1-555-123-4567\n'
            'URL: https://user:pass@example.com/path\n'  # pragma: allowlist secret
            'DB: mysql://user:pass@localhost/db\n'  # pragma: allowlist secret
            'JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c\n'  # pragma: allowlist secret
        )

        result = DataScrubber.scrub_text(text_with_secrets)

        # Verify all patterns are scrubbed
        assert '123456789012' not in result
        assert 'AKIAIOSFODNN7EXAMPLE' not in result  # pragma: allowlist secret
        assert 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' not in result  # pragma: allowlist secret
        assert '192.168.1.1' not in result
        assert 'user@example.com' not in result
        assert '+1-555-123-4567' not in result
        assert 'user:pass@example.com' not in result
        assert 'user:pass@localhost' not in result

        # Verify replacements are present
        assert '************' in result  # Account ID
        assert 'AKIA****************' in result  # Access Key
        assert '****************************************' in result  # Secret
        assert 'XXX.XXX.XXX.XXX' in result  # IP
        assert '[REDACTED_EMAIL]' in result  # Email
        assert '[REDACTED_PHONE]' in result  # Phone
        assert '[REDACTED_URL_WITH_CREDENTIALS]' in result  # URL with creds
        assert '[REDACTED_DB_CONNECTION]' in result  # DB connection

    def test_scrub_dict_deep_copy_false(self):
        """Test scrubbing dictionary without deep copy."""
        data = {
            'password': 'secret123',  # pragma: allowlist secret
            'nested': {'key': 'AKIAIOSFODNN7EXAMPLE'},  # pragma: allowlist secret
        }

        result = DataScrubber.scrub_dict(data, deep_copy=False)

        # Original data should be modified when deep_copy=False
        assert result is not data  # Still returns a copy, but shallow
        assert 'password' in result
        assert 'nested' in result

    def test_scrub_dict_recursive_nested_structures(self):
        """Test scrubbing deeply nested dictionary structures."""
        data = {
            'level1': {
                'level2': {
                    'level3': {
                        'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                        'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                        'list_with_secrets': [
                            {'password': 'secret123'},  # pragma: allowlist secret
                            'AKIAIOSFODNN7EXAMPLE',  # pragma: allowlist secret
                            123456789012,
                        ],
                    }
                }
            }
        }

        result = DataScrubber.scrub_dict(data)

        # Navigate to deeply nested structure
        level3 = result['level1']['level2']['level3']
        assert level3['AccessKeyId'] == '[REDACTED]'
        assert level3['SecretAccessKey'] == '[REDACTED]'

        # Check list scrubbing
        scrubbed_list = level3['list_with_secrets']
        # First item should be a dict with scrubbed password
        if isinstance(scrubbed_list[0], dict):
            assert scrubbed_list[0]['password'] == '[REDACTED]'
        # Second item should be scrubbed access key
        assert 'AKIA****************' in str(scrubbed_list[1])
        # Third item should be scrubbed account ID
        assert '************' in str(scrubbed_list[2])
        assert 'AKIA****************' in scrubbed_list[1]  # String in list scrubbed
        assert scrubbed_list[2] == '************'  # Number converted to string and scrubbed

    def test_looks_like_sensitive_value_pattern_matches(self):
        """Test values matching sensitive patterns."""
        assert DataScrubber._looks_like_sensitive_value('123456789012')  # Account ID
        assert DataScrubber._looks_like_sensitive_value(
            'AKIAIOSFODNN7EXAMPLE'  # pragma: allowlist secret
        )  # Access key

    def test_looks_like_sensitive_value_high_entropy(self):
        """Test values with high entropy."""
        # Base64-like string with high entropy
        high_entropy = 'SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0IHN0cmluZyB3aXRoIGhpZ2ggZW50cm9weQ=='  # pragma: allowlist secret
        assert DataScrubber._looks_like_sensitive_value(high_entropy)

    def test_looks_like_sensitive_value_low_entropy(self):
        """Test values with low entropy."""
        low_entropy = 'aaaaaaaaaaaaaaaaaaaaaa'  # Repeated characters
        assert not DataScrubber._looks_like_sensitive_value(low_entropy)

    def test_has_high_entropy_short_strings(self):
        """Test entropy calculation for short strings."""
        assert not DataScrubber._has_high_entropy('short')
        assert not DataScrubber._has_high_entropy('123456789')  # 9 chars

    def test_has_high_entropy_high_entropy_string(self):
        """Test high entropy string detection."""
        # Random-looking base64 string
        high_entropy = (
            'aB3dE7fG9hI2jK4lM6nO8pQ1rS5tU7vW9xY2zA4bC6dE8fG'  # pragma: allowlist secret
        )
        assert DataScrubber._has_high_entropy(high_entropy)

    def test_has_high_entropy_low_entropy_string(self):
        """Test low entropy string detection."""
        low_entropy = 'aaaaaaaaaaaaaaaaaaaaaa'
        assert not DataScrubber._has_high_entropy(low_entropy)

    def test_scrub_aws_response_basic(self):
        """Test scrubbing AWS API responses."""
        response = {
            'Account': '123456789012',
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-type': 'application/json',
                    'authorization': 'AWS4-HMAC-SHA256 Credential=...',
                    'x-amzn-requestid': '12345',
                    'date': 'Mon, 01 Jan 2024 00:00:00 GMT',
                }
            },
        }
        result = DataScrubber.scrub_aws_response(response)
        assert '123456789012' not in str(result)

        # Check that safe headers are kept
        headers = result['ResponseMetadata']['HTTPHeaders']
        assert 'content-type' in headers
        assert 'date' in headers

        # Check that unsafe headers are removed
        assert 'authorization' not in headers
        assert 'x-amzn-requestid' not in headers

    def test_scrub_aws_response_no_metadata(self):
        """Test scrubbing AWS response without ResponseMetadata."""
        response = {'Account': '123456789012'}
        result = DataScrubber.scrub_aws_response(response)
        assert '123456789012' not in str(result)

    def test_scrub_aws_response_no_headers(self):
        """Test scrubbing AWS response without HTTPHeaders."""
        response = {'Account': '123456789012', 'ResponseMetadata': {'RequestId': '12345'}}
        result = DataScrubber.scrub_aws_response(response)
        assert '123456789012' not in str(result)
        assert result['ResponseMetadata']['RequestId'] == '12345'

    def test_scrub_lambda_config_with_sensitive_field_name(self):
        """Test scrubbing Lambda config with sensitive field names at top level."""
        config = {
            'FunctionName': 'my-function',
            'password': 'top-level-secret',  # pragma: allowlist secret
            'Environment': {
                'Variables': {
                    'NORMAL_VAR': 'normal-value',
                }
            },
        }
        result = DataScrubber.scrub_lambda_config(config)
        assert result['FunctionName'] == 'my-function'
        assert result['password'] == '[REDACTED]'  # Top-level sensitive field
        assert result['Environment']['Variables']['NORMAL_VAR'] == 'normal-value'
