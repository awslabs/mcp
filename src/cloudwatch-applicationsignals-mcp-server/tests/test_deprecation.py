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

"""Tests for the deprecation signals of the CloudWatch Application Signals MCP server."""

import pytest
import subprocess
import sys
import warnings
from awslabs.cloudwatch_applicationsignals_mcp_server import server
from awslabs.cloudwatch_applicationsignals_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from unittest.mock import patch


EXPECTED_TOOLS = {
    # server.py
    'audit_services',
    'audit_slos',
    'audit_service_operations',
    'analyze_canary_failures',
    'list_canaries',
    'list_monitored_services',
    'query_service_metrics',
    'get_slo',
    'list_slos',
    'search_transaction_spans',
    'get_xray_trace',
    'list_slis',
    'get_enablement_guide',
    'list_change_events',
    'list_group_services',
    'audit_group_health',
    'get_group_dependencies',
    'get_group_changes',
    'list_grouping_attribute_definitions',
    'query_rum_events',
    # service_events/registration.py
    'list_monitored_functions',
    'get_function_metrics',
    'search_functions_by_name',
    'get_endpoint_performance',
    'get_recent_incidents',
    'get_incident_root_cause',
    'get_service_health_overview',
    'find_deployment',
    # dynamic_instrumentation/registration.py
    'create_instrumentation',
    'list_instrumentations',
    'get_instrumentation',
    'delete_instrumentation',
    'batch_delete_instrumentations_by_scope',
    'batch_delete_instrumentations_by_arns',
    'get_instrumentation_configuration_status',
    'check_instrumentation_status',
    'search_snapshots_for_status_event',
    'get_sample_snapshot_for_breakpoint',
}


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.cloudwatch-applicationsignals-mcp-server')
    assert 'will not receive further updates' in DEPRECATION_NOTICE
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-cloudwatch-applicationsignals.md'
        in DEPRECATION_NOTICE
    )


def test_main_emits_one_future_warning_before_run():
    """main() warns once, from the caller's line, before it starts the server."""
    warnings_at_run = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')

        def record_run(*args, **kwargs):
            warnings_at_run.append(len(caught))

        with (
            patch.object(server, 'service_events_state'),
            patch.object(server.mcp, 'run', side_effect=record_run) as mock_run,
        ):
            main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert future_warnings[0].filename == __file__
    mock_run.assert_called_once_with(transport='stdio')
    assert warnings_at_run == [1]


def test_import_does_not_warn():
    """Importing the server module emits no FutureWarning."""
    result = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.cloudwatch_applicationsignals_mcp_server.server',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert DEPRECATION_NOTICE not in result.stderr


def test_instructions_start_with_notice():
    """The server instructions start with the deprecation notice."""
    assert mcp.instructions is not None
    assert mcp.instructions.startswith(DEPRECATION_NOTICE)


@pytest.mark.asyncio
async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool, including the imported modules' tools, is marked deprecated."""
    tools = await mcp.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
