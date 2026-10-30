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

"""Tests for the SSM module."""

import pytest
import shlex
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl import Ec2rlModule, validate_command
from awslabs.ec2rescue_for_linux_mcp_server.ssm import (
    _list_ssm_instances_sync,
    _run_ssm_command_sync,
    _unwrap_login_shell,
    _wrap_login_shell,
    list_ssm_instances,
    run_ssm_command,
)
from unittest.mock import MagicMock, patch


class TestListSsmInstancesSync:
    """Tests for _list_ssm_instances_sync."""

    def test_returns_instances(self, mock_session):
        """Should return merged SSM and EC2 instance data."""
        mock_ssm = MagicMock()
        mock_ec2 = MagicMock()
        mock_session.client.side_effect = lambda svc, **kw: {'ssm': mock_ssm, 'ec2': mock_ec2}[svc]

        mock_paginator = MagicMock()
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'i-1234567890abcdef0',
                        'PlatformType': 'Linux',
                        'PingStatus': 'Online',
                        'IPAddress': '10.0.0.1',
                    }
                ]
            }
        ]

        mock_ec2.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234567890abcdef0',
                            'InstanceType': 't3.micro',
                            'Tags': [{'Key': 'Name', 'Value': 'test-instance'}],
                        }
                    ]
                }
            ]
        }

        result = _list_ssm_instances_sync(mock_session)

        assert len(result) == 1
        assert result[0]['instance_id'] == 'i-1234567890abcdef0'
        assert result[0]['name'] == 'test-instance'
        assert result[0]['platform'] == 'Linux'
        assert result[0]['ping_status'] == 'Online'
        assert result[0]['ip_address'] == '10.0.0.1'
        assert result[0]['instance_type'] == 't3.micro'

    def test_returns_empty_when_no_instances(self, mock_session):
        """Should return empty list when no SSM instances found."""
        mock_ssm = MagicMock()
        mock_session.client.side_effect = lambda svc, **kw: {'ssm': mock_ssm}[svc]

        mock_paginator = MagicMock()
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'InstanceInformationList': []}]

        result = _list_ssm_instances_sync(mock_session)

        assert result == []

    def test_handles_instance_without_tags(self, mock_session):
        """Should handle instances without Name tag."""
        mock_ssm = MagicMock()
        mock_ec2 = MagicMock()
        mock_session.client.side_effect = lambda svc, **kw: {'ssm': mock_ssm, 'ec2': mock_ec2}[svc]

        mock_paginator = MagicMock()
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'InstanceInformationList': [
                    {
                        'InstanceId': 'i-abcdef1234567890',
                        'PlatformType': 'Linux',
                        'PingStatus': 'Online',
                        'IPAddress': '10.0.0.2',
                    }
                ]
            }
        ]

        mock_ec2.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-abcdef1234567890',
                            'InstanceType': 't3.small',
                        }
                    ]
                }
            ]
        }

        result = _list_ssm_instances_sync(mock_session)

        assert len(result) == 1
        assert result[0]['name'] == ''


