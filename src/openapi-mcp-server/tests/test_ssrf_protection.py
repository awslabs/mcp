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

import httpx
import json
import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server_async
from awslabs.openapi_mcp_server.utils.openapi import _pinned_fetch, load_openapi_spec
from awslabs.openapi_mcp_server.utils.url_validator import (
    validate_spec_path,
    validate_url_for_spec,
)
from fastmcp.server.auth.ssrf import SSRFError, SSRFFetchError, ValidatedURL
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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

        def load_side_effect(url='', path='', validated_url=None, **kwargs):
            url = url or (validated_url.original_url if validated_url else '')
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


# --- DNS-pinned fetch: rebinding / redirect / size cap ---
#
# These directly exercise the TOCTOU SSRF fix: the spec is fetched by connecting
# ONLY to the IP(s) validation pinned, so a hostname that rebinds between the
# validation lookup and the fetch can never steer the connection.


class _FakeStreamResponse:
    """Minimal stand-in for an httpx streaming response."""

    def __init__(self, status_code=200, headers=None, chunks=(b'{}',)):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('error', request=None, response=None)

    def iter_bytes(self):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_fake_client(capture, response):
    """Build a fake httpx.Client class that records the URL it was asked to dial."""

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            capture['client_kwargs'] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, method, url, headers=None, extensions=None):
            capture.setdefault('requests', []).append(
                {'method': method, 'url': url, 'headers': headers, 'extensions': extensions}
            )
            return response

    return _FakeClient


def _validated(**overrides):
    defaults = {
        'original_url': 'https://spec.example.com/openapi.json',
        'hostname': 'spec.example.com',
        'port': 443,
        'path': '/openapi.json',
        'resolved_ips': ['93.184.216.34'],
    }
    defaults.update(overrides)
    return ValidatedURL(**defaults)


def test_pinned_fetch_connects_to_pinned_ip_with_host_and_sni():
    """The fetch dials the pinned IP literal, keeping Host + SNI = validated host."""
    capture = {}
    response = _FakeStreamResponse(chunks=(b'{"ok": true}',))
    with patch('httpx.Client', _make_fake_client(capture, response)):
        body = _pinned_fetch(_validated(), allow_http=False)

    assert body == b'{"ok": true}'
    req = capture['requests'][0]
    # Connection target is the pinned IP literal, not the hostname.
    assert req['url'] == 'https://93.184.216.34:443/openapi.json'
    assert req['headers']['Host'] == 'spec.example.com'
    assert req['extensions']['sni_hostname'] == 'spec.example.com'
    # Redirects are disabled on the client.
    assert capture['client_kwargs'].get('follow_redirects') is False


def test_pinned_fetch_refuses_redirect_to_metadata():
    """A 302 toward the metadata IP is rejected, not followed (redirect bypass)."""
    capture = {}
    response = _FakeStreamResponse(
        status_code=302, headers={'location': 'http://169.254.169.254/latest/meta-data/'}
    )
    with patch('httpx.Client', _make_fake_client(capture, response)):
        with pytest.raises(SSRFFetchError, match='redirect'):
            _pinned_fetch(_validated(), allow_http=False)

    # We only ever dialed the pinned public IP; the redirect target was never used.
    assert capture['requests'][0]['url'] == 'https://93.184.216.34:443/openapi.json'


def test_pinned_fetch_rejects_oversized_body_streaming():
    """A body exceeding the size cap is rejected while streaming."""
    capture = {}
    response = _FakeStreamResponse(chunks=(b'x' * 50, b'y' * 50))
    with patch('httpx.Client', _make_fake_client(capture, response)):
        with pytest.raises(SSRFFetchError, match='too large'):
            _pinned_fetch(_validated(), allow_http=False, max_size=10)


def test_pinned_fetch_rejects_oversized_body_content_length():
    """A body advertising an oversized Content-Length is rejected up front."""
    capture = {}
    response = _FakeStreamResponse(headers={'content-length': '999999'}, chunks=(b'{}',))
    with patch('httpx.Client', _make_fake_client(capture, response)):
        with pytest.raises(SSRFFetchError, match='too large'):
            _pinned_fetch(_validated(), allow_http=False, max_size=10)


def test_pinned_fetch_http_requires_opt_in():
    """An http:// pinned URL is refused unless allow_http is set."""
    vurl = _validated(original_url='http://spec.example.com/openapi.json', port=80)
    with pytest.raises(SSRFError, match='allow_insecure_http'):
        _pinned_fetch(vurl, allow_http=False)


