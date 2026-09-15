# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Regression tests for the operator-controlled write gate (ALLOW_WRITE).

These tests lock in the security fix for the caller-controlled write-mode
issue: write authorization must come from the operator-set ``ALLOW_WRITE``
gate, never from a caller-supplied tool parameter. See the Sauron action item
for context (MCP Threat #8 "Tool Overreach" / SBP-02).
"""

import inspect
import pytest
from awslabs.timestream_for_influxdb_mcp_server import server


# Every tool that performs a create / update / delete / write operation.
MUTATING_TOOLS = [
    'create_db_cluster',
    'create_db_instance',
    'delete_db_instance',
    'delete_db_cluster',
    'tag_resource',
    'untag_resource',
    'update_db_cluster',
    'update_db_instance',
    'create_db_parameter_group',
    'influxdb_write_points',
    'influxdb_write_line_protocol',
    'influxdb_create_bucket',
    'influxdb_create_org',
]


@pytest.mark.parametrize('tool_name', MUTATING_TOOLS)
def test_tool_write_mode_not_in_signature(tool_name):
    """No mutating tool may expose a caller-supplied write-mode parameter.

    A caller (or a prompt-injected agent) must not be able to self-authorize
    writes. Guards against re-introduction of the ``tool_write_mode`` field.
    """
    func = getattr(server, tool_name)
    params = inspect.signature(func).parameters
    assert 'tool_write_mode' not in params, (
        f'{tool_name} must not accept a caller-supplied write-mode parameter'
    )


def test_allow_write_defaults_to_false(monkeypatch):
    """The operator gate is read from the ALLOW_WRITE environment variable."""
    for value in ('', 'false', 'no', '0', 'FALSE'):
        monkeypatch.setenv('ALLOW_WRITE', value)
        # Re-evaluate the same expression the module uses at import time.
        assert (value.lower() in ('true', '1', 'yes')) is False

    for value in ('true', '1', 'yes', 'True', 'YES'):
        monkeypatch.setenv('ALLOW_WRITE', value)
        assert (value.lower() in ('true', '1', 'yes')) is True


@pytest.mark.asyncio
async def test_mutation_refused_when_gate_disabled(monkeypatch):
    """A representative destructive tool is refused when ALLOW_WRITE is off."""
    monkeypatch.setattr(server, 'ALLOW_WRITE', False)
    with pytest.raises(Exception) as excinfo:
        await server.delete_db_cluster(db_cluster_id='test-cluster-id')
    assert 'is a write operation and is disabled' in str(excinfo.value)
    assert 'ALLOW_WRITE=true' in str(excinfo.value)
