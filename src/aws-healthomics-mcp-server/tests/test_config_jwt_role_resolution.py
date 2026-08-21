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

"""Unit tests for JWT session-duration parsing and single-resolver-source selection.

These tests exercise the pure decision logic in
``awslabs.aws_healthomics_mcp_server.config`` that supports customer-account role
assumption: parsing/validating ``MCP_JWT_SESSION_DURATION`` and selecting exactly
one of ``MCP_JWT_ROLE_ARN`` / ``MCP_JWT_ROLE_REGISTRY`` as the active
role-resolution source.

``parse_config`` reads real process environment variables via ``os.environ``, so
every test isolates the relevant ``MCP_*`` variables with monkeypatch and passes
``argv`` explicitly. Both the environment-variable and command-line paths are
covered, including CLI-over-environment precedence.

Test docstrings refer to requirements by name (never by number) per project
steering:
  - "Configuration surface and single-resolver selection" (Requirement 4)
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    TransportConfigError,
    parse_config,
)


# Environment variables that parse_config reads. Transport/network variables are
# cleared so the developer's shell environment never pollutes parsing, and the
# JWT role-resolution variables are cleared so each test controls them explicitly.
_MCP_ENV_VARS = (
    consts.MCP_TRANSPORT_ENV,
    consts.MCP_HOST_ENV,
    consts.MCP_PORT_ENV,
    consts.MCP_PATH_ENV,
    consts.MCP_MULTI_TENANT_ENV,
    consts.MCP_INBOUND_AUTH_ENV,
    consts.MCP_JWT_SESSION_DURATION_ENV,
    consts.MCP_JWT_ROLE_ARN_ENV,
    consts.MCP_JWT_ROLE_REGISTRY_ENV,
)

# Sample role-resolution source values used across the selection tests.
_SAMPLE_ROLE_ARN = 'arn:aws:iam::123456789012:role/CustomerRole'
_SAMPLE_ROLE_REGISTRY = 'file:///etc/aho/role-map.json'


@pytest.fixture(autouse=True)
def _clear_mcp_env(monkeypatch):
    """Ensure no MCP_* env vars leak into parsing for any test in this module."""
    for name in _MCP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _arg(flag, value):
    """Build a single ``--flag=value`` argv token (unambiguous for argparse)."""
    return '{}={}'.format(flag, value)


# ---------------------------------------------------------------------------
# Session-duration parsing
#
# Validates: Requirements Configuration surface and single-resolver selection
# ---------------------------------------------------------------------------


class TestJwtSessionDurationParsing:
    """Session-duration default, accepted range, and rejection behavior."""

    def test_unset_uses_default_session_duration(self):
        """An unset session duration defaults to consts.DEFAULT_JWT_SESSION_DURATION."""
        config = parse_config([])
        assert config.jwt_session_duration == consts.DEFAULT_JWT_SESSION_DURATION
        assert consts.DEFAULT_JWT_SESSION_DURATION == 3600

    def test_blank_cli_value_uses_default_session_duration(self):
        """A whitespace-only session-duration flag value falls back to the default."""
        config = parse_config([_arg('--jwt-session-duration', '   ')])
        assert config.jwt_session_duration == consts.DEFAULT_JWT_SESSION_DURATION

    @pytest.mark.parametrize(
        'value',
        [
            consts.JWT_SESSION_DURATION_MIN,  # 900 (inclusive lower bound)
            3600,  # a representative mid-range value
            consts.JWT_SESSION_DURATION_MAX,  # 43200 (inclusive upper bound)
        ],
    )
    def test_valid_cli_values_are_accepted(self, value):
        """Integers within the inclusive range 900..43200 are accepted via CLI."""
        config = parse_config([_arg('--jwt-session-duration', str(value))])
        assert config.jwt_session_duration == value

    def test_padded_valid_value_is_trimmed_and_accepted(self):
        """A valid value with surrounding whitespace is trimmed then accepted."""
        config = parse_config([_arg('--jwt-session-duration', '  1800  ')])
        assert config.jwt_session_duration == 1800

    @pytest.mark.parametrize(
        'value',
        [
            'not-an-integer',
            '90.0',  # non-integer numeric text
            '',  # handled as unset only when blank; non-blank invalid text below
        ],
    )
    def test_non_integer_cli_values_raise(self, value):
        """A non-integer session duration is rejected, except a blank value (default)."""
        if value.strip() == '':
            # A blank value is treated as unset and yields the default; it must not raise.
            config = parse_config([_arg('--jwt-session-duration', value)])
            assert config.jwt_session_duration == consts.DEFAULT_JWT_SESSION_DURATION
            return
        with pytest.raises(TransportConfigError) as exc_info:
            parse_config([_arg('--jwt-session-duration', value)])
        assert value in str(exc_info.value)

    @pytest.mark.parametrize(
        'value',
        [
            consts.JWT_SESSION_DURATION_MIN - 1,  # 899, just below the lower bound
            consts.JWT_SESSION_DURATION_MAX + 1,  # 43201, just above the upper bound
            0,
            -100,
        ],
    )
    def test_out_of_range_cli_values_raise(self, value):
        """Integers outside the inclusive range 900..43200 are rejected."""
        with pytest.raises(TransportConfigError) as exc_info:
            parse_config([_arg('--jwt-session-duration', str(value))])
        message = str(exc_info.value)
        # The descriptive error identifies the rejected value and the accepted range.
        assert str(value) in message
        assert str(consts.JWT_SESSION_DURATION_MIN) in message
        assert str(consts.JWT_SESSION_DURATION_MAX) in message

    def test_env_var_value_is_accepted(self, monkeypatch):
        """The environment-variable path also parses a valid session duration."""
        monkeypatch.setenv(consts.MCP_JWT_SESSION_DURATION_ENV, '7200')
        config = parse_config([])
        assert config.jwt_session_duration == 7200

    def test_env_var_out_of_range_value_raises(self, monkeypatch):
        """An out-of-range value supplied via environment variable is rejected."""
        monkeypatch.setenv(consts.MCP_JWT_SESSION_DURATION_ENV, '50')
        with pytest.raises(TransportConfigError):
            parse_config([])

    def test_cli_value_overrides_env_var(self, monkeypatch):
        """A CLI session-duration value wins over the environment variable."""
        monkeypatch.setenv(consts.MCP_JWT_SESSION_DURATION_ENV, '7200')
        config = parse_config([_arg('--jwt-session-duration', '1200')])
        assert config.jwt_session_duration == 1200


# ---------------------------------------------------------------------------
# Single-resolver-source selection
#
# Validates: Requirements Configuration surface and single-resolver selection
# ---------------------------------------------------------------------------


class TestRoleResolutionSourceSelection:
    """Exactly-one-source selection, both-source conflict, and neither-source cases."""

    def test_neither_source_disables_role_resolution(self):
        """When neither source is set, both selectors are None (resolution disabled)."""
        config = parse_config([])
        assert config.jwt_role_arn is None
        assert config.jwt_role_registry is None

    def test_role_arn_only_selects_static_source_via_cli(self):
        """Setting only the role ARN selects it and leaves the registry unset."""
        config = parse_config([_arg('--jwt-role-arn', _SAMPLE_ROLE_ARN)])
        assert config.jwt_role_arn == _SAMPLE_ROLE_ARN
        assert config.jwt_role_registry is None

    def test_role_registry_only_selects_registry_source_via_cli(self):
        """Setting only the registry selects it and leaves the role ARN unset."""
        config = parse_config([_arg('--jwt-role-registry', _SAMPLE_ROLE_REGISTRY)])
        assert config.jwt_role_registry == _SAMPLE_ROLE_REGISTRY
        assert config.jwt_role_arn is None

    def test_role_arn_only_selects_static_source_via_env(self, monkeypatch):
        """The environment-variable path also selects the static role-ARN source."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_ARN_ENV, _SAMPLE_ROLE_ARN)
        config = parse_config([])
        assert config.jwt_role_arn == _SAMPLE_ROLE_ARN
        assert config.jwt_role_registry is None

    def test_role_registry_only_selects_registry_source_via_env(self, monkeypatch):
        """The environment-variable path also selects the registry source."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_REGISTRY_ENV, _SAMPLE_ROLE_REGISTRY)
        config = parse_config([])
        assert config.jwt_role_registry == _SAMPLE_ROLE_REGISTRY
        assert config.jwt_role_arn is None

    def test_blank_sources_are_treated_as_unset(self, monkeypatch):
        """Whitespace-only source values are treated as unset (resolution disabled)."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_ARN_ENV, '   ')
        monkeypatch.setenv(consts.MCP_JWT_ROLE_REGISTRY_ENV, '\t')
        config = parse_config([])
        assert config.jwt_role_arn is None
        assert config.jwt_role_registry is None

    def test_selected_source_value_is_trimmed(self):
        """A selected source value is normalized by trimming surrounding whitespace."""
        config = parse_config([_arg('--jwt-role-arn', '  {}  '.format(_SAMPLE_ROLE_ARN))])
        assert config.jwt_role_arn == _SAMPLE_ROLE_ARN

    def test_both_sources_via_cli_raise_conflict(self):
        """Configuring both sources via CLI is rejected as a conflict."""
        with pytest.raises(TransportConfigError) as exc_info:
            parse_config(
                [
                    _arg('--jwt-role-arn', _SAMPLE_ROLE_ARN),
                    _arg('--jwt-role-registry', _SAMPLE_ROLE_REGISTRY),
                ]
            )
        message = str(exc_info.value)
        # The descriptive error names both conflicting sources.
        assert consts.MCP_JWT_ROLE_ARN_ENV in message
        assert consts.MCP_JWT_ROLE_REGISTRY_ENV in message

    def test_both_sources_via_env_raise_conflict(self, monkeypatch):
        """Configuring both sources via environment variables is rejected as a conflict."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_ARN_ENV, _SAMPLE_ROLE_ARN)
        monkeypatch.setenv(consts.MCP_JWT_ROLE_REGISTRY_ENV, _SAMPLE_ROLE_REGISTRY)
        with pytest.raises(TransportConfigError):
            parse_config([])

    def test_both_sources_mixed_cli_and_env_raise_conflict(self, monkeypatch):
        """A conflict is detected even when the two sources come from different origins."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_REGISTRY_ENV, _SAMPLE_ROLE_REGISTRY)
        with pytest.raises(TransportConfigError):
            parse_config([_arg('--jwt-role-arn', _SAMPLE_ROLE_ARN)])

    def test_cli_role_arn_overrides_env_role_arn(self, monkeypatch):
        """A CLI role-ARN value wins over the environment role-ARN value."""
        monkeypatch.setenv(consts.MCP_JWT_ROLE_ARN_ENV, 'arn:aws:iam::999999999999:role/EnvRole')
        config = parse_config([_arg('--jwt-role-arn', _SAMPLE_ROLE_ARN)])
        assert config.jwt_role_arn == _SAMPLE_ROLE_ARN
        assert config.jwt_role_registry is None
