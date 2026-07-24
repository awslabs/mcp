# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for multi-tenant startup wiring in ``server.main()`` (Task 10.1).

Validates: Requirements 8.1, 9.2, 13.8
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts, server
from awslabs.aws_healthomics_mcp_server.config import ServerConfig, TransportConfigError
from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import InboundExplicitCredentials
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import InboundJwtExchange
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RegistryRoleResolver,
    StaticRoleResolver,
)
from awslabs.aws_healthomics_mcp_server.mechanisms.sigv4 import InboundSigV4
from awslabs.aws_healthomics_mcp_server.middleware import IdentityMiddleware
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    DefaultCredentialResolver,
    RequestScopedCredentialResolver,
    get_active_resolver,
    set_active_resolver,
)
from unittest.mock import MagicMock, patch


def _config(
    *,
    transport='streamable-http',
    multi_tenant=False,
    inbound_mechanisms=(),
    host='127.0.0.1',
    port=8000,
    path='/mcp',
    jwt_session_duration=consts.DEFAULT_JWT_SESSION_DURATION,
    jwt_role_arn=None,
    jwt_role_registry=None,
):
    """Build a ServerConfig for tests."""
    return ServerConfig(
        transport=transport,
        host=host,
        port=port,
        path=path,
        multi_tenant=multi_tenant,
        inbound_mechanisms=tuple(inbound_mechanisms),
        jwt_session_duration=jwt_session_duration,
        jwt_role_arn=jwt_role_arn,
        jwt_role_registry=jwt_role_registry,
    )


@pytest.fixture(autouse=True)
def _restore_active_resolver():
    """Restore the default active resolver after each test (Phase 1 default)."""
    set_active_resolver(DefaultCredentialResolver())
    yield
    set_active_resolver(DefaultCredentialResolver())


class TestSingleTenantPath:
    """Single-tenant mode keeps the Phase 1 path unchanged."""

    def test_single_tenant_uses_transport_selector_and_default_resolver(self):
        """Disabled multi-tenant uses TransportSelector.start and keeps the default resolver."""
        config = _config(multi_tenant=False)

        with (
            patch.object(server, 'parse_config', return_value=config),
            patch.object(server.TransportSelector, 'start') as mock_start,
            patch.object(server, '_run_multi_tenant') as mock_run_mt,
        ):
            server.main()

        mock_start.assert_called_once_with(server.mcp, config)
        mock_run_mt.assert_not_called()
        # The active resolver remains the Phase 1 default.
        assert isinstance(get_active_resolver(), DefaultCredentialResolver)


class TestMultiTenantWiring:
    """Multi-tenant mode installs the request-scoped resolver and wraps the app."""

    def test_main_routes_to_multi_tenant(self):
        """Enabled multi-tenant routes to _run_multi_tenant, not TransportSelector.start."""
        config = _config(multi_tenant=True, inbound_mechanisms=('sigv4',))

        with (
            patch.object(server, 'parse_config', return_value=config),
            patch.object(server.TransportSelector, 'start') as mock_start,
            patch.object(server, '_run_multi_tenant') as mock_run_mt,
        ):
            server.main()

        mock_run_mt.assert_called_once_with(server.mcp, config)
        mock_start.assert_not_called()

    def test_run_multi_tenant_installs_request_scoped_resolver(self):
        """_run_multi_tenant installs a RequestScopedCredentialResolver as active."""
        config = _config(multi_tenant=True, inbound_mechanisms=('sigv4',))
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock(name='base_app')

        with patch.object(server, '_serve_asgi_app') as mock_serve:
            server._run_multi_tenant(mock_mcp, config)

        assert isinstance(get_active_resolver(), RequestScopedCredentialResolver)
        mock_serve.assert_called_once()

    def test_streamable_http_app_is_wrapped_with_identity_middleware(self):
        """The streamable-http base app is wrapped with IdentityMiddleware before serving."""
        config = _config(
            transport='streamable-http',
            multi_tenant=True,
            inbound_mechanisms=('sigv4', 'explicit'),
        )
        mock_mcp = MagicMock()
        base_app = MagicMock(name='base_app')
        mock_mcp.streamable_http_app.return_value = base_app

        with patch.object(server, '_serve_asgi_app') as mock_serve:
            server._run_multi_tenant(mock_mcp, config)

        mock_mcp.streamable_http_app.assert_called_once()
        mock_mcp.sse_app.assert_not_called()
        served_app = mock_serve.call_args[0][1]
        assert isinstance(served_app, IdentityMiddleware)
        assert served_app.app is base_app

    def test_sse_app_is_wrapped_with_identity_middleware(self):
        """The sse base app is wrapped with IdentityMiddleware before serving."""
        config = _config(
            transport='sse',
            multi_tenant=True,
            inbound_mechanisms=('sigv4',),
        )
        mock_mcp = MagicMock()
        base_app = MagicMock(name='base_app')
        mock_mcp.sse_app.return_value = base_app

        with patch.object(server, '_serve_asgi_app') as mock_serve:
            server._run_multi_tenant(mock_mcp, config)

        mock_mcp.sse_app.assert_called_once()
        mock_mcp.streamable_http_app.assert_not_called()
        served_app = mock_serve.call_args[0][1]
        assert isinstance(served_app, IdentityMiddleware)
        assert served_app.app is base_app

    def test_network_bind_settings_applied(self):
        """Host/port/path bind settings are applied onto the FastMCP instance."""
        config = _config(
            transport='streamable-http',
            multi_tenant=True,
            inbound_mechanisms=('sigv4',),
            host='0.0.0.0',
            port=9001,
            path='/custom',
        )
        mock_mcp = MagicMock()
        mock_mcp.streamable_http_app.return_value = MagicMock()

        with patch.object(server, '_serve_asgi_app'):
            server._run_multi_tenant(mock_mcp, config)

        assert mock_mcp.settings.host == '0.0.0.0'
        assert mock_mcp.settings.port == 9001
        assert mock_mcp.settings.streamable_http_path == '/custom'


