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


"""Tenant-record modeling for the DynamoDB-backed multi-tenant role registry.

The multi-tenancy demonstration maps each authenticated caller (the JWT ``sub``
claim, the Authenticated_Identity) to a per-tenant role and ``ExternalId`` via a
DynamoDB role registry. This module provides the pure-logic types the harness
uses to build those registry items offline, before any AWS resource exists:

- :class:`TenantSpec` -- the operator-supplied description of one tenant.
- :class:`TenantRecord` -- a validated record that renders to the DynamoDB item
  shape the server's ``RegistryRoleResolver`` reads.
- :func:`build_tenant_records` -- builds two or more records, failing closed when
  the inputs would collide or carry an empty ``external_id``.

The rendered item field names (``identity`` partition key, ``role_arn``,
``external_id``, and optional ``account_id`` / ``enabled``) match exactly what
``awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver.RegistryRoleResolver``
looks up, so records this module produces resolve without any server-side schema
override (the resolver's ``_DEFAULT_PARTITION_KEY`` is ``'identity'``).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


# Registry_Record field names. These mirror the server's resolver constants
# (``_RECORD_ROLE_ARN`` / ``_RECORD_EXTERNAL_ID`` / ``_RECORD_ENABLED`` and the
# ``_DEFAULT_PARTITION_KEY`` identity attribute) so the produced item shape is
# read without a server-side override.
_ITEM_IDENTITY = 'identity'
_ITEM_ROLE_ARN = 'role_arn'
_ITEM_EXTERNAL_ID = 'external_id'
_ITEM_ACCOUNT_ID = 'account_id'
_ITEM_ENABLED = 'enabled'


@dataclass(frozen=True)
class TenantSpec:
    """The operator-supplied description of one tenant to register.

    Attributes:
        identity: The Authenticated_Identity (the JWT ``sub`` claim) that keys
            the tenant in the registry; becomes the DynamoDB partition key.
        role_arn: The ARN of the Tenant_Role the server assumes for this tenant.
        external_id: The non-empty ``sts:ExternalId`` guarding the assume-role
            call for this tenant.
        account_id: Optional owning account id (informational only).
        enabled: Whether the tenant is enabled. An enabled tenant resolves; a
            disabled one is rejected by the server's resolver. Defaults to
            ``True``.
    """

    identity: str
    role_arn: str
    external_id: str
    account_id: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class TenantRecord:
    """A validated tenant mapping that renders to the registry item shape.

    Attributes:
        identity: The Authenticated_Identity (the JWT ``sub`` claim), which is the
            DynamoDB partition key the resolver looks up.
        role_arn: The ARN of the Tenant_Role the server assumes for this tenant.
        external_id: The non-empty ``sts:ExternalId`` passed unmodified on the
            assume-role call for this tenant.
        account_id: Optional owning account id (informational only).
        enabled: Whether the tenant is enabled. Defaults to ``True``.
    """

    identity: str
    role_arn: str
    external_id: str
    account_id: str | None = None
    enabled: bool = True

    def to_registry_item(self) -> dict[str, Any]:
        """Render the record to the DynamoDB item the resolver reads.

        Produces the ``{identity, role_arn, external_id, account_id?, enabled?}``
        shape with plain Python values (as the server's resolver sees them after
        DynamoDB deserialization). The required fields ``identity``, ``role_arn``,
        and ``external_id`` are always present. ``enabled`` is always included so
        the record's enabled state is explicit and round-trips exactly.
        ``account_id`` is included only when set, since it is optional and purely
        informational.

        Returns:
            The registry item as a plain ``dict``.
        """
        item: dict[str, Any] = {
            _ITEM_IDENTITY: self.identity,
            _ITEM_ROLE_ARN: self.role_arn,
            _ITEM_EXTERNAL_ID: self.external_id,
            _ITEM_ENABLED: self.enabled,
        }
        if self.account_id is not None:
            item[_ITEM_ACCOUNT_ID] = self.account_id
        return item


def build_tenant_records(specs: Sequence[TenantSpec]) -> list[TenantRecord]:
    """Build two or more validated tenant records, failing closed on collisions.

    Guarantees the invariants Requirement 5.2 places on the registry: at least
    two records, each with a non-empty ``external_id``, pairwise-distinct
    ``role_arn`` values, and pairwise-distinct ``external_id`` values. Because the
    registry is keyed on the Authenticated_Identity, the ``identity`` values must
    also be pairwise distinct (a duplicate key would overwrite another tenant's
    record). Any violation raises :class:`ValueError` so the harness never writes
    a registry that silently maps two tenants to the same role, ``ExternalId``, or
    partition key.

    Args:
        specs: Two or more tenant specifications to validate and convert.

    Returns:
        The validated records in the same order as ``specs``.

    Raises:
        ValueError: If fewer than two specs are given, any ``identity`` is empty,
            any ``external_id`` is empty, or any ``identity`` / ``role_arn`` /
            ``external_id`` value collides with another spec's.
    """
    if len(specs) < 2:
        raise ValueError(
            f'At least two tenant specs are required to demonstrate isolation; got {len(specs)}.'
        )

    seen_identities: set[str] = set()
    seen_role_arns: set[str] = set()
    seen_external_ids: set[str] = set()
    records: list[TenantRecord] = []

    for index, spec in enumerate(specs):
        if not spec.identity:
            raise ValueError(f'Tenant spec at index {index} has an empty identity.')
        if not spec.external_id:
            raise ValueError(f'Tenant spec at index {index} has an empty external_id.')

        if spec.identity in seen_identities:
            raise ValueError(f'Duplicate tenant identity at index {index}.')
        if spec.role_arn in seen_role_arns:
            raise ValueError(f'Duplicate tenant role_arn at index {index}.')
        if spec.external_id in seen_external_ids:
            raise ValueError(f'Duplicate tenant external_id at index {index}.')

        seen_identities.add(spec.identity)
        seen_role_arns.add(spec.role_arn)
        seen_external_ids.add(spec.external_id)

        records.append(
            TenantRecord(
                identity=spec.identity,
                role_arn=spec.role_arn,
                external_id=spec.external_id,
                account_id=spec.account_id,
                enabled=spec.enabled,
            )
        )

    return records
