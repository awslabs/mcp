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

"""Unit tests for transport start and the configuration error table.

These example-based tests complement the property-based tests in
``test_config.py`` and ``test_transport_exposure.py``. They verify that
``TransportSelector.start`` invokes ``mcp.run`` with exactly the selected
transport mode and applies the correct network bind settings, and that the
startup error table (unsupported transport, invalid port, invalid host) is
rejected during configuration parsing and handled by ``server.main()`` by
logging a descriptive message and exiting non-zero without binding.

Test docstrings refer to requirements by name (never by number) per project
steering.
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    ServerConfig,
    TransportConfigError,
    UnsupportedTransportError,
    parse_config,
)
from awslabs.aws_healthomics_mcp_server.transport import TransportSelector
from mcp.server.fastmcp import FastMCP
from types import SimpleNamespace
from unittest.mock import MagicMock


# Environment variables that parse_config reads. They must be unset for every
# test so that the developer's shell environment never pollutes the parsed
# configuration or the selected transport.
_MCP_ENV_VARS = (
    consts.MCP_TRANSPORT_ENV,
    consts.MCP_HOST_ENV,
    consts.MCP_PORT_ENV,
    consts.MCP_PATH_ENV,
)


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch):
    """Ensure no MCP_* transport/network env vars leak into parsing."""
    for name in _MCP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _make_mcp() -> MagicMock:
    """Build a mock FastMCP whose ``run`` and ``settings`` can be inspected.

    ``settings`` is a plain namespace (not a mock) so that attribute
    assignments are observable and, crucially, attributes that were never
    assigned remain genuinely absent.
    """
    mcp = MagicMock(spec=FastMCP)
    mcp.settings = SimpleNamespace()
    return mcp


# ---------------------------------------------------------------------------
# TransportSelector.start — transport mode and bind settings
# ---------------------------------------------------------------------------


def test_start_stdio_runs_stdio_without_bind_settings():
    """start() runs the stdio transport with exactly the selected mode.

    Validates: Requirements Transport selection.
    """
    mcp = _make_mcp()
    config = ServerConfig(transport='stdio', host='127.0.0.1', port=8000, path='/mcp')

    TransportSelector.start(mcp, config)

    mcp.run.assert_called_once_with(transport='stdio')
    # stdio must not apply any network bind settings.
    assert not hasattr(mcp.settings, 'host')
    assert not hasattr(mcp.settings, 'port')
    assert not hasattr(mcp.settings, 'streamable_http_path')
    assert not hasattr(mcp.settings, 'sse_path')


def test_start_streamable_http_applies_settings_and_runs_mode():
    """start() applies host/port/streamable_http_path and runs streamable-http.

    Validates: Requirements Transport selection, Network bind configuration.
    """
    mcp = _make_mcp()
    config = ServerConfig(transport='streamable-http', host='127.0.0.1', port=9001, path='/custom')

    TransportSelector.start(mcp, config)

    assert mcp.settings.host == '127.0.0.1'
    assert mcp.settings.port == 9001
    assert mcp.settings.streamable_http_path == '/custom'
    mcp.run.assert_called_once_with(transport='streamable-http')


def test_start_sse_applies_settings_and_runs_mode():
    """start() applies host/port/sse_path and runs the sse transport.

    Validates: Requirements Transport selection, Network bind configuration.
    """
    mcp = _make_mcp()
    config = ServerConfig(transport='sse', host='127.0.0.1', port=9002, path='/events')

    TransportSelector.start(mcp, config)

    assert mcp.settings.host == '127.0.0.1'
    assert mcp.settings.port == 9002
    assert mcp.settings.sse_path == '/events'
    mcp.run.assert_called_once_with(transport='sse')


# ---------------------------------------------------------------------------
# Configuration error table — parse_config rejects invalid configuration
# ---------------------------------------------------------------------------


def test_parse_config_rejects_unsupported_transport():
    """An unsupported transport value is rejected during parsing.

    Validates: Requirements Transport selection.
    """
    with pytest.raises(UnsupportedTransportError):
        parse_config(['--transport', 'grpc'])


def test_parse_config_rejects_invalid_port():
    """A network transport with an out-of-range port is rejected during parsing.

    Validates: Requirements Network bind configuration.
    """
    with pytest.raises(TransportConfigError):
        parse_config(['--transport', 'streamable-http', '--port', '0'])


def test_parse_config_rejects_non_integer_port():
    """A network transport with a non-integer port is rejected during parsing.

    Validates: Requirements Network bind configuration.
    """
    with pytest.raises(TransportConfigError):
        parse_config(['--transport', 'streamable-http', '--port', 'not-a-number'])


def test_parse_config_rejects_invalid_host():
    """A network transport with an invalid host is rejected during parsing.

    Validates: Requirements Network bind configuration.
    """
    with pytest.raises(TransportConfigError):
        parse_config(['--transport', 'sse', '--host', 'not a valid host'])


# ---------------------------------------------------------------------------
# server.main() error handling — log a descriptive message, exit non-zero,
# and do not start any transport
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'error',
    [
        UnsupportedTransportError(consts.ERROR_UNSUPPORTED_TRANSPORT.format('grpc', 'stdio')),
        TransportConfigError(consts.ERROR_INVALID_PORT.format('0')),
        TransportConfigError(consts.ERROR_INVALID_HOST.format('bad host')),
    ],
    ids=['unsupported-transport', 'invalid-port', 'invalid-host'],
)
def test_main_logs_and_exits_without_starting_transport(monkeypatch, error):
    """main() logs the config error, exits non-zero, and never starts a transport.

    Validates: Requirements Transport selection, Network bind configuration.
    """
    from awslabs.aws_healthomics_mcp_server import server

    def _raise(*_args, **_kwargs):
        raise error

    logged_errors: list[str] = []
    monkeypatch.setattr(server, 'parse_config', _raise)
    monkeypatch.setattr(server.logger, 'error', lambda message: logged_errors.append(message))

    start_mock = MagicMock()
    monkeypatch.setattr(server.TransportSelector, 'start', start_mock)

    with pytest.raises(SystemExit) as exc_info:
        server.main()

    # Non-zero exit status and no transport started.
    assert exc_info.value.code != 0
    start_mock.assert_not_called()
    # A descriptive error message was logged (the error text itself).
    assert logged_errors == [str(error)]