class TestMechanismBuilding:
    """The enabled mechanisms list is built from the resolved config."""

    def test_builds_sigv4_and_explicit(self):
        """'sigv4' and 'explicit' map to their concrete mechanisms."""
        config = _config(inbound_mechanisms=('sigv4', 'explicit'))
        built = server._build_inbound_mechanisms(config)

        assert [type(m) for m in built] == [InboundSigV4, InboundExplicitCredentials]

    def test_builds_jwt_with_static_role_arn(self):
        """'jwt' with a static role ARN builds a StaticRoleResolver-backed exchange."""
        role_arn = 'arn:aws:iam::123456789012:role/jwt-callers'
        config = _config(inbound_mechanisms=('jwt',), jwt_role_arn=role_arn)

        built = server._build_inbound_mechanisms(config)

        assert len(built) == 1
        assert isinstance(built[0], InboundJwtExchange)
        assert isinstance(built[0].role_resolver, StaticRoleResolver)
        assert built[0].role_resolver.resolve({'sub': 'anyone'}).role_arn == role_arn
        assert built[0].role_resolver.resolve({'sub': 'anyone'}).external_id is None

    def test_jwt_static_resolver_uses_configured_session_duration(self):
        """The validated session duration is injected into the JWT exchange."""
        config = _config(
            inbound_mechanisms=('jwt',),
            jwt_role_arn='arn:aws:iam::123456789012:role/jwt-callers',
            jwt_session_duration=7200,
        )

        built = server._build_inbound_mechanisms(config)

        assert isinstance(built[0], InboundJwtExchange)
        assert built[0].session_duration == 7200

    def test_builds_jwt_with_registry_source(self):
        """'jwt' with a registry source builds a RegistryRoleResolver-backed exchange."""
        config = _config(
            inbound_mechanisms=('jwt',),
            jwt_role_registry='dynamodb://customer-roles',
        )

        built = server._build_inbound_mechanisms(config)

        assert len(built) == 1
        assert isinstance(built[0], InboundJwtExchange)
        assert isinstance(built[0].role_resolver, RegistryRoleResolver)
        # Registry config must not build the static resolver (single-source selection).
        assert not isinstance(built[0].role_resolver, StaticRoleResolver)

    def test_static_role_arn_does_not_build_registry_resolver(self):
        """'jwt' with a static ARN builds only the static resolver, never the registry one.

        Guards the single-resolver-source selection so a static-ARN config can never
        be wired to the registry-backed resolver.

        Validates: Requirements Backward Compatibility, Configuration surface and
        single-resolver selection.
        """
        config = _config(
            inbound_mechanisms=('jwt',),
            jwt_role_arn='arn:aws:iam::123456789012:role/jwt-callers',
        )

        built = server._build_inbound_mechanisms(config)

        assert isinstance(built[0], InboundJwtExchange)
        assert isinstance(built[0].role_resolver, StaticRoleResolver)
        assert not isinstance(built[0].role_resolver, RegistryRoleResolver)

    def test_jwt_registry_resolver_uses_configured_session_duration(self):
        """The validated session duration is injected into the registry-backed exchange.

        Complements the static-resolver session-duration coverage so the injection is
        asserted for both resolver types.

        Validates: Requirements Configuration surface and single-resolver selection.
        """
        config = _config(
            inbound_mechanisms=('jwt',),
            jwt_role_registry='dynamodb://customer-roles',
            jwt_session_duration=1800,
        )

        built = server._build_inbound_mechanisms(config)

        assert isinstance(built[0], InboundJwtExchange)
        assert isinstance(built[0].role_resolver, RegistryRoleResolver)
        assert built[0].session_duration == 1800

    def test_mechanisms_built_in_config_order(self):
        """The mechanisms list mirrors the order of config.inbound_mechanisms."""
        config = _config(inbound_mechanisms=('explicit', 'sigv4'))
        built = server._build_inbound_mechanisms(config)

        assert [m.name for m in built] == ['explicit', 'sigv4']

    def test_jwt_without_role_source_raises_config_error(self):
        """'jwt' enabled with neither role source configured raises a config error."""
        config = _config(inbound_mechanisms=('jwt',))

        with pytest.raises(TransportConfigError):
            server._build_inbound_mechanisms(config)

    def test_jwt_with_invalid_registry_source_raises_config_error(self):
        """An unsupported registry source value fails closed at startup."""
        config = _config(
            inbound_mechanisms=('jwt',),
            jwt_role_registry='ftp://not-supported',
        )

        with pytest.raises(TransportConfigError):
            server._build_inbound_mechanisms(config)


