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

"""Property-based tests for multi-tenant enable/disable parsing.

These tests exercise the pure decision logic in
``awslabs.aws_healthomics_mcp_server.config`` for the ``--multi-tenant`` flag and
the ``MCP_MULTI_TENANT`` environment variable. A network transport
(``streamable-http``) is always supplied so the multi-tenant + ``stdio``
rejection rule (covered separately by the "Multi-tenant + stdio is rejected"
property) never interferes with this property.

Test docstrings/IDs refer to requirements and design correctness properties by
name (never by number) per project steering.
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    _MULTI_TENANT_DISABLE_VALUES,
    _MULTI_TENANT_ENABLE_VALUES,
    TransportConfigError,
    parse_config,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


# Environment variables that parse_config reads. They must be unset for every
# test so the developer's shell environment never pollutes the parsed config.
_MCP_ENV_VARS = (
    consts.MCP_TRANSPORT_ENV,
    consts.MCP_HOST_ENV,
    consts.MCP_PORT_ENV,
    consts.MCP_PATH_ENV,
    consts.MCP_MULTI_TENANT_ENV,
    consts.MCP_INBOUND_AUTH_ENV,
)

# Recognized values after trimming + lowercasing. Used to filter the
# unrecognized-value generator.
_RECOGNIZED_VALUES = frozenset(_MULTI_TENANT_ENABLE_VALUES + _MULTI_TENANT_DISABLE_VALUES)


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch):
    """Ensure no MCP_* transport/network env vars leak into parsing."""
    for name in _MCP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _arg(flag, value):
    """Build a single ``--flag=value`` argv token (unambiguous for argparse)."""
    return '{}={}'.format(flag, value)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_WHITESPACE = st.text(alphabet=' \t', max_size=3)


@st.composite
def enable_values_noisy(draw):
    """A recognized enable value with random case and surrounding whitespace."""
    value = draw(st.sampled_from(_MULTI_TENANT_ENABLE_VALUES))
    transform = draw(st.sampled_from(['lower', 'upper', 'swapcase']))
    if transform == 'upper':
        value = value.upper()
    elif transform == 'swapcase':
        value = value.swapcase()
    return draw(_WHITESPACE) + value + draw(_WHITESPACE)


@st.composite
def disable_values_noisy(draw):
    """A recognized disable value with random case and surrounding whitespace."""
    value = draw(st.sampled_from(_MULTI_TENANT_DISABLE_VALUES))
    transform = draw(st.sampled_from(['lower', 'upper', 'swapcase']))
    if transform == 'upper':
        value = value.upper()
    elif transform == 'swapcase':
        value = value.swapcase()
    return draw(_WHITESPACE) + value + draw(_WHITESPACE)


@st.composite
def unrecognized_values(draw):
    """A non-empty value that is neither a recognized enable nor disable value.

    Anything that trims/lowercases into a recognized value or into the empty
    string is filtered out, since those are handled by the enable/disable and
    absent-value branches respectively.
    """
    return draw(st.text(min_size=1, max_size=12))


def _is_unrecognized(raw):
    normalized = raw.strip().lower()
    return normalized != '' and normalized not in _RECOGNIZED_VALUES


class TestMultiTenantEnableDisableParsing:
    """Property: Multi-tenant enable/disable parsing.

    Validates: Requirements Multi-tenant mode selection
    """

    @settings(max_examples=100)
    @given(value=enable_values_noisy())
    def test_recognized_enable_values_enable_multi_tenant(self, value):
        """Any recognized enable value (any case, padded) enables multi-tenant mode."""
        config = parse_config(
            [_arg('--transport', 'streamable-http'), _arg('--multi-tenant', value)]
        )
        assert config.multi_tenant is True

    @settings(max_examples=100)
    @given(value=disable_values_noisy())
    def test_recognized_disable_values_use_single_tenant(self, value):
        """Any recognized disable value (any case, padded) yields single-tenant mode."""
        config = parse_config(
            [_arg('--transport', 'streamable-http'), _arg('--multi-tenant', value)]
        )
        assert config.multi_tenant is False

    def test_absent_value_uses_single_tenant(self):
        """An absent multi-tenant flag yields single-tenant mode."""
        config = parse_config([_arg('--transport', 'streamable-http')])
        assert config.multi_tenant is False

    @settings(max_examples=100)
    @given(blank=st.text(alphabet=' \t', max_size=4))
    def test_blank_value_uses_single_tenant(self, blank):
        """An empty/whitespace-only flag value yields single-tenant mode."""
        config = parse_config(
            [_arg('--transport', 'streamable-http'), _arg('--multi-tenant', blank)]
        )
        assert config.multi_tenant is False

    @settings(max_examples=100)
    @given(value=unrecognized_values().filter(_is_unrecognized))
    def test_unrecognized_values_raise_error(self, value):
        """Any unrecognized non-empty value raises TransportConfigError naming accepted values."""
        with pytest.raises(TransportConfigError) as exc_info:
            parse_config([_arg('--transport', 'streamable-http'), _arg('--multi-tenant', value)])
        # The error identifies the accepted values (enable + disable).
        message = str(exc_info.value)
        for accepted in _MULTI_TENANT_ENABLE_VALUES + _MULTI_TENANT_DISABLE_VALUES:
            assert accepted in message

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(value=enable_values_noisy())
    def test_env_var_enable_values_enable_multi_tenant(self, value, monkeypatch):
        """The environment variable path also recognizes enable values."""
        monkeypatch.setenv(consts.MCP_MULTI_TENANT_ENV, value)
        config = parse_config([_arg('--transport', 'streamable-http')])
        assert config.multi_tenant is True
