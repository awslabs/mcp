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

"""Backward-compatibility property tests for ``StaticRoleResolver``.

Property-based tests for ``StaticRoleResolver.resolve`` in
``mechanisms/role_resolver.py``. This module is dedicated to Property
"Backward compatibility": regardless of the decoded token claims, the static
resolver reproduces the current static ``MCP_JWT_ROLE_ARN`` behavior by
returning the configured ARN with no ``ExternalId``.

The Hypothesis conventions (strategies, ``@given``/``@settings`` usage,
inclusive parameter names) mirror those established in
``tests/test_partition_cache_isolation.py``.
"""

from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    RoleTarget,
    StaticRoleResolver,
)
from hypothesis import given, settings
from hypothesis import strategies as st


# Role ARN strings supplied to the resolver constructor. Printable, non-space
# ASCII keeps the values readable; the resolver treats the ARN as an opaque
# provider-controlled string, so any non-empty text exercises the contract.
role_arn_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=1,
    max_size=64,
)

# Arbitrary decoded-token claim dicts. Keys are short identifier-like strings;
# values may be strings, integers, booleans, ``None``, or nested lists/dicts so
# the generated claims cover realistic JWT payload shapes (including one that
# carries a competing ``role_arn`` claim, asserting it is never honored).
claim_values = st.recursive(
    st.one_of(
        st.text(max_size=32),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=3),
        st.dictionaries(st.text(min_size=1, max_size=8), children, max_size=3),
    ),
    max_leaves=5,
)

claims_strategy = st.dictionaries(
    st.text(min_size=1, max_size=16),
    claim_values,
    max_size=6,
)


class TestStaticRoleResolverBackwardCompatibility:
    """Property: Backward compatibility.

    Validates: Requirements Backward Compatibility.
    """

    @given(role_arn=role_arn_strategy, claims=claims_strategy)
    @settings(max_examples=200)
    def test_resolve_returns_configured_arn_and_no_external_id(self, role_arn, claims):
        """Property: Backward compatibility.

        For any configured role ARN and any decoded token claims,
        ``StaticRoleResolver.resolve`` returns a ``RoleTarget`` whose ``role_arn``
        equals the configured value and whose ``external_id`` is ``None``. The
        claims never influence the result, so the resolver reproduces the current
        static ``MCP_JWT_ROLE_ARN`` behavior regardless of the token payload.

        Validates: Requirements Backward Compatibility.
        """
        resolver = StaticRoleResolver(role_arn)

        target = resolver.resolve(claims)

        assert isinstance(target, RoleTarget)
        assert target.role_arn == role_arn
        assert target.external_id is None

    @given(
        role_arn=role_arn_strategy,
        claim_arn=st.text(min_size=1, max_size=64),
    )
    @settings(max_examples=200)
    def test_resolve_ignores_role_arn_claim(self, role_arn, claim_arn):
        """Property: Backward compatibility (claim never selects the role).

        Even when the claims carry their own ``role_arn`` value, the static
        resolver returns the provider-configured ARN and never the claim-supplied
        one, keeping the assumed role determined solely by configuration.

        Validates: Requirements Backward Compatibility.
        """
        resolver = StaticRoleResolver(role_arn)

        target = resolver.resolve({'sub': 'caller', 'role_arn': claim_arn})

        assert target.role_arn == role_arn
        assert target.external_id is None
