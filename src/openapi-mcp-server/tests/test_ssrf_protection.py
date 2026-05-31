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
"""Tests for SSRF protection in multi-spec configuration."""

import json
import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server_async
from awslabs.openapi_mcp_server.utils.url_validator import (
    validate_spec_path,
    validate_url_for_spec,
)
from fastmcp.server.auth.ssrf import SSRFError
from unittest.mock import MagicMock, patch


PETSTORE_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Petstore', 'version': '1.0.0'},
    'paths': {
        '/pets': {
            'get': {
                'operationId': 'listPets',
                'summary': 'List pets',
                'tags': ['pet'],
                'responses': {'200': {'description': 'OK'}},
            },
        },
    },
}

EXTRA_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Payments', 'version': '1.0.0'},
    'paths': {
        '/payments': {
            'post': {
                'operationId': 'createPayment',
                'summary': 'Create payment',
                'responses': {'201': {'description': 'Created'}},
            },
        },
    },
}


def _config(**overrides):
    defaults = {
        'api_name': 'Test',
        'api_base_url': 'https://example.com',
        'api_spec_url': 'https://example.com/spec.json',
    }
    defaults.update(overrides)
    return Config(**defaults)


# --- URL Validation Tests ---


@pytest.mark.asyncio
async def test_validate_url_blocks_private_ips():
    """Private IPs are blocked by default."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['10.0.0.1'],
    ):
        with pytest.raises(SSRFError, match='blocked IP'):
            await validate_url_for_spec('https://internal.example.com/spec.json')


@pytest.mark.asyncio
async def test_validate_url_blocks_metadata_endpoint():
    """AWS metadata endpoint (169.254.169.254) is blocked."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['169.254.169.254'],
    ):
        with pytest.raises(SSRFError, match='blocked IP'):
            await validate_url_for_spec('https://metadata.internal/latest/meta-data')


@pytest.mark.asyncio
async def test_validate_url_blocks_loopback():
    """Loopback addresses are blocked."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['127.0.0.1'],
    ):
        with pytest.raises(SSRFError, match='blocked IP'):
            await validate_url_for_spec('https://localhost/spec.json')


@pytest.mark.asyncio
async def test_validate_url_blocks_http_by_default():
    """HTTP scheme is rejected when allow_http=False (default)."""
    with pytest.raises(SSRFError, match='not allowed'):
        await validate_url_for_spec('http://example.com/spec.json')


@pytest.mark.asyncio
async def test_validate_url_allows_http_when_opted_in():
    """HTTP scheme is allowed when allow_http=True."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34'],
    ):
        result = await validate_url_for_spec('http://example.com/spec.json', allow_http=True)
        assert result.hostname == 'example.com'


@pytest.mark.asyncio
async def test_validate_url_allows_private_when_opted_in():
    """Private IPs are allowed when allow_private_networks=True."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['10.0.0.1'],
    ):
        result = await validate_url_for_spec(
            'https://internal.example.com/spec.json',
            allow_private_networks=True,
        )
        assert result.hostname == 'internal.example.com'


@pytest.mark.asyncio
async def test_validate_url_allows_public_ip():
    """Public IPs pass validation."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34'],
    ):
        result = await validate_url_for_spec('https://example.com/spec.json')
        assert result.hostname == 'example.com'
        assert result.resolved_ips == ['93.184.216.34']


# --- Path Validation Tests ---


def test_validate_spec_path_blocks_etc():
    """Paths under /etc are blocked."""
    with patch('awslabs.openapi_mcp_server.utils.url_validator.Path.resolve') as mock_resolve:
        resolved = MagicMock()
        resolved.suffix = '.json'
        resolved.exists.return_value = True
        resolved.__str__ = lambda s: '/etc/secrets.json'
        mock_resolve.return_value = resolved
        with pytest.raises(SSRFError, match='blocked location'):
            validate_spec_path('/etc/secrets.json')


def test_validate_spec_path_blocks_non_spec_extension():
    """Non-spec file extensions are rejected."""
    with patch('awslabs.openapi_mcp_server.utils.url_validator.Path') as MockPath:
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.py'
        mock_resolved.exists.return_value = True
        mock_resolved.__str__ = lambda s: '/app/code.py'
        MockPath.return_value.resolve.return_value = mock_resolved
        with pytest.raises(SSRFError, match='spec file'):
            validate_spec_path('/app/code.py')


