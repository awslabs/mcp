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
"""Tests that the LOG_LEVEL environment variable documented in the README is honored."""

import pytest
import sys
from awslabs.openapi_mcp_server import get_log_level_from_env
from awslabs.openapi_mcp_server.server import main
from unittest.mock import MagicMock, patch


@pytest.mark.parametrize(
    'env_value, expected',
    [
        (None, 'INFO'),
        ('', 'INFO'),
        ('ERROR', 'ERROR'),
        ('debug', 'DEBUG'),
        (' Warning ', 'WARNING'),
        ('verbose', 'INFO'),
    ],
)
def test_get_log_level_from_env(monkeypatch, env_value, expected):
    """LOG_LEVEL is case-insensitive and falls back to INFO when unset or unrecognized."""
    if env_value is None:
        monkeypatch.delenv('LOG_LEVEL', raising=False)
    else:
        monkeypatch.setenv('LOG_LEVEL', env_value)

    assert get_log_level_from_env() == expected


def _run_main(argv):
    """Run main() with the given CLI arguments and return the mocked logger."""
    mock_config = MagicMock()
    mock_config.transport = 'stdio'
    with (
        patch.object(sys, 'argv', ['awslabs.openapi-mcp-server', *argv]),
        patch('awslabs.openapi_mcp_server.server.logger') as mock_logger,
        patch('awslabs.openapi_mcp_server.server.load_config', return_value=mock_config),
        patch('awslabs.openapi_mcp_server.server.create_mcp_server', return_value=MagicMock()),
        patch('awslabs.openapi_mcp_server.server.setup_signal_handlers'),
        patch('awslabs.openapi_mcp_server.server.asyncio.run', return_value=(0, 1, 0, 0)),
    ):
        main()
    return mock_logger


def _configured_level(mock_logger):
    """Return the level main() passed to logger.add."""
    mock_logger.add.assert_called_once()
    return mock_logger.add.call_args.kwargs['level']


def test_main_uses_log_level_env_var(monkeypatch):
    """The README configures LOG_LEVEL=ERROR; main() must apply it without --log-level."""
    monkeypatch.setenv('LOG_LEVEL', 'ERROR')

    assert _configured_level(_run_main([])) == 'ERROR'


def test_main_cli_log_level_overrides_env_var(monkeypatch):
    """An explicit --log-level wins over LOG_LEVEL."""
    monkeypatch.setenv('LOG_LEVEL', 'ERROR')

    assert _configured_level(_run_main(['--log-level', 'DEBUG'])) == 'DEBUG'


def test_main_defaults_to_info_without_env_var(monkeypatch):
    """Without LOG_LEVEL or --log-level the level stays INFO."""
    monkeypatch.delenv('LOG_LEVEL', raising=False)

    mock_logger = _run_main([])

    assert _configured_level(mock_logger) == 'INFO'
    mock_logger.warning.assert_not_called()


def test_main_warns_on_unrecognized_log_level_env_var(monkeypatch):
    """An unrecognized LOG_LEVEL falls back to INFO and is reported, not silently dropped."""
    monkeypatch.setenv('LOG_LEVEL', 'verbose')

    mock_logger = _run_main([])

    assert _configured_level(mock_logger) == 'INFO'
    warnings = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("LOG_LEVEL='verbose'" in message for message in warnings)
