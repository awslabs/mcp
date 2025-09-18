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

from awslabs.aws_api_mcp_server.core.common.scrubber import (
    SensitiveDataScrubber,
)


def test_scrub_creds_with_single_sensitive_key():
    """Test scrubbing credentials with a single sensitive key."""
    scrubber = SensitiveDataScrubber()
    data = {'password': 'secret123', 'username': 'testuser'}  # pragma: allowlist secret

    result = scrubber.scrub_creds(data)

    assert result['password'] == '*****************'
    assert result['username'] == 'testuser'


def test_scrub_creds_with_multiple_sensitive_keys():
    """Test scrubbing credentials with multiple sensitive keys."""
    scrubber = SensitiveDataScrubber()
    data = {
        'password': 'secret123',  # pragma: allowlist secret
        'secret_key': 'abc123',  # pragma: allowlist secret
        'session_token': 'xyz789',
        'username': 'testuser',
    }

    result = scrubber.scrub_creds(data)

    assert result['password'] == '*****************'
    assert result['secret_key'] == '*****************'
    assert result['session_token'] == '*****************'
    assert result['username'] == 'testuser'


def test_scrub_creds_with_nested_dicts():
    """Test scrubbing credentials in nested dictionaries."""
    scrubber = SensitiveDataScrubber()
    data = {
        'user': {
            'credentials': {
                'password': 'secret123',  # pragma: allowlist secret
                'api_key': 'key456',  # pragma: allowlist secret
            },
            'profile': {'security_token': 'token789'},
        },
        'settings': {'theme': 'dark'},
    }

    result = scrubber.scrub_creds(data)

    assert result['user']['credentials'] == '*****************'
    assert result['user']['profile']['security_token'] == '*****************'
    assert result['settings']['theme'] == 'dark'


def test_scrub_creds_with_list_containing_dicts():
    """Test scrubbing credentials in lists containing dictionaries."""
    scrubber = SensitiveDataScrubber()
    data = {
        'users': [
            {'name': 'user1', 'password': 'pass1'},  # pragma: allowlist secret
            {'name': 'user2', 'secret': 'sec2'},  # pragma: allowlist secret
        ]
    }

    result = scrubber.scrub_creds(data)

    assert result['users'][0]['password'] == '*****************'
    assert result['users'][1]['secret'] == '*****************'
    assert result['users'][0]['name'] == 'user1'
    assert result['users'][1]['name'] == 'user2'


def test_scrub_creds_with_mixed_data_types():
    """Test scrubbing credentials with mixed data types."""
    scrubber = SensitiveDataScrubber()
    data = {
        'string_value': 'hello',
        'int_value': 42,
        'bool_value': True,
        'password': 'secret123',  # pragma: allowlist secret
        'list_value': [1, 2, 3],
        'none_value': None,
    }

    result = scrubber.scrub_creds(data)

    assert result['password'] == '*****************'
    assert result['string_value'] == 'hello'
    assert result['int_value'] == 42
    assert result['bool_value'] is True
    assert result['list_value'] == [1, 2, 3]
    assert result['none_value'] is None


def test_scrub_creds_with_case_insensitive_matching():
    """Test that credential scrubbing is case insensitive."""
    scrubber = SensitiveDataScrubber()
    data = {
        'PASSWORD': 'secret123',  # pragma: allowlist secret
        'Secret': 'key456',  # pragma: allowlist secret
        'SESSION_TOKEN': 'token789',
        'SecurityToken': 'sec123',
    }

    result = scrubber.scrub_creds(data)

    assert result['PASSWORD'] == '*****************'
    assert result['Secret'] == '*****************'
    assert result['SESSION_TOKEN'] == '*****************'
    assert result['SecurityToken'] == '*****************'


def test_scrub_creds_with_partial_matches():
    """Test that partial matches in blocked keywords are handled correctly."""
    scrubber = SensitiveDataScrubber()
    data = {
        'user_password': 'secret123',  # pragma: allowlist secret
        'api_secret_key': 'key456',  # pragma: allowlist secret
        'session_auth_token': 'token789',
        'security_credentials': 'creds123',
    }

    result = scrubber.scrub_creds(data)

    assert result['user_password'] == '*****************'
    assert result['api_secret_key'] == '*****************'
    assert result['session_auth_token'] == '*****************'
    assert result['security_credentials'] == '*****************'


def test_scrub_creds_with_no_sensitive_data():
    """Test scrubbing when no sensitive data is present."""
    scrubber = SensitiveDataScrubber()
    data = {'username': 'testuser', 'email': 'test@example.com', 'age': 25, 'is_active': True}

    result = scrubber.scrub_creds(data)

    # Data should remain unchanged
    assert result == data


def test_scrub_creds_with_empty_dict():
    """Test scrubbing with an empty dictionary."""
    scrubber = SensitiveDataScrubber()
    data = {}

    result = scrubber.scrub_creds(data)

    assert result == {}