def test_validate_spec_path_enforces_allowed_dirs():
    """When allowed_dirs is set, path must be within them."""
    with patch('awslabs.openapi_mcp_server.utils.url_validator.Path') as MockPath:
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.json'
        mock_resolved.exists.return_value = True
        mock_resolved.__str__ = lambda s: '/data/other/spec.json'
        MockPath.return_value.resolve.return_value = mock_resolved
        MockPath.return_value.resolve.return_value = mock_resolved
        # Also mock Path(d).resolve() for allowed_dirs
        MockPath.side_effect = lambda p: (
            MagicMock(resolve=MagicMock(return_value=MagicMock(__str__=lambda s: str(p))))
            if p != '/data/other/spec.json'
            else MagicMock(resolve=MagicMock(return_value=mock_resolved))
        )
        with pytest.raises(SSRFError, match='not within allowed'):
            validate_spec_path('/data/other/spec.json', allowed_dirs=['/app/specs'])


def test_validate_spec_path_boundary_guard():
    """allowed_dirs '/app/specs' must NOT admit '/app/specs-evil/spec.json'."""
    with patch('awslabs.openapi_mcp_server.utils.url_validator.Path') as MockPath:
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.json'
        mock_resolved.exists.return_value = True
        mock_resolved.__str__ = lambda s: '/app/specs-evil/spec.json'
        MockPath.side_effect = lambda p: (
            MagicMock(resolve=MagicMock(return_value=MagicMock(__str__=lambda s: str(p))))
            if p != '/app/specs-evil/spec.json'
            else MagicMock(resolve=MagicMock(return_value=mock_resolved))
        )
        with pytest.raises(SSRFError, match='not within allowed'):
            validate_spec_path('/app/specs-evil/spec.json', allowed_dirs=['/app/specs'])


def test_validate_spec_path_accepts_valid_path(tmp_path):
    """A valid spec file within an allowed directory is accepted."""
    spec_file = tmp_path / 'openapi.json'
    spec_file.write_text('{}')
    result = validate_spec_path(str(spec_file), allowed_dirs=[str(tmp_path)])
    assert result == str(spec_file.resolve())


def test_validate_spec_path_rejects_symlink_escape(tmp_path):
    """A symlink that escapes the allowed directory is rejected."""
    allowed_dir = tmp_path / 'allowed'
    allowed_dir.mkdir()
    outside_file = tmp_path / 'secret.json'
    outside_file.write_text('{}')
    symlink = allowed_dir / 'escape.json'
    symlink.symlink_to(outside_file)
    with pytest.raises(SSRFError, match='not within allowed'):
        validate_spec_path(str(symlink), allowed_dirs=[str(allowed_dir)])


@pytest.mark.asyncio
async def test_validate_url_malformed_hostname_does_not_crash():
    """A malformed hostname raises SSRFError, not an uncaught exception."""
    with pytest.raises(SSRFError):
        await validate_url_for_spec('https://\x00invalid/spec.json')


@pytest.mark.asyncio
async def test_validate_url_oserror_from_dns_wrapped_as_ssrf():
    """OSError from DNS resolution is wrapped as SSRFError."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        side_effect=OSError('Network unreachable'),
    ):
        with pytest.raises(SSRFError, match='DNS resolution failed'):
            await validate_url_for_spec('https://unreachable.example.com/spec.json')


@pytest.mark.asyncio
async def test_validate_url_unicode_error_wrapped_as_ssrf():
    """UnicodeError from DNS resolution is wrapped as SSRFError."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        side_effect=UnicodeError('encoding error'),
    ):
        with pytest.raises(SSRFError, match='DNS resolution failed'):
            await validate_url_for_spec('https://bad-encoding.example.com/spec.json')


# --- Credential Isolation Tests ---