@pytest.mark.asyncio
async def test_validate_url_rejects_mixed_public_and_private_ips():
    """A hostname resolving to a mix of public + private IPs is rejected at validation."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34', '169.254.169.254'],
    ):
        with pytest.raises(SSRFError, match='blocked IP'):
            await validate_url_for_spec('https://rebind.example.com/spec.json')


def test_load_openapi_spec_rebinding_never_hits_metadata_ip():
    """Rebinding PoC: validation resolves once to a public IP; the fetch is pinned to it.

    Simulates an authoritative DNS that would answer 93.184.216.34 first (passing
    the SSRF check) and 169.254.169.254 on any later lookup. Because the fetch
    connects to the IP validation pinned — and never re-resolves — the metadata
    IP is unreachable, and DNS is queried exactly once.
    """
    resolve_calls = {'n': 0}

    def rebinding_resolve(hostname, port=443):
        resolve_calls['n'] += 1
        # First answer public (passes), any subsequent answer is the metadata IP.
        return ['93.184.216.34'] if resolve_calls['n'] == 1 else ['169.254.169.254']

    capture = {}
    response = _FakeStreamResponse(chunks=(b'{"openapi": "3.0.0"}',))

    with (
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            side_effect=rebinding_resolve,
        ),
        patch('httpx.Client', _make_fake_client(capture, response)),
        patch(
            'awslabs.openapi_mcp_server.utils.openapi._parse_spec_bytes',
            return_value=PETSTORE_SPEC,
        ),
        patch(
            'awslabs.openapi_mcp_server.utils.openapi.validate_openapi_spec',
            return_value=True,
        ),
    ):
        # Unique host avoids the 1-hour spec cache colliding with other tests.
        spec = load_openapi_spec(url='https://rebind-poc.example.com/openapi.json')

    assert spec == PETSTORE_SPEC
    # DNS was resolved exactly once — the single source of truth for the target.
    assert resolve_calls['n'] == 1
    # Every connection went to the pinned public IP; the metadata IP was never dialed.
    dialed = [r['url'] for r in capture['requests']]
    assert dialed == ['https://93.184.216.34:443/openapi.json']
    assert all('169.254.169.254' not in url for url in dialed)


def test_load_openapi_spec_bare_url_is_validated_and_blocks_private():
    """The primary-spec path (bare url) is now validated: a private IP is blocked."""
    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['10.0.0.5'],
    ):
        with pytest.raises(SSRFError, match='blocked IP'):
            load_openapi_spec(url='https://internal-primary.example.com/openapi.json')


def test_pinned_fetch_rejects_disallowed_scheme():
    """A non-http(s) scheme on the validated URL is rejected."""
    vurl = _validated(original_url='ftp://spec.example.com/openapi.json')
    with pytest.raises(SSRFError, match='not allowed'):
        _pinned_fetch(vurl, allow_http=False)


def test_pinned_fetch_tries_next_ip_on_transient_error():
    """A transient error on the first pinned IP falls through to the next."""
    capture = {}
    good = _FakeStreamResponse(chunks=(b'{"ok": true}',))

    class _FlakyClient:
        _calls = {'n': 0}

        def __init__(self, *args, **kwargs):
            capture['client_kwargs'] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, method, url, headers=None, extensions=None):
            capture.setdefault('urls', []).append(url)
            type(self)._calls['n'] += 1
            if type(self)._calls['n'] == 1:
                raise httpx.ConnectError('connection refused')
            return good

    vurl = _validated(resolved_ips=['93.184.216.34', '198.51.100.7'])
    with patch('httpx.Client', _FlakyClient):
        body = _pinned_fetch(vurl, allow_http=False)

    assert body == b'{"ok": true}'
    # Both pinned IPs were attempted, in order.
    assert capture['urls'] == [
        'https://93.184.216.34:443/openapi.json',
        'https://198.51.100.7:443/openapi.json',
    ]


def test_pinned_fetch_raises_last_error_when_all_ips_fail():
    """When every pinned IP errors transiently, the last error is raised."""

    class _AlwaysFailClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            raise httpx.ConnectError('down')

    vurl = _validated(resolved_ips=['93.184.216.34', '198.51.100.7'])
    with patch('httpx.Client', _AlwaysFailClient):
        with pytest.raises(httpx.ConnectError, match='down'):
            _pinned_fetch(vurl, allow_http=False)


def test_pinned_fetch_no_resolved_ips():
    """A ValidatedURL with no IPs surfaces a clear SSRFFetchError."""
    vurl = _validated(resolved_ips=[])
    with pytest.raises(SSRFFetchError, match='No resolved IPs'):
        _pinned_fetch(vurl, allow_http=False)


def test_validate_url_sync_bridges_from_running_loop():
    """_validate_url_sync works when called from inside a running event loop.

    load_openapi_spec is synchronous but is invoked from create_mcp_server_async;
    the async validator must be driven without touching the live loop.
    """
    from awslabs.openapi_mcp_server.utils.openapi import _validate_url_sync

    async def _drive():
        # Calling the sync helper from within this running loop must not raise
        # "asyncio.run() cannot be called from a running event loop".
        return _validate_url_sync(
            'https://spec.example.com/openapi.json',
            allow_http=False,
            allow_private_networks=False,
        )

    with patch(
        'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
        return_value=['93.184.216.34'],
    ):
        import asyncio

        result = asyncio.run(_drive())

    assert result.hostname == 'spec.example.com'
    assert result.resolved_ips == ['93.184.216.34']


def test_parse_spec_bytes_uses_prance_when_available():
    """When prance is available, its resolved specification is returned."""
    from awslabs.openapi_mcp_server.utils import openapi as openapi_mod

    resolved = {'openapi': '3.0.0', 'info': {'title': 'Resolved', 'version': '1'}}
    with (
        patch.object(openapi_mod, 'PRANCE_AVAILABLE', True),
        patch.object(openapi_mod, 'ResolvingParser') as mock_parser,
    ):
        mock_parser.return_value.specification = resolved
        result = openapi_mod._parse_spec_bytes(b'{"openapi": "3.0.0"}')

    assert result == resolved


def test_parse_spec_bytes_falls_back_to_json_when_prance_fails():
    """A prance failure falls back to basic JSON parsing."""
    from awslabs.openapi_mcp_server.utils import openapi as openapi_mod

    with (
        patch.object(openapi_mod, 'PRANCE_AVAILABLE', True),
        patch.object(openapi_mod, 'ResolvingParser', side_effect=Exception('prance boom')),
    ):
        result = openapi_mod._parse_spec_bytes(b'{"openapi": "3.0.0", "x": 1}')

    assert result == {'openapi': '3.0.0', 'x': 1}


def test_parse_spec_bytes_falls_back_to_yaml_when_not_json():
    """Non-JSON content is parsed as YAML."""
    from awslabs.openapi_mcp_server.utils import openapi as openapi_mod

    yaml_body = b'openapi: "3.0.0"\ninfo:\n  title: YAML API\n  version: "1"\n'
    with patch.object(openapi_mod, 'PRANCE_AVAILABLE', False):
        result = openapi_mod._parse_spec_bytes(yaml_body)

    assert result['info']['title'] == 'YAML API'


def test_load_openapi_spec_does_not_retry_ssrf_failures():
    """An SSRFFetchError from the fetch is raised immediately, not retried away."""
    with (
        patch(
            'awslabs.openapi_mcp_server.utils.url_validator.resolve_hostname',
            return_value=['93.184.216.34'],
        ),
        patch(
            'awslabs.openapi_mcp_server.utils.openapi._pinned_fetch',
            side_effect=SSRFFetchError('redirect refused'),
        ) as mock_fetch,
    ):
        with pytest.raises(SSRFFetchError, match='redirect refused'):
            load_openapi_spec(url='https://no-retry.example.com/openapi.json')

    # Exactly one attempt — security failures must not be retried.
    assert mock_fetch.call_count == 1


def test_pinned_fetch_http_opt_in_uses_no_sni():
    """An opted-in http:// fetch dials the pinned IP with no TLS SNI extension."""
    capture = {}
    response = _FakeStreamResponse(chunks=(b'{}',))
    vurl = _validated(original_url='http://spec.example.com/openapi.json', port=80)
    with patch('httpx.Client', _make_fake_client(capture, response)):
        _pinned_fetch(vurl, allow_http=True)

    req = capture['requests'][0]
    assert req['url'] == 'http://93.184.216.34:80/openapi.json'
    assert req['headers']['Host'] == 'spec.example.com'
    # No SNI extension for plaintext http.
    assert req['extensions'] == {}
