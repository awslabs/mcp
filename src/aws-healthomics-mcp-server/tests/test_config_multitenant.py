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

"""Property-based tests for multi-tenant transport selection.

These tests exercise the decision logic in
``awslabs.aws_healthomics_mcp_server.config`` governing the multi-tenant mode
selection rule: enabling multi-tenant mode together with the ``stdio`` transport
is an incompatible configuration that is rejected before any transport starts.

Test docstrings/IDs refer to requirements and design correctness properties by
name (never by number) per project steering.
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    TransportConfigError,
    parse_config,
)
from hypothesis import given, settings
from hypothesis import strategies as st


# Environment variables that parse_config reads. They must be unset for every
# test so that the developer's shell environment never pollutes the parsed
# configuration.
_MCP_ENV_VARS = (
    consts.MCP_TRANSPORT_ENV,
    consts.MCP_HOST_ENV,
    consts.MCP_PORT_ENV,
    consts.MCP_PATH_ENV,
    consts.MCP_MULTI_TENANT_ENV,
    consts.MCP_INBOUND_AUTH_ENV,
)


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch):
    """Ensure no MCP_* transport/network/multi-tenant env vars leak into parsing."""
    for name in _MCP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

# Recognized values that enable multi-tenant mode (case-insensitive). Mirrors
# the private _MULTI_TENANT_ENABLE_VALUES set in the config module.
_MULTI_TENANT_ENABLE_VALUES = ('true', '1', 'yes', 'on', 'enabled')


@st.composite
def multi_tenant_enable_values(draw):
    """An enable value with optional case variation (parsing is case-insensitive)."""
    value = draw(st.sampled_from(_MULTI_TENANT_ENABLE_VALUES))
    return draw(st.sampled_from([value, value.upper(), value.title(), value.swapcase()]))


def _arg(flag, value):
    """Build a single ``--flag=value`` argv token (unambiguous for argparse)."""
    return '{}={}'.format(flag, value)


# ---------------------------------------------------------------------------
# Property: Multi-tenant mode selection
# ---------------------------------------------------------------------------


class TestMultiTenantStdioRejection:
    """Property: Multi-tenant + stdio is rejected.

    Validates: Requirements Multi-tenant mode selection.
    """

    @settings(max_examples=100)
    @given(
        enable=multi_tenant_enable_values(),
        transport=st.sampled_from(['stdio', None]),
    )
    def test_multi_tenant_with_stdio_is_rejected(self, enable, transport):
        """Enabling multi-tenant with stdio (explicit or default) is rejected.

        For any recognized enable value combined with the stdio transport -
        whether selected explicitly via ``--transport stdio`` or left absent so
        it defaults to stdio - parse_config signals an incompatibility error and
        no transport configuration is returned.
        """
        argv = [_arg('--multi-tenant', enable)]
        if transport is not None:
            argv.append(_arg('--transport', transport))

        with pytest.raises(TransportConfigError):
            parse_config(argv)

    @settings(max_examples=100)
    @given(
        enable=multi_tenant_enable_values(),
        transport=st.sampled_from(consts.NETWORK_TRANSPORTS),
    )
    def test_multi_tenant_with_network_transport_is_accepted(self, enable, transport):
        """Sanity contrast: multi-tenant with a network transport is accepted.

        The same enable values that are rejected with stdio must NOT raise when
        paired with a network transport; the resulting configuration enables
        multi-tenant mode on that transport.
        """
        config = parse_config([_arg('--multi-tenant', enable), _arg('--transport', transport)])
        assert config.multi_tenant is True
        assert config.transport == transport
