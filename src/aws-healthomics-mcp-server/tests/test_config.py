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

"""Property-based tests for transport/network configuration parsing.

These tests exercise the pure decision logic in
``awslabs.aws_healthomics_mcp_server.config`` (transport normalization,
CLI-over-environment precedence, port/host validation, loopback
classification, network defaults, and the stdio bind-ignoring rule).

Test docstrings/IDs refer to requirements and design correctness properties by
name (never by number) per project steering.
"""

import ipaddress
import pytest
import string
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    TransportConfigError,
    UnsupportedTransportError,
    is_loopback,
    normalize_transport,
    parse_config,
)
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st


# Environment variables that parse_config reads. They must be unset for every
# test that does not explicitly exercise environment-variable behavior so that
# the developer's shell environment never pollutes the parsed configuration.
_MCP_ENV_VARS = (
    consts.MCP_TRANSPORT_ENV,
    consts.MCP_HOST_ENV,
    consts.MCP_PORT_ENV,
    consts.MCP_PATH_ENV,
)

_ASCII_ALNUM = string.ascii_letters + string.digits


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch):
    """Ensure no MCP_* transport/network env vars leak into parsing."""
    for name in _MCP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_WHITESPACE = st.text(alphabet=' \t', max_size=3)


@st.composite
def padded(draw, value):
    """Wrap a value in random leading/trailing whitespace."""
    return draw(_WHITESPACE) + value + draw(_WHITESPACE)


@st.composite
def supported_transports_padded(draw):
    """A supported transport mode with optional surrounding whitespace."""
    transport = draw(st.sampled_from(consts.SUPPORTED_TRANSPORTS))
    return draw(padded(transport))


@st.composite
def whitespace_only(draw):
    """A non-empty whitespace-only string (or the empty string)."""
    return draw(st.text(alphabet=' \t', max_size=4))


@st.composite
def unsupported_transports(draw):
    """A non-empty value that is not a supported transport after trimming."""
    raw = draw(st.text(min_size=1, max_size=12))
    trimmed = raw.strip()
    assume(trimmed != '')
    assume(trimmed not in consts.SUPPORTED_TRANSPORTS)
    return raw


@st.composite
def wrong_case_transports(draw):
    """A supported transport mutated so case no longer matches (unsupported)."""
    transport = draw(st.sampled_from(consts.SUPPORTED_TRANSPORTS))
    mutated = draw(st.sampled_from([transport.upper(), transport.swapcase(), transport.title()]))
    assume(mutated not in consts.SUPPORTED_TRANSPORTS)
    return mutated


@st.composite
def valid_hostnames(draw):
    """A syntactically valid RFC 1123 hostname built from alphanumeric labels."""
    label_count = draw(st.integers(min_value=1, max_value=3))
    labels = [
        draw(st.text(alphabet=_ASCII_ALNUM, min_size=1, max_size=12)) for _ in range(label_count)
    ]
    return '.'.join(labels)


_valid_ipv4 = st.ip_addresses(v=4).map(str)
_valid_ipv6 = st.ip_addresses(v=6).map(str)
valid_hosts = st.one_of(_valid_ipv4, _valid_ipv6, valid_hostnames())


@st.composite
def invalid_hosts(draw):
    """A non-empty host containing a character invalid in IPs and hostnames."""
    # prefix and suffix are non-empty so the invalid character is always
    # interior and is never removed by surrounding-whitespace trimming.
    prefix = draw(st.text(alphabet=_ASCII_ALNUM, min_size=1, max_size=8))
    bad = draw(st.sampled_from(list(' _!@#$%/\\')))
    suffix = draw(st.text(alphabet=_ASCII_ALNUM, min_size=1, max_size=8))
    return prefix + bad + suffix


valid_ports = st.integers(min_value=1, max_value=65535)
invalid_int_ports = st.one_of(st.integers(max_value=0), st.integers(min_value=65536))


@st.composite
def non_integer_port_strings(draw):
    """A non-empty, non-whitespace string that does not parse as an integer."""
    # Alphabet excludes digits so int() always fails for non-empty input.
    return draw(st.text(alphabet=string.ascii_letters + '.-', min_size=1, max_size=8))


