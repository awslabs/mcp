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

"""Tests for the MCP tool annotations on the S3 Tables MCP Server."""

import pytest
from awslabs.s3_tables_mcp_server.server import app


READ_ONLY_TOOLS = {
    'list_table_buckets',
    'list_namespaces',
    'list_tables',
    'get_table_maintenance_config',
    'get_maintenance_job_status',
    'get_table_metadata_location',
    'get_bucket_metadata_config',
    'query_database',
}

# Write tools that only add new resources or rows; nothing existing is changed.
ADDITIVE_TOOLS = {
    'create_table_bucket',
    'create_namespace',
    'create_table',
    'import_csv_to_table',
    'import_parquet_to_table',
    'append_rows_to_table',
}

# Write tools that add rows, so calling them twice duplicates data.
NON_IDEMPOTENT_TOOLS = {
    'import_csv_to_table',
    'import_parquet_to_table',
    'append_rows_to_table',
}

# Write tools that change existing resources.
DESTRUCTIVE_TOOLS = {
    'rename_table',
    'update_table_metadata_location',
}

ALL_TOOLS = READ_ONLY_TOOLS | ADDITIVE_TOOLS | DESTRUCTIVE_TOOLS


@pytest.fixture
async def tools():
    """Return the registered tools keyed by name."""
    return {tool.name: tool for tool in await app.list_tools()}


async def test_expected_tools_are_registered(tools):
    """The annotated tool set matches the registered tool set exactly."""
    assert len(ALL_TOOLS) == 16
    assert set(tools) == ALL_TOOLS


async def test_every_tool_has_annotations_and_title(tools):
    """Every tool carries annotations with a human-readable title."""
    for name, tool in tools.items():
        assert tool.annotations is not None, f'{name} has no annotations'
        assert tool.annotations.title, f'{name} has no title'


async def test_every_tool_is_open_world(tools):
    """Every tool calls AWS, so every tool is open world."""
    for name, tool in tools.items():
        assert tool.annotations.open_world_hint is True, name


@pytest.mark.parametrize('name', sorted(READ_ONLY_TOOLS))
async def test_read_only_tools(tools, name):
    """Read-only tools are marked read-only."""
    annotations = tools[name].annotations
    assert annotations.read_only_hint is True
    assert annotations.destructive_hint is None
    assert annotations.idempotent_hint is None


@pytest.mark.parametrize('name', sorted(ADDITIVE_TOOLS))
async def test_additive_tools(tools, name):
    """Create, import, and append tools write but are not destructive."""
    annotations = tools[name].annotations
    assert annotations.read_only_hint is False
    assert annotations.destructive_hint is False
    if name in NON_IDEMPOTENT_TOOLS:
        assert annotations.idempotent_hint is False
    else:
        assert annotations.idempotent_hint is None


@pytest.mark.parametrize('name', sorted(DESTRUCTIVE_TOOLS))
async def test_destructive_tools(tools, name):
    """Tools that change existing resources are marked destructive."""
    annotations = tools[name].annotations
    assert annotations.read_only_hint is False
    assert annotations.destructive_hint is True
    assert annotations.idempotent_hint is None