class TestMultiTenantRequiresMechanism:
    """Multi-tenant mode with no inbound mechanisms is rejected before serving."""

    def test_run_multi_tenant_without_mechanisms_raises(self):
        """_run_multi_tenant raises a config error when no mechanisms are enabled."""
        config = _config(multi_tenant=True, inbound_mechanisms=())
        mock_mcp = MagicMock()

        with patch.object(server, '_serve_asgi_app') as mock_serve:
            with pytest.raises(TransportConfigError):
                server._run_multi_tenant(mock_mcp, config)

        # The server never bound and the resolver was not swapped.
        mock_serve.assert_not_called()
        assert isinstance(get_active_resolver(), DefaultCredentialResolver)

    def test_main_exits_when_no_mechanisms_enabled(self):
        """main() exits with code 1 and never serves when no mechanism is enabled."""
        config = _config(multi_tenant=True, inbound_mechanisms=())

        with (
            patch.object(server, 'parse_config', return_value=config),
            patch.object(server, '_serve_asgi_app') as mock_serve,
            pytest.raises(SystemExit) as exc_info,
        ):
            server.main()

        assert exc_info.value.code == 1
        mock_serve.assert_not_called()
        assert isinstance(get_active_resolver(), DefaultCredentialResolver)


class TestConflictingRoleSourcesExit:
    """Configuring both JWT role-resolution sources is rejected before serving."""

    def test_main_exits_when_both_role_sources_configured(self):
        """main() exits with code 1 and never serves when both role sources are set.

        parse_config performs the single-resolver-source selection and rejects
        configuring both MCP_JWT_ROLE_ARN and MCP_JWT_ROLE_REGISTRY at once by raising
        a config error; main() surfaces that as a non-zero exit without starting any
        transport, so the conflicting configuration fails closed.

        Validates: Requirements Configuration surface and single-resolver selection.
        """
        conflict = TransportConfigError(
            consts.ERROR_CONFLICTING_ROLE_RESOLUTION_SOURCES.format(
                consts.MCP_JWT_ROLE_ARN_ENV, consts.MCP_JWT_ROLE_REGISTRY_ENV
            )
        )

        with (
            patch.object(server, 'parse_config', side_effect=conflict),
            patch.object(server.TransportSelector, 'start') as mock_start,
            patch.object(server, '_run_multi_tenant') as mock_run_mt,
            patch.object(server, '_serve_asgi_app') as mock_serve,
            pytest.raises(SystemExit) as exc_info,
        ):
            server.main()

        assert exc_info.value.code == 1
        # Neither the single-tenant nor the multi-tenant serving path was entered.
        mock_start.assert_not_called()
        mock_run_mt.assert_not_called()
        mock_serve.assert_not_called()
        # The active resolver was never swapped to the request-scoped one.
        assert isinstance(get_active_resolver(), DefaultCredentialResolver)


class TestJwtMissingRoleArnExits:
    """A missing JWT role ARN logs an error and exits without starting a server."""

    def test_main_exits_when_jwt_role_arn_missing(self, monkeypatch):
        """main() exits with code 1 and never serves when JWT role ARN is missing."""
        monkeypatch.delenv(consts.MCP_JWT_ROLE_ARN_ENV, raising=False)
        config = _config(multi_tenant=True, inbound_mechanisms=('jwt',))

        with (
            patch.object(server, 'parse_config', return_value=config),
            patch.object(server, '_serve_asgi_app') as mock_serve,
            pytest.raises(SystemExit) as exc_info,
        ):
            server.main()

        assert exc_info.value.code == 1
        mock_serve.assert_not_called()
        # The active resolver must not have been swapped to the request-scoped one
        # because the error is raised before set_active_resolver is called.
        assert isinstance(get_active_resolver(), DefaultCredentialResolver)


class TestServeEntryPoint:
    """The serve entry point builds a uvicorn server from FastMCP settings."""

    def test_serve_asgi_app_runs_uvicorn_with_settings(self):
        """_serve_asgi_app configures uvicorn from mcp.settings and serves the app."""
        mock_mcp = MagicMock()
        mock_mcp.settings.host = '0.0.0.0'
        mock_mcp.settings.port = 9002
        mock_mcp.settings.log_level = 'INFO'
        app = MagicMock(name='wrapped_app')

        fake_server = MagicMock()
        with (
            patch('uvicorn.Config') as mock_config,
            patch('uvicorn.Server', return_value=fake_server) as mock_server_cls,
            patch.object(server, 'anyio') as mock_anyio,
        ):
            server._serve_asgi_app(mock_mcp, app)

        mock_config.assert_called_once_with(app, host='0.0.0.0', port=9002, log_level='info')
        mock_server_cls.assert_called_once_with(mock_config.return_value)
        mock_anyio.run.assert_called_once_with(fake_server.serve)
