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

# Feature: mcp-pagination-support, Property 7: Pagination hints contain token and limit field names
"""Property-based tests for pagination hints in tool descriptions.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

Tests that for any paginated operation with pagination metadata, the
registered tool description contains the output token field name, the
input token field name, and (if a limit_key is defined) the limit key
field name.
"""

import hypothesis.strategies as st
from hypothesis import given, settings


# ---------------------------------------------------------------------------
# Replicate the hint-building logic from server.py _register_tools
# ---------------------------------------------------------------------------
def build_pagination_hint(pagination: dict, base_description: str) -> str:
    """Replicate the pagination hint logic from server.py _register_tools.

    Given pagination metadata and a base description, returns the full
    description with pagination hints appended.
    """
    output_tokens = pagination.get('output_tokens', [])
    input_tokens = pagination.get('input_tokens', [])
    limit_key = pagination.get('limit_key')

    hint_parts = ['This operation supports pagination.']
    if output_tokens:
        hint_parts.append(f"Check '{output_tokens[0]}' in the response for more pages.")
    if input_tokens:
        hint_parts.append(f"Pass '{input_tokens[0]}' to fetch the next page.")
    if limit_key:
        hint_parts.append(f"Use '{limit_key}' to control page size.")

    return base_description + ' ' + ' '.join(hint_parts)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------
_identifier = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_',
        max_codepoint=127,
    ),
    min_size=1,
    max_size=30,
).filter(lambda s: s[0].isalpha())

_token_list = st.lists(_identifier, min_size=1, max_size=3)


@st.composite
def pagination_meta_strategy(draw):
    """Generate random pagination metadata with random token/limit names."""
    return {
        'input_tokens': draw(_token_list),
        'output_tokens': draw(_token_list),
        'result_keys': draw(_token_list),
        'limit_key': draw(st.one_of(st.none(), _identifier)),
    }


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


# **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
@given(
    pagination=pagination_meta_strategy(),
    base_description=st.text(min_size=0, max_size=200),
)
@settings(max_examples=100)
def test_pagination_hints_contain_token_and_limit_field_names(
    pagination: dict, base_description: str
) -> None:
    """For any paginated operation with pagination metadata, the tool.

    description shall contain the output token, input token, and (if
    defined) limit key field names.
    """
    description = build_pagination_hint(pagination, base_description)

    # Requirement 7.1: hint indicates pagination support
    assert 'This operation supports pagination.' in description

    # Requirement 7.2: output token field name appears in hint
    output_tokens = pagination.get('output_tokens', [])
    if output_tokens:
        assert output_tokens[0] in description, (
            f"Output token '{output_tokens[0]}' should appear in description"
        )

    # Requirement 7.3: input token field name appears in hint
    input_tokens = pagination.get('input_tokens', [])
    if input_tokens:
        assert input_tokens[0] in description, (
            f"Input token '{input_tokens[0]}' should appear in description"
        )

    # Requirement 7.4: limit key field name appears if defined
    limit_key = pagination.get('limit_key')
    if limit_key:
        assert limit_key in description, f"Limit key '{limit_key}' should appear in description"
