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

"""Persistent resource inventory for the integration harness.

Each provisioning step appends a :class:`ResourceRecord` to a
:class:`ResourceInventory` at the moment a resource is created, so a mid-flight
provisioning failure still leaves a complete-enough inventory for teardown. The
inventory persists as deterministic, round-trippable JSON.

The inventory NEVER stores Credential_Material. Every record's ``attributes``
values are validated through a :class:`~integration.harness.credential_scan.CredentialMaterialScanner`
before the inventory is written to disk (Req 7.3). The scanner is injected so the
offline round-trip property test can serialize without one, while the live write
path enforces cleanliness by supplying the harness's registered scanner.
"""

import json
import os
from dataclasses import dataclass, field
from integration.harness.credential_scan import CredentialMaterialScanner
from pathlib import Path
from typing import Optional, Union


@dataclass(frozen=True)
class ResourceRecord:
    """A single provisioned AWS resource recorded for teardown.

    Attributes:
        resource_id: Provider identifier (ARN, name, or physical id).
        resource_type: Resource category, e.g. ``'dynamodb-table'``,
            ``'agentcore-runtime'``, or ``'apigateway-restapi'``.
        region: The AWS region the resource lives in.
        deployment: The owning deployment, ``'agentcore'`` or ``'apigateway'``.
        attributes: Non-secret extras (for example an endpoint reference). These
            values are validated against the ``CredentialMaterialScanner`` before
            the inventory is written so no Credential_Material is ever persisted.
    """

    resource_id: str
    resource_type: str
    region: str
    deployment: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class ResourceInventory:
    """An ordered, JSON-persistable collection of provisioned resources.

    ``records`` preserves creation order: each :meth:`add` appends, and
    serialization/deserialization keeps the order intact so teardown can walk the
    resources deterministically.
    """

    deployment: str
    region: str
    records: list[ResourceRecord] = field(default_factory=list)

    def add(self, record: ResourceRecord) -> None:
        """Append ``record``, preserving creation order.

        Args:
            record: The resource record to record in the inventory.
        """
        self.records.append(record)

    def _validate(self, scanner: CredentialMaterialScanner) -> None:
        """Assert no record ``attributes`` value contains Credential_Material.

        Args:
            scanner: The scanner registered with the harness's known secrets.

        Raises:
            AssertionError: If any attribute value contains a registered secret.
                The message names the material type and location, never the value.
        """
        for record in self.records:
            for key, value in record.attributes.items():
                scanner.assert_clean(value, f'inventory:{record.resource_id}:{key}')

    def to_json(self, scanner: Optional[CredentialMaterialScanner] = None) -> str:
        """Serialize to a deterministic, ordered JSON string.

        When ``scanner`` is provided, every record's ``attributes`` values are
        validated against it before serialization so no Credential_Material is
        ever emitted (Req 7.3). When ``scanner`` is ``None`` the content is
        serialized as-is, which supports the offline round-trip property test.

        Args:
            scanner: Optional credential-material scanner used to enforce that no
                registered secret is serialized.

        Returns:
            A deterministic JSON representation of the inventory.

        Raises:
            AssertionError: If ``scanner`` is provided and any attribute value
                contains a registered secret.
        """
        if scanner is not None:
            self._validate(scanner)
        payload = {
            'deployment': self.deployment,
            'region': self.region,
            'records': [
                {
                    'resource_id': record.resource_id,
                    'resource_type': record.resource_type,
                    'region': record.region,
                    'deployment': record.deployment,
                    'attributes': {
                        key: record.attributes[key] for key in sorted(record.attributes)
                    },
                }
                for record in self.records
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=False)

    @classmethod
    def from_json(cls, text: str) -> 'ResourceInventory':
        """Deserialize an inventory from a JSON string produced by :meth:`to_json`.

        Args:
            text: The JSON text to parse.

        Returns:
            The reconstructed :class:`ResourceInventory`.
        """
        payload = json.loads(text)
        records = [
            ResourceRecord(
                resource_id=raw['resource_id'],
                resource_type=raw['resource_type'],
                region=raw['region'],
                deployment=raw['deployment'],
                attributes=dict(raw.get('attributes', {})),
            )
            for raw in payload.get('records', [])
        ]
        return cls(
            deployment=payload['deployment'],
            region=payload['region'],
            records=records,
        )

    def save(
        self,
        path: Union[str, Path],
        scanner: Optional[CredentialMaterialScanner] = None,
    ) -> None:
        """Atomically write the inventory to ``path`` as JSON.

        The content is written to a temporary file in the same directory and then
        moved into place with :func:`os.replace`, so a reader never observes a
        partially written inventory. When ``scanner`` is provided the content is
        validated against it before any bytes are written (Req 7.3).

        Args:
            path: Destination file path.
            scanner: Optional credential-material scanner used to enforce that no
                registered secret is written to disk.

        Raises:
            AssertionError: If ``scanner`` is provided and any attribute value
                contains a registered secret; no file is written in that case.
        """
        target = Path(path)
        content = self.to_json(scanner=scanner)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target.with_name(f'{target.name}.{os.getpid()}.tmp')
        try:
            tmp_path.write_text(content, encoding='utf-8')
            os.replace(tmp_path, target)
        finally:
            # Clean up the temp file if os.replace did not consume it (e.g. on error).
            if tmp_path.exists():
                tmp_path.unlink()

    @classmethod
    def load(cls, path: Union[str, Path]) -> 'ResourceInventory':
        """Load an inventory previously written by :meth:`save`.

        Args:
            path: The file path to read.

        Returns:
            The reconstructed :class:`ResourceInventory`.
        """
        text = Path(path).read_text(encoding='utf-8')
        return cls.from_json(text)
