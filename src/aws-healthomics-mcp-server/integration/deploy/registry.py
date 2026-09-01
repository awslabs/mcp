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

"""DynamoDB role-registry provisioning for the integration harness.

The multi-tenancy demonstration is backed by a real DynamoDB role registry: the
server's ``jwt`` inbound mechanism reads per-tenant role mappings from a table
selected by ``MCP_JWT_ROLE_REGISTRY=dynamodb://<table>`` (Req 5.3). This module
creates that table (partition key ``identity`` -- the resolver's default,
:data:`awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver._DEFAULT_PARTITION_KEY`),
writes the Tenant_A / Tenant_B :class:`~integration.harness.tenants.TenantRecord`
items (Req 5.1, 5.2), records the table in the
:class:`~integration.harness.inventory.ResourceInventory` for teardown, and emits
the registry URI the deployments inject.

AWS isolation / testability
----------------------------
This module never constructs a boto3 client at import time. The write path takes
an **injected** DynamoDB client (``dynamodb_client``), so the unit test can drive
provisioning with a fake client and assert the emitted ``dynamodb://<table>`` URI
without touching AWS. :func:`registry_uri` is a pure helper that can be tested
directly and offline. :func:`create_dynamodb_client` builds a real client using the
same pattern as the server's registry source, but is only called by live callers
(the CLI / deployment modules), never at import.
"""

import boto3
import botocore.session
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import build_user_agent_extra
from boto3.dynamodb.types import TypeSerializer
from collections.abc import Sequence
from integration.harness.inventory import ResourceInventory, ResourceRecord
from integration.harness.tenants import TenantRecord
from typing import Any


# URI scheme the server's ``parse_registry_source`` recognizes for a DynamoDB-backed
# registry (``dynamodb://<table>``); see ``role_resolver._DYNAMODB_SCHEME``.
_DYNAMODB_SCHEME = 'dynamodb'

# Attribute name of the table's partition key that holds the Authenticated_Identity.
# This mirrors the resolver's ``_DEFAULT_PARTITION_KEY`` so the created table needs no
# server-side schema override; ``TenantRecord.to_registry_item`` emits the same name.
_PARTITION_KEY = 'identity'

# DynamoDB attribute type for the (String) partition key.
_ATTR_TYPE_STRING = 'S'

# On-demand billing so the table costs nothing when idle between test runs.
_BILLING_MODE = 'PAY_PER_REQUEST'

# ``resource_type`` recorded in the inventory for the created table (Req 8.1).
RESOURCE_TYPE_DYNAMODB_TABLE = 'dynamodb-table'


def registry_uri(table_name: str) -> str:
    """Return the ``MCP_JWT_ROLE_REGISTRY`` value selecting the given table.

    This is the exact value the deployments inject so the server's ``jwt`` mechanism
    reads role mappings from the provisioned table (Req 5.3). It is a pure function of
    the table name and can be tested offline.

    Args:
        table_name: Name of the DynamoDB role-registry table.

    Returns:
        The ``dynamodb://<table_name>`` registry URI.
    """
    return f'{_DYNAMODB_SCHEME}://{table_name}'


def create_dynamodb_client(region: str | None = None) -> Any:
    """Build a DynamoDB client for live provisioning.

    Uses the harness/server's own default credential chain with the standard
    ``user_agent_extra``. This is only for live callers (the CLI / deployment
    modules); it is never invoked at import time and the write path accepts an
    injected client instead so tests stay offline.

    Args:
        region: Optional AWS region for the client. When ``None`` the underlying
            session's default region resolution applies.

    Returns:
        A configured boto3 DynamoDB client.
    """
    botocore_session = botocore.session.Session()
    botocore_session.user_agent_extra = build_user_agent_extra()
    session = boto3.Session(botocore_session=botocore_session, region_name=region)
    return session.client('dynamodb')


def _serialize_item(record: TenantRecord) -> dict[str, Any]:
    """Serialize a tenant record into DynamoDB low-level attribute values.

    ``TenantRecord.to_registry_item`` yields plain Python values
    (``{identity, role_arn, external_id, account_id?, enabled?}``); the low-level
    ``put_item`` API expects typed attribute values (e.g. ``{'S': 'arn'}``). The
    resulting item deserializes back to that same plain shape via the resolver's
    ``TypeDeserializer``, so records written here resolve without any transform.

    Args:
        record: The tenant record to serialize.

    Returns:
        The DynamoDB item as typed attribute values.
    """
    serializer = TypeSerializer()
    return {key: serializer.serialize(value) for key, value in record.to_registry_item().items()}


def provision_role_registry(
    *,
    dynamodb_client: Any,
    table_name: str,
    region: str,
    records: Sequence[TenantRecord],
    inventory: ResourceInventory,
) -> str:
    """Create the role-registry table, write the tenant records, and emit the URI.

    The table is recorded in the inventory **before** it is created so a mid-flight
    failure still leaves a teardown trail (Req 8.3). The table is created with the
    ``identity`` String partition key (Req 5.1), provisioning waits for it to become
    active, and each tenant record is written (Req 5.2). Finally the
    ``dynamodb://<table>`` registry URI the deployments inject is returned (Req 5.3).

    The ``dynamodb_client`` is injected: live callers pass a client from
    :func:`create_dynamodb_client`, while tests pass a fake so no AWS call leaves the
    process.

    Args:
        dynamodb_client: An injected boto3-compatible DynamoDB client. Must support
            ``create_table``, ``get_waiter('table_exists')``, and ``put_item``.
        table_name: Name of the role-registry table to create.
        region: The AWS region the table is provisioned in; recorded on the inventory
            record (Req 8.4).
        records: The tenant records to write (typically the Tenant_A / Tenant_B
            records from ``build_tenant_records``); at least two for isolation.
        inventory: The resource inventory the created table is appended to.

    Returns:
        The ``dynamodb://<table_name>`` registry URI.
    """
    # Record the table before creating it so teardown can find it even if creation
    # fails partway (Req 8.3). Already-absent resources are handled idempotently by
    # the Teardown_Workflow.
    inventory.add(
        ResourceRecord(
            resource_id=table_name,
            resource_type=RESOURCE_TYPE_DYNAMODB_TABLE,
            region=region,
            deployment=inventory.deployment,
        )
    )

    dynamodb_client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {'AttributeName': _PARTITION_KEY, 'AttributeType': _ATTR_TYPE_STRING},
        ],
        KeySchema=[
            {'AttributeName': _PARTITION_KEY, 'KeyType': 'HASH'},
        ],
        BillingMode=_BILLING_MODE,
    )

    # Wait until the table is active before writing records so the puts do not race
    # table creation.
    dynamodb_client.get_waiter('table_exists').wait(TableName=table_name)

    for record in records:
        dynamodb_client.put_item(TableName=table_name, Item=_serialize_item(record))

    return registry_uri(table_name)
