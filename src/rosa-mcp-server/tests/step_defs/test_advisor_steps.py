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

"""BDD step definitions for ROSA advisor (no API needed)."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_advisor_handler import RosaAdvisorHandler
from pytest_bdd import parsers, scenarios, then, when
from tests.step_defs.conftest import run
from unittest.mock import MagicMock


scenarios('../features/rosa_advisor.feature')


# --- Fixtures ---


@pytest.fixture
def advisor_handler():
    """Create a RosaAdvisorHandler."""
    mock_mcp = MagicMock()
    mock_mcp.tool = MagicMock(return_value=lambda f: f)
    return RosaAdvisorHandler(mock_mcp)


@pytest.fixture
def mock_context():
    """Create a mock MCP context for advisor calls."""
    ctx = MagicMock()
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def advisor_response():
    """Hold advisor response data between steps."""
    return {'result': None}


# --- When Steps ---


@when(parsers.parse(
    'I request instance recommendation for "{workload}" with {vcpus:d} vCPUs and {memory:d}GB'
))
def request_instance_recommendation(
    advisor_handler, mock_context, advisor_response, workload, vcpus, memory
):
    """Request an instance type recommendation."""
    result = run(advisor_handler.rosa_recommend_instance_type(
        mock_context,
        workload_type=workload,
        vcpus=vcpus,
        memory_gb=memory,
    ))
    advisor_response['result'] = result


@when(parsers.parse(
    'I validate config name="{name}" multi_az={multi_az} '
    'replicas={replicas:d} type="{machine_type}" version="{version}"'
))
def validate_config(
    advisor_handler, mock_context, advisor_response, name, multi_az, replicas, machine_type, version
):
    """Validate a cluster configuration."""
    multi_az_bool = multi_az.lower() == 'true'
    result = run(advisor_handler.rosa_validate_cluster_config(
        mock_context,
        cluster_name=name,
        multi_az=multi_az_bool,
        replicas=replicas,
        machine_type=machine_type,
        version=version,
    ))
    advisor_response['result'] = result


@when(parsers.parse('I request recommended config for "{env}"'))
def request_recommended_config(advisor_handler, mock_context, advisor_response, env):
    """Request recommended config for an environment."""
    result = run(advisor_handler.rosa_recommend_cluster_config(
        mock_context,
        environment=env,
    ))
    advisor_response['result'] = result


@when(parsers.parse('I estimate cost for {replicas:d} nodes of type "{machine_type}"'))
def estimate_cost(advisor_handler, mock_context, advisor_response, replicas, machine_type):
    """Estimate cluster cost."""
    result = run(advisor_handler.rosa_estimate_cluster_cost(
        mock_context,
        machine_type=machine_type,
        replicas=replicas,
        region='us-east-1',
    ))
    advisor_response['result'] = result


# --- Then Steps ---


@then(parsers.parse('the recommendation should include an instance from the "{family}" family'))
def recommendation_from_family(advisor_response, family):
    """Verify the recommendation includes the expected family."""
    data = json.loads(advisor_response['result'][0].text)
    recommendations = data.get('recommendations', [])
    assert len(recommendations) > 0
    has_family = any(r['instance_type'].startswith(family) for r in recommendations)
    assert has_family, (
        f"Expected recommendation from '{family}' family, "
        f"got: {[r['instance_type'] for r in recommendations]}"
    )


@then("the validation should pass with no errors")
def validation_passes(advisor_response):
    """Verify validation passes."""
    data = json.loads(advisor_response['result'][0].text)
    assert data.get('valid') is True
    assert len(data.get('errors', [])) == 0


@then("the validation should fail")
def validation_fails(advisor_response):
    """Verify validation fails."""
    data = json.loads(advisor_response['result'][0].text)
    assert data.get('valid') is False


@then(parsers.parse('the validation should fail with "{text}"'))
def validation_fails_with_text(advisor_response, text):
    """Verify validation fails with specific error text."""
    data = json.loads(advisor_response['result'][0].text)
    assert data.get('valid') is False
    errors = data.get('errors', [])
    all_errors = ' '.join(errors).lower()
    assert text.lower() in all_errors, (
        f"Expected error to mention '{text}', got errors: {errors}"
    )


@then(parsers.parse('the config should recommend {replicas:d} replicas'))
def config_has_replicas(advisor_response, replicas):
    """Verify the recommended config has expected replicas."""
    data = json.loads(advisor_response['result'][0].text)
    assert data['recommended_config']['replicas'] == replicas


@then("the monthly estimate should be greater than 0")
def monthly_cost_positive(advisor_response):
    """Verify the monthly cost is greater than zero."""
    data = json.loads(advisor_response['result'][0].text)
    assert data['costs']['estimated_monthly_total'] > 0
