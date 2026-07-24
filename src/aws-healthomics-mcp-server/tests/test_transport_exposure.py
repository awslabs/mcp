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

"""Property-based tests for the secure-by-default network exposure check.

These tests exercise the secure-by-default exposure behavior wired into
``TransportSelector.start``: a network transport bound to a non-loopback host
emits exactly one fronting-auth warning before the server begins accepting
requests and still proceeds to bind, while a loopback host binds silently.

Test docstrings/IDs refer to requirements and design correctness properties by
name (never by number) per project steering.
"""

import ipaddress
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import ServerConfig
from awslabs.aws_healthomics_mcp_server.transport import TransportSelector
from hypothesis import example, given, settings
from hypothesis import strategies as st
from loguru import logger
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_ASCII_ALNUM = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


@st.composite
def loopback_hosts(draw):
    """A loopback host literal: IPv4 within 127.0.0.0/8 or the IPv6 ``::1``."""
    choice = draw(st.sampled_from(['ipv4', 'ipv6']))
    if choice == 'ipv6':
        return '::1'
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(3)]
    return '127.{}.{}.{}'.format(*octets)


@st.composite
def valid_hostnames(draw):
    """A syntactically valid RFC 1123 hostname built from alphanumeric labels."""
    label_count = draw(st.integers(min_value=1, max_value=3))
    labels = [
        draw(st.text(alphabet=_ASCII_ALNUM, min_size=1, max_size=12)) for _ in range(label_count)
    ]
    return '.'.join(labels)


_non_loopback_ipv4 = (
    st.ip_addresses(v=4)
    .filter(lambda addr: addr not in ipaddress.ip_network('127.0.0.0/8'))
    .map(str)
)
_non_loopback_ipv6 = (
    st.ip_addresses(v=6).filter(lambda addr: addr != ipaddress.IPv6Address('::1')).map(str)
)


@st.composite
def non_loopback_hosts(draw):
    """A non-loopback host: non-127/8 IPv4, non-``::1`` IPv6, or a hostname.

    A randomly generated alphanumeric hostname could coincidentally be a
    loopback IP literal (e.g. ``127.0.0.1``); such inputs would be classified
    as loopback by :func:`is_loopback`, so they are excluded here to keep the
    property focused on genuinely non-loopback hosts.
    """
    host = draw(st.one_of(_non_loopback_ipv4, _non_loopback_ipv6, valid_hostnames()))
    try:
        address = ipaddress.ip_address(host)
        is_loopback_literal = address.is_loopback
    except ValueError:
        is_loopback_literal = False
    if is_loopback_literal:
        host = '203.0.113.7'
    return host


network_transports = st.sampled_from(consts.NETWORK_TRANSPORTS)


def _make_mcp(captured_run_warning_count):
    """Build a fake FastMCP whose ``run`` records the warning count at call time.

    Args:
        captured_run_warning_count: A single-element list used to record how many
            warnings had been captured at the moment ``mcp.run`` was invoked.

    Returns:
        A tuple of (the captured-warnings list, the fake FastMCP instance).
    """
    captured_warnings = []

    def _sink(message):
        captured_warnings.append(message.record['message'])

    mcp = MagicMock()
    mcp.settings = MagicMock()

    def _run(transport):
        # Record how many warnings existed at the time serving begins so the
        # test can assert ordering (warning emitted before serving).
        captured_run_warning_count[0] = len(captured_warnings)

    mcp.run.side_effect = _run
    return captured_warnings, mcp, _sink


# ---------------------------------------------------------------------------
# Property: Non-loopback exposure warns before serving
# ---------------------------------------------------------------------------


class TestNonLoopbackExposureWarnsBeforeServing:
    """Property: Non-loopback exposure warns before serving.

    Validates: Requirements Secure-by-default network exposure.
    """

    @settings(max_examples=100)
    @given(host=non_loopback_hosts(), transport=network_transports)
    @example(host='0.0.0.0', transport='streamable-http')
    @example(host='localhost', transport='sse')
    def test_non_loopback_emits_exactly_one_warning_before_serving(self, host, transport):
        """A non-loopback host emits exactly one warning before binding/serving."""
        captured_run_warning_count = [None]
        captured_warnings, mcp, sink = _make_mcp(captured_run_warning_count)
        config = ServerConfig(transport=transport, host=host, port=8000, path='/mcp')

        handler_id = logger.add(sink, level='WARNING')
        try:
            TransportSelector.start(mcp, config)
        finally:
            logger.remove(handler_id)

        # Exactly one fronting-auth warning is emitted for the non-loopback host.
        exposure_warnings = [
            message
            for message in captured_warnings
            if consts.WARN_NON_LOOPBACK_EXPOSURE.format(host) == message
        ]
        assert len(exposure_warnings) == 1

        # Startup still proceeds to bind/serve with exactly the selected mode.
        mcp.run.assert_called_once_with(transport=transport)

        # The warning was emitted before the server began accepting requests:
        # at least one warning had been captured by the time ``run`` was called.
        assert captured_run_warning_count[0] is not None
        assert captured_run_warning_count[0] >= 1

    @settings(max_examples=100)
    @given(host=loopback_hosts(), transport=network_transports)
    @example(host='127.0.0.1', transport='streamable-http')
    @example(host='::1', transport='sse')
    def test_loopback_emits_no_exposure_warning(self, host, transport):
        """A loopback host binds silently with no fronting-auth warning."""
        captured_run_warning_count = [None]
        captured_warnings, mcp, sink = _make_mcp(captured_run_warning_count)
        config = ServerConfig(transport=transport, host=host, port=8000, path='/mcp')

        handler_id = logger.add(sink, level='WARNING')
        try:
            TransportSelector.start(mcp, config)
        finally:
            logger.remove(handler_id)

        # No fronting-auth exposure warning is emitted for a loopback host.
        exposure_warnings = [
            message
            for message in captured_warnings
            if consts.WARN_NON_LOOPBACK_EXPOSURE.format(host) == message
        ]
        assert len(exposure_warnings) == 0

        # Startup still proceeds to bind/serve with exactly the selected mode.
        mcp.run.assert_called_once_with(transport=transport)

        # No warning existed at the time serving began.
        assert captured_run_warning_count[0] == 0
