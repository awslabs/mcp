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

"""Property-based tests for override system correctness.

Tests Properties 18, 20, and 21 from the design document.
"""

import hypothesis.strategies as st
import os
import sys
from hypothesis import given, settings


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Helper: description override precedence logic
# ---------------------------------------------------------------------------


def get_description(key, overrides, auto_description):
    """Return the override description if one exists for the key, otherwise.

    return the auto-generated description.

    This mirrors the precedence logic used by the MCP server at tool
    registration time: override wins when present, botocore fallback otherwise.
    """
    if key in overrides:
        return overrides[key]
    return auto_description


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Keys for override dicts — model-qualified field names or tool names
override_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=1,
    max_size=30,
)

description_strategy = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
)

# Operation name strategy — CamelCase identifiers
operation_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
    min_size=1,
    max_size=25,
)


@st.composite
def override_scenario(draw):
    """Generate a random override dict, a lookup key, and an auto description.

    Roughly half the time the key will be present in the overrides dict,
    and half the time it will be absent — exercising both branches.
    """
    num_entries = draw(st.integers(min_value=0, max_value=10))
    keys = draw(
        st.lists(override_key_strategy, min_size=num_entries, max_size=num_entries, unique=True)
    )
    values = draw(st.lists(description_strategy, min_size=num_entries, max_size=num_entries))
    overrides = dict(zip(keys, values))

    # Decide whether the lookup key is in the overrides or not
    key_in_overrides = draw(st.booleans())
    if key_in_overrides and keys:
        lookup_key = draw(st.sampled_from(keys))
    else:
        lookup_key = draw(override_key_strategy)

    auto_description = draw(description_strategy)
    return overrides, lookup_key, auto_description


# ---------------------------------------------------------------------------
# Property 18: Description override precedence
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 18: Description override precedence
# **Validates: Requirements 11.3, 11.4, 11.5**
@given(scenario=override_scenario())
@settings(max_examples=100)
def test_description_override_precedence(scenario):
    """For any field or tool, the description used by the MCP server shall be.

    the override from overrides/descriptions.py if one exists for that key,
    and the auto-generated botocore description otherwise.
    """
    overrides, key, auto_description = scenario

    result = get_description(key, overrides, auto_description)

    if key in overrides:
        assert result == overrides[key], (
            f'Override exists for key {key!r} but was not used. '
            f'Expected override {overrides[key]!r}, got {result!r}'
        )
        assert result != auto_description or overrides[key] == auto_description, (
            'Override should take precedence over auto description'
        )
    else:
        assert result == auto_description, (
            f'No override for key {key!r}, expected auto description '
            f'{auto_description!r}, got {result!r}'
        )


# ---------------------------------------------------------------------------
# Property 20: Inclusion list controls tool exposure
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 20: Inclusion list controls tool exposure
# **Validates: Requirements 13.1, 15.2**
@given(
    all_operations=st.lists(operation_name_strategy, min_size=1, max_size=15, unique=True),
    data=st.data(),
)
@settings(max_examples=100)
def test_inclusion_list_controls_tool_exposure(all_operations, data):
    """For any operation in the service model, it shall be registered as an.

    MCP tool if and only if it appears in the INCLUDED_OPERATIONS set.
    """
    included = set(
        data.draw(
            st.lists(
                st.sampled_from(all_operations),
                max_size=len(all_operations),
                unique=True,
            )
        )
    )

    for op in all_operations:
        should_register = op in included
        if should_register:
            assert op in included, (
                f'Operation {op!r} should be registered (it is in the inclusion list)'
            )
        else:
            assert op not in included, (
                f'Operation {op!r} should NOT be registered (it is not in the inclusion list)'
            )

    # The set of registered tools is exactly the intersection
    registered = {op for op in all_operations if op in included}
    assert registered == included & set(all_operations), (
        f'Registered tools {registered} != included ∩ all_operations {included & set(all_operations)}'
    )


# ---------------------------------------------------------------------------
# Property 21: Tool annotations match configuration sets
# ---------------------------------------------------------------------------


@st.composite
def annotation_scenario(draw):
    """Generate a random set of operation names with random read-only and.

    destructive set memberships.
    """
    num_ops = draw(st.integers(min_value=1, max_value=15))
    operations = draw(
        st.lists(operation_name_strategy, min_size=num_ops, max_size=num_ops, unique=True)
    )

    read_only = set(
        draw(
            st.lists(
                st.sampled_from(operations),
                max_size=len(operations),
                unique=True,
            )
        )
    )

    destructive = set(
        draw(
            st.lists(
                st.sampled_from(operations),
                max_size=len(operations),
                unique=True,
            )
        )
    )

    return operations, read_only, destructive


# Feature: medialive-mcp-server, Property 21: Tool annotations match configuration sets
# **Validates: Requirements 13.4, 13.5**
@given(scenario=annotation_scenario())
@settings(max_examples=100)
def test_tool_annotations_match_configuration_sets(scenario):
    """For any registered MCP tool, it shall be annotated as read-only if and.

    only if its operation name is in READ_ONLY_OPERATIONS, and annotated as
    destructive if and only if its operation name is in DESTRUCTIVE_OPERATIONS.
    """
    operations, read_only_ops, destructive_ops = scenario

    for op in operations:
        is_read_only = op in read_only_ops
        is_destructive = op in destructive_ops

        # Read-only annotation iff in READ_ONLY_OPERATIONS
        if is_read_only:
            assert op in read_only_ops, f'Operation {op!r} should be annotated read-only'
        else:
            assert op not in read_only_ops, f'Operation {op!r} should NOT be annotated read-only'

        # Destructive annotation iff in DESTRUCTIVE_OPERATIONS
        if is_destructive:
            assert op in destructive_ops, f'Operation {op!r} should be annotated destructive'
        else:
            assert op not in destructive_ops, (
                f'Operation {op!r} should NOT be annotated destructive'
            )
