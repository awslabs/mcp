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

"""Property tests for the pure-logic resource inventory model.

This module lives outside ``integration/tests/`` (which is opt-in gated behind a
real-AWS signal) and outside the top-level ``tests/`` suite, so it runs as a
fully offline unit-style property test: it never constructs an AWS client,
resolves credentials, or opens a network connection.

Property: The resource inventory round-trips and preserves every recorded
resource in order.

Validates: Requirements Provisioning and teardown lifecycle.
"""

# Feature: remote-deployment-integration-tests, Property: The resource inventory round-trips and preserves every recorded resource in order

from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.inventory import ResourceInventory, ResourceRecord


# Non-empty printable field text. The inventory treats these as opaque
# provider-controlled strings, so any text exercises the contract; bounded
# printable text keeps failing examples readable.
field_text = st.text(min_size=1, max_size=16)

# Attribute maps carry only plain string values (no Credential_Material and no
# nested structures), matching the ``dict[str, str]`` contract of a record.
attribute_maps = st.dictionaries(
    keys=st.text(min_size=1, max_size=8),
    values=st.text(min_size=0, max_size=16),
    max_size=4,
)


@st.composite
def resource_records(draw: st.DrawFn) -> ResourceRecord:
    """Draw a single :class:`ResourceRecord` with plain-string attributes."""
    return ResourceRecord(
        resource_id=draw(field_text),
        resource_type=draw(field_text),
        region=draw(field_text),
        deployment=draw(field_text),
        attributes=draw(attribute_maps),
    )


@settings(max_examples=200)
@given(
    deployment=field_text,
    region=field_text,
    added_records=st.lists(resource_records(), max_size=8),
)
def test_inventory_round_trips_and_preserves_order(
    deployment: str,
    region: str,
    added_records: list[ResourceRecord],
) -> None:
    """Property: The resource inventory round-trips and preserves every recorded resource in order.

    For any inventory header and any sequence of resource records appended via
    ``add``, serializing with ``to_json`` and deserializing with ``from_json``
    yields an equivalent inventory (same deployment, region, and records), and
    the reconstructed ``records`` contain every added resource's identifier and
    type in exactly the order they were added. Serialization is also
    deterministic: calling ``to_json`` twice yields identical text.

    Validates: Requirements Provisioning and teardown lifecycle.
    """
    inventory = ResourceInventory(deployment=deployment, region=region)
    for record in added_records:
        inventory.add(record)

    # Round-trip without a scanner: the offline property does not need credential
    # scanning, only structural fidelity.
    serialized = inventory.to_json()
    loaded = ResourceInventory.from_json(serialized)

    # The reconstructed inventory equals the original header-for-header. Records
    # are frozen dataclasses, so ``==`` compares them structurally; attribute-key
    # sorting in ``to_json`` does not affect order-independent dict equality.
    assert loaded.deployment == inventory.deployment
    assert loaded.region == inventory.region
    assert loaded.records == added_records

    # Every added resource's identifier and type survives in the added order.
    assert [(record.resource_id, record.resource_type) for record in loaded.records] == [
        (record.resource_id, record.resource_type) for record in added_records
    ]

    # Serialization is deterministic across repeated calls.
    assert inventory.to_json() == serialized
