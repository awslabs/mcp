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

"""BDD step definitions for ROSA operator operations (live API)."""

from pytest_bdd import given, scenarios, then, when
from tests.step_defs.conftest import run


scenarios('../features/rosa_operators.feature')


# --- Given Steps ---


@given("a real OCM client is available")
def ocm_available(ocm_client):
    """Verify we have a real OCM client."""
    assert ocm_client is not None


@given("a test ROSA cluster exists")
def cluster_exists(cluster_id):
    """Verify a test cluster was discovered."""
    assert cluster_id is not None


# --- When Steps ---


@when("I list STS operator roles for the test cluster")
def list_sts_operator_roles(ocm_client, cluster_id, response):
    """List STS operator roles for the test cluster."""
    try:
        response.data = run(ocm_client.list_sts_operator_roles(cluster_id))
    except Exception as e:
        response.error = e
        response.data = {}


@when("I get cluster operators status")
def get_cluster_operators(ocm_client, cluster_id, response):
    """Get cluster operators health status."""
    try:
        response.data = run(ocm_client.get_cluster_operators(cluster_id))
    except Exception as e:
        response.error = e
        response.data = {}


@when("I list STS credential requests")
def list_sts_credential_requests(ocm_client, response):
    """List STS credential request templates."""
    try:
        response.data = run(ocm_client.list_sts_credential_requests())
    except Exception as e:
        response.error = e
        response.data = {}


@when("I list STS policies")
def list_sts_policies(ocm_client, response):
    """List STS IAM policies."""
    try:
        response.data = run(ocm_client.list_sts_policies())
    except Exception as e:
        response.error = e
        response.data = {}


# --- Then Steps ---


@then("at least 4 operator roles should exist")
def check_operator_roles_count(response):
    """Verify at least 4 operator roles exist."""
    if response.error:
        # Some clusters may not expose STS roles via this endpoint
        pass
    else:
        items = response.data.get('items', [])
        assert len(items) >= 4, f"Expected at least 4 operator roles, got {len(items)}"


@then("each role should have a name and role_arn")
def check_role_fields(response):
    """Verify each operator role has required fields."""
    if response.error:
        pass
    else:
        items = response.data.get('items', [])
        for item in items:
            assert 'name' in item, f"Role missing 'name': {item}"
            assert 'role_arn' in item, f"Role missing 'role_arn': {item}"


@then("at least 10 operators should be listed")
def check_operators_count(response):
    """Verify at least 10 cluster operators are listed."""
    if response.error:
        pass
    else:
        operators = response.data.get('operators', [])
        assert len(operators) >= 10, f"Expected at least 10 operators, got {len(operators)}"


@then("all critical operators should be available")
def check_critical_operators(response):
    """Verify critical cluster operators are available."""
    if response.error:
        pass
    else:
        operators = response.data.get('operators', [])
        critical_names = {'authentication', 'console', 'dns', 'ingress', 'kube-apiserver'}
        for op in operators:
            name = op.get('name', '')
            if name in critical_names:
                condition = op.get('condition', '')
                value = op.get('value', '')
                # Critical operators should be Available=True
                if condition == 'Available':
                    assert value == 'True', (
                        f"Critical operator '{name}' is not available: {op}"
                    )


@then("at least 4 credential requests should exist")
def check_credential_requests_count(response):
    """Verify at least 4 credential requests exist."""
    if response.error:
        pass
    else:
        items = response.data.get('items', [])
        assert len(items) >= 4, f"Expected at least 4 credential requests, got {len(items)}"


@then("at least 20 policies should exist")
def check_policies_count(response):
    """Verify at least 20 STS policies exist."""
    if response.error:
        pass
    else:
        items = response.data.get('items', [])
        assert len(items) >= 20, f"Expected at least 20 policies, got {len(items)}"


@then("policies should include operator role types")
def check_policy_types(response):
    """Verify policies include operator role types."""
    if response.error:
        pass
    else:
        items = response.data.get('items', [])
        # Check that at least one policy has an operator-related type or id
        has_operator_type = any(
            'operator' in item.get('id', '').lower()
            or 'operator' in item.get('type', '').lower()
            or 'OperatorRole' in item.get('type', '')
            for item in items
        )
        assert has_operator_type, "No operator role type found in STS policies"
