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

"""BDD step definitions for ROSA troubleshooting (no API needed)."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_troubleshoot_handler import RosaTroubleshootHandler
from pytest_bdd import parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import MagicMock


scenarios('../features/rosa_troubleshoot.feature')


# --- Fixtures ---


@pytest.fixture
def troubleshoot_handler():
    """Create a RosaTroubleshootHandler."""
    mock_mcp = MagicMock()
    mock_mcp.tool = MagicMock(return_value=lambda f: f)
    return RosaTroubleshootHandler(mock_mcp)


@pytest.fixture
def mock_context():
    """Create a mock MCP context for troubleshoot calls."""
    ctx = MagicMock()
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def troubleshoot_response():
    """Hold troubleshoot response data between steps."""
    return {'result': None}


# --- When Steps ---


@when(parsers.parse('I search the troubleshoot guide for "{query}"'))
def search_troubleshoot_guide(troubleshoot_handler, mock_context, troubleshoot_response, query):
    """Search the troubleshoot guide."""
    result = run(troubleshoot_handler.rosa_search_troubleshoot_guide(
        mock_context,
        query=query,
    ))
    troubleshoot_response['result'] = result


@when('I request metrics guidance')
def request_metrics_guidance(troubleshoot_handler, mock_context, troubleshoot_response):
    """Request metrics guidance."""
    result = run(troubleshoot_handler.rosa_get_metrics_guidance(mock_context))
    troubleshoot_response['result'] = result


# --- Then Steps ---


@then(parsers.parse('at least {count:d} result should be returned'))
def at_least_n_results(troubleshoot_response, count):
    """Verify at least N results are returned."""
    data = json.loads(troubleshoot_response['result'][0].text)
    assert data['results_count'] >= count, (
        f"Expected at least {count} results, got {data['results_count']}"
    )


@then(parsers.parse('the result should mention "{text}"'))
def result_mentions_text(troubleshoot_response, text):
    """Verify that at least one result mentions the given text."""
    data = json.loads(troubleshoot_response['result'][0].text)
    all_text = json.dumps(data['results']).lower()
    assert text.lower() in all_text, (
        f"Expected results to mention '{text}', got: {data['results']}"
    )


@then('the response should include ContainerInsights metrics')
def response_includes_container_insights(troubleshoot_response):
    """Verify that the response includes ContainerInsights metrics."""
    data = json.loads(troubleshoot_response['result'][0].text)
    assert 'container_insights' in data
    assert data['container_insights']['namespace'] == 'ContainerInsights'
    assert len(data['container_insights']['key_metrics']) > 0


@then('the response should include recommended alarms')
def response_includes_recommended_alarms(troubleshoot_response):
    """Verify that the response includes recommended alarms."""
    data = json.loads(troubleshoot_response['result'][0].text)
    assert 'recommended_alarms' in data
    assert len(data['recommended_alarms']) > 0
    # Verify alarm structure
    alarm = data['recommended_alarms'][0]
    assert 'metric' in alarm
    assert 'threshold' in alarm
    assert 'action' in alarm
