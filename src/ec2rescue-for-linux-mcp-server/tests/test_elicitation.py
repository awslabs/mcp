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

"""Tests for the perfimpact and install gates in elicitation.py."""

import json
import pytest
from awslabs.ec2rescue_for_linux_mcp_server import elicitation as elicitation_module
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl import Ec2rlModule
from awslabs.ec2rescue_for_linux_mcp_server.elicitation import (
    _install_gate,
    _perfimpact_consent_gate,
)
from unittest.mock import patch


_INSTANCE_ID = 'i-1234567890abcdef0'


@pytest.fixture()
def perfimpact_module():
    """A perfimpact-flagged module (e.g. packet capture / syscall tracing)."""
    return Ec2rlModule('atop', 'mod_out/run/atop.log', perfimpact=True)


class TestPerfimpactConsentGate:
    """The gate is fail-closed.

    A perfimpact module runs only when the operator started the server with
    --allow-perfimpact.
    """

    def test_denied_when_flag_not_set(self, perfimpact_module):
        """Fail-closed: without --allow-perfimpact the gate aborts the run."""
        with patch.object(elicitation_module, '_ALLOW_PERFIMPACT', False):
            result = _perfimpact_consent_gate(_INSTANCE_ID, perfimpact_module)

        assert result is not None
        data = json.loads(result)
        assert data['status'] == 'Aborted'
        assert data['reason'] == 'perfimpact_not_permitted'
        assert data['module'] == 'atop'
        assert data['instance_id'] == _INSTANCE_ID

    def test_permitted_when_flag_set(self, perfimpact_module):
        """With --allow-perfimpact the gate permits the run (returns None)."""
        with patch.object(elicitation_module, '_ALLOW_PERFIMPACT', True):
            result = _perfimpact_consent_gate(_INSTANCE_ID, perfimpact_module)

        assert result is None


class TestInstallGate:
    """The gate is fail-closed: install needs --allow-install."""

    def test_denied_when_flag_not_set(self):
        """Fail-closed: without --allow-install the gate aborts the install."""
        with patch.object(elicitation_module, '_ALLOW_INSTALL', False):
            result = _install_gate(_INSTANCE_ID)

        assert result is not None
        data = json.loads(result)
        assert data['status'] == 'Aborted'
        assert data['reason'] == 'install_not_permitted'
        assert data['module'] == 'install_ec2rescue_linux'
        assert data['instance_id'] == _INSTANCE_ID

    def test_permitted_when_flag_set(self):
        """With --allow-install the gate permits the install (returns None)."""
        with patch.object(elicitation_module, '_ALLOW_INSTALL', True):
            result = _install_gate(_INSTANCE_ID)

        assert result is None

    def test_denial_names_the_flag(self):
        """The abort message tells the operator which flag to restart with."""
        with patch.object(elicitation_module, '_ALLOW_INSTALL', False):
            result = _install_gate(_INSTANCE_ID)

        assert result is not None, 'the gate must block without the flag'
        assert '--allow-install' in json.loads(result)['message']

    def test_gate_takes_no_context(self):
        """No ctx: the outcome cannot be auto-answered by an agent."""
        import inspect

        assert not inspect.iscoroutinefunction(_install_gate)
        assert list(inspect.signature(_install_gate).parameters) == ['instance_id']
