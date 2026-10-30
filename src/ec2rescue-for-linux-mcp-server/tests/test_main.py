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

"""Tests for the main function in server.py."""

import inspect
import os
import pytest
import sys
from awslabs.ec2rescue_for_linux_mcp_server import ec2rl as ec2rl_module
from awslabs.ec2rescue_for_linux_mcp_server.server import (
    _default_mod_dir,
    _parse_args,
    main,
    mcp,
)
from unittest.mock import patch


@pytest.fixture()
def restore_registry():
    """Snapshot and restore EC2RL_MODULES around a test."""
    prev = dict(ec2rl_module.EC2RL_MODULES)
    yield
    ec2rl_module.EC2RL_MODULES.clear()
    ec2rl_module.EC2RL_MODULES.update(prev)


@pytest.fixture()
def restore_mcp_settings():
    """Snapshot and restore mcp.settings.host/port around a test."""
    prev_host = mcp.settings.host
    prev_port = mcp.settings.port
    yield
    mcp.settings.host = prev_host
    mcp.settings.port = prev_port


class TestParseArgs:
    """Tests for the _parse_args helper."""

    def test_defaults(self):
        """Default args: remediate=False."""
        args = _parse_args([])
        assert args.remediate is False

    def test_remediate_flag(self):
        """--remediate sets remediate=True."""
        args = _parse_args(['--remediate'])
        assert args.remediate is True

    def test_default_transport_is_stdio(self):
        """Default transport/host/port: stdio with no host/port override."""
        args = _parse_args([])
        assert args.transport == 'stdio'
        assert args.host is None
        assert args.port is None

    def test_transport_streamable_http(self):
        """--transport streamable-http parses through verbatim."""
        args = _parse_args(['--transport', 'streamable-http'])
        assert args.transport == 'streamable-http'

    def test_host_port_parsed(self):
        """--host / --port populate the namespace; port is coerced to int."""
        args = _parse_args(['--host', '192.168.1.100', '--port', '9000'])
        assert args.host == '192.168.1.100'
        assert args.port == 9000

    def test_invalid_transport_rejected(self):
        """Unsupported transport values cause argparse to exit."""
        with pytest.raises(SystemExit):
            _parse_args(['--transport', 'sse'])

    def test_allow_perfimpact_default_false(self):
        """--allow-perfimpact defaults to False."""
        args = _parse_args([])
        assert args.allow_perfimpact is False

    def test_allow_perfimpact_flag(self):
        """--allow-perfimpact sets the namespace attribute."""
        args = _parse_args(['--allow-perfimpact'])
        assert args.allow_perfimpact is True

    def test_allow_install_default_false(self):
        """--allow-install defaults to False."""
        args = _parse_args([])
        assert args.allow_install is False

    def test_allow_install_flag(self):
        """--allow-install sets the namespace attribute."""
        args = _parse_args(['--allow-install'])
        assert args.allow_install is True


class TestDefaultModDir:
    """Tests for _default_mod_dir."""

    def test_returns_existing_path(self):
        """Returns an existing directory when mod.d is bundled."""
        result = _default_mod_dir()
        # Result should be either a real directory or the fallback 'mod.d'
        assert result == 'mod.d' or os.path.isdir(result)


