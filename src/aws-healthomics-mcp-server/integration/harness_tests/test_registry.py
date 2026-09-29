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

"""Offline unit tests for the DynamoDB role-registry URI emission.

This module lives outside ``integration/tests/`` (which is opt-in gated behind a
real-AWS signal) and outside the top-level ``tests/`` suite, so it runs as a
fully offline unit test: it never constructs a real AWS client, resolves
credentials, or opens a network connection. The write path is driven with a
``MagicMock`` fake DynamoDB client so no API call leaves the process, and the
pure :func:`registry_uri` helper is exercised directly.

Validates: Requirements DynamoDB-backed multi-tenant registry.
"""

from integration.deploy.registry import (
    RESOURCE_TYPE_DYNAMODB_TABLE,
    provision_role_registry,
    registry_uri,
)
from integration.harness.inventory import ResourceInventory
from integration.harness.tenants import TenantSpec, build_tenant_records
from typing import Any
from unittest.mock import MagicMock


def _make_fake_dynamodb_client() -> Any:
    """Build an offline fake DynamoDB client recording every call.

    The fake supports exactly the surface ``provision_role_registry`` uses --
    ``create_table``, ``get_waiter('table_exists').wait(...)``, and ``put_item``
    -- via ``MagicMock`` so no real client is constructed and no request leaves
    the process. Returns the ``MagicMock`` so callers can assert on recorded calls.
    """
    fake = MagicMock(name='dynamodb_client')
    fake.get_waiter.return_value = MagicMock(name='table_exists_waiter')
    return fake


def _tenant_records() -> list[Any]:
    """Build the Tenant_A / Tenant_B records used to drive provisioning."""
    return build_tenant_records(
        [
            TenantSpec(
                identity='Tenant_A',
                role_arn='arn:aws:iam::111111111111:role/tenant-a',
                external_id='external-a',
                account_id='111111111111',
            ),
            TenantSpec(
                identity='Tenant_B',
                role_arn='arn:aws:iam::222222222222:role/tenant-b',
                external_id='external-b',
                account_id='222222222222',
            ),
        ]
    )


def test_registry_uri_table_part_equals_table_name() -> None:
    """The emitted ``dynamodb://<table>`` value's table part equals the name.

    The pure helper is a function of the table name alone; for any table name the
    emitted URI is exactly ``dynamodb://<table_name>``, so the ``<table>`` part
    equals the supplied name verbatim (Req 5.3).

    Validates: Requirements DynamoDB-backed multi-tenant registry.
    """
    for table_name in (
        'my-table',
        'aho-mcp-itest-registry',
        'Registry_With_Underscores',
    ):
        uri = registry_uri(table_name)
        assert uri == f'dynamodb://{table_name}'
        # The scheme-stripped remainder is the created table name, exactly.
        assert uri.split('://', 1)[1] == table_name


def test_provision_role_registry_emits_uri_for_created_table() -> None:
    """End-to-end emission returns ``dynamodb://<table>`` for the created table.

    Driving ``provision_role_registry`` with an injected fake client (no real
    AWS) creates the named table and returns the registry URI whose table part
    equals the created table name -- the core Req 5.3 assertion. The table is
    also recorded in the inventory for teardown.

    Validates: Requirements DynamoDB-backed multi-tenant registry.
    """
    fake = _make_fake_dynamodb_client()
    records = _tenant_records()
    inventory = ResourceInventory(deployment='agentcore', region='us-east-1')
    table_name = 'aho-mcp-itest-registry'

    uri = provision_role_registry(
        dynamodb_client=fake,
        table_name=table_name,
        region='us-east-1',
        records=records,
        inventory=inventory,
    )

    # The emitted value's table equals the created table name (core Req 5.3).
    assert uri == f'dynamodb://{table_name}'

    # The table was created under the same name the URI selects.
    fake.create_table.assert_called_once()
    _, create_kwargs = fake.create_table.call_args
    assert create_kwargs['TableName'] == table_name

    # A dynamodb-table record for the table was appended to the inventory.
    table_records = [
        record
        for record in inventory.records
        if record.resource_type == RESOURCE_TYPE_DYNAMODB_TABLE
    ]
    assert len(table_records) == 1
    assert table_records[0].resource_id == table_name
    assert table_records[0].region == 'us-east-1'

    # One put_item per tenant record, each targeting the created table.
    assert fake.put_item.call_count == len(records)
    for _, put_kwargs in fake.put_item.call_args_list:
        assert put_kwargs['TableName'] == table_name