@st.composite
def loopback_ipv4(draw):
    """An IPv4 literal within the 127.0.0.0/8 loopback range."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(3)]
    return '127.{}.{}.{}'.format(*octets)


_non_loopback_ipv4 = (
    st.ip_addresses(v=4)
    .filter(lambda addr: addr not in ipaddress.ip_network('127.0.0.0/8'))
    .map(str)
)
_non_loopback_ipv6 = (
    st.ip_addresses(v=6).filter(lambda addr: addr != ipaddress.IPv6Address('::1')).map(str)
)


def _arg(flag, value):
    """Build a single ``--flag=value`` argv token (unambiguous for argparse)."""
    return '{}={}'.format(flag, value)


# ---------------------------------------------------------------------------
# Property: Transport normalization and selection
# ---------------------------------------------------------------------------


class TestTransportNormalizationAndSelection:
    """Property: Transport normalization and selection.

    Validates: Requirements Transport selection.
    """

    @settings(max_examples=100)
    @given(raw=supported_transports_padded())
    def test_supported_transport_is_trimmed_and_selected(self, raw):
        """A supported transport (with surrounding whitespace) normalizes to itself."""
        expected = raw.strip()
        assert normalize_transport(raw) == expected
        assert parse_config([_arg('--transport', raw)]).transport == expected

    @settings(max_examples=100)
    @given(blank=whitespace_only())
    @example(blank='')
    def test_absent_or_blank_transport_defaults_to_stdio(self, blank):
        """Absent, empty, or whitespace-only transport selects the stdio default."""
        assert normalize_transport(None) == consts.DEFAULT_TRANSPORT
        assert normalize_transport(blank) == consts.DEFAULT_TRANSPORT
        # No transport flag and no env var -> stdio.
        assert parse_config([]).transport == consts.DEFAULT_TRANSPORT
        # Blank flag value falls back to the stdio default.
        assert parse_config([_arg('--transport', blank)]).transport == consts.DEFAULT_TRANSPORT

    @settings(max_examples=100)
    @given(raw=unsupported_transports())
    def test_unsupported_transport_raises(self, raw):
        """A non-empty unsupported transport raises UnsupportedTransportError."""
        with pytest.raises(UnsupportedTransportError):
            normalize_transport(raw)
        with pytest.raises(UnsupportedTransportError):
            parse_config([_arg('--transport', raw)])

    @settings(max_examples=100)
    @given(raw=wrong_case_transports())
    def test_transport_match_is_case_sensitive(self, raw):
        """Case-mismatched transports are unsupported (case-sensitive match)."""
        with pytest.raises(UnsupportedTransportError):
            normalize_transport(raw)


# ---------------------------------------------------------------------------
# Property: CLI-over-environment precedence
# ---------------------------------------------------------------------------


class TestCliOverEnvironmentPrecedence:
    """Property: CLI-over-environment precedence.

    Validates: Requirements Transport selection, Network bind configuration.
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cli=st.one_of(supported_transports_padded(), whitespace_only()),
        env=st.sampled_from(consts.SUPPORTED_TRANSPORTS),
    )
    def test_transport_cli_wins_when_non_empty(self, monkeypatch, cli, env):
        """A non-empty CLI transport wins; a blank CLI value falls back to env."""
        monkeypatch.setenv(consts.MCP_TRANSPORT_ENV, env)
        expected_raw = cli if cli.strip() != '' else env
        expected = normalize_transport(expected_raw)
        assert parse_config([_arg('--transport', cli)]).transport == expected

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cli_host=st.one_of(valid_hosts.flatmap(lambda h: padded(h)), whitespace_only()),
        env_host=valid_hosts,
        cli_port=st.one_of(valid_ports.map(str).flatmap(lambda p: padded(p)), whitespace_only()),
        env_port=valid_ports,
    )
    def test_host_and_port_cli_wins_when_non_empty(
        self, monkeypatch, cli_host, env_host, cli_port, env_port
    ):
        """Non-empty CLI host/port win over env; blank CLI values fall back to env."""
        monkeypatch.setenv(consts.MCP_HOST_ENV, env_host)
        monkeypatch.setenv(consts.MCP_PORT_ENV, str(env_port))

        expected_host = (cli_host if cli_host.strip() != '' else env_host).strip()
        expected_port = int((cli_port if cli_port.strip() != '' else str(env_port)).strip())

        config = parse_config(
            [
                _arg('--transport', 'streamable-http'),
                _arg('--host', cli_host),
                _arg('--port', cli_port),
            ]
        )
        assert config.host == expected_host
        assert config.port == expected_port


# ---------------------------------------------------------------------------
# Property: Port validation
# ---------------------------------------------------------------------------