@pytest.mark.asyncio
async def test_additional_specs_do_not_inherit_primary_auth():
    """Additional specs must NOT receive the primary API's auth credentials."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
            }
        ]
    )
    config = _config(
        additional_specs=extra,
        auth_type='bearer',
        auth_token='SECRET_PRIMARY_TOKEN',
    )
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        await create_mcp_server_async(config)

        # Find the call for the additional spec client (second call to create_client)
        assert mock_client.call_count >= 2
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        extra_headers = extra_kwargs.get('headers') or {}

        # The primary token must NOT be forwarded
        assert 'Authorization' not in (extra_headers or {})
        assert extra_kwargs.get('auth') is None


@pytest.mark.asyncio
async def test_additional_specs_per_entry_auth():
    """Additional specs use their own per-entry auth configuration."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
                'auth_type': 'bearer',
                'auth_token': 'PARTNER_TOKEN',
            }
        ]
    )
    config = _config(
        additional_specs=extra,
        auth_type='bearer',
        auth_token='SECRET_PRIMARY_TOKEN',
    )
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
        patch('awslabs.openapi_mcp_server.auth.register.register_provider_by_type'),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        await create_mcp_server_async(config)

        # Second call is for the additional spec
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        extra_headers = extra_kwargs.get('headers') or {}

        # Partner's own token is used, NOT the primary
        assert extra_headers.get('Authorization') == 'Bearer PARTNER_TOKEN'


@pytest.mark.asyncio
async def test_validate_url_rejects_no_host():
    """URL without a host is rejected."""
    with pytest.raises(SSRFError, match='must have a host'):
        await validate_url_for_spec('https://')


@pytest.mark.asyncio
async def test_validate_url_http_port_defaults_to_80():
    """HTTP URL defaults to port 80."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34'],
    ):
        result = await validate_url_for_spec('http://example.com/spec.json', allow_http=True)
        assert result.port == 80


@pytest.mark.asyncio
async def test_validate_url_https_port_defaults_to_443():
    """HTTPS URL defaults to port 443."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34'],
    ):
        result = await validate_url_for_spec('https://example.com/spec.json')
        assert result.port == 443


def test_validate_spec_path_file_not_found():
    """Non-existent file raises FileNotFoundError."""
    with patch('awslabs.openapi_mcp_server.utils.url_validator.Path') as MockPath:
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.json'
        mock_resolved.exists.return_value = False
        mock_resolved.__str__ = lambda s: '/app/specs/missing.json'
        MockPath.return_value.resolve.return_value = mock_resolved
        with pytest.raises(FileNotFoundError, match='File not found'):
            validate_spec_path('/app/specs/missing.json')


# --- Integration: SSRF blocks additional specs ---


@pytest.mark.asyncio
async def test_additional_spec_with_private_ip_is_skipped():
    """Additional spec pointing to private IP is skipped with warning."""
    extra = json.dumps(
        [
            {
                'name': 'internal',
                'spec_url': 'https://internal-api/spec.json',
                'base_url': 'https://internal-api',
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['10.0.0.5'],
        ),
    ):
        mock_load.return_value = PETSTORE_SPEC
        mock_client.return_value = MagicMock()

        server = await create_mcp_server_async(config)
        tools = await server.list_tools()
        names = {t.name for t in tools}

        # Only primary spec tools should be registered
        assert 'listPets' in names
        # The additional spec should have been skipped
        assert 'createPayment' not in names


def test_validate_spec_path_blocks_windows_system_dir():
    """Windows system directories are blocked when os.name == 'nt'."""
    with (
        patch('awslabs.openapi_mcp_server.utils.url_validator.os.name', 'nt'),
        patch('awslabs.openapi_mcp_server.utils.url_validator.os.sep', '\\'),
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.os.environ',
            {'SYSTEMROOT': r'C:\Windows'},
        ),
        patch('awslabs.openapi_mcp_server.utils.url_validator.os.path') as mock_ospath,
        patch('awslabs.openapi_mcp_server.utils.url_validator.Path') as MockPath,
    ):
        mock_ospath.expanduser.return_value = r'C:\Users\admin'
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.json'
        mock_resolved.exists.return_value = True
        mock_resolved.__str__ = lambda s: r'C:\Windows\System32\config\spec.json'
        MockPath.return_value.resolve.return_value = mock_resolved
        with pytest.raises(SSRFError, match='blocked location'):
            validate_spec_path(r'C:\Windows\System32\config\spec.json')