class TestWrapLoginShellRoundTrip:
    """Round-trip tests for the login-shell wrapping layer.

    Commands are validated against the allowlist and then re-quoted into
    ``bash -l -c '...'`` for SSM. These tests pin the property that closes
    that gap: unwrapping the wrapped command with the shell's own lexical
    rules must recover exactly the validated input, as a single argument.
    """

    @pytest.fixture
    def registry(self):
        """Registry with modules exercising every wrapped command shape."""
        return {
            'top': Ec2rlModule(
                'top',
                'mod_out/run/top.log',
                required_args=['times'],
            ),
            'atopmod': Ec2rlModule(
                'atopmod',
                'mod_out/run/atopmod.log',
                package='atop',
                software='atop',
            ),
        }

    # Every allowlisted command shape that starts with a login-shell prefix
    # and therefore gets wrapped. The software-check form legitimately
    # contains single quotes, so quoting can never be assumed away.
    WRAPPED_ALLOWLISTED_COMMANDS = (
        'ec2rl run --only-modules=top --times=5',
        "ec2rl software-check | grep -i 'atop' || true",
        'which atop',
    )

    @pytest.mark.parametrize('command', WRAPPED_ALLOWLISTED_COMMANDS)
    def test_wrapped_output_round_trips_to_validated_command(self, command, registry):
        """Unwrapping the wrapped command recovers the exact validated input."""
        assert validate_command(command, registry) is True

        wrapped = _wrap_login_shell(command)

        assert wrapped != command  # it was actually wrapped
        recovered = _unwrap_login_shell(wrapped)
        assert recovered is not None, 'the wrapping must be reversible'
        assert recovered == command
        # The recovered command still passes the allowlist, so the string
        # sent to SSM corresponds to a validated command and nothing else.
        assert validate_command(recovered, registry) is True

    @pytest.mark.parametrize('command', WRAPPED_ALLOWLISTED_COMMANDS)
    def test_wrapped_output_is_single_shell_argument(self, command, registry):
        """The wrapped form tokenizes to exactly ``bash -l -c <command>``.

        Four tokens means the entire command travels as ONE argument to
        ``bash -c``; a fifth token would mean quoting broke and part of the
        command escaped into the outer shell.
        """
        tokens = shlex.split(_wrap_login_shell(command))
        assert tokens == ['bash', '-l', '-c', command]

    def test_wrapping_scheme_is_single_quotes_literally(self):
        """The wrapper emits exactly the POSIX single-quote scheme.

        The shlex round-trip verifies word-level containment but cannot
        distinguish single-quote from double-quote wrapping, because shlex
        models tokenization, not expansion. Under double quotes a shell
        would still expand ``$(...)`` and ``$VAR`` inside the -c argument,
        so the single-quote scheme (which suppresses ALL expansion) must be
        pinned byte-for-byte, not just via the round-trip property.
        """
        assert _wrap_login_shell('which atop') == "bash -l -c 'which atop'"
        assert (
            _wrap_login_shell("ec2rl software-check | grep -i 'atop' || true")
            == "bash -l -c 'ec2rl software-check | grep -i '\\''atop'\\'' || true'"
        )

    @pytest.mark.parametrize(
        'command',
        (
            'cat /var/tmp/ec2rl/2026-04-14T02_50_34.749027/mod_out/run/dmesg.log',
            # Quote-bearing log-read form: must pass through byte-identical,
            # not get re-quoted.
            "grep -hE '^(CONFIG_SMP)=' /var/tmp/ec2rl/2026-04-14T02_50_34.749027/mod_out/run/kernelconfig.log",
        ),
    )
    def test_non_login_shell_commands_pass_through_unwrapped(self, command):
        """Log-read commands are not wrapped and are returned unchanged."""
        assert _wrap_login_shell(command) == command

    @pytest.mark.parametrize(
        'command',
        (
            # Values that would break out of a single-quoted string if the
            # escaping mishandled them. validate_command rejects these long
            # before wrapping; this asserts the quoting layer contains them
            # anyway (defense in depth for the accepted-risk re-quoting).
            "ec2rl x'; id; '",
            "ec2rl a' && rm -rf / && 'b",
            'ec2rl "double" quotes',
            'ec2rl trailing-backslash\\',
            'ec2rl embedded\nnewline',
            "which a'b",
            # Expansion metacharacters: inert inside single quotes, and the
            # single-argument shape below proves they never reach the outer
            # shell level where they could expand.
            'ec2rl $(id)',
            'ec2rl `id`',
            'ec2rl $HOME/x',
        ),
    )
    def test_hostile_input_stays_one_argument(self, command):
        """Even hostile inputs are contained as a single bash -c argument."""
        wrapped = _wrap_login_shell(command)
        tokens = shlex.split(wrapped)
        assert tokens == ['bash', '-l', '-c', command]

    @pytest.mark.parametrize(
        'broken',
        (
            # What a future escaping bug would emit for "ec2rl x'; id; '":
            # the quote closes early and `id` escapes the -c argument.
            "bash -l -c 'ec2rl x'; id; ''",
            # Unbalanced quote (truncated wrapping).
            "bash -l -c 'ec2rl run",
            # Wrong wrapper shape entirely.
            "sh -c 'ec2rl run --only-modules=top --times=5'",
            # Missing -l: not the exact wrapper this module emits.
            "bash -c 'ec2rl run --only-modules=top --times=5'",
        ),
    )
    def test_unwrap_rejects_broken_wrappings(self, broken):
        """A wrapping that is not exactly ``bash -l -c <one-arg>`` yields None."""
        assert _unwrap_login_shell(broken) is None

    def test_equality_check_catches_breakout_glued_to_quote(self):
        """The equality comparison, not the token count, is load-bearing.

        For ``bash -l -c 'x';id`` (no space after the quote) a real shell
        treats ``;`` as a separator and runs ``id`` as a second command,
        but shlex -- which does not split on ``;`` -- merges it into one
        word, so the token count stays at four. The unwrap therefore
        returns ``x;id``, and containment is only proven because that does
        NOT equal the original command ``x``: the wrapper's equality check
        is what turns this into a failure.
        """
        assert _unwrap_login_shell("bash -l -c 'x';id") == 'x;id'

    def test_wrap_raises_instead_of_returning_unverified_command(self):
        """The round-trip guard blocks the return path when it fails.

        Simulates an escaping regression by forcing the unwrap side to
        disagree with the input: the wrapper must raise rather than hand the
        unverified string to SSM.
        """
        with patch(
            'awslabs.ec2rescue_for_linux_mcp_server.ssm._unwrap_login_shell',
            return_value=None,
        ):
            with pytest.raises(ValueError, match='round-trip'):
                _wrap_login_shell('ec2rl run --only-modules=top --times=5')


