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
"""Tests for additional spec per-spec auth and validation (CWE-522)."""

import json
import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import _build_additional_spec_auth, create_mcp_server
from unittest.mock import MagicMock, patch


# --- Unit tests for _build_additional_spec_auth ---


class TestBuildAdditionalSpecAuth:
    """Tests for the _build_additional_spec_auth helper function."""

    def test_bearer_auth(self):
        """Test bearer token auth returns correct Authorization header."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {'type': 'bearer', 'token': 'my-test-token'}  # pragma: allowlist secret
        )
        assert headers == {
            'Authorization': 'Bearer my-test-token'  # pragma: allowlist secret
        }
        assert httpx_auth is None
        assert cookies == {}

    def test_bearer_auth_missing_token(self):
        """Test bearer auth raises ValueError when token is missing."""
        with pytest.raises(ValueError, match="Bearer auth requires 'token' field"):
            _build_additional_spec_auth({'type': 'bearer'})

    def test_bearer_auth_empty_token(self):
        """Test bearer auth raises ValueError when token is empty."""
        with pytest.raises(ValueError, match="Bearer auth requires 'token' field"):
            _build_additional_spec_auth(
                {'type': 'bearer', 'token': ''}  # pragma: allowlist secret
            )

    def test_api_key_in_header(self):
        """Test API key placed in header."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {
                'type': 'api_key',
                'key': 'abc123',  # pragma: allowlist secret
                'key_name': 'X-API-Key',
                'key_in': 'header',
            }
        )
        assert headers == {'X-API-Key': 'abc123'}
        assert httpx_auth is None
        assert cookies == {}

    def test_api_key_in_cookie(self):
        """Test API key placed in cookie."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {
                'type': 'api_key',
                'key': 'abc123',  # pragma: allowlist secret
                'key_name': 'session',
                'key_in': 'cookie',
            }
        )
        assert headers == {}
        assert httpx_auth is None
        assert cookies == {'session': 'abc123'}

    def test_api_key_default_header(self):
        """Test API key defaults to header location."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {'type': 'api_key', 'key': 'abc123'}  # pragma: allowlist secret
        )
        assert headers == {'api_key': 'abc123'}  # pragma: allowlist secret
        assert httpx_auth is None
        assert cookies == {}

    def test_api_key_missing_key(self):
        """Test API key auth raises ValueError when key is missing."""
        with pytest.raises(ValueError, match="API key auth requires 'key' field"):
            _build_additional_spec_auth({'type': 'api_key', 'key_name': 'X-Key'})

    def test_api_key_invalid_location(self):
        """Test API key auth raises ValueError for invalid location."""
        with pytest.raises(ValueError, match='Invalid key_in value'):
            _build_additional_spec_auth(
                {
                    'type': 'api_key',
                    'key': 'abc',  # pragma: allowlist secret
                    'key_in': 'body',
                }
            )

    def test_basic_auth(self):
        """Test basic auth returns httpx.BasicAuth instance."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {
                'type': 'basic',
                'username': 'user',
                'password': 'pass',  # pragma: allowlist secret
            }
        )
        assert headers == {}
        assert httpx_auth is not None
        assert cookies == {}
        import httpx

        assert isinstance(httpx_auth, httpx.BasicAuth)

    def test_basic_auth_missing_username(self):
        """Test basic auth raises ValueError when username is missing."""
        with pytest.raises(
            ValueError,
            match="Basic auth requires 'username' and 'password'",
        ):
            _build_additional_spec_auth(
                {'type': 'basic', 'password': 'pass'}  # pragma: allowlist secret
            )

    def test_basic_auth_missing_password(self):
        """Test basic auth raises ValueError when password is missing."""
        with pytest.raises(
            ValueError,
            match="Basic auth requires 'username' and 'password'",
        ):
            _build_additional_spec_auth({'type': 'basic', 'username': 'user'})

    def test_none_auth(self):
        """Test explicit none auth returns empty credentials."""
        headers, httpx_auth, cookies = _build_additional_spec_auth({'type': 'none'})
        assert headers == {}
        assert httpx_auth is None
        assert cookies == {}

    def test_empty_type(self):
        """Test empty type string returns empty credentials."""
        headers, httpx_auth, cookies = _build_additional_spec_auth({'type': ''})
        assert headers == {}
        assert httpx_auth is None
        assert cookies == {}

    def test_missing_type(self):
        """Test missing type key returns empty credentials."""
        headers, httpx_auth, cookies = _build_additional_spec_auth({})
        assert headers == {}
        assert httpx_auth is None
        assert cookies == {}

    def test_unsupported_type(self):
        """Test unsupported auth type raises ValueError."""
        with pytest.raises(ValueError, match='Unsupported auth type'):
            _build_additional_spec_auth({'type': 'oauth2'})

    def test_api_key_query_falls_back_to_header(self):
        """API key in query is not fully supported; falls back to header."""
        headers, httpx_auth, cookies = _build_additional_spec_auth(
            {
                'type': 'api_key',
                'key': 'abc123',  # pragma: allowlist secret
                'key_name': 'api_key',
                'key_in': 'query',
            }
        )
        assert headers == {'api_key': 'abc123'}  # pragma: allowlist secret
        assert httpx_auth is None
        assert cookies == {}


# --- Integration tests for additional specs in create_mcp_server ---


SAMPLE_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Test API', 'version': '1.0.0'},
    'paths': {},
}


def _make_mock_auth(headers=None, cookies=None, httpx_auth=None):
    """Create a mock auth provider."""
    mock_auth = MagicMock()
    mock_auth.is_configured.return_value = True
    mock_auth.get_auth_headers.return_value = headers or {}
    mock_auth.get_auth_params.return_value = {}
    mock_auth.get_auth_cookies.return_value = cookies or {}
    mock_auth.get_httpx_auth.return_value = httpx_auth
    mock_auth.provider_name = 'test_auth'
    return mock_auth


def _test_config(additional_specs_json):
    """Create a Config with the given additional_specs JSON string."""
    return Config(
        api_name='test',
        api_base_url='https://example.com/api',
        api_spec_url='https://example.com/openapi.json',
        additional_specs=additional_specs_json,
    )


class TestAdditionalSpecIntegration:
    """Integration tests for additional spec auth in create_mcp_server."""

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_no_auth_by_default(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs without auth field get no credentials."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={'Authorization': 'Bearer primary-token'}  # pragma: allowlist secret
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'partner',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2
        _, kwargs = mock_create_client.call_args_list[1]
        assert kwargs['headers'] == {}
        assert kwargs['auth'] is None
        assert kwargs['cookies'] == {}

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_inherit_auth(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs with auth=inherit receive primary credentials."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={'Authorization': 'Bearer primary-token'}  # pragma: allowlist secret
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'internal',
                        'spec_url': 'https://api.example.com/v2/spec.json',
                        'base_url': 'https://api.example.com/v2',
                        'auth': 'inherit',
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2
        _, kwargs = mock_create_client.call_args_list[1]
        assert kwargs['headers'] == {
            'Authorization': 'Bearer primary-token'  # pragma: allowlist secret
        }

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_per_spec_bearer_auth(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs with per-spec bearer use their own token."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={'Authorization': 'Bearer primary-token'}  # pragma: allowlist secret
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'partner',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'auth': {
                            'type': 'bearer',
                            'token': 'partner-token',  # pragma: allowlist secret
                        },
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2
        _, kwargs = mock_create_client.call_args_list[1]
        assert kwargs['headers'] == {
            'Authorization': 'Bearer partner-token'  # pragma: allowlist secret
        }
        assert kwargs['auth'] is None
        assert kwargs['cookies'] == {}

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_per_spec_api_key_auth(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs with per-spec API key use their own key."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={'Authorization': 'Bearer primary-token'}  # pragma: allowlist secret
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'partner',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'auth': {
                            'type': 'api_key',
                            'key': 'partner-key',  # pragma: allowlist secret
                            'key_name': 'X-Partner-Key',
                            'key_in': 'header',
                        },
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2
        _, kwargs = mock_create_client.call_args_list[1]
        assert kwargs['headers'] == {'X-Partner-Key': 'partner-key'}
        assert kwargs['auth'] is None
        assert kwargs['cookies'] == {}

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_invalid_auth_config_skips_spec(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs with invalid auth config are skipped."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'bad-auth',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'auth': {'type': 'bearer'},  # missing token
                    }
                ]
            )
        )

        create_mcp_server(config)

        # Only primary client should be created (additional spec skipped)
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_validation_failure_skips_by_default(
        self,
        mock_create_client,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Additional specs that fail validation are skipped by default."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'bad-spec',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                    }
                ]
            )
        )

        with patch(
            'awslabs.openapi_mcp_server.server.validate_openapi_spec',
            side_effect=[True, False],
        ):
            create_mcp_server(config)

        # Only primary client should be created
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_validation_failure_allowed_per_spec(
        self,
        mock_create_client,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Specs with allow_invalid=true load despite validation failure."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'loose-spec',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'allow_invalid': True,
                    }
                ]
            )
        )

        with patch(
            'awslabs.openapi_mcp_server.server.validate_openapi_spec',
            side_effect=[True, False],
        ):
            create_mcp_server(config)

        # Both primary and additional client should be created
        assert mock_create_client.call_count == 2

    @patch.dict('os.environ', {'ADDITIONAL_SPECS_ALLOW_INVALID': 'true'})
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_validation_failure_allowed_globally(
        self,
        mock_create_client,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """ADDITIONAL_SPECS_ALLOW_INVALID=true allows invalid specs."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'loose-spec',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                    }
                ]
            )
        )

        with patch(
            'awslabs.openapi_mcp_server.server.validate_openapi_spec',
            side_effect=[True, False],
        ):
            create_mcp_server(config)

        # Both primary and additional client should be created
        assert mock_create_client.call_count == 2

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_primary_creds_never_leak_by_default(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """Primary bearer token must NOT appear in additional spec client."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={
                'Authorization': 'Bearer super-secret-primary-token'  # pragma: allowlist secret
            }
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'attacker',
                        'spec_url': 'https://evil.com/spec.json',
                        'base_url': 'https://evil.com',
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2

        # Verify additional spec client does NOT have the primary token
        _, kwargs = mock_create_client.call_args_list[1]
        headers = kwargs.get('headers', {})
        auth = kwargs.get('auth')
        cookies = kwargs.get('cookies', {})

        assert 'Authorization' not in headers
        assert auth is None
        assert cookies == {}

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_inherit_case_insensitive(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """auth=INHERIT (case-insensitive) should inherit credentials."""
        mock_get_auth.return_value = _make_mock_auth(
            headers={'Authorization': 'Bearer primary-token'}  # pragma: allowlist secret
        )
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'internal',
                        'spec_url': 'https://api.example.com/v2/spec.json',
                        'base_url': 'https://api.example.com/v2',
                        'auth': 'INHERIT',
                    }
                ]
            )
        )

        create_mcp_server(config)

        assert mock_create_client.call_count == 2
        _, kwargs = mock_create_client.call_args_list[1]
        assert kwargs['headers'] == {
            'Authorization': 'Bearer primary-token'  # pragma: allowlist secret
        }

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_invalid_auth_type_boolean_skips_spec(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """auth=true (invalid type) should skip the spec."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'bad',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'auth': True,
                    }
                ]
            )
        )

        create_mcp_server(config)

        # Only primary client (spec with invalid auth skipped)
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_invalid_auth_type_list_skips_spec(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """auth=list (invalid type) should skip the spec."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'bad',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'auth': ['bearer'],
                    }
                ]
            )
        )

        create_mcp_server(config)

        # Only primary client (spec with invalid auth skipped)
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_allow_invalid_string_false_does_not_allow(
        self,
        mock_create_client,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """allow_invalid='false' (string) should NOT allow invalid specs."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'spec',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'allow_invalid': 'false',
                    }
                ]
            )
        )

        with patch(
            'awslabs.openapi_mcp_server.server.validate_openapi_spec',
            side_effect=[True, False],
        ):
            create_mcp_server(config)

        # Only primary — "false" string should NOT be truthy
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_allow_invalid_non_bool_non_str_falls_back(
        self,
        mock_create_client,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """allow_invalid as non-bool/non-str (e.g. int) falls back to global."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        mock_create_client.return_value = MagicMock()

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'spec',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                        'allow_invalid': 1,
                    }
                ]
            )
        )

        with patch(
            'awslabs.openapi_mcp_server.server.validate_openapi_spec',
            side_effect=[True, False],
        ):
            create_mcp_server(config)

        # Global default is false, so spec is skipped
        assert mock_create_client.call_count == 1

    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch(
        'awslabs.openapi_mcp_server.server.validate_openapi_spec',
        return_value=True,
    )
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
    def test_client_creation_failure_skips_spec(
        self,
        mock_create_client,
        mock_validate,
        mock_load_spec,
        mock_fastmcp,
        mock_openapi_provider,
        mock_get_auth,
    ):
        """If HttpClientFactory.create_client raises, spec is skipped."""
        mock_get_auth.return_value = _make_mock_auth()
        mock_fastmcp.return_value = MagicMock()
        mock_load_spec.return_value = SAMPLE_SPEC
        # First call (primary) succeeds, second call (additional) raises
        mock_create_client.side_effect = [
            MagicMock(),
            RuntimeError('connection pool exhausted'),
        ]

        config = _test_config(
            json.dumps(
                [
                    {
                        'name': 'broken',
                        'spec_url': 'https://partner.com/spec.json',
                        'base_url': 'https://partner.com',
                    }
                ]
            )
        )

        create_mcp_server(config)

        # Server should still be created (failure doesn't crash)
        mock_fastmcp.assert_called_once()
