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

"""BDD step definitions for ROSA advisor and recommendations scenarios."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_advisor_handler import RosaAdvisorHandler
from pytest_bdd import given, parsers, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_advisor.feature')


# --- Fixtures ---


@pytest.fixture
def advisor_handler(mock_mcp):
    """Create a RosaAdvisorHandler with mocks."""
    return RosaAdvisorHandler(mock_mcp)


# --- Given Steps ---


@given('the ROSA advisor is initialized')
def advisor_initialized(advisor_handler):
    """The ROSA advisor is initialized."""
    pass


# --- When Steps ---


@when(parsers.parse(
    'I request instance recommendation for "{workload}" workload with {vcpus:d} vCPUs and {memory:d}GB memory'
))
def request_instance_recommendation(advisor_handler, mock_context, response_holder, workload, vcpus, memory):
    """Request an instance type recommendation."""
    result = run(advisor_handler.rosa_recommend_instance_type(
        mock_context,
        workload_type=workload,
        vcpus=vcpus,
        memory_gb=memory,
    ))
    response_holder['result'] = result


@when('I validate cluster config:')
def validate_cluster_config_table(advisor_handler, mock_context, response_holder, datatable):
    """Validate cluster config using data from a table."""
    params = {}
    for row in datatable:
        key = row[0].strip()
        value = row[1].strip()
        if key == 'multi_az':
            params[key] = value.lower() == 'true'
        elif key == 'replicas':
            params[key] = int(value)
        else:
            params[key] = value

    result = run(advisor_handler.rosa_validate_cluster_config(
        mock_context,
        cluster_name=params.get('cluster_name', 'test-cluster'),
        multi_az=params.get('multi_az', False),
        replicas=params.get('replicas', 2),
        machine_type=params.get('machine_type', 'm5.xlarge'),
        version=params.get('version', '4.14.5'),
    ))
    response_holder['result'] = result


@when(parsers.parse('I validate cluster config with name "{name}"'))
def validate_cluster_config_name(advisor_handler, mock_context, response_holder, name):
    """Validate cluster config with a specific name."""
    result = run(advisor_handler.rosa_validate_cluster_config(
        mock_context,
        cluster_name=name,
        multi_az=False,
        replicas=2,
        machine_type='m5.xlarge',
        version='4.14.5',
    ))
    response_holder['result'] = result


@when(parsers.parse('I request recommended config for "{environment}"'))
def request_recommended_config(advisor_handler, mock_context, response_holder, environment):
    """Request recommended config for an environment."""
    result = run(advisor_handler.rosa_recommend_cluster_config(
        mock_context,
        environment=environment,
    ))
    response_holder['result'] = result


@when(parsers.parse('I estimate cost for {replicas:d} {machine_type} nodes in {region}'))
def estimate_cost(advisor_handler, mock_context, response_holder, replicas, machine_type, region):
    """Estimate cluster cost."""
    result = run(advisor_handler.rosa_estimate_cluster_cost(
        mock_context,
        machine_type=machine_type,
        replicas=replicas,
        region=region,
    ))
    response_holder['result'] = result


# --- Then Steps ---


@then(parsers.parse('the recommendation should be from the "{family}" family'))
def recommendation_from_family(response_holder, family):
    """The recommendation should be from the expected instance family."""
    data = json.loads(response_holder['result'][0].text)
    recommendations = data.get('recommendations', [])
    assert len(recommendations) > 0
    # Check that at least one recommendation starts with the expected family
    has_family = any(r['instance_type'].startswith(family) for r in recommendations)
    assert has_family, (
        f"Expected recommendation from '{family}' family, "
        f"got: {[r['instance_type'] for r in recommendations]}"
    )


@then('the validation should pass')
def validation_passes(response_holder):
    """The validation passes."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('valid') is True


@then('there should be no errors')
def no_errors(response_holder):
    """There are no validation errors."""
    data = json.loads(response_holder['result'][0].text)
    assert len(data.get('errors', [])) == 0


@then('the validation should fail')
def validation_fails(response_holder):
    """The validation fails."""
    data = json.loads(response_holder['result'][0].text)
    assert data.get('valid') is False


@then(parsers.parse('the error should mention "{text}"'))
def error_mentions_text(response_holder, text):
    """The error mentions the expected text."""
    data = json.loads(response_holder['result'][0].text)
    errors = data.get('errors', [])
    all_errors = ' '.join(errors).lower()
    assert text.lower() in all_errors, (
        f"Expected error to mention '{text}', got errors: {errors}"
    )


@then(parsers.parse('the config should have multi_az {multi_az}'))
def config_has_multi_az(response_holder, multi_az):
    """The config has the expected multi_az value."""
    data = json.loads(response_holder['result'][0].text)
    expected = multi_az.lower() == 'true'
    assert data['recommended_config']['multi_az'] is expected


@then(parsers.parse('the config should have replicas {replicas:d}'))
def config_has_replicas(response_holder, replicas):
    """The config has the expected number of replicas."""
    data = json.loads(response_holder['result'][0].text)
    assert data['recommended_config']['replicas'] == replicas


@then('the estimate should include monthly cost')
def estimate_includes_monthly_cost(response_holder):
    """The estimate includes a monthly cost."""
    data = json.loads(response_holder['result'][0].text)
    assert 'costs' in data
    assert 'estimated_monthly_total' in data['costs']


@then('the estimate should include per-node cost')
def estimate_includes_per_node_cost(response_holder):
    """The estimate includes per-node cost."""
    data = json.loads(response_holder['result'][0].text)
    assert 'worker_nodes' in data['costs']
    assert 'hourly_per_node' in data['costs']['worker_nodes']


@then('the monthly cost should be greater than 0')
def monthly_cost_positive(response_holder):
    """The monthly cost is greater than zero."""
    data = json.loads(response_holder['result'][0].text)
    assert data['costs']['estimated_monthly_total'] > 0