class TestPortValidation:
    """Property: Port validation.

    Validates: Requirements Network bind configuration.
    """

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS), port=valid_ports)
    @example(transport='streamable-http', port=1)
    @example(transport='streamable-http', port=65535)
    def test_in_range_ports_are_accepted(self, transport, port):
        """Integer ports in 1..65535 are accepted and returned unchanged."""
        config = parse_config([_arg('--transport', transport), _arg('--port', str(port))])
        assert config.port == port

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS), port=invalid_int_ports)
    @example(transport='streamable-http', port=0)
    @example(transport='streamable-http', port=65536)
    @example(transport='streamable-http', port=-1)
    def test_out_of_range_ports_are_rejected(self, transport, port):
        """Integer ports outside 1..65535 raise TransportConfigError."""
        with pytest.raises(TransportConfigError):
            parse_config([_arg('--transport', transport), _arg('--port', str(port))])

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS), port=non_integer_port_strings())
    @example(transport='streamable-http', port='abc')
    @example(transport='streamable-http', port='12.5')
    def test_non_integer_ports_are_rejected(self, transport, port):
        """Non-integer port strings raise TransportConfigError."""
        with pytest.raises(TransportConfigError):
            parse_config([_arg('--transport', transport), _arg('--port', port)])


# ---------------------------------------------------------------------------
# Property: Host validation and loopback classification
# ---------------------------------------------------------------------------


class TestHostValidationAndLoopbackClassification:
    """Property: Host validation and loopback classification.

    Validates: Requirements Network bind configuration, Secure-by-default
    network exposure.
    """

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS), host=valid_hosts)
    def test_valid_hosts_are_accepted(self, transport, host):
        """Valid IPv4/IPv6/hostname values are accepted and returned trimmed."""
        config = parse_config([_arg('--transport', transport), _arg('--host', host)])
        assert config.host == host.strip()

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS), host=invalid_hosts())
    def test_invalid_hosts_are_rejected(self, transport, host):
        """Syntactically invalid hosts raise TransportConfigError."""
        with pytest.raises(TransportConfigError):
            parse_config([_arg('--transport', transport), _arg('--host', host)])

    @settings(max_examples=100)
    @given(host=st.one_of(loopback_ipv4(), st.just('::1')))
    @example(host='127.0.0.1')
    @example(host='::1')
    def test_loopback_literals_are_classified_as_loopback(self, host):
        """IPv4 127.0.0.0/8 and IPv6 ::1 literals classify as loopback."""
        assert is_loopback(host) is True

    @settings(max_examples=100)
    @given(host=st.one_of(_non_loopback_ipv4, _non_loopback_ipv6, valid_hostnames()))
    @example(host='localhost')
    @example(host='0.0.0.0')
    def test_non_loopback_values_are_not_loopback(self, host):
        """Non-loopback IP literals and any hostname are not loopback."""
        # A randomly generated alphanumeric hostname could coincidentally be a
        # loopback IP literal (e.g. "127.0.0.1"); such inputs are out of scope
        # for this property.
        assume(not (host[0].isdigit() and is_loopback(host)))
        assert is_loopback(host) is False


# ---------------------------------------------------------------------------
# Property: Network default bind values
# ---------------------------------------------------------------------------


class TestNetworkDefaultBindValues:
    """Property: Network default bind values.

    Validates: Requirements Network bind configuration.
    """

    @settings(max_examples=100)
    @given(transport=st.sampled_from(consts.NETWORK_TRANSPORTS))
    def test_absent_bind_values_use_network_defaults(self, transport):
        """With no host/port/path supplied, network transports use the defaults."""
        config = parse_config([_arg('--transport', transport)])
        assert config.transport == transport
        assert config.host == consts.DEFAULT_HTTP_HOST
        assert config.port == consts.DEFAULT_HTTP_PORT
        assert config.path == consts.DEFAULT_HTTP_PATH


# ---------------------------------------------------------------------------
# Property: stdio ignores bind configuration
# ---------------------------------------------------------------------------


class TestStdioIgnoresBindConfiguration:
    """Property: stdio ignores bind configuration.

    Validates: Requirements Network bind configuration.
    """

    @settings(max_examples=100)
    @given(
        host=st.one_of(valid_hosts, invalid_hosts()),
        port=st.one_of(
            valid_ports.map(str),
            invalid_int_ports.map(str),
            non_integer_port_strings(),
        ),
        path=st.text(max_size=20),
    )
    @example(host='not a host', port='999999', path='')
    def test_stdio_ignores_and_does_not_validate_bind_values(self, host, port, path):
        """The stdio transport never raises on bind values and uses network defaults."""
        config = parse_config(
            [
                _arg('--transport', 'stdio'),
                _arg('--host', host),
                _arg('--port', port),
                _arg('--path', path),
            ]
        )
        assert config.transport == 'stdio'
        assert config.host == consts.DEFAULT_HTTP_HOST
        assert config.port == consts.DEFAULT_HTTP_PORT
        assert config.path == consts.DEFAULT_HTTP_PATH