class TestMain:
    """Tests for main() with the new argparse + dynamic registration flow."""

    def test_default_loads_only_curated_modules(self, restore_registry):
        """Without --all, only DEFAULT_MODULES are registered."""
        argv = ['prog']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run') as mock_run:
            main()
        mock_run.assert_called_once()

        names = set(ec2rl_module.EC2RL_MODULES.keys())
        assert 'dmesg' in names  # in DEFAULT_MODULES
        assert 'top' in names  # in DEFAULT_MODULES
        assert 'tcpdump' not in names  # not in DEFAULT_MODULES
        assert 'openssh' not in names  # remediation excluded by default

    def test_all_flag_loads_all_modules(self, restore_registry):
        """With --all, all non-remediation modules are included."""
        argv = ['prog', '--all']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run') as mock_run:
            main()
        mock_run.assert_called_once()

        names = set(ec2rl_module.EC2RL_MODULES.keys())
        assert 'tcpdump' in names
        assert 'openssh' not in names  # remediation still excluded

    def test_all_with_remediate_loads_everything(self, restore_registry):
        """With --all --remediate, remediation modules are included."""
        argv = ['prog', '--all', '--remediate']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run') as mock_run:
            main()
        mock_run.assert_called_once()

        names = set(ec2rl_module.EC2RL_MODULES.keys())
        assert 'openssh' in names

    def test_modules_flag_adds_extras(self, restore_registry):
        """--modules=tcpdump adds tcpdump beyond the default set."""
        argv = ['prog', '--modules=tcpdump']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run'):
            main()

        names = set(ec2rl_module.EC2RL_MODULES.keys())
        assert 'dmesg' in names  # default
        assert 'tcpdump' in names  # added via --modules

    def test_registers_mcp_tools_for_modules(self, restore_registry):
        """main() registers run_ec2rescue_linux_<name> tools only for selected modules."""
        argv = ['prog']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run'):
            main()

        registered = {t.name for t in mcp._tool_manager.list_tools()}
        assert 'run_ec2rescue_linux_dmesg' in registered
        assert 'run_ec2rescue_linux_top' in registered
        assert 'run_ec2rescue_linux_tcpdump' not in registered  # not in DEFAULT
        assert 'run_ec2rescue_linux_openssh' not in registered

    def test_dynamic_instructions_swapped_in(self, restore_registry):
        """main() replaces the FastMCP instructions with a dynamic build."""
        argv = ['prog']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run'):
            main()

        text = mcp.instructions
        assert text is not None
        assert '# EC2Rescue for Linux MCP Server' in text
        assert 'ec2rl diagnostic modules' in text


class TestMainTransport:
    """Tests for transport selection and host/port wiring in main()."""

    def test_main_default_calls_stdio(self, restore_registry, restore_mcp_settings):
        """No --transport flag → mcp.run(transport='stdio')."""
        argv = ['prog']
        with patch.object(sys, 'argv', argv), patch.object(mcp, 'run') as mock_run:
            main()
        mock_run.assert_called_once_with(transport='stdio')

    def test_main_streamable_http_passes_transport(self, restore_registry, restore_mcp_settings):
        """--transport streamable-http applies host/port and runs HTTP."""
        argv = [
            'prog',
            '--transport',
            'streamable-http',
            '--host',
            '1.2.3.4',
            '--port',
            '9999',
        ]
        with (
            patch.dict('os.environ', {'AUTH_TYPE': 'no-auth'}),
            patch.object(sys, 'argv', argv),
            patch.object(mcp, 'run') as mock_run,
        ):
            main()
        mock_run.assert_called_once_with(transport='streamable-http')
        assert mcp.settings.host == '1.2.3.4'
        assert mcp.settings.port == 9999

    def test_main_warns_on_host_under_stdio(self, restore_registry, restore_mcp_settings):
        """--host under stdio is ignored with a warning, settings unchanged."""
        from loguru import logger

        original_host = mcp.settings.host
        captured: list[str] = []
        sink_id = logger.add(lambda msg: captured.append(str(msg)), level='WARNING')
        try:
            argv = ['prog', '--host', '1.2.3.4']
            with patch.object(sys, 'argv', argv), patch.object(mcp, 'run') as mock_run:
                main()
        finally:
            logger.remove(sink_id)

        mock_run.assert_called_once_with(transport='stdio')
        assert mcp.settings.host == original_host
        assert any('--host/--port ignored' in msg for msg in captured)


class TestModuleExecution:
    """Module-level smoke checks."""

    def test_module_has_main_block(self):
        """server.py has the `if __name__ == '__main__': main()` block."""
        from awslabs.ec2rescue_for_linux_mcp_server import server

        source = inspect.getsource(server)
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source