class TestRunSsmCommandSync:
    """Tests for _run_ssm_command_sync."""

    def test_sends_wrapped_command_to_ssm(self, mock_session):
        """The string handed to send_command is the wrapped, re-validated form.

        Pins the integration point: removing the wrapping call (or the
        round-trip guard inside it) would change what reaches SSM without
        any other test noticing.
        """
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-123'}}
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': '',
            'StandardErrorContent': '',
            'ResponseCode': 0,
        }

        command = "ec2rl software-check | grep -i 'atop' || true"
        _run_ssm_command_sync(mock_session, 'i-1234567890abcdef0', command)

        sent = mock_ssm.send_command.call_args.kwargs['Parameters']['commands']
        assert sent == [_wrap_login_shell(command)]
        assert shlex.split(sent[0]) == ['bash', '-l', '-c', command]

    def test_round_trip_failure_blocks_send(self, mock_session):
        """If the wrapping guard raises, nothing is sent to the instance."""
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        with patch(
            'awslabs.ec2rescue_for_linux_mcp_server.ssm._unwrap_login_shell',
            return_value=None,
        ):
            with pytest.raises(ValueError, match='round-trip'):
                _run_ssm_command_sync(
                    mock_session, 'i-1234567890abcdef0', 'ec2rl run --only-modules=dmesg'
                )

        mock_ssm.send_command.assert_not_called()

    def test_successful_command(self, mock_session):
        """Should return successful command result."""
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-123'}}
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Success',
            'StandardOutputContent': 'dmesg output here',
            'StandardErrorContent': '',
            'ResponseCode': 0,
        }

        result = _run_ssm_command_sync(
            mock_session, 'i-1234567890abcdef0', 'ec2rl run --only-modules=dmesg'
        )

        assert result['status'] == 'Success'
        assert result['stdout'] == 'dmesg output here'
        assert result['stderr'] == ''
        assert result['exit_code'] == 0

    def test_failed_command(self, mock_session):
        """Should return failed command result."""
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-456'}}
        mock_ssm.get_command_invocation.return_value = {
            'Status': 'Failed',
            'StandardOutputContent': '',
            'StandardErrorContent': 'command not found',
            'ResponseCode': 1,
        }

        result = _run_ssm_command_sync(
            mock_session, 'i-1234567890abcdef0', 'ec2rl run --only-modules=dmesg'
        )

        assert result['status'] == 'Failed'
        assert result['stderr'] == 'command not found'
        assert result['exit_code'] == 1

    @patch('awslabs.ec2rescue_for_linux_mcp_server.ssm.time')
    def test_retries_on_invocation_not_exist(self, mock_time, mock_session):
        """Should retry when InvocationDoesNotExist is raised."""
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-789'}}

        # Simulate monotonic time progression
        mock_time.monotonic.side_effect = [0, 1, 2, 3]
        mock_time.sleep = MagicMock()

        # First call raises InvocationDoesNotExist, second succeeds
        exc = mock_ssm.exceptions.InvocationDoesNotExist
        mock_ssm.get_command_invocation.side_effect = [
            exc('not yet'),
            {
                'Status': 'Success',
                'StandardOutputContent': 'output',
                'StandardErrorContent': '',
                'ResponseCode': 0,
            },
        ]

        result = _run_ssm_command_sync(
            mock_session,
            'i-1234567890abcdef0',
            'ec2rl run --only-modules=dmesg',
            poll_deadline_seconds=60,
            poll_interval=2.0,
        )

        assert result['status'] == 'Success'
        assert mock_time.sleep.called

    @patch('awslabs.ec2rescue_for_linux_mcp_server.ssm.time')
    def test_timeout(self, mock_time, mock_session):
        """Should return TimedOut when deadline is exceeded."""
        mock_ssm = MagicMock()
        mock_session.client.return_value = mock_ssm

        mock_ssm.send_command.return_value = {'Command': {'CommandId': 'cmd-timeout'}}

        # Simulate time exceeding deadline immediately
        mock_time.monotonic.side_effect = [0, 100]
        mock_time.sleep = MagicMock()

        result = _run_ssm_command_sync(
            mock_session,
            'i-1234567890abcdef0',
            'ec2rl run --only-modules=dmesg',
            poll_deadline_seconds=5,
        )

        assert result['status'] == 'TimedOut'
        assert result['exit_code'] == -1


class TestAsyncWrappers:
    """Tests for the async wrapper functions."""

    @pytest.mark.asyncio
    async def test_list_ssm_instances_async(self, mock_session):
        """list_ssm_instances should delegate to _list_ssm_instances_sync."""
        with patch(
            'awslabs.ec2rescue_for_linux_mcp_server.ssm._list_ssm_instances_sync',
            return_value=[{'instance_id': 'i-test'}],
        ) as mock_sync:
            result = await list_ssm_instances(mock_session)
            mock_sync.assert_called_once_with(mock_session)
            assert result == [{'instance_id': 'i-test'}]

    @pytest.mark.asyncio
    async def test_run_ssm_command_async(self, mock_session):
        """run_ssm_command should delegate to _run_ssm_command_sync."""
        with patch(
            'awslabs.ec2rescue_for_linux_mcp_server.ssm._run_ssm_command_sync',
            return_value={'status': 'Success', 'stdout': 'ok', 'stderr': '', 'exit_code': 0},
        ) as mock_sync:
            result = await run_ssm_command(mock_session, 'i-test', 'test cmd')
            mock_sync.assert_called_once_with(
                mock_session, 'i-test', 'test cmd', 60, 3600, 3600, 2.0
            )
            assert result['status'] == 'Success'