@pytest.mark.asyncio
async def test_additional_spec_with_invalid_spec_path_is_skipped():
    """Additional spec with blocked spec_path is skipped."""
    extra = json.dumps(
        [
            {
                'name': 'internal',
                'spec_path': '/etc/shadow.json',
                'base_url': 'https://public-api.example.com',
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.Path',
        ) as MockPath,
    ):
        mock_resolved = MagicMock()
        mock_resolved.suffix = '.json'
        mock_resolved.exists.return_value = True
        mock_resolved.__str__ = lambda s: '/etc/shadow.json'
        MockPath.return_value.resolve.return_value = mock_resolved

        mock_load.return_value = PETSTORE_SPEC
        mock_client.return_value = MagicMock()

        server = await create_mcp_server_async(config)
        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert 'createPayment' not in names


@pytest.mark.asyncio
async def test_additional_spec_load_failure_is_skipped():
    """Additional spec that fails to load is skipped gracefully."""
    extra = json.dumps(
        [
            {
                'name': 'broken',
                'spec_url': 'https://broken.example.com/spec.json',
                'base_url': 'https://broken.example.com',
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'broken' in url:
                raise RuntimeError('Connection refused')
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        server = await create_mcp_server_async(config)
        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert 'listPets' in names
        assert 'createPayment' not in names


@pytest.mark.asyncio
async def test_additional_spec_with_private_spec_url_is_skipped():
    """Additional spec with private spec_url is skipped."""
    extra = json.dumps(
        [
            {
                'name': 'internal',
                'spec_url': 'https://internal-spec/openapi.json',
                'base_url': 'https://public-api.example.com',
            }
        ]
    )
    config = _config(additional_specs=extra)
    call_count = [0]

    async def mock_resolve(hostname, port=443):
        call_count[0] += 1
        if call_count[0] == 1:
            return ['93.184.216.34']  # base_url passes
        return ['10.0.0.5']  # spec_url blocked

    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            side_effect=mock_resolve,
        ),
    ):
        mock_load.return_value = PETSTORE_SPEC
        mock_client.return_value = MagicMock()

        server = await create_mcp_server_async(config)
        tools = await server.list_tools()
        names = {t.name for t in tools}
        assert 'createPayment' not in names


@pytest.mark.asyncio
async def test_additional_spec_api_key_query_warns():
    """API key in query is dropped with a warning (not sent, not silently ignored)."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
                'auth_type': 'api_key',
                'auth_api_key': 'MY_KEY',  # pragma: allowlist secret
                'auth_api_key_in': 'query',  # pragma: allowlist secret
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        await create_mcp_server_async(config)

        # The spec loads but the API key is NOT sent (query not supported)
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        extra_headers = extra_kwargs.get('headers') or {}
        assert 'X-API-Key' not in extra_headers
        assert extra_kwargs.get('cookies') is None


@pytest.mark.asyncio
async def test_additional_spec_api_key_cookie_is_passed():
    """API key in cookie is passed via cookies kwarg to client."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
                'auth_type': 'api_key',
                'auth_api_key': 'MY_KEY',  # pragma: allowlist secret
                'auth_api_key_in': 'cookie',  # pragma: allowlist secret
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        await create_mcp_server_async(config)

        # Second call is for the additional spec
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        assert extra_kwargs.get('cookies') == {'X-API-Key': 'MY_KEY'}


@pytest.mark.asyncio
async def test_additional_spec_basic_auth():
    """Additional spec with basic auth creates client with BasicAuth."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
                'auth_type': 'basic',
                'auth_username': 'user',
                'auth_password': 'pass',  # pragma: allowlist secret
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        await create_mcp_server_async(config)

        # Second call is for the additional spec
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        import httpx

        assert isinstance(extra_kwargs.get('auth'), httpx.BasicAuth)


@pytest.mark.asyncio
async def test_additional_spec_unrecognized_auth_type_warns():
    """Unrecognized auth_type logs warning and proceeds unauthenticated."""
    extra = json.dumps(
        [
            {
                'name': 'partner',
                'spec_url': 'https://partner.example.com/spec.json',
                'base_url': 'https://partner.example.com',
                'auth_type': 'bearter',  # typo
            }
        ]
    )
    config = _config(additional_specs=extra)
    with (
        patch('awslabs.openapi_mcp_server.server.load_openapi_spec') as mock_load,
        patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True),
        patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client') as mock_client,
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
    ):

        def load_side_effect(url='', path=''):
            if 'partner' in url:
                return EXTRA_SPEC
            return PETSTORE_SPEC

        mock_load.side_effect = load_side_effect
        mock_client.return_value = MagicMock()

        server = await create_mcp_server_async(config)
        tools = await server.list_tools()
        names = {t.name for t in tools}
        # Spec still loads, just unauthenticated
        assert 'createPayment' in names
        # Client created with no auth
        extra_call = mock_client.call_args_list[1]
        extra_kwargs = extra_call.kwargs if extra_call.kwargs else {}
        assert extra_kwargs.get('auth') is None
        assert not (extra_kwargs.get('headers') or {})
