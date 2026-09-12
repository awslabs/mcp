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

"""Shared pytest fixtures for the Timestream for InfluxDB MCP server tests."""

import pytest
from awslabs.timestream_for_influxdb_mcp_server import server


@pytest.fixture(autouse=True)
def allow_write_enabled(monkeypatch):
    """Enable the operator write gate for the majority of tests.

    Write authorization is controlled by the operator-set module global
    ``ALLOW_WRITE`` (from the ``ALLOW_WRITE`` environment variable at startup),
    not by a caller-supplied tool parameter. Most tool tests exercise the
    success path and therefore need the gate enabled. Tests that assert the
    read-only refusal path override this by patching ``server.ALLOW_WRITE`` to
    ``False`` within the test.
    """
    monkeypatch.setattr(server, 'ALLOW_WRITE', True)
